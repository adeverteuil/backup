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

This module configures three logging handlers:

    1.  A stream handler that writes to stdout and stderr;
    2.  A memory handler that memorizes output from the rsync subprocess for
        post-processing;
    3.  A file handler that writes to a log file.


There are also the following module level functions:
    add_file_handler():
        This function is called when the destination directory is known,
        which happens after parsing the configuration file and command
        line arguments.
    move_file_handler(dest):
        This function is called when a backup is completed and the log file
        can be added to the snapshot's directory.
"""


import logging
import shutil


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
