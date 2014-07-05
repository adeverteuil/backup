import unittest
import unittest.mock

from .basic_setup import BasicSetup
from ..config import *


class TestConfiguration(BasicSetup):

    def test_init(self):
        c = Configuration()

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


# vim:cc=80
