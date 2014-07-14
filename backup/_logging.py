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


"""Logging configuration.

This module configures two logging handlers:

    1.  A stream handler that writes to stdout and stderr;
    2.  A memory handler that memorizes output for deferred writing to a
        log file who's path is known at runtime.

The following class is defined:
    Logging
        Subclass for any class that could use a _logger attribute.

There are also the following module level functions:
    add_file_handler():
        This function is called when the destination directory is known,
        which happens after parsing the configuration file and command
        line arguments.
    move_file_handler(dest):
        This function is called when a backup is completed and the log file
        can be added to the snapshot's directory.
"""


import io
import logging
import shutil
import sys


formatters = {
    'stream': logging.Formatter("%(name)s %(levelname)s: %(message)s"),
    'file': logging.Formatter(
        "%(asctime)s  %(name)s %(levelname)s: %(message)s",
        ),
    }


handlers = {
    'stream': logging.StreamHandler(stream=sys.stdout),
    # Create an in-memory stream handler for deferred writing into a log file.
    # A FileHandler will be created by the engine.Controller class. However,
    # it's file location is only known a runtime. This handler will hold
    # log record that will be written to the file when it is created.
    'memory': logging.StreamHandler(stream=io.StringIO()),
    }
handlers['stream'].setFormatter(formatters['stream'])
handlers['stream'].setLevel(logging.WARNING)
handlers['memory'].setFormatter(formatters['file'])
handlers['memory'].setLevel(logging.INFO)


def add_file_handler(filename):
    """Adds a FileHandler to the root logger.

    The file name for logging is only known at runtime.
    This function is called after the configuration of backup has been parsed.
    """
    logger = logging.getLogger()
    _handlers['file'] = logging.FileHandler(filename)
    _handlers['file'].setFormatter(_formatters['file'])
    logger.addHandler(_handlers['file'])


def move_log_file(dest):
    """Moves the log file to a new location.

    Closes the file handler, then changes its location according to dest.
    """
    h = _handlers['file']
    h.acquire()
    try:
        h.close()
        shutil.move(h.baseFilename, dest)
        h.baseFilename = dest
        # The new file will be automatically opened when a method to
        # handle a record is called.
    finally:
        h.release()


class Logging:

    """Subclass for any class that could use a _logger attribute."""

    def __init__(self, *args, **kwargs):
        """Define a _logger attribute in a uniform way across the program."""
        super().__init__(*args, **kwargs)
        # The name of the logger is the qualified name of the subclass.
        # For example, if the C class in the m.s module subclasses Logging,
        # Its _logger will be called "m.s.C".
        self._logger = logging.getLogger(
            self.__module__+"."+self.__class__.__name__
            )
