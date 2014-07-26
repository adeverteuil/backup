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


import configparser
import io
import threading
import unittest
import unittest.mock

from .basic_setup import BasicSetup
from ..engine import *


class TestEngine(BasicSetup):

    def setUp(self):
        super().setUp()
        self.minimal_options = configparser.ConfigParser(
            defaults={
                'rsync': "/usr/bin/rsync",
                'sourcedirs': self.testsource,
                'dest': self.testdest,
                'dry-run': "False",
                'configdir': self.configdir,
                'bw_warn': "0",
                'bw_err': "0",
                }
            )['DEFAULT']

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
        r = rsyncWrapper(self.minimal_options)
        r.sync_to(self.testdest, "/foo/link-dest")
        r.wait()
        self.assertListEqual(
            mockpopen.call_args[0][0],  # The first non-keyword argument.
            [
                "/usr/bin/rsync",
                "--link-dest=/foo/link-dest",
                "--delete",
                "--archive",
                "--one-file-system",
                "--partial-dir=.rsync-partial",
                "--verbose",
                "--out-format=#%l#%f",
                self.testsource,
                self.testdest,
                ]
            )

    def test_args(self):
        r = rsyncWrapper(self.minimal_options)
        expected = [
            "/usr/bin/rsync",
            "--delete",
            "--archive",
            "--one-file-system",
            "--partial-dir=.rsync-partial",
            "--verbose",
            "--out-format=#%l#%f",
            self.testsource,
            ]
        self.assertEqual(r.args, expected)

        options = {'bwlimit': "30", 'sourcehost': "root@machine"}
        self.minimal_options.update(options)
        expected = expected[0:7]
        expected += [
            "--bwlimit=30",
            "--rsh=ssh -o BatchMode=yes",
            "root@machine:"+self.testsource,
            ]
        r = rsyncWrapper(self.minimal_options)
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

    def test_dry_run(self):
        self.minimal_options['dry-run'] = "True"
        r = rsyncWrapper(self.minimal_options)
        self.assertIn("--dry-run", r.args)
        r.sync_to(self.testdest)
        r.wait()
        r.close_pipes()
        self.assertEqual(os.listdir(self.testdest), [])
        self.assertEqual(r.process.returncode, 0)

    def test_filterfile_and_excludefile(self):
        excludefile = os.path.join(self.configdir, "DEFAULT.exclude")
        filterfile = os.path.join(self.configdir, "DEFAULT.filter")
        open(excludefile, "w").close()
        open(filterfile, "w").close()
        r = rsyncWrapper(self.minimal_options)
        self.assertIn("--exclude-from={}".format(excludefile), r.args)
        self.assertIn( "--filter=merge {}".format(filterfile), r.args)

    @unittest.mock.patch("subprocess.Popen")
    @unittest.mock.patch("backup.engine.PipeLogger")
    def test_wait(self, mockpl, mockpopen):
        # Configure mocks.
        mockpopen().wait.side_effect = subprocess.TimeoutExpired("cmd", 1)
        mockpl().join.return_value = None
        mockpl().is_alive.return_value = False
        mockpl.reset_mock()
        mockpopen.reset_mock()
        # Test with subprocess timeout.
        r = rsyncWrapper(self.minimal_options)
        r.sync_to(self.testdest)
        with self.assertRaises(subprocess.TimeoutExpired):
            r.wait(1)
        self.assertFalse(mockpl().join.called)
        # Test with everything ending within timeout.
        mockpopen().wait.side_effect = None
        r.wait(1)
        self.assertEqual(
            mockpopen().wait.call_args,
            unittest.mock.call(timeout=1),
            )
        self.assertEqual(mockpl().join.call_count, 2)
        # Test with 1st logger stopped, 2nd logger times out.
        mockpl().is_alive.side_effect = [False, True]
        mockpl.reset_mock()
        with self.assertRaises(subprocess.TimeoutExpired):
            r.wait(1)
        self.assertEqual(mockpl().is_alive.call_count, 2)

    def test_bw_err_1(self):
        self.minimal_options['bw_err'] = "1"
        r = rsyncWrapper(self.minimal_options)
        with self.assertLogs(
            logging.getLogger("backup.engine.PipeLogger"),
            logging.ERROR,
            ):
            r.sync_to(self.testdest)
            r.wait()
            r.close_pipes()
        self.assertTrue(r.interrupt_event.is_set())

    @unittest.mock.patch('logging.getLogger')
    def test_bw_err_and_bw_warn_1000000(self, mocklogger):
        self.minimal_options['bw_err'] = "1000000"
        self.minimal_options['bw_warn'] = "1000000"
        r = rsyncWrapper(self.minimal_options)
        r.sync_to(self.testdest)
        r.wait()
        r.close_pipes()
        self.assertFalse(r.interrupt_event.is_set())
        self.assertFalse(mocklogger().warning.called)
        self.assertFalse(mocklogger().error.called)

    def test_bw_warn(self):
        self.minimal_options['bw_warn'] = "1"
        r = rsyncWrapper(self.minimal_options)
        with self.assertLogs(
            logging.getLogger("backup.engine.PipeLogger"),
            logging.WARNING,
            ):
            r.sync_to(self.testdest)
            r.wait()
            r.close_pipes()
        self.assertFalse(r.interrupt_event.is_set())


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

    files_output = (
        "Some intro text\n"
        "#2#2\n"
        "#12#12\n"
        "#3#3\n"
        "#1#1\n"
        "#4#4\n"
        "#6#6\n"
        "#7#7\n"
        "#8#8\n"
        "#11#11\n"
        "#9#9\n"
        "#5#5\n"
        "#10#10\n"
        "\n"
        "Footer\n"
        )

    def test_biggest_files(self):
        r, w = os.pipe()
        m = unittest.mock.Mock()
        m.is_set.return_value = False
        with open(r) as rf, open(w, "w") as wf:
            p = PipeLogger(rf, m, m)
            p.start()
            wf.write(self.files_output)
            wf.flush()
            wf.close()
            p.join()
        self.assertEqual(
            p.biggest_files,
            [
                (12, "12"),
                (11, "11"),
                (10, "10"),
                (9, "9"),
                (8, "8"),
                (7, "7"),
                (6, "6"),
                (5, "5"),
                (4, "4"),
                (3, "3"),
                ],
            )
        self.assertEqual(p.bytes_count, sum(range(1, 13)))

    def test_format_biggest_files(self):
        p = PipeLogger("spam", "spam", "eggs")
        p.biggest_files = [(i, str(i)) for i in range(5, 12)]
        self.assertEqual(
            p.format_biggest_files(),
            " 5 5\n 6 6\n 7 7\n 8 8\n 9 9\n10 10\n11 11",
            )

    def test_warn(self):
        r, w = os.pipe()
        m = unittest.mock.Mock()
        m.is_set.return_value = False
        with self.assertLogs(
            logging.getLogger("backup.engine.PipeLogger"),
            logging.WARNING,
            ) as logs:
            with open(r) as rf, open(w, "w") as wf:
                p = PipeLogger(rf, m, m)
                p.bw_warn = 10
                p.start()
                wf.write(self.files_output)
                wf.flush()
                wf.close()
                p.join()

    def test_err(self):
        r, w = os.pipe()
        m = unittest.mock.Mock()
        m.is_set.return_value = False
        with self.assertLogs(
            logging.getLogger("backup.engine.PipeLogger"),
            logging.ERROR,
            ) as logs:
            with open(r) as rf, open(w, "w") as wf:
                p = PipeLogger(rf, m, m)
                p.bw_err = 10
                p.start()
                wf.write(self.files_output)
                wf.flush()
                wf.close()
                p.join()
                self.assertEqual(rf.readline(), "#3#3\n")
        self.assertTrue(m.set.called)  # p.interrupt_event.set()
