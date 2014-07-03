import unittest
import unittest.mock

from .basic_setup import BasicSetup
from ..config import *


class TestBaseConfiguration(BasicSetup):

    def test_init(self):
        c = BaseConfiguration()

    def test_computed_attributes(self):
        c = BaseConfiguration()
        self.assertEqual(c['configfile'], "/etc/backup")

    def test_values(self):
        c = BaseConfiguration()
        # Check sane values for source directories list.
        for d in ("/sys", "/proc", "/dev"):
            self.assertNotIn(d, c['sources'])
        for d in ("/etc", "/home", "/usr"):
            self.assertIn(d, c['sources'])

    def test_dict_api(self):
        c = BaseConfiguration()
        options = {'a': "value_a", 'b': "value_b"}
        c._options = options.copy()
        self.assertDictEqual(dict(c), options)
        self.assertSequenceEqual(c.keys(), options.keys())
        self.assertTrue('a' in c)
        self.assertFalse('c' in c)
        self.assertTrue(list(c.items()))
        c['c'] = "value_c"
        self.assertEqual(c['c'], "value_c")


class TestEnvironmentReader(BasicSetup):

    def test_init(self):
        c = EnvironmentReader()
        self.assertIsInstance(c, BaseConfiguration)

    def test_empty_environ(self):
        c = EnvironmentReader(environ=dict())
        self.assertEqual(c['configfile'], "/etc/backup")

    def test_loaded_environ(self):
        environ = {
            'BACKUP_CONFIGFILE': self.configfile,
            }
        c = EnvironmentReader(environ=environ)
        self.assertEqual(c['configfile'], self.configfile)


class TestPartialArgumentParser(BasicSetup):

    def test_init(self):
        c = PartialArgumentParser()
        self.assertIsInstance(c, BaseConfiguration)
        self.assertIsInstance(c, EnvironmentReader)


class TestConfigParser(BasicSetup):

    def test_init(self):
        c = ConfigParser(configfile=self.configfile)
        self.assertIsInstance(c, BaseConfiguration)
        self.assertIsInstance(c, EnvironmentReader)
        self.assertIsInstance(c, PartialArgumentParser)


class TestArgumentParser(BasicSetup):

    def test_init(self):
        c = ArgumentParser()
        self.assertIsInstance(c, BaseConfiguration)
        self.assertIsInstance(c, EnvironmentReader)
        self.assertIsInstance(c, PartialArgumentParser)
        self.assertIsInstance(c, ConfigParser)


class TestConfiguration(BasicSetup):

    @unittest.skip
    def test_init(self):
        Configuration.environ = {
            'BACKUP_CONFIGFILE': self.configfile,
            }
        c = Configuration()
        self.assertIsInstance(c, BaseConfiguration)
        self.assertIsInstance(c, EnvironmentReader)
        self.assertIsInstance(c, PartialArgumentParser)
        self.assertIsInstance(c, ConfigParser)
        self.assertIsInstance(c, ArgumentParser)


# vim:cc=80
