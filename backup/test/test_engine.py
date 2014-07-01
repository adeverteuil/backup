import datetime
import io
import unittest
import unittest.mock

from .basic_setup import BasicSetup
from ..engine import *


class EngineSetup(BasicSetup):

    """Override BasicSetup's methods for added functionnality."""

    pass


class TestEngine(EngineSetup):

    def test_init(self):
        r = rsyncWrapper(object())

    @unittest.mock.patch("subprocess.Popen")
    def test_execute_with_mock(self, mockpopen):
        mockpopen().stdout = io.StringIO()
        mockpopen().stderr = io.StringIO()
        mockpopen.reset_mock()
        self.assertFalse(mockpopen.called)
        r = rsyncWrapper(object())
        r.execute()
        r.wait()
        self.assertTrue(mockpopen.called)


class TestPipeLogger(EngineSetup):

    def test_init(self):
        buffer = []
        def method(line):
            buffer.append(line)
        stream = io.StringIO()  # In-memory text stream.

    def test_using_stringio(self):
        buffer = []
        def method(line):
            buffer.append(line)
        stdout = io.StringIO("A\nB\n")
        stderr = io.StringIO("C\nD")
        p1 = PipeLogger(stdout, method)
        p2 = PipeLogger(stderr, method)
        p1.start()
        p2.start()
        p1.join()
        p2.join()
        self.assertEqual(sorted(buffer), ["A", "B", "C", "D"])

    def test_using_logger(self):
        logger = logging.getLogger("test_using_logger")
        logger.propagate = False
        stdout = io.StringIO("A\nB\n")
        stderr = io.StringIO("C\nD")
        p1 = PipeLogger(stdout, logger.info)
        p2 = PipeLogger(stderr, logger.warning)
        with self.assertLogs(logger, logging.INFO) as cm:
            p1.start()
            p1.join()
            self.assertEqual(
                cm.output,
                ["INFO:test_using_logger:A", "INFO:test_using_logger:B"]
                )
        with self.assertLogs(logger, logging.INFO) as cm:
            p2.start()
            p2.join()
            self.assertEqual(
                cm.output,
                ["WARNING:test_using_logger:C", "WARNING:test_using_logger:D"])


class TestSnapshot(EngineSetup):

    def test_init(self):
        now = datetime.datetime.now()
        s = Snapshot(self.testdest, "name", "interval")
        self.assertGreaterEqual(s.timestamp, now)
        self.assertTrue(s.path.startswith(self.testdest))
        self.assertEqual(s.interval, "interval")
        self.assertEqual(s.name, "name")

    def test_set_timestamp(self):
        t = datetime.datetime(2014, 7, 1, 10, 10)
        s = Snapshot(self.testdest, "name", "interval")
        s.timestamp = t
        self.assertEqual(s.timestamp, t)
        self.assertTrue(s.path.endswith("2014-07-01T10:10"), msg=s.path)

    def test_find_timestamp_by_index(self):
        os.chdir(self.testdest)
        os.mkdir("name")
        os.chdir("name")
        for d in range(1, 5):
            os.mkdir("daily.2014-07-{:02}T00:00".format(d))
        os.mkdir("hourly.2014-07-01T00:00")
        os.mkdir("some_random_directory")
        for d in range(4):
            s = Snapshot(self.testdest, "name", "daily", d)
            self.assertEqual(s.timestamp, datetime.datetime(2014, 7, d+1))
        with self.assertRaises(IndexError):
            s = Snapshot(self.testdest, "name", "daily", 4)

    def test_locking(self):
        # Setup
        s1 = Snapshot(self.testdest, "name", "interval")
        os.mkdir(os.path.join(self.testdest, "name"))
        s1.mkdir()
        s1.acquire()

        # Test existence of lock file.
        self.assertTrue(os.access(s1.lockfile, os.R_OK), msg=s1.lockfile)
        # Test acquiring the lock with another snapshot object.
        with self.assertRaises(RuntimeError):
            s2 = Snapshot(self.testdest, "name", "interval", 0)
            s2.acquire()
        # Attempt to acquire the lock a second time.
        with self.assertRaises(RuntimeError):
            s1.acquire()
        s2.release()
        # Test context manager.
        with s2:
            with self.assertRaises(RuntimeError):
                s1.acquire()
        # Test releasing an unlocked lock.
        with self.assertRaises(FileNotFoundError):
            s2.release()



# vim:cc=80
