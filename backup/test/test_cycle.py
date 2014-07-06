import os
import glob

from .basic_setup import BasicSetup
from ..cycle import *
from ..locking import *
from ..config import *
from ..engine import *


class TestCycle(BasicSetup):

    def test_init(self):
        c = Cycle(self.testdest, "daily")
        c = Cycle(self.testdest, "hourly")

    def test_lock(self):
        c = Cycle(self.testdest, "daily")
        with c:
            self.assertEqual(os.listdir(self.testdest), [".daily.lock"])

    def test_create_new_snapshot(self):
        cycle = Cycle(self.testdest, "hourly")
        configuration = Configuration(argv=["-c", self.configfile], environ={})
        config = configuration.configure()
        rsync = rsyncWrapper(config['DEFAULT'])
        with cycle:
            cycle.create_new_snapshot(rsync)
        dest = glob.glob("{}/hourly.????-??-??T??:??".format(self.testdest))[0]
        self.assertEqual(
            sorted(os.listdir(self.testsource)),
            sorted(os.listdir(dest))
            )


# vim:cc=80
