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


class TestSnapshot(BasicSetup):

    def test_init(self):
        now = datetime.datetime.now()
        s = Snapshot(self.testdest, "interval")
        self.assertIsNone(s.timestamp)
        self.assertTrue(s.path.startswith(self.testdest))
        self.assertEqual(s.interval, "interval")
        self.assertTrue(s.path.endswith(".0"), msg=s.path)

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
            s.status = SYNCING
            self.assertEqual(
                sorted(os.listdir(self.testdest)),
                [".interval.0.lock", ".interval.0.status", "interval.0"]
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

    def test_snapshot_from_index(self):
        os.chdir(self.testdest)
        for d in range(1, 5):
            os.mkdir("daily.2014-07-{:02}T00:00".format(d))
        # Create irrelevant directories to make sure they don't cause trouble.
        os.mkdir("hourly.2014-07-01T00:00")
        os.mkdir("some_random_directory")
        for d in range(4):
            s = Snapshot.from_index(self.testdest, "daily", d)
            self.assertEqual(s.timestamp, datetime.datetime(2014, 7, d+1))
        with self.assertRaises(IndexError):
            s = Snapshot.from_index(self.testdest, "daily", 4)
        s = Snapshot.from_index(self.testdest, "daily", -1)
        self.assertEqual(s.timestamp, datetime.datetime(2014, 7, 4))

    def test_snapshot_from_path(self):
        os.chdir(self.testdest)
        os.mkdir("daily.2014-07-01T00:00")
        os.mkdir("daily.0")
        s = Snapshot.from_path(os.path.join(self.testdest, "daily.0"))
        self.assertIsNone(s.timestamp)
        self.assertEqual(
            s.path,
            os.path.join(self.testdest, "daily.0")
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
        # VOID -> BLANK -> SYNCING -> COMPLETE -> DELETING -> VOID
        s = Snapshot(self.testdest, "interval")
        self.assertEqual(s.status, VOID)
        s.mkdir()
        self.assertEqual(s.status, BLANK)
        s.status = SYNCING
        self.assertEqual(s.status, SYNCING)
        s.status = COMPLETE
        self.assertEqual(s.status, COMPLETE)
        s.status = DELETING
        self.assertEqual(s.status, DELETING)
        s.status = DELETED
        # Changing the status of a DELETED snapshot should raise an exception.
        for status in (VOID, BLANK, SYNCING, COMPLETE, DELETING):
            with self.assertRaises(RuntimeError):
                s.status = status

    def test_delete(self):
        # Try to delete a VOID snapshot.
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
        #   2014-07-01 -- BLANK
        #   2014-07-02 -- SYNCING
        #   2014-07-03 -- COMPLETE
        #   2014-07-04 -- DELETING
        os.chdir(self.testdest)
        os.mkdir("daily.2014-07-01T00:00")
        os.mkdir("daily.2014-07-02T00:00")
        with open(".daily.2014-07-02T00:00.status", "w") as f:
            f.write(str(SYNCING))
        os.mkdir("daily.2014-07-03T00:00")
        open("daily.2014-07-03T00:00/a", "wb").close()
        os.mkdir("daily.2014-07-04T00:00")
        with open(".daily.2014-07-04T00:00.status", "w") as f:
            f.write(str(DELETING))

        snapshots = []
        for d in range(4):
            snapshots.append(Snapshot.from_index(self.testdest, "daily", d))
        self.assertEqual(snapshots[0].status, BLANK)
        self.assertEqual(snapshots[1].status, SYNCING)
        self.assertEqual(snapshots[2].status, COMPLETE)
        self.assertEqual(snapshots[3].status, DELETING)
