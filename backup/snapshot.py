#   Alexandre's backup script
#   Copyright © 2014  Alexandre A. de Verteuil
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.


"""This module provides the Snapshot class.

Classes:
    Snapshot
        Abstraction object for a backup snapshot.

    Status
        Class of Enum type.
"""


import datetime
import enum
import errno
import glob
import logging
import os
import os.path
import shutil
import sys


from . import _logging
from .dry_run import if_not_dry_run
from .locking import Lockable


Status = enum.Enum(
    "Status",
    "void, blank, syncing, flagged, complete, deleting, deleted",
    )


class Snapshot(_logging.Logging, Lockable):

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
        mkdir -- void -> blank
        delete -- blank, syncing, flagged, complete, deleting -> deleted
        acquire
        release
        is_locked

    Status semantics:
        void -- Snapshot instance not yet existing on the filesystem.
        blank -- Snapshot is an empty directory.
        syncing -- Flagged as dirty while rsync is working. Can be resumed.
        flagged -- Bandwidth error triggered. Can be resumed with --force.
        complete -- Clean snapshot, safe for rsync to link-dest from.
        deleting -- In the process of removing the tree. Flagged as dirty.
        deleted -- Same as VOID, but cannot change status anymore.
    """

    _timeformat = "%Y-%m-%dT%H:%M"  # ISO 8601 format: yyyy-mm-ddThh:mm

    wip_suffix = "wip"

    @staticmethod
    def from_path(path):
        """Create a snapshot object from a path name.

        The expected string format is:
            /path/to/backups/name/interval.yyyy-mm-ddThh:mm:ss
        """
        dir = os.path.dirname(path)
        interval, stimestamp = os.path.basename(path).split(".")
        if stimestamp == Snapshot.wip_suffix:
            stimestamp = None
        return Snapshot(dir, interval, timestamp=stimestamp)

    @staticmethod
    def from_index(dir, interval, index):
        # Try to find timestamp by index in existing directories.
        dirs = glob.glob("{}/{}.*".format(dir, interval))
        dirs.sort(reverse=True)
        dirs[index]  # raises IndexError.
        if dirs[index].endswith("."+Snapshot.wip_suffix):
            timestamp = None
        else:
            timestamp = datetime.datetime.strptime(
                dirs[index].rsplit(".")[-1],
                Snapshot._timeformat
                )
        return Snapshot(dir, interval, timestamp)

    def __init__(self, dir, interval, timestamp=None, **kwargs):
        super().__init__(**kwargs)
        self.dir = dir
        self._interval = interval
        self._status = None
        if isinstance(timestamp, str):
            timestamp = datetime.datetime.strptime(timestamp, self._timeformat)
        self._timestamp = timestamp
        self.infer_status()

    def __repr__(self):
        name = self.__class__.__name__
        dir = self.dir
        interval = self.interval
        timestamp = repr(self.timestamp)
        return "{}({}, {}, {})".format(name, dir, interval, timestamp)

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
        oldpath = self.path
        oldlock = self.lockfile
        oldstatus = self.statusfile
        self._timestamp = value
        newpath = self.path
        newlock = self.lockfile
        newstatus = self.statusfile
        if os.access(oldlock, os.F_OK):
            self._logger.debug("Moving {} to {}.".format(oldlock, newlock))
            self._rename(oldlock, newlock)
        if os.access(oldpath, os.F_OK):
            self._logger.debug("Moving {} to {}.".format(oldpath, newpath))
            self._rename(oldpath, newpath)
        if os.access(oldstatus, os.F_OK):
            self._logger.debug("Moving {} to {}.".format(oldstatus, newstatus))
            self._rename(oldstatus, newstatus)
        self._logger.debug("timestamp set to {}.".format(self.stimestamp))

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        oldpath = self.path
        oldlock = self.lockfile
        oldstatus = self.statusfile
        self._interval = value
        newpath = self.path
        newlock = self.lockfile
        newstatus = self.statusfile
        if os.access(oldlock, os.F_OK):
            self._logger.debug("Moving {} to {}.".format(oldlock, newlock))
            self._rename(oldlock, newlock)
        if os.access(oldpath, os.F_OK):
            self._logger.debug("Moving {} to {}.".format(oldpath, newpath))
            self._rename(oldpath, newpath)
        if os.access(oldstatus, os.F_OK):
            self._logger.debug("Moving {} to {}.".format(oldstatus, newstatus))
            self._rename(oldstatus, newstatus)
        self._logger.debug("timestamp set to {}.".format(self.stimestamp))

    @if_not_dry_run
    def _rename(self, old, new):
        os.rename(old, new)

    @property
    def stimestamp(self):
        """The timestamp as a ISO 8601 string."""
        if self.timestamp is None:
            return self.wip_suffix
        else:
            return self.timestamp.strftime(self._timeformat)

    @property
    def status(self):
        """Status of this Snapshot.

        Normal flow:
            void -> blank -> syncing -> complete -> deleting -> deleted

        Error flow:
            void -> blank -> syncing -> flagged
                Resume with --force after verifying errors.
            flagged -> flagged -> complete -> deleting -> deleted
                Notice how the status does not change to syncing. This is to
                make sure every time this snapshot is resumed, --force will
                be required until it is complete.
        """
        self._status_file_check()
        return self._status

    @if_not_dry_run
    def _status_file_check(self):
        if self._status in (Status.syncing, Status.flagged, Status.deleting):
            with open(self.statusfile) as f:
                filestatus = Status(int(f.read()))
                assert filestatus is self._status, _status_lookup[filestatus]

    @status.setter
    def status(self, newstatus):
        """Setter for the status property.

        The status syncing, flagged and deleting create a statusfile
        which flags this snapshot as "dirty" and not safe for link-dest.
        """
        assert newstatus in Status, newstatus
        if self._status is not None:
            self._logger.debug(
                "Changing status from {} to {}.".format(
                    self._status.name,
                    newstatus.name
                    )
                )
        if self.status is Status.deleted and newstatus != self.status:
            msg = "Cannot change the status of a deleted snapshot."
            raise RuntimeError(msg)
        if self.status is Status.flagged and newstatus is Status.syncing:
            newstatus = Status.flagged
        if newstatus in (Status.syncing, Status.flagged, Status.deleting):
            self._create_file(self.statusfile, str(newstatus.value))
        else:
            try:
                self._unlink(self.statusfile)
            except FileNotFoundError:
                pass
        self._status = newstatus

    @if_not_dry_run
    def _create_file(self, path, content):
        with open(path, "w") as f:
            f.write(content)

    @if_not_dry_run
    def _unlink(self, path):
        os.unlink(path)

    def infer_status(self):
        """Infer status by analyzing snapshot directory and status file."""
        status = None
        if not os.access(self.path, os.F_OK):
            status = Status.void
        else:
            try:
                with open(self.statusfile) as f:
                    # This covers the SYNCING, FLAGGED and DELETING cases.
                    status = Status(int(f.read()))
            except FileNotFoundError:
                if os.listdir(self.path):
                    status = Status.complete
                else:
                    status = Status.blank
        assert status in Status
        self.status = status
        return status

    def mkdir(self):
        """Create the snapshot directory on the filesystem."""
        if self.status != Status.void:
            msg = "status is {}, must be void.".format(
                self.status.name,
                )
            raise RuntimeError(msg)
        self._mkdir(self.path)
        self._logger.debug("Created directory {}.".format(self.path))
        self.status = Status.blank  # void -> blank

    @if_not_dry_run
    def _mkdir(self, path):
        os.mkdir(self.path)

    def delete(self):
        if self.status is Status.void:
            raise RuntimeError("Deleting a void snapshot.")
        self._logger.info("Deleting {}.".format(self.path))
        self.status = Status.deleting
        self._rmtree(self.path)
        self.status = Status.deleted
        self._logger.info("Deletion complete.")

    @if_not_dry_run
    def _rmtree(self, path):
        shutil.rmtree(self.path)
