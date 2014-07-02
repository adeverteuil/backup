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


"""This module provides the Snapshot class.

Classes:
    Snapshot
        Abstraction object for a backup snapshot.

Constants indicating the status of a Snapshot instance:
    VOID
    BLANK
    SYNCING
    COMPLETE
    DELETING
    DELETED
"""


import datetime
import errno
import glob
import logging
import os
import os.path
import shutil
import sys


from .locking import Lockable


# Status constants for Snapshot objects.
VOID = 0
BLANK = 1
SYNCING = 2
COMPLETE = 3
DELETING = 4
DELETED = 5
_status_count = DELETED+1  # For "assert status in range(_status_count)".
# Status lookup for logging purposes.
_status_lookup = {
    None: "UNSET",
    0: "VOID",
    1: "BLANK",
    2: "SYNCING",
    3: "COMPLETE",
    4: "DELETING",
    5: "DELETED",
    }


class Snapshot(Lockable):

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

    Static methods:
        from_path(path)

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
        infer_status
        mkdir -- VOID -> BLANK
        delete -- BLANK, SYNCING, COMPLETE, DELETING -> DELETING
        acquire
        release
        is_locked
    """

    _timeformat = "%Y-%m-%dT%H:%M"  # ISO 8601 format: yyyy-mm-ddThh:mm

    @staticmethod
    def from_path(path):
        """Create a snapshot object from a path name.

        The expected string format is:
            /path/to/backups/name/interval.yyyy-mm-ddThh:mm:ss
        """
        pass

    def __init__(self, dir, interval, index=None):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.dir = dir
        self.interval = interval
        self._status = None
        if index is None:
            self._timestamp = datetime.datetime.now()
            self.index = 0
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
                dirs[index].rsplit(".")[-1],  # raises IndexError.
                self._timeformat
                )
            self.index = index
        self.infer_status()

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

    @property
    def timestamp(self):
        """The date and time at which this backup snapshot was made."""
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

        Normal flow:
            VOID -> BLANK -> SYNCING -> COMPLETE -> DELETING -> DELETED

        Return values (compare with module-level constants):
            VOID : Snapshot doesn't exist on the filesystem.
            BLANK : Directory exists and is empty.
            SYNCING : Synchronization is in progress.
            COMPLETE : Is safe to link-dest against.
            DELETING : In the process of being removed from the filesystem.
            DELETED : Snapshot is deleted and can no longer change status.
        """
        if self._status in (SYNCING, DELETING):
            with open(self.statusfile) as f:
                filestatus = int(f.read())
                assert filestatus == self._status, _status_lookup[filestatus]
        return self._status

    @status.setter
    def status(self, value):
        """Setter for the status property.

        The status SYNCING and DELETING create a statusfile which flags
        this snapshot as "dirty" and not safe for link-dest.
        """
        assert value in range(_status_count), value
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
            with open(self.statusfile, "w") as f:
                f.write(str(value))
        else:
            try:
                os.unlink(self.statusfile)
            except FileNotFoundError:
                pass
        self._status = value

    def infer_status(self):
        """Infer status by analyzing snapshot directory and status file."""
        status = None
        if not os.access(self.path, os.F_OK):
            status = VOID
        else:
            try:
                with open(self.statusfile) as f:
                    # This covers the DELETING and SYNCING cases.
                    status = int(f.read())
            except FileNotFoundError:
                if os.listdir(self.path):
                    status = COMPLETE
                else:
                    status = BLANK
        assert status in range(_status_count)
        self.status = status
        return status

    def mkdir(self):
        """Create the snapshot directory on the filesystem."""
        if self.status != VOID:
            msg = "status is {}, must be VOID.".format(self.status)
            raise RuntimeError(msg)
        os.mkdir(self.path)
        self._logger.debug("Created directory {}.".format(self.path))
        self.status = BLANK  # VOID -> BLANK

    def delete(self):
        if self.status == VOID:
            raise RuntimeError("Deleting a VOID snapshot.")
        self._logger.info("Deleting {}.".format(self.path))
        self.status = DELETING
        shutil.rmtree(self.path)
        self.status = DELETED
        self._logger.info("Deletion complete.")


# vim:cc=80