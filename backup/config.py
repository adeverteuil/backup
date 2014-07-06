#!/usr/bin/python3
#
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


"""Get configuration options.

This module defines the Configuration class which handles all the configuration
and parsing tasks.

Option values are the first ones found in the following places:

    Command line arguments
    Configuration files
    Environment variables
    Hard coded default values

The Configuration instance configures two logging handlers:

    1.  A stream handler that writes to stdout and stderr;
    2.  A memory handler that memorizes output from the rsync subprocess for
        post-processing;
"""


import argparse
import atexit
import collections.abc
import configparser
import io
import logging
import os
import os.path
import sys

from .version import __version__


def _make_sources_list():
    """Return a default list of directories to back up.

    Start with the list of direct children of "/".
    Remove virtual filesystems from the list.
    """
    sources = os.listdir('/')
    for d in ("sys", "proc", "dev", "lost+found"):
        try:
            sources.remove(d)
        except ValueError:
            continue
    return ":".join(sorted(["/"+s for s in sources]))


DEFAULTS = {
    'sources': _make_sources_list(),
    'configfile': "/etc/backup",
    'dest': "/root/var/backups",
    'rsync': "/usr/bin/rsync",
    }


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
handlers['stream'].setLevel(logging.WARNING)
handlers['memory'].setFormatter(formatters['memory'])
handlers['memory'].setLevel(logging.INFO)


class Configuration:

    """Collects options from command line arguments and configuration files."""

    def __init__(self, argv=None, environ=None):
        """Instantiates ConfigParser with defaults and ArgumentParser.

        Parameters:
        argv -- If not None, will be parsed instead of sys.argv[1:].
        environ -- If not None, will be used insted of os.environ.
        """
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.argv = argv if argv is not None else sys.argv[1:]
        self.args = None  # This will hold the return value of parse_args().
        self.environ = environ if environ is not None else os.environ
        self.config = configparser.ConfigParser(defaults=DEFAULTS)
        self.argumentparser = argparse.ArgumentParser(add_help=False)
        self._configure_argumentparser()

    def _configure_argumentparser(self):
        parser = self.argumentparser
        parser.add_argument("--help", "-h",
            # The only change from the default is a capital S and a full stop.
            action="help",
            help="Show this help and exit.",
            )
        parser.add_argument("--version",
            action="version",
            version="%(prog)s {}".format(__version__),
            help="Show program's version number and exit.",
            )
        parser.add_argument("--verbose", "-v",
            action="count",
            help=("Set verbosity to INFO. This option may be repeated once for"
                  " verbosity level DEBUG."),
            )
        parser.add_argument("--configfile", "-c",
                            help="Use this file rather than the default.",
                            )
        parser.add_argument("host",
            nargs="*",
            help=("List of hosts to do a backup of. Hosts are defined through "
                  "configuration files in /etc/backup.d. If no hosts are "
                  "specified, all defined hosts are backed up sequentially."),
            )

    def configure(self):
        """Executes all the configurations tasks in the right order.

        Returns the ConfigParser object with all the collected options.
        """
        self.parse_environ()
        self.parse_args()
        self.do_early_logging_config()
        self.read_config()
        self.process_remaining_args()
        return self.config

    def parse_environ(self):
        """Overrides some defaults with environment variables."""
        if 'BACKUP_CONFIGFILE' in self.environ:
            self.config['DEFAULT']['configfile'] = \
                self.environ['BACKUP_CONFIGFILE']

    def parse_args(self):
        """Adds arguments to the ArgumentParser instance and parses args."""
        self.args = self.argumentparser.parse_args(self.argv)

    def do_early_logging_config(self):
        """Configures early logging according to the --verbose option."""
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        # The handler will be configured, but not added to the Logger. This
        # must be done in backup.controller.main() so that logging will not
        # interfere with unit tests.
        #logger.addHandler(_handlers['stream'])
        atexit.register(logging.shutdown)
        lvl = "WARNING"
        if self.args.verbose:
            if self.args.verbose >= 2:
                handlers['stream'].setLevel(logging.DEBUG)
                lvl = "DEBUG"
            elif self.args.verbose == 1:
                handlers['stream'].setLevel(logging.INFO)
                lvl = "INFO"
        self._logger.debug("Log level set to {}".format(lvl))

    def read_config(self):
        """Finds and reads the config files. Uses the --configfile option."""
        self._logger.debug("START reading configuration from file.")
        if self.args.configfile:
            configfile = self.args.configfile
        else:
            configfile = self.config['DEFAULT']['configfile']
        with open(configfile) as fh:
            self.config.read_file(fh)
        self._logger.debug("DONE reading configuration from file.")

    def process_remaining_args(self):
        """Parses remaining arguments and overrides some config values."""
        # There is nothing to do at the moment.
        pass


# vim:cc=80
