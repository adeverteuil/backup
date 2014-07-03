#   Alexandre's backup script
#   Copyright (C) 2010  Alexandre A. de Verteuil
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.
#   If not, see <http://www.gnu.org/licenses/>.


"""Logging configuration.

This module configures three logging handlers:

    1.  A stream handler that writes to stdout and stderr;
    2.  A memory handler that memorizes output from the rsync subprocess for
        post-processing;
    3.  A file handler that writes to a log file.

Logging verbosity is controlled set according to the command line parameters.

There are also the following module level functions:
    add_file_handler():
        This function is called when the destination directory is known,
        which happens after parsing the configuration file and command
        line arguments.
    move_file_handler(dest):
        This function is called when a backup is completed and the log file
        can be added to the snapshot's directory.
"""


import argparse
import io
import logging
import sys
import shutil


_formatters = {
    'stream': logging.Formatter("%(name)s %(levelname)s: %(message)s"),
    'memory': logging.Formatter("%(message)s"),
    'file': logging.Formatter(
        "%(asctime)s  %(name)s %(levelname)s: %(message)s",
        ),
    }


_handlers = {
    'stream': logging.StreamHandler(stream=sys.stdout),
    # Create an in-memory stream handler for output post-processing,
    # only adding it to the logger if option -q is used.
    'memory': logging.StreamHandler(stream=io.StringIO()),
    }
_handlers['stream'].setFormatter(_formatters['stream'])
_handlers['stream'].setLevel(logging.WARNING)
_handlers['memory'].setFormatter(_formatters['memory'])
_handlers['memory'].setLevel(logging.INFO)


def config_logging():
    """Configures the root logger and adds handlers in early configuration."""
    # Create an argument parser that will only act on the verbosity option.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--verbose", "-v", action="count")
    options, extra_args = parser.parse_known_args()
    if options.verbose:
        if options.verbose >= 2:
            _handlers['stream'].setLevel(logging.DEBUG)
        elif options.verbose == 1:
            _handlers['stream'].setLevel(logging.INFO)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(_handlers['stream'])


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

# vim:cc=80
