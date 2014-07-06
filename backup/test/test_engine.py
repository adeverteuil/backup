import io
import threading
import unittest
import unittest.mock

from .basic_setup import BasicSetup
from ..engine import *


class TestEngine(BasicSetup):

    def setUp(self):
        super().setUp()
        self.minimal_options = {
            'rsync': "/usr/bin/rsync",
            'sourcedirs': self.testsource,
            'dest': self.testdest,
            }

    def test_init(self):
        r = rsyncWrapper(object())

    @unittest.mock.patch("subprocess.Popen")
    def test_sync_to_with_mock(self, mockpopen):
        mockpopen().stdout = io.StringIO()
        mockpopen().stderr = io.StringIO()
        mockpopen.reset_mock()
        self.assertFalse(mockpopen.called)
        r = rsyncWrapper(self.minimal_options)
        r.sync_to(self.testdest)
        r.wait()
        self.assertTrue(mockpopen.called)

    def test_args(self):
        r = rsyncWrapper(self.minimal_options)
        expected = ["/usr/bin/rsync", "--delete", "--archive",
            "--one-file-system", "--partial-dir=.rsync-partial",
            "--out-format=%l %f", self.testsource]
        self.assertEqual(r.args, expected)

        options = {'bwlimit': "30", 'sourcehost': "root@machine"}
        options.update(self.minimal_options)
        expected = expected[0:6]
        expected += ["--bwlimit=30", "root@machine:"+self.testsource]
        r = rsyncWrapper(options)
        self.assertEqual(r.args, expected)

    def test_sync_to(self):
        r = rsyncWrapper(self.minimal_options)
        r.sync_to(self.testdest)
        r.wait()
        r.close_pipes()
        self.assertListEqual(
            sorted(os.listdir(self.testsource)),
            sorted(os.listdir(self.testdest))
            )


class TestPipeLogger(BasicSetup):

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
        p1 = PipeLogger(stdout, method, threading.Event())
        p2 = PipeLogger(stderr, method, threading.Event())
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
        p1 = PipeLogger(stdout, logger.info, threading.Event())
        p2 = PipeLogger(stderr, logger.warning, threading.Event())
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

    def test_interrupt_event(self):
        r, w = os.pipe()
        e = threading.Event()
        m = unittest.mock.Mock()
        with open(r) as rf, open(w, "w") as wf:
            p = PipeLogger(rf, m, e)
            p.start()
            wf.write("1\n")
            wf.flush()
            # The thread is now blocked, waiting for the next line.
            e.set() # The thread will return before trying to read line 2.
            wf.write("2\n")
            wf.flush()
            p.join()
            self.assertEqual(rf.readline(), "2\n")


# vim:cc=80
