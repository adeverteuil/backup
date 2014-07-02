from .basic_setup import BasicSetup
from ..cycle import *
from ..locking import *


class TestCycle(BasicSetup):

    def test_init(self):
        c = Cycle(self.testdest, "daily")
        c = Cycle(self.testdest, "hourly")


# vim:cc=80
