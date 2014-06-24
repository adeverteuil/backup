import unittest
from .basic_setup import BasicSetup
from ..config import *


class TestHardCodedConfiguration(BasicSetup):

    def test_init(self):
        c = HardCodedConfiguration()

    def test_computed_attributes(self):
        c = HardCodedConfiguration()
        self.assertEqual(c.configfile, "/etc/backup")

    def test_values(self):
        c = HardCodedConfiguration()
        # Check sane values for source directories list.
        for d in ("/sys", "/proc", "/dev"):
            self.assertNotIn(d, c.sources)
        for d in ("/etc", "/home", "/usr"):
            self.assertIn(d, c.sources)


class TestBackupEnvironmentCollector(BasicSetup):

    def test_init(self):
        a = BackupEnvironmentCollector()

    def test_empty_environ(self):
        BackupEnvironmentCollector.environ = dict()
        c = BackupEnvironmentCollector()
        self.assertEqual(c.configfile, "/etc/backup")

    def test_loaded_environ(self):
        BackupEnvironmentCollector.environ = {
            'BACKUP_CONFIGFILE': self.configfile,
            }
        c = BackupEnvironmentCollector()
        self.assertEqual(c.configfile, self.configfile)


class TestBackupConfigParser(BasicSetup):

    def test_init(self):
        c = BackupConfigParser(self.configfile)


class TestBackupArgumentParser(BasicSetup):

    def test_init(self):
        c = BackupArgumentParser()


class TestConfiguration(BasicSetup):

    def test_init(self):
        Configuration.environ = {
            'BACKUP_CONFIGFILE': self.configfile,
            }
        c = Configuration()


# vim:cc=80
