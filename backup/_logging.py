#   Alexandre's backup script
#   Copyright (C) 2010  Alexandre A. de Verteuil  {{{
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
#}}}

import io
import sys
import shutil
import logging
import logging.config

formatters = {
    'stream': logging.Formatter("%(name)s %(levelname)s: %(message)s"),
    'memory': logging.Formatter("%(message)s"),
    'file': logging.Formatter(
        "%(asctime)s  %(name)s %(levelname)s: %(message)s",
        ),
    }


handlers = {
    'stream': logging.StreamHandler(stream=sys.stdout),
    # Create an in-memory stream handler for output post-processing,
    # only adding it to the logger if option -q is used.
    'memory': logging.StreamHandler(stream=io.StringIO()),
    }
handlers['stream'].setFormatter(formatters['stream'])
handlers['stream'].setLevel(logging.INFO)
handlers['memory'].setFormatter(formatters['memory'])
handlers['memory'].setLevel(logging.INFO)

def config_logging():
    """Configures the root logger."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handlers['stream'])


def add_file_handler(filename):
    """Adds a FileHandler to the root logger.

    The file name for logging is only known at runtime.
    This function is called after the configuration of backup has been parsed.
    """
    logger = logging.getLogger()
    handlers['file'] = logging.FileHandler(filename)
    handlers['file'].setFormatter(formatters['file'])
    logger.addHandler(handlers['file'])


def move_log_file(dest):
    """Moves the log file to a new location."""
    h = handlers['file']
    h.acquire()
    try:
        h.close()
        shutil.move(h.baseFilename, dest)
        h.baseFilename = dest
    finally:
        h.release()

# vim:fdm=marker:fdl=0:fdc=3
