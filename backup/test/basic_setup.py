#! /usr/bin/python3
#
#   This file is part of Alexandre's backup script
#   Copyright (C) 2010  Alexandre A. de Verteuil
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.


"""Shared testing module for Alexandre's backup script.

This module provides the class BasicSetup which is inherited by TestCases in
this package's other modules.
"""


import os
import shutil
import os.path
import tempfile
import unittest


# This is where temporary directories will live for a brief moment.
BASEDIR = os.getcwd()


class BasicSetup(unittest.TestCase):

    """Dummy TestCase with basic setup to be inherited."""

    def setUp(self):
        """Create temporary directories and files for testing purposes."""
        os.chdir(BASEDIR)
        self.__testsource = tempfile.mkdtemp(prefix="testsource_", dir=BASEDIR)
        self.__testdest = tempfile.mkdtemp(prefix="testdest_", dir=BASEDIR)
        self.__configfile = tempfile.mkstemp(
            prefix="testconfig_",
            dir=BASEDIR, text=True
            )[1]
        n = 20  # Create n files.
        for i in range(1, n+1):
            testfilepath = os.path.join(
                self.__testsource,
                "testfile_{}_of_{}".format(i, n),
                )
            with open(testfilepath, "w") as f:
                f.write("Test content {} of {}.".format(i, n))
        with open(self.__configfile, "w") as fh:
            fh.write(self.generate_config())

    def generate_config(self):
        """Dynamically create a testing configuration file.

        In the future, it might be necessary to tailor the contents according
        to the tests to conduct.
        """
        config = (
            "[backup]\n"
            "sourcedirs=" + self.__testsource + "\n"
            "dest=" + self.__testdest + "\n"
            "excludefile=/dev/null\n"
            "filterfile=/dev/null\n"
            "\n"
            "[daily]\n"
            "snapshotlimit=4\n"
            )
        return config

    @property
    def testsource(self):
        return self.__testsource

    @property
    def testdest(self):
        return self.__testdest

    @property
    def configfile(self):
        return self.__configfile

    def tearDown(self):
        shutil.rmtree(self.__testsource)
        self.__testsource = None

        shutil.rmtree(self.__testdest)
        self.__testdest = None

        os.remove(self.__configfile)
        self.__configfile = None


# vim:cc=80
