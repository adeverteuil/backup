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


import unittest
import unittest.mock

import logging
import os

from .basic_setup import BasicSetup
from .._logging import *


class TestConfiguration(BasicSetup):

    def test_init_ManualFlushMemoryHandler(self):
        h = ManualFlushMemoryHandler(0)

    def test_log_events_and_keep_buffer_even_when_flushed(self):
        handler = ManualFlushMemoryHandler(0)
        mockhandler = unittest.mock.Mock()
        logger = logging.getLogger("test")
        logger.propagate = False
        logger.addHandler(handler)
        logger.debug("debug")
        logger.info("info")
        logger.warning("warning")
        logger.error("error")
        handler.setTarget(mockhandler)
        buffer_before_flush = handler.buffer.copy()
        handler.flush()
        self.assertEqual(len(handler.buffer), 4)
        self.assertEqual(handler.buffer, buffer_before_flush)

    def test_move_log_file(self):
        """Test the concept of moving the log file around."""
        file_a = os.path.join(self.testdest, "a")
        file_b = os.path.join(self.testdest, "b")
        logger = logging.getLogger("test")
        handler = logging.FileHandler(file_a)
        logger.addHandler(handler)
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
        # Actual test begins.
        logger.info("info")
        with open(file_a) as f:
            self.assertEqual(f.read(), "info\n")
        handler.acquire()
        try:
            handler.close()
        finally:
            handler.release()
        os.rename(file_a, file_b)
        handler.baseFilename = file_b
        logger.info("line 2")
        with open(file_b) as f:
            self.assertEqual(f.read(), "info\nline 2\n")

    def test_init_MovableFileHandler(self):
        h = MovableFileHandler("foo")
        h.close()

    def test_move_MovableFileHandler(self):
        # Preparation
        file1 = os.path.join(self.testdest, "file1")
        file2 = os.path.join(self.testdest, "file2")
        logger = logging.getLogger("test")
        logger.propagate = False
        h = MovableFileHandler(file1)
        logger.addHandler(h)
        # Pre-test
        logger.warning("line 1")
        self.assertEqual(os.listdir(self.testdest), ["file1"])
        with open(file1) as f:
            self.assertEqual(f.read(), "line 1\n")
        # Now the actual test
        h.move_to(file2)
        logger.warning("line 2")
        self.assertEqual(os.listdir(self.testdest), ["file2"])
        with open(file2) as f:
            self.assertEqual(f.read(), "line 1\nline 2\n")
        # Cleanup
        logger.removeHandler(h)
        h.close()
