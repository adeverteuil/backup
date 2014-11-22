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


"""This module provides the Cycle class.

Cycle
    Manages a group of Snapshots of the same interval.
"""


import datetime
import logging
import os.path
import stat
import subprocess

from . import *
from . import _logging
from .dry_run import if_not_dry_run
from .locking import Lockable
from .snapshot import *


TIMEDELTA = {
    'hourly': datetime.timedelta(hours=1),
    'daily': datetime.timedelta(days=1),
    'weekly': datetime.timedelta(days=7),
    }
DEFAULT_TIMEDELTA = TIMEDELTA['hourly']


class Cycle(Lockable, _logging.Logging):

    """Manages a group of Snapshots of the same interval."""

    def __init__(self, dir, interval, **kwargs):
        super().__init__(**kwargs)
        self.dir = dir
        self.interval = interval
        self.timedelta = TIMEDELTA.get(interval, DEFAULT_TIMEDELTA)
        self.snapshots = []
        self._build_snapshots_list()
        self.path = os.path.join(dir)
        self.lockfile = os.path.join(dir, "."+interval+".lock")
        self.overflow_cycle = None

    def _build_snapshots_list(self):
        self._logger.debug("Building {} snapshots list.".format(self.interval))
        dirs = sorted(glob.glob("{}/{}.*".format(self.dir, self.interval)))
        for dir in dirs:
            self._logger.debug("Inserting {}.".format(dir))
            self.snapshots.insert(0, Snapshot.from_path(dir))

    def get_linkdest(self):
        """Return the most recent complete Snapshot in its list, or None."""
        for snapshot in self.snapshots:
            if snapshot.status is Status.complete and not snapshot.is_locked():
                return snapshot
        return None

    def delete(self, index):
        """Delete the snapshot at the specified index."""
        with self.snapshots[index]:
            self._logger(
                "Deleting snapshot {}.".format(self.snapshots[index].path)
                )
            self.snapshots.pop(index).delete()

    def purge(self, maxnumber):
        """Delete snapshots exceeding maxnumber of complete backups.

        Parameters:
            maxnumber -- An int, the number of snapshots to keep.

        If the overflow_cycle attribute is not None, it must be a tuple
        of one Cycle instance and one integer. The Cycle instance's feed()
        method will be called with a list of snapshot overflowed from this
        purge. Then, its purge() method will be called with the integer
        as its maxnumber parameter.

        For example, if:
            overflow_cycle = (Cycle("dir", "daily"), 4)
        …then these calls will happen:
            # Possibly keep one or more snapshots and change their cycle name
            # and delete the unneeded snapshots.
            overflow_cycle[0].feed(snapshots)
            overflow_cycle[0].purge(overflow_cycle[1])
        """
        # Iterate over the snapshots list until we count maxnumber complete
        # backups. Delete snapshots beyond that index.
        self._logger.debug(
            "Purging {} cycle, keeping {} snapshots.".format(
                self.interval,
                maxnumber,
                )
            )
        complete_count = 0
        cutoff_index = 0
        for snapshot in self.snapshots:
            if complete_count >= maxnumber:
                break
            if snapshot.status is Status.complete:
                complete_count += 1
            cutoff_index += 1
        if self.overflow_cycle is not None:
            self._logger.debug(
                "Feeding {} snapshots into {} cycle.".format(
                    len(self.snapshots[cutoff_index:]),
                    self.overflow_cycle[0].interval,
                    )
                )
            self.overflow_cycle[0].feed(self.snapshots[cutoff_index:])
            self.overflow_cycle[0].purge(self.overflow_cycle[1])
        else:
            self._logger.debug(
                "No overflow cycle. Deleting {} snapshots".format(
                    len(self.snapshots[cutoff_index:]),
                    )
                )
            for snapshot in self.snapshots[cutoff_index:]:
                with snapshot:
                    snapshot.status = Status.deleting
                    snapshot.delete()
                    snapshot.status = Status.deleted
        del self.snapshots[cutoff_index:]

    def feed(self, snapshots):
        """Assimilate snapshots purged from another Cycle instance."""
        # Keep snapshots that are at least timedelta appart.
        inserted = 1
        while inserted == 1:
            inserted = 0
            for snapshot in reversed(snapshots):  # Iterate from old to recent.
                #last_snapshot_time = self.snapshots[0].timestamp
                #this_snapshot_time = snapshot.timestamp
                #difference = this_snapshot_time - last_snapshot_time
                if (snapshot.status is Status.complete and
                    len(self.snapshots) == 0 or
                    (
                     snapshot.timestamp - self.snapshots[0].timestamp >=
                     self.timedelta
                     )
                    ):
                    with snapshot:
                        snapshot.interval = self.interval
                        self.snapshots.insert(0, snapshot)
                        snapshots.remove(snapshot)
                    inserted = 1
                    break
        for snapshot in snapshots:
            with snapshot:
                snapshot.status = Status.deleting
                snapshot.delete()
                snapshot.status = Status.deleted

    def create_new_snapshot(self, engine, force=False):
        """Use rsyncWrapper to make a new snapshot.

        engine -- rsyncWrapper instance
        force -- Ignore flagged status
        """
        if (len(self.snapshots) > 0 and
            self.snapshots[0].status is Status.flagged and
            not force):
            raise FlaggedSnapshotError(
                "The last snapshot is FLAGGED; check for errors and run "
                "backup again manually with the --force argument."
                )
        elif (
            len(self.snapshots) > 0 and
            (
                self.snapshots[0].status is Status.syncing or
                self.snapshots[0].status is Status.flagged
                )
            ):
            # Resume an aborted sync.
            snapshot = self.snapshots[0]
            msg = "Resuming snapshot {}.".format(snapshot.path)
        else:
            snapshot = Snapshot(self.dir, self.interval)
            self.snapshots.insert(0, snapshot)
            msg = "Creating a new snapshot at {}.".format(snapshot.path)
            with snapshot:
                snapshot.mkdir()
                snapshot.status = Status.syncing
        self._logger.info(msg)
        with snapshot:
            # Get a clean snapshot to hardlink unchanged files to.
            linkdest = self.get_linkdest()
            try:
                if linkdest is not None:
                    linkdest.acquire()
                    linkdestpath = linkdest.path
                else:
                    linkdestpath = None
                engine.sync_to(snapshot.path, linkdestpath)
                while True:
                    try:
                        returncode = engine.wait(0.1)
                    except subprocess.TimeoutExpired:
                        continue  # Subprocess not finished.
                    else:
                        break  # Subprocess exited.
                    finally:
                        if engine.kill_switch_event.is_set() and not force:
                            # PipeLogger instance logged an error.
                            try:
                                engine.process.kill()
                            except OSError:
                                # Don't care if subprocess already exited.
                                self._logger.info(
                                    "rsync had time to finish anyways."
                                    )
                            finally:
                                snapshot.status = Status.flagged
                                raise FlaggedSnapshotError(
                                    "Bandwidth safety kill switch triggered."
                                    )
                if returncode > 0:
                    raise RuntimeError(
                        "Engine returned {} ({}).".format(
                            returncode,
                            RSYNC_E_CODES.get(returncode, "unknown error"),
                            )
                        )
            except KeyboardInterrupt:
                try:
                    engine.process.terminate()
                except OSError:
                    pass
                else:
                    self._logger.info("Waiting for subprocess to terminate.")
                    engine.wait()
                raise
            finally:
                engine.close_pipes()
                if linkdest is not None:
                    linkdest.release()
            snapshot.status = Status.complete
            snapshot.timestamp = datetime.datetime.now()
