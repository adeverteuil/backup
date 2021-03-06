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
import unittest.mock

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
        rsync = rsyncWrapper(config['default'])
        with cycle:
            cycle.create_new_snapshot(rsync)
        dest = glob.glob("{}/hourly.????-??-??T??:??".format(self.testdest))[0]
        self.assertEqual(
            sorted(os.listdir(self.testsource)),
            sorted(os.listdir(dest))
            )

    def test_resume_create_new_snapshot(self):
        # Simulate an aborted sync.
        os.chdir(self.testdest)
        os.mkdir("hourly.wip")
        with open(".hourly.wip.status", "w") as f:
            f.write(str(Status.syncing.value))
        inode = os.stat("hourly.wip").st_ino
        # Setup as usual.
        cycle = Cycle(self.testdest, "hourly")
        config= Configuration(
            argv=["-c", self.configfile],
            environ={},
            ).configure()
        rsync = rsyncWrapper(config['default'])
        # Go.
        with cycle:
            cycle.create_new_snapshot(rsync)
        # Check.
        self.assertEqual(len(os.listdir()), 1, msg=os.listdir())
        self.assertEqual(
            os.stat(os.listdir()[0]).st_ino,
            inode
            )

    @unittest.mock.patch("subprocess.Popen")
    def test_create_new_snapshot_trigger_bw_err(self, popenmock):
        # Setup the mock.
        popenmock().stdout.readline.side_effect = [
            "#10#file1\n", "#1#file2\n", "",
            ]
        popenmock().stderr.readline.return_value = ""
        popenmock().wait.side_effect = subprocess.TimeoutExpired("rsync", 0.1)
        # Setup the test.
        cycle = Cycle(self.testdest, "hourly")
        configuration = Configuration(argv=["-c", self.configfile], environ={})
        config = configuration.configure()
        config['default']['bw_err'] = "10"
        rsync = rsyncWrapper(config['default'])
        # Here is the test.
        with cycle, self.assertRaises(FlaggedSnapshotError):
            cycle.create_new_snapshot(rsync)
        self.assertTrue(popenmock().kill.called)
        self.assertEqual(cycle.snapshots[0].status, Status.flagged)

    def test_resume_FLAGGED_snapshot(self):
        # Simulate an aborted sync.
        os.chdir(self.testdest)
        os.mkdir("hourly.wip")
        with open(".hourly.wip.status", "w") as f:
            f.write(str(Status.flagged.value))
        # Setup as usual.
        cycle = Cycle(self.testdest, "hourly")
        config= Configuration(
            argv=["-c", self.configfile],
            environ={},
            ).configure()
        rsync = rsyncWrapper(config['default'])
        # Go.
        with cycle, self.assertRaises(FlaggedSnapshotError):
            cycle.create_new_snapshot(rsync)

    def test_build_snapshots_list(self):
        os.chdir(self.testdest)
        os.mkdir("daily.2014-07-01T00:00")
        os.mkdir("daily.2014-07-02T00:00")
        open("daily.2014-07-02T00:00/file", "w").close()
        cycle = Cycle(self.testdest, "daily")
        self.assertEqual(
            [os.path.basename(s.path) for s in cycle.snapshots],
            sorted(os.listdir(self.testdest), reverse=True)
            )
        self.assertEqual(
            [s.status for s in cycle.snapshots],
            [Status.complete, Status.blank]
            )
        cycle = Cycle(self.testdest, "hourly")
        self.assertEqual(cycle.snapshots, [])

    def test_get_linkdest(self):
        cycle = Cycle(self.testdest, "hourly")
        config = Configuration(
            argv=["-c", self.configfile],
            environ={},
            ).configure()
        rsync = rsyncWrapper(config['default'])
        cycle.create_new_snapshot(rsync)
        self.assertEqual(
            cycle.get_linkdest().path,
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

    @unittest.skip("Deprecated method.")
    def test_archive_from(self):
        cycle_h = Cycle(self.testdest, "hourly")
        cycle_d = Cycle(self.testdest, "daily")
        config = Configuration(
            argv=["-c", self.configfile],
            environ={},
            ).configure()
        rsync = rsyncWrapper(config['default'])
        cycle_h.create_new_snapshot(rsync)
        cycle_d.archive_from(cycle_h)
        self.assertEqual(
            sorted(os.listdir(cycle_h.snapshots[0].path)),
            sorted(os.listdir(cycle_d.snapshots[0].path))
            )
        for file in os.listdir(cycle_d.snapshots[0].path):
            filepath = os.path.join(cycle_d.snapshots[0].path, file)
            self.assertEqual(
                os.stat(filepath).st_nlink,
                2
                )

    def test_purge(self):
        os.chdir(self.testdest)
        for d in range(1, 5):
            os.mkdir("hourly.2014-07-{:02}T00:00".format(d))
            open("hourly.2014-07-{:02}T00:00/file".format(d), "w").close()
        c = Cycle(self.testdest, "hourly")
        self.assertEqual(len(c.snapshots), 4)
        c.purge(1)
        self.assertEqual(
            os.listdir(self.testdest),
            ["hourly.2014-07-04T00:00"],
            )

    def test_purge_nothing(self):
        c = Cycle(self.testdest, "hourly")
        c.purge(10)
        self.assertEqual(os.listdir(self.testdest), [])
        self.assertEqual(len(c.snapshots), 0)

    def test_purge_but_keep_all(self):
        os.chdir(self.testdest)
        for d in range(1, 5):
            os.mkdir("hourly.2014-07-{:02}T00:00".format(d))
            open("hourly.2014-07-{:02}T00:00/file".format(d), "w").close()
        c = Cycle(self.testdest, "hourly")
        self.assertEqual(len(c.snapshots), 4)
        c.purge(4)
        self.assertEqual(
            sorted(os.listdir(self.testdest)),
            ["hourly.2014-07-{:02}T00:00".format(d) for d in range(1, 5)],
            )

    def test_purge_with_incomplete_snapshots(self):
        os.chdir(self.testdest)
        for d in range(1, 5):
            os.mkdir("hourly.2014-07-{:02}T00:00".format(d))
            open("hourly.2014-07-{:02}T00:00/file".format(d), "w").close()
        # Mark 1 snapshot dirty.
        with open(".hourly.2014-07-03T00:00.status", "w") as f:
            f.write(str(Status.deleting.value))
        # Mark the most ancient snapshot dirty. It should be purged.
        with open(".hourly.2014-07-01T00:00.status", "w") as f:
            f.write(str(Status.deleting.value))
        c = Cycle(self.testdest, "hourly")
        c.purge(2)
        self.assertEqual(
            sorted(os.listdir(self.testdest)),
            [
                ".hourly.2014-07-03T00:00.status",
                "hourly.2014-07-02T00:00",
                "hourly.2014-07-03T00:00",
                "hourly.2014-07-04T00:00",
                ],
            )
        self.assertEqual(len(c.snapshots), 3)

    def test_purge_with_feed_to_cycle(self):
        # Preparation
        os.chdir(self.testdest)
        for h in range(1, 5):
            os.mkdir("hourly.2014-07-01T{:02}:00".format(h))
            open("hourly.2014-07-01T{:02}:00/file".format(h), "w").close()
        # Start of test
        c = Cycle(self.testdest, "hourly")
        c.overflow_cycle = (Cycle(self.testdest, "daily"), 1)
        c.purge(1)
        # End of test
        self.assertEqual(
            sorted(os.listdir(self.testdest)),
            [
                "daily.2014-07-01T01:00",
                "hourly.2014-07-01T04:00",
                ],
            )

    def test_feed_to_cycle_large_amount_of_snapshots(self):
        # Preparation
        os.chdir(self.testdest)
        for d in range(1, 5):
            for h in range(24):
                os.mkdir("hourly.2014-07-{:02}T{:02}:00".format(d, h))
                open(
                    "hourly.2014-07-{:02}T{:02}:00/file".format(d, h),
                    "w",
                    ).close()
        # Start test
        c = Cycle(self.testdest, "hourly")
        c.overflow_cycle = (Cycle(self.testdest, "daily"), 10)
        c.purge(1)
        # End of test
        self.assertEqual(
            sorted(os.listdir(self.testdest)),
            [
                "daily.2014-07-01T00:00",
                "daily.2014-07-02T00:00",
                "daily.2014-07-03T00:00",
                "daily.2014-07-04T00:00",
                "hourly.2014-07-04T23:00",
                ]
            )

    def test_feed_with_intermediary_empty_cycle(self):
        # Preparation
        os.chdir(self.testdest)
        for h in range(1, 5):
            os.mkdir("hourly.2014-07-01T{:02}:00".format(h))
            open("hourly.2014-07-01T{:02}:00/file".format(h), "w").close()
        # Start test
        hourly = Cycle(self.testdest, "hourly")
        daily = Cycle(self.testdest, "daily")
        weekly = Cycle(self.testdest, "weekly")
        hourly.overflow_cycle = (daily, 0)  # This is the catch.
        daily.overflow_cycle = (weekly, 10)
        hourly.purge(1)
        # End of test
        self.assertEqual(
            sorted(os.listdir(self.testdest)),
            [
                "hourly.2014-07-01T04:00",
                "weekly.2014-07-01T01:00",
                ]
            )

    def test_error_code_unknown(self):
        # Test the case when rsync exits with an error code that is not
        # in RSYNC_ERROR_CODES. It should just abort and log that an
        # an unknown error occurred.
        cycle = Cycle(self.testdest, "hourly")
        configuration = Configuration(argv=["-c", self.configfile], environ={})
        config = configuration.configure()
        rsync = rsyncWrapper(config['default'])
        rsync.wait = unittest.mock.Mock(return_value=255)
        rsync.sync_to = unittest.mock.Mock()
        with self.assertRaisesRegex(RuntimeError, r"255 \(unknown error\)"), \
                cycle:
            cycle.create_new_snapshot(rsync)
