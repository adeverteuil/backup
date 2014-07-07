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


import os
import glob

from .basic_setup import BasicSetup
from ..cycle import *
from ..locking import *
from ..config import *
from ..engine import *


class TestCycle(BasicSetup):

    def test_init(self):
        c = Cycle(self.testdest, "daily")
        c = Cycle(self.testdest, "hourly")

    def test_lock(self):
        c = Cycle(self.testdest, "daily")
        with c:
            self.assertEqual(os.listdir(self.testdest), [".daily.lock"])

    def test_create_new_snapshot(self):
        cycle = Cycle(self.testdest, "hourly")
        configuration = Configuration(argv=["-c", self.configfile], environ={})
        config = configuration.configure()
        rsync = rsyncWrapper(config['DEFAULT'])
        with cycle:
            cycle.create_new_snapshot(rsync)
        dest = glob.glob("{}/hourly.????-??-??T??:??".format(self.testdest))[0]
        self.assertEqual(
            sorted(os.listdir(self.testsource)),
            sorted(os.listdir(dest))
            )

    def test_build_snapshots_list(self):
        os.chdir(self.testdest)
        os.mkdir("daily.2014-07-01T00:00")
        os.mkdir("daily.2014-07-02T00:00")
        open("daily.2014-07-02T00:00/file", "w").close()
        cycle = Cycle(self.testdest, "daily")
        self.assertEqual(
            [os.path.basename(s.path) for s in cycle.snapshots],
            sorted(os.listdir(self.testdest))
            )
        self.assertEqual(
            [s.status for s in cycle.snapshots],
            [BLANK, COMPLETE]
            )
        cycle = Cycle(self.testdest, "hourly")
        self.assertEqual(cycle.snapshots, [])

    def test_get_linkdest(self):
        cycle = Cycle(self.testdest, "hourly")
        config = Configuration(
            argv=["-c", self.configfile],
            environ={},
            ).configure()
        rsync = rsyncWrapper(config['DEFAULT'])
        cycle.create_new_snapshot(rsync)
        self.assertEqual(
            cycle.get_linkdest(),
            os.path.join(self.testdest, os.listdir(self.testdest)[0])
            )
        # Set-back snapshot's timestamp so the next one will not raise OSError.
        cycle.snapshots[0].timestamp = datetime.datetime(2014, 7, 1)
        cycle.create_new_snapshot(rsync)
        # We check to make sure all files are hard-linked.
        for file in os.listdir(cycle.snapshots[0].path):
            filepath = os.path.join(cycle.snapshots[0].path, file)
            self.assertEqual(
                os.stat(filepath).st_nlink,
                2
                )
        # Again, same thing.
        cycle.snapshots[0].timestamp = datetime.datetime(2014, 7, 2)
        cycle.create_new_snapshot(rsync)
        for file in os.listdir(cycle.snapshots[0].path):
            filepath = os.path.join(cycle.snapshots[0].path, file)
            self.assertEqual(
                os.stat(filepath).st_nlink,
                3
                )
