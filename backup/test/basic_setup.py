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


"""Shared testing module for Alexandre's backup script.

This module provides the class BasicSetup which is inherited by TestCases in
this package's other modules.
"""


import os
import os.path
import shutil
import tempfile
import unittest

from ..dry_run import if_dry_run_False


# This is where temporary test files and directories will live for a
# brief moment.
BASEDIR = os.getcwd()


class BasicSetup(unittest.TestCase):

    """Base TestCase with basic setup to be inherited."""

    def setUp(self):
        """Create temporary directories and files for unit tests."""
        os.chdir(BASEDIR)
        self.testsource = tempfile.mkdtemp(prefix="testsource_", dir=BASEDIR)
        # Append a / to testsource so that rsync will back up the contents
        # of it instead of testsource itself.
        self.testsource += "/"
        self.testdest = tempfile.mkdtemp(prefix="testdest_", dir=BASEDIR)
        self.configfile = tempfile.mkstemp(
            prefix="testconfig_",
            dir=BASEDIR, text=True
            )[1]
        n = 20  # Create n files.
        for i in range(1, n+1):
            testfilepath = os.path.join(
                self.testsource,
                "testfile_{:02}_of_{:02}".format(i, n),
                )
            with open(testfilepath, "w") as f:
                f.write("Test content {:02} of {:02}.".format(i, n))
        with open(self.configfile, "w") as fh:
            fh.write(self.generate_config())

    def generate_config(self):
        """Dynamically create a testing configuration file.

        In the future, it might be necessary to tailor the contents according
        to the tests to conduct.
        """
        config = (
            "[default]\n"
            "sourcedirs=" + self.testsource + "\n"
            "dest=" + self.testdest + "\n"
            "excludefile=/dev/null\n"
            "filterfile=/dev/null\n"
            "[host_1_1]\n"
            "hourlies = 1\n"
            "dailies = 1\n"
            "[host_0_1]\n"
            "hourlies = 0\n"
            "dailies = 1\n"
            "[host_1_0]\n"
            "hourlies = 1\n"
            "dailies = 0\n"
            )
        return config

    def tearDown(self):
        shutil.rmtree(self.testsource)
        self.testsource = None

        shutil.rmtree(self.testdest)
        self.testdest = None

        os.remove(self.configfile)
        self.configfile = None

        if_dry_run_False.dry_run = False
