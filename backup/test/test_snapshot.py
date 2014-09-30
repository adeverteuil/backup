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


import datetime
import io
import queue
import threading
import unittest

from .basic_setup import BasicSetup
from ..snapshot import *
from ..locking import *
from ..dry_run import if_not_dry_run


class TestSnapshot(BasicSetup):

    def test_init(self):
        now = datetime.datetime.now()
        s = Snapshot(self.testdest, "interval")
        self.assertIsNone(s.timestamp)
        self.assertTrue(s.path.startswith(self.testdest))
        self.assertEqual(s.interval, "interval")
        self.assertTrue(s.path.endswith(".wip"), msg=s.path)

    def test_set_timestamp(self):
        t = datetime.datetime(2014, 7, 1, 10, 10)
        s = Snapshot(self.testdest, "interval")
        s.timestamp = t
        self.assertEqual(s.timestamp, t)
        self.assertTrue(s.path.endswith("2014-07-01T10:10"), msg=s.path)

        # Now test renaming directory.
        s = Snapshot(self.testdest, "interval")
        s.mkdir()
        with s:
            s.status = Status.syncing
            self.assertEqual(
                sorted(os.listdir(self.testdest)),
                [".interval.wip.lock", ".interval.wip.status", "interval.wip"]
                )
            s.timestamp = t
            self.assertEqual(
                sorted(os.listdir(self.testdest)),
                [
                    ".interval.2014-07-01T10:10.lock",
                    ".interval.2014-07-01T10:10.status",
                    "interval.2014-07-01T10:10",
                    ]
                )

    def test_set_interval(self):
        t = datetime.datetime(2014, 7, 1, 10, 10)
        s = Snapshot(self.testdest, "hourly")
        s.interval = "daily"
        s.timestamp = t
        self.assertEqual(s.interval, "daily")
        self.assertTrue(s.path.endswith("daily.2014-07-01T10:10"), msg=s.path)

        # Now test renaming directory.
        s = Snapshot(self.testdest, "hourly")
        s.mkdir()
        with s:
            s.timestamp = t
            self.assertEqual(
                sorted(os.listdir(self.testdest)),
                [".hourly.2014-07-01T10:10.lock", "hourly.2014-07-01T10:10"]
                )
            s.interval = "daily"
            self.assertEqual(
                sorted(os.listdir(self.testdest)),
                [
                    ".daily.2014-07-01T10:10.lock",
                    "daily.2014-07-01T10:10",
                    ]
                )

    def test_snapshot_from_index(self):
        os.chdir(self.testdest)
        for d in range(1, 5):
            os.mkdir("daily.2014-07-{:02}T00:00".format(d))
        # Create irrelevant directories to make sure they don't cause trouble.
        os.mkdir("hourly.2014-07-01T00:00")
        os.mkdir("some_random_directory")
        for d in range(4):
            s = Snapshot.from_index(self.testdest, "daily", d)
            self.assertEqual(s.timestamp, datetime.datetime(2014, 7, 4-d))
        with self.assertRaises(IndexError):
            s = Snapshot.from_index(self.testdest, "daily", 4)
        s = Snapshot.from_index(self.testdest, "daily", -1)
        self.assertEqual(s.timestamp, datetime.datetime(2014, 7, 1))

    def test_snapshot_from_path(self):
        os.chdir(self.testdest)
        os.mkdir("daily.2014-07-01T00:00")
        os.mkdir("daily.wip")
        s = Snapshot.from_path(os.path.join(self.testdest, "daily.wip"))
        self.assertIsNone(s.timestamp)
        self.assertEqual(
            s.path,
            os.path.join(self.testdest, "daily.wip")
            )
        s = Snapshot.from_path(
            os.path.join(self.testdest, "daily.2014-07-01T00:00")
            )
        self.assertEqual(s.timestamp, datetime.datetime(2014, 7, 1))
        self.assertEqual(
            s.path,
            os.path.join(self.testdest, "daily.2014-07-01T00:00")
            )

    def test_locking(self):
        # Setup
        s1 = Snapshot(self.testdest, "interval")
        s1.mkdir()
        s1.acquire()

        # Test existence of lock file.
        self.assertTrue(os.access(s1.lockfile, os.R_OK), msg=s1.lockfile)
        # Test acquiring the lock with another snapshot object.
        with self.assertRaises(AlreadyLocked):
            s2 = Snapshot.from_index(self.testdest, "interval", 0)
            s2.acquire()
        # Attempt to acquire the lock a second time from another thread.
        def grab_lock(lockable, q):
            try:
                lockable.acquire()
            except Exception as err:
                q.put(err)
            else:
                q.put(None)
        with self.assertRaises(AlreadyLocked):
            # do the test here.
            q = queue.Queue()
            t = threading.Thread(
                target=grab_lock,
                args=(s1, q),
                )
            t.start()
            err = q.get()
            if err is not None:
                raise err
        # Test breaking a lock.
        self.assertTrue(s2.is_locked())
        self.assertFalse(s2.i_am_locking())
        with self.assertRaises(NotMyLock):
            s2.release()
        s2.break_lock()
        self.assertFalse(s2.is_locked())
        # Test context manager.
        with s2:
            with self.assertRaises(AlreadyLocked):
                s1.acquire()
        # Test releasing an unlocked lock.
        with self.assertRaises(AlreadyUnlocked):
            s2.release()

    def test_status_cycle(self):
        # void -> blank -> syncing -> complete -> deleting -> void
        s = Snapshot(self.testdest, "interval")
        self.assertEqual(s.status, Status.void)
        s.mkdir()
        self.assertEqual(s.status, Status.blank)
        s.status = Status.syncing
        self.assertEqual(s.status, Status.syncing)
        s.status = Status.complete
        self.assertEqual(s.status, Status.complete)
        s.status = Status.deleting
        self.assertEqual(s.status, Status.deleting)
        s.status = Status.deleted
        # Changing the status of a deleted snapshot should raise an exception.
        statuses = "void blank syncing flagged complete deleting"
        for status in (statuses.split(" ")):
            with self.assertRaises(RuntimeError):
                s.status = Status[status]

    def test_status_flagged(self):
        s = Snapshot(self.testdest, "interval")
        s.mkdir()
        s.status = Status.syncing
        self.assertEqual(s.status, Status.syncing)
        s.status = Status.flagged
        self.assertEqual(s.status, Status.flagged)
        s.status = Status.syncing
        self.assertEqual(s.status, Status.flagged)
        s.status = Status.deleting
        self.assertEqual(s.status, Status.deleting)
        s.status = Status.deleted
        self.assertEqual(s.status, Status.deleted)
        with self.assertRaises(RuntimeError):
            s.status = Status.flagged

    def test_delete(self):
        # Try to delete a void snapshot.
        s = Snapshot(self.testdest, "interval")
        with self.assertRaises(RuntimeError):
            with s:
                s.delete()
        s.mkdir()
        with s:
            s.delete()

    def test_existing_dirty_snapshot(self):
        # If a snapshot is instantiated for which a dirty directory exists,
        # Snapshot should set the proper status.

        # Create 4 snapshot directories:
        #   2014-07-01 -- Status.blank
        #   2014-07-02 -- Status.syncing
        #   2014-07-03 -- Status.complete
        #   2014-07-04 -- Status.deleting
        os.chdir(self.testdest)
        os.mkdir("daily.2014-07-04T00:00")
        os.mkdir("daily.2014-07-03T00:00")
        with open(".daily.2014-07-03T00:00.status", "w") as f:
            f.write(str(Status.syncing.value))
        os.mkdir("daily.2014-07-02T00:00")
        open("daily.2014-07-02T00:00/a", "wb").close()
        os.mkdir("daily.2014-07-01T00:00")
        with open(".daily.2014-07-01T00:00.status", "w") as f:
            f.write(str(Status.deleting.value))

        snapshots = []
        for d in range(4):
            snapshots.append(Snapshot.from_index(self.testdest, "daily", d))
        self.assertEqual(snapshots[0].status, Status.blank)
        self.assertEqual(snapshots[1].status, Status.syncing)
        self.assertEqual(snapshots[2].status, Status.complete)
        self.assertEqual(snapshots[3].status, Status.deleting)

    def test_dry_run(self):
        # Directory must not be created.
        s = Snapshot(self.testdest, "interval", datetime.datetime(2014, 7, 1))
        if_not_dry_run.dry_run = True
        s.mkdir()
        s.status = Status.syncing
        self.assertEqual(os.listdir(self.testdest), [])
        # Reset
        if_not_dry_run.dry_run = False
        s = Snapshot(self.testdest, "interval", datetime.datetime(2014, 7, 1))
        s.mkdir()
        # Directory must not be deleted.
        if_not_dry_run.dry_run = True
        s.delete()
        self.assertEqual(
            os.listdir(self.testdest),
            ["interval.2014-07-01T00:00"],
            )
        # Reset
        s._status = Status.blank
        # Directory must not be renamed.
        s.timestamp = datetime.datetime(2014, 7, 2)
        self.assertEqual(
            os.listdir(self.testdest),
            ["interval.2014-07-01T00:00"],
            )
        # But the internal timestamp must still be changed.
        self.assertEqual(
            s.timestamp,
            datetime.datetime(2014, 7, 2),
            )
