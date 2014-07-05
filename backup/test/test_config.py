import unittest
import unittest.mock

from .basic_setup import BasicSetup
from ..config import *


class TestConfiguration(BasicSetup):

    def test_init(self):
        Configuration()
        Configuration(argv=["a"])
        Configuration(environ={'a': "b"})

    def test_defaults(self):
        c = Configuration()
        options = c.config['DEFAULT']
        self.assertEqual(options['configfile'], "/etc/backup")
        # Check sane values for source directories list.
        sources = options['sources'].split(":")
        for d in ("/sys", "/proc", "/dev"):
            self.assertNotIn(d, sources)
        for d in ("/etc", "/home", "/usr"):
            self.assertIn(d, sources)

    def test_parse_environ(self):
        # Empty environment
        c = Configuration(environ=dict())
        c.parse_environ()
        options = c.config['DEFAULT']
        self.assertEqual(options['configfile'], "/etc/backup")
        # Loaded environment
        environ = {
            'BACKUP_CONFIGFILE': self.configfile,
            }
        c = Configuration(environ=environ)
        c.parse_environ()
        options = c.config['DEFAULT']
        self.assertEqual(options['configfile'], self.configfile)

    def test_parse_args(self):
        c = Configuration(argv=[])
        c.parse_args()
        self.assertIsNotNone(c.args)
        self.assertEqual(c.args.host, [])
        c = Configuration(argv=["--verbose", "aaa"])
        c.parse_args()
        self.assertEqual(c.args.verbose, 1)
        self.assertEqual(c.args.host, ["aaa"])

    def test_do_early_logging_config(self):
        c = Configuration(argv=[])
        c.parse_args()
        with self.assertLogs("backup.config.Configuration", "DEBUG") as cm:
            c.do_early_logging_config()
        self.assertIn("Log level set to WARNING", cm.output[0])
        c.argv = ["-v"]
        c.parse_args()
        with self.assertLogs("backup.config.Configuration", "DEBUG") as cm:
            c.do_early_logging_config()
        self.assertIn("Log level set to INFO", cm.output[0])
        c.argv = ["-vv"]
        c.parse_args()
        with self.assertLogs("backup.config.Configuration", "DEBUG") as cm:
            c.do_early_logging_config()
        self.assertIn("Log level set to DEBUG", cm.output[0])


# vim:cc=80
