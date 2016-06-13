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

from .basic_setup import BasicSetup
from ..config import *
from ..dry_run import if_not_dry_run


class TestConfiguration(BasicSetup):

    def test_init(self):
        Configuration()
        Configuration(argv=["a"])
        Configuration(environ={'a': "b"})

    def test_defaults(self):
        c = Configuration()
        options = c.config.defaults()
        self.assertEqual(options['configfile'], "/etc/backup")
        # Check sane values for source directories list.
        sources = options['sourcedirs'].split(":")
        for d in ("/sys", "/proc", "/dev"):
            self.assertNotIn(d, sources)
        for d in ("/etc", "/home", "/usr"):
            self.assertIn(d, sources)

    def test_default_ssh_port(self):
        c = Configuration()
        options = c.config.defaults()
        self.assertEqual(options['ssh_port'], "22")

    def test_parse_environ(self):
        # Empty environment
        c = Configuration(environ=dict())
        c._parse_environ()
        options = c.config.defaults()
        self.assertEqual(options['configfile'], "/etc/backup")
        # Loaded environment
        environ = {
            'BACKUP_CONFIGFILE': self.configfile,
            }
        c = Configuration(environ=environ)
        c._parse_environ()
        options = c.config.defaults()
        self.assertEqual(options['configfile'], self.configfile)

    def test_parse_args(self):
        c = Configuration(argv=[])
        c._parse_args()
        self.assertIsNotNone(c.args)
        self.assertEqual(c.args.hosts, [])
        c = Configuration(argv=["--verbose", "aaa"])
        c._parse_args()
        self.assertEqual(c.args.verbose, 1)
        self.assertEqual(c.args.hosts, ["aaa"])

    def test_do_early_logging_config(self):
        c = Configuration(argv=[])
        c._parse_args()
        with self.assertLogs("backup.config.Configuration", "DEBUG") as cm:
            c._do_early_logging_config()
        self.assertIn("stdout log level set to WARNING", cm.output[0])
        c.argv = ["-v"]
        c._parse_args()
        with self.assertLogs("backup.config.Configuration", "DEBUG") as cm:
            c._do_early_logging_config()
        self.assertIn("stdout log level set to INFO", cm.output[0])
        c.argv = ["-vv"]
        c._parse_args()
        with self.assertLogs("backup.config.Configuration", "DEBUG") as cm:
            c._do_early_logging_config()
        self.assertIn("stdout log level set to DEBUG", cm.output[0])

    def test_read_config(self):
        c = Configuration(argv=[])
        c._parse_args()
        c.args.configfile = self.configfile
        c._read_config()
        self.assertEqual(c.config.defaults()['dest'], self.testdest)

    def test_merge_args_with_config(self):
        c = Configuration(argv=["--dry-run", "spamhost"])
        c._parse_args()
        c._merge_args_with_config()
        self.assertTrue(if_not_dry_run.dry_run)
        self.assertEqual(c.config.defaults()['dry-run'], "True")
        self.assertEqual(c.config.defaults()['hosts'], "spamhost")
        if_not_dry_run.dry_run = False
        c = Configuration(argv=[])
        c.config.add_section("eggs")
        c.config.add_section("penguin")
        c._parse_args()
        c._merge_args_with_config()
        self.assertFalse(if_not_dry_run.dry_run)
        self.assertEqual(c.config.defaults()['hosts'], "eggs penguin")
