#!/usr/bin/python3
#
#   Alexandre's backup script
#   Copyright (C) 2010  Alexandre A. de Verteuil
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.
#   If not, see <http://www.gnu.org/licenses/>.


"""Classes that actually perform the backups are declared within.

This module provides the following classes:

    rsyncWrapper
        Manages an rsync subprocess and threads that log its output streams.
    PipeLogger
        Logs lines of text recieved until the end of stream.
    Snapshot
        Abstraction object for a backup snapshot.
"""


import datetime
import errno
import glob
import logging
import os
import os.path
import subprocess
import sys
import time
import threading


# Status constants for Snapshot objects.
VOID = 0
BLANK = 1
SYNCING = 2
COMPLETE = 3
DELETING = 4
DELETED = 5
# Status lookup for logging purposes.
_status_lookup = {
    0: "VOID",
    1: "BLANK",
    2: "SYNCING",
    3: "COMPLETE",
    4: "DELETING",
    5: "DELETED",
    }


class rsyncWrapper:

    """Manages an rsync subprocess and threads that log its output streams."""

    def __init__(self, options):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self._options = options
        self.args = []

    def execute(self):
        """Invoke rsync and manage its outputs.

        This is where the parent class is initiated.
        """
        self._logger.debug(
            "Invoking rsync with arguments {}.".format(self.args)
            )
        #TODO use --out-format="%l %f" for tracking biggest files.
        # %l = length of file in bytes
        # %f = filename
        self.process = subprocess.Popen(
            self.args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        self.loggers = {
            'stdout': PipeLogger(
                self.process.stdout,
                logging.getLogger("rsync.stdout").info
                ),
            'stderr': PipeLogger(
                self.process.stderr,
                logging.getLogger("rsync.stderr").warning
                ),
            }
        for logger in self.loggers.values():
            logger.start()

    def wait(self, timeout=None):
        """Wait on the subprocess and both logger threads."""
        start = time.perf_counter()
        self.process.wait(timeout=timeout)
        for logger in self.loggers.values():
            timeleft = time.perf_counter() - start
            start = time.perf_counter()
            if timeout is not None:
                timeout = timeleft
            logger.join(timeout=timeout)
            if logger.is_alive():
                raise subprocess.TimeoutExpired


class PipeLogger(threading.Thread):

    """Logs lines of text read from a stream."""

    def __init__(self, stream, method, **kwargs):
        """PipeLogger constructor.

        Takes two positional arguments:
        stream -- a text stream (with a readline() method)
        method -- a function that takes a string argument

        Typically, stream is either the stdout or stderr stream of a
        child process. method is a method of a Logger object.
        Here is a use case:
            p = subprocess.Popen(...)
            pl = PipeLogger(
                p.stdout,
                logging.getLogger("stdout").info,
                ... additionnal threading.Thread keyword arguments go here ...
                )
        """
        # TODO: have a way of communicating KeybordInterrupt and such messages
        # with the main thread.
        self.stream = stream
        self.method = method
        super().__init__(**kwargs)

    def run(self):
        """Log lines from stream using method until empty read."""
        while True:
            line = self.stream.readline()
            if line:
                self.method(line.strip())
            else:
                return


class Snapshot:

    """Abstraction object for a backup snapshot.

    Parameters:
        dir -- Path to the directory where snapshots are located.
        interval -- Name of the backup cycle (i. e. hourly, daily, etc.)
        index -- Index number of the individual snapshot in the cycle.

    The constructor's parameters are components to build the snapshot's path:
        /dir/interval.timestamp
    If index is None, the timestamp will be the current date and time.
    If index is an integer, existing snapshot directories of the same
    interval will be sorted and the one at the given index number will
    be represented.

    Properties:
        timestamp
        stimestamp -- ISO 8601 string of the timestamp
        status
        path
        lockfile
        statusfile

    Attributes:
        dir
        interval
        index

    Methods:
        delete
        mkdir
    """

    _timeformat = "%Y-%m-%dT%H:%M"  # ISO 8601 format: yyyy-mm-ddThh:mm

    def __init__(self, dir, interval, index=None):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self._timestamp = None
        self._status = VOID
        self.interval = interval
        self.index = index
        self.dir = dir
        self.timestamp  # Raises IndexError if self.index is out of range.

    @property
    def path(self):
        path = os.path.join(
            self.dir,
            self.interval+"."+self.stimestamp
            )
        return path

    @property
    def lockfile(self):
        path = os.path.join(
            self.dir,
            "."+self.interval+"."+self.stimestamp+".lock"
            )
        return path

    @property
    def statusfile(self):
        path = os.path.join(
            self.dir,
            "."+self.interval+"."+self.stimestamp+".status"
            )
        return path

    def mkdir(self):
        """Create the snapshot directory on the filesystem."""
        if self.status != VOID:
            msg = "status is {}, must be VOID.".format(self.status)
            raise RuntimeError(msg)
        os.mkdir(self.path)
        self.status = BLANK  # VOID -> BLANK
        self._logger.debug("Created directory {}.".format(self.path))

    @property
    def timestamp(self):
        """The date and time at which this backup snapshot was made."""
        if self._timestamp is None:
            if self.index is None:
                self._timestamp = datetime.datetime.now()
                self.status = VOID
            else:
                # Try to find timestamp by index in existing directories.
                dirs = glob.glob(
                    "{}/{}.????-??-??T??:??".format(
                        self.dir,
                        self.interval
                        )
                    )
                dirs.sort()
                self._timestamp = datetime.datetime.strptime(
                    dirs[self.index].rsplit(".")[-1],  # raises IndexError.
                    self._timeformat
                    )
                self._status = COMPLETE
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        assert isinstance(value, datetime.datetime), type(value)
        self._timestamp = value
        self._logger.debug("timestamp set to {}.".format(self.stimestamp))

    @property
    def stimestamp(self):
        """The timestamp as a ISO 8601 string."""
        return self.timestamp.strftime(self._timeformat)

    @property
    def status(self):
        """Status of this Snapshot.

        VOID -> BLANK -> SYNCING -> COMPLETE -> DELETING -> DELETED

        VOID : Snapshot doesn't exist on the filesystem.
        BLANK : Directory exists and is empty.
        SYNCING : Synchronization is in progress.
        COMPLETE : Is safe to link-dest against.
        DELETING : In the process of being removed from the filesystem.
        DELETED : Snapshot is deleted and can no longer change status.
        """
        return self._status

    @status.setter
    def status(self, value):
        assert value in (VOID, BLANK, SYNCING, COMPLETE, DELETING, DELETED)
        self._logger.debug(
            "Changing status from {} to {}.".format(
                _status_lookup[self._status],
                _status_lookup[value]
                )
            )
        if self.status == DELETED and value != self.status:
            msg = "Cannot change the status of a deleted snapshot."
            raise RuntimeError(msg)
        if value in (SYNCING, DELETING):
            if not self.is_locked():
                msg = "Snapshot must be locked to enter this status."
                raise RuntimeError(msg)
            with open(self.statusfile, "w") as f:
                f.write(str(value))
        else:
            try:
                os.unlink(self.statusfile)
            except FileNotFoundError:
                pass
        self._status = value

    def delete(self):
        self._logger.info("Deleting {}.".format(self.path))
        # Mark snapshot as dirty, status as deleting, or something.
        with self:
            self.status = DELETING
            shutil.rmtree(self.path)
            self.status = VOID
        self._logger.info("Deletion complete.")

    def acquire(self):
        try:
            os.mkdir(self.lockfile)  # Atomic operation.
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.EEXIST:
                # Already locked.
                raise RuntimeError  #TODO raise a more specific error.
            else:
                raise

    def release(self):
        os.rmdir(self.lockfile)

    def is_locked(self):
        try:
            self.acquire()
            self.release()
            return False
        except RuntimeError:  #XXX Will be changed for a different exception.
            return True

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            # Leave the lock in place if an exception was raised.
            return False  # Exception will be re-raised in the calling context.
        else:
            self.release()

    @staticmethod
    def from_path(path):
        """Create a snapshot object from a path name.

        The expected string format is:
            /path/to/backups/name/interval.yyyy-mm-ddThh:mm:ss
        """
        pass


# vim:cc=80
