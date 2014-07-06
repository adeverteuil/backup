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

from .locking import Lockable
from .snapshot import *


class Cycle(Lockable):

    """Manages a group of Snapshots of the same interval."""

    def __init__(self, dir, interval):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.dir = dir
        self.interval = interval
        self.snapshots = []
        self.path = os.path.join(dir)
        self.lockfile = os.path.join(dir, "."+interval+".lock")

    def _make_snapshots_list(self):
        for file in glob.glob("{}/{}.*".format(self.dir, self.interval)):
            pass

    @staticmethod
    def _cp_la(src, dst):
        """Emulate cp -la.

        Recursively copy a tree while hard-linking all files and preserving
        attributes.
        """
        # src and dst should be snapshots that I can lock maybe?
        pass

    def delete(self, index):
        """Delete the snapshot at the specified index."""
        with self.snapshots[index]:
            self.snapshots.pop(index).delete()

    def purge(self, maxnumber, mintime=None):
        """Delete snapshots exceeding maxnumber.

        Parameters:
            maxnumber -- An int, the number of snapshots to keep.
            mintime -- A datetime.timedelta, snapshots in amount exceeding
                       maxnumber will be kept if they are newer than
                       mintime ago.
        """
        pass

    def create_new_snapshot(self, engine):
        """Use rsyncWrapper to make a new snapshot."""
        snapshot = Snapshot(self.dir, self.interval)
        self.snapshots.insert(0, snapshot)
        msg = "Creating a new snapshot at {}.".format(snapshot.path)
        self._logger.info(msg)
        with snapshot:
            snapshot.mkdir()
            snapshot.status = SYNCING
            try:
                engine.sync_to(snapshot.path)
                engine.wait()
            except KeyboardInterrupt:
                engine.interrupt_event.set()
                raise
            finally:
                engine.close_pipes()
            snapshot.status = COMPLETE
            snapshot.timestamp = datetime.datetime.now()
