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


# vim:cc=80
