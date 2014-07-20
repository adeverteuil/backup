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


import os

from .basic_setup import BasicSetup
from ..dry_run import *


class TestWriter:

    """Dummy class to test the @modifies_filesystem decorator."""

    @if_not_dry_run
    def create_file(self, path):
        with open(path, "w") as f:
            f.write("Hello")

    @if_not_dry_run
    def create_file_with_alt(self, path):
        with open(path, "w") as f:
            f.write("Hello")

    @create_file_with_alt.alternative
    def create_file_with_alt(self, path):
        self.out = "Hello"


class Test_modifies_filesystem(BasicSetup):

    def test_function(self):
        func = if_not_dry_run(lambda a: a+1)
        self.assertEqual(func(1), 2)
        if_not_dry_run.dry_run = True
        self.assertIsNone(func(1))

    def test_class(self):
        # Test when dry_run==False
        spam = os.path.join(self.testdest, "spam")
        testwriter = TestWriter()
        testwriter.create_file(spam)
        self.assertTrue(os.access(spam, os.R_OK))
        with open(spam) as f:
            self.assertEqual(f.read(), "Hello")
        os.unlink(spam)
        # Test when dry_run==True
        # NOOP method
        if_not_dry_run.dry_run = True
        testwriter.create_file(spam)
        with self.assertRaises(OSError):
            open(spam)
        # Alternate method
        testwriter.create_file_with_alt(spam)
        self.assertEqual(testwriter.out, "Hello")
