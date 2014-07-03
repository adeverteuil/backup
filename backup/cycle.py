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


"""This module provides the Cycle class.

Cycle
    Manages a group of Snapshots of the same interval.
"""


import logging
import os.path

from .locking import Lockable


class Cycle(Lockable):

    """Manages a group of Snapshots of the same interval."""

    def __init__(self, dir, interval):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.dir = dir
        self.interval = interval
        self.snapshots = []
        self.path = os.path.join(dir)
        self.lockfile = os.path.join(dir, "."+interval+".lock")

    @staticmethod
    def _cp_la(src, dst):
        """Emulate cp -la.

        Recursively copy a tree while hard-linking all files and preserving
        attributes.
        """
        # src and dst should be snapshots that I can lock maybe?

    def delete(self, index):
        """Delete the snapshot at the specified index."""
        with self.snapshots[index]:
            self.snapshots[index].delete()

    def purge(self, maxnumber, mintime=None):
        """Delete snapshots exceeding maxnumber.

        Parameters:
            maxnumber -- An int, the number of snapshots to keep.
            mintime -- A datetime.timedelta, snapshots in amount exceeding
                       maxnumber will be kept if they are newer than
                       mintime ago.
        """
        pass



# vim:cc=80