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
import stat

from .basic_setup import BasicSetup
from ..controller import *


class TestController(BasicSetup):

    def test_init(self):
        c = Controller(
            Configuration(argv=["-c", self.configfile], environ={}).configure()
            )

    def test_host_1_0(self):
        # 1 hourly, 0 dailies
        os.chdir(self.testdest)
        os.mkdir("host_1_0")
        c = Controller(
            Configuration(
                argv=["-c", self.configfile, "host_1_0"],
                environ={},
                ).configure()
            )
        c.run()
        self.assertEqual(os.listdir(self.testdest), ["host_1_0"])
        dir = os.listdir("host_1_0")[0]
        self.assertEqual(
            sorted(os.listdir(self.testsource)+["backup.log"]),
            sorted(os.listdir(os.path.join("host_1_0", dir))),
            )

    def test_dry_run(self):
        os.chdir(self.testdest)
        os.mkdir("host_1_0")
        # Make destination dir read-only and see if PermissionError is raised.
        readonly = stat.S_IXUSR | stat.S_IRUSR
        os.chmod(self.testdest, readonly)
        os.chmod("host_1_0", readonly)
        c = Controller(
            Configuration(
                argv=["-c", self.configfile, "--dry-run", "host_1_0"],
                environ={},
                ).configure()
            )
        try:
            c._run_host("host_1_0")
        finally:
            # Reset write permission for tearDown().
            os.chmod(self.testdest, readonly | stat.S_IWUSR)
        self.assertEqual(
            os.listdir(os.path.join(self.testdest, "host_1_0")),
            [],
            )
