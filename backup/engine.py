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
        Logs lines of text recieved until the end of stream
"""


import datetime
import glob
import logging
import os
import os.path
import subprocess
import time
import threading


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

    dest -- Path to the root of the backup directory.
    name -- Name of the backup (usually a host name).
    interval -- Name of the backup cycle (i. e. hourly, daily, etc.)
    index -- Index number of the individual snapshot in the cycle.

    The constructor's parameters are components to build the snapshot's path:
        /dest/name/interval.timestamp
    If index is None, the timestamp will be the current date and time.
    If index is a positive integer, existing snapshot directories of the same
    interval will be sorted and the one at the given index number will
    be represented.
    """

    _timeformat = "%Y-%m-%dT%H:%M"  # ISO 8601 format: yyyy-mm-ddThh:mm

    def __init__(self, dest, name, interval, index=None):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self._timestamp = None
        self.name = name
        self.interval = interval
        self.index = index
        self.dest = dest
        self.timestamp  # Raises IndexError if self.index is out of range.

    @property
    def path(self):
        path = os.path.join(
            self.dest,
            self.name,
            self.interval+"."+self.stimestamp
            )
        return path

    def get_status(self):
        # Status: blank, locked, dirty, complete, deleting, syncing
        pass

    @property
    def timestamp(self):
        """The date and time at which this backup snapshot was made."""
        if self._timestamp is None:
            if self.index is None:
                self._timestamp = datetime.datetime.now()
            else:
                # Try to find timestamp by index in existing directories.
                dirs = glob.glob(
                    "{}/{}/{}.*".format(self.dest, self.name, self.interval)
                    )
                dirs.sort()
                self._timestamp = datetime.datetime.strptime(
                    dirs[self.index].rsplit(".")[-1],  # raises IndexError.
                    self._timeformat
                    )
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value):
        assert isinstance(value, datetime.datetime), type(value)
        self._timestamp = value

    @property
    def stimestamp(self):
        """The timestamp as a ISO 8601 string."""
        return self.timestamp.strftime(self._timeformat)

    def delete(self):
        pass

    def acquire(self):
        pass

    def release(self):
        pass

    def __enter__(self):
        pass

    def __exit__(self):
        pass

    @staticmethod
    def from_path(path):
        """Create a snapshot object from a path name.

        The expected string format is:
            /path/to/backups/name/interval.yyyy-mm-ddThh:mm:ss
        """
        pass


# vim:cc=80
