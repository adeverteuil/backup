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
from .controller import RSYNC_E_CODES
from .dry_run import if_not_dry_run
from .locking import Lockable
from .snapshot import *


class Cycle(Lockable, _logging.Logging):

    """Manages a group of Snapshots of the same interval."""

    def __init__(self, dir, interval, **kwargs):
        super().__init__(**kwargs)
        self.dir = dir
        self.interval = interval
        self.snapshots = []
        self._build_snapshots_list()
        self.path = os.path.join(dir)
        self.lockfile = os.path.join(dir, "."+interval+".lock")

    def _build_snapshots_list(self):
        self._logger.debug("Building {} snapshots list.".format(self.interval))
        dirs = sorted(glob.glob("{}/{}.*".format(self.dir, self.interval)))
        for dir in dirs:
            self._logger.debug("Inserting {}.".format(dir))
            self.snapshots.insert(0, Snapshot.from_path(dir))

    @if_not_dry_run
    def _cp_la(self, src, dst):
        """Emulate cp -la.

        Recursively copy a tree while hard-linking all files and preserving
        attributes.
        """
        src = os.path.normpath(src)
        dst = os.path.normpath(dst)
        self._logger.info("Hard-linking {} to {}.".format(src, dst))
        for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
            dirpath_dst = os.path.join(dst, os.path.relpath(dirpath, src))
            for dir in dirnames:
                if stat.S_ISLNK(os.lstat(os.path.join(dirpath, dir)).st_mode):
                    # Source directory is a symbolic link.
                    # Copy the symlink instead of creating a new directory.
                    shutil.copy2(os.path.join(dirpath, dir),
                                 os.path.join(dirpath_dst, dir),
                                 follow_symlinks=False)
                else:
                    os.mkdir(os.path.join(dirpath_dst, dir))
                    uid = os.stat(os.path.join(dirpath, dir)).st_uid
                    gid = os.stat(os.path.join(dirpath, dir)).st_gid
                    os.chown(os.path.join(dirpath_dst, dir), uid, gid)
                    shutil.copystat(os.path.join(dirpath, dir),
                                    os.path.join(dirpath_dst, dir))
            for file in filenames:
                os.link(os.path.join(dirpath, file),
                        os.path.join(dirpath_dst, file))
        shutil.copystat(src, dst)

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
        """
        # Iterate over the snapshots list until we count maxnumber complete
        # backups. Delete snapshots beyond that index.
        complete_count = 0
        cutoff_index = 0
        for snapshot in self.snapshots:
            if snapshot.status is Status.complete:
                complete_count += 1
            cutoff_index += 1
            if complete_count >= maxnumber:
                break
        for snapshot in self.snapshots[cutoff_index:]:
            with snapshot:
                snapshot.status = Status.deleting
                snapshot.delete()
                snapshot.status = Status.deleted
        del self.snapshots[cutoff_index:]

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
                            RSYNC_E_CODES[returncode],
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

    def archive_from(self, cycle):
        """Copy a snapshot from another cycle.

        This method copies the most recent complete snapshot from cycle into
        itself. It copies the directory hierarchy while hard-linking all files.

        Let's say there is a daily and an hourly backup. The hourly cycle will
        be updated with the create_new_snapshot method while the daily cycle
        will be updated with the archive_from method.
        """
        snapshot = Snapshot(self.dir, self.interval)
        origin = cycle.get_linkdest()
        if origin is None:
            msg = "No {} snapshot to copy was found in {}.".format(
                cycle.interval,
                cycle.dir,
                )
            self._logger.info(msg)
            return
        if (len(self.snapshots) > 0 and
            origin.timestamp <= self.snapshots[0].timestamp):
            msg = "{} backup is as recent as {}.".format(
                self.interval,
                cycle.interval,
                )
            self._logger.info(msg)
            return
        msg = "Copying snapshot from {} cycle to {} cycle.".format(
            cycle.interval,
            self.interval,
            )
        self._logger.debug(msg)
        self.snapshots.insert(0, snapshot)
        with snapshot, origin:
            snapshot.mkdir()
            snapshot.status = Status.syncing
            self._cp_la(origin.path, snapshot.path)
            snapshot.status = Status.complete
            snapshot.timestamp = origin.timestamp
