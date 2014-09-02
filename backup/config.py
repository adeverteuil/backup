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

from . import _logging
from .dry_run import if_not_dry_run
from .version import __version__


def _make_sources_list():
    """Return a default string of colon-separated paths to back up.

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
    'configfile': "/etc/backup",
    'configdir': "/etc/backup.d",
    'rsync': "/usr/bin/rsync",
    'ssh': "/usr/bin/ssh",
    'sourcehost': "localhost",
    'sourcedirs': _make_sources_list(),
    'dest': "/root/var/backups",
    'hourlies': "24",
    'dailies': "31",
    'warn bytes transferred': str(1 * 10**8),  # 100MB
    'bw_warn': "0",
    'bw_err': "0",
    'force': "False",
    }


class Configuration(_logging.Logging):

    """Collects options from command line arguments and configuration files."""

    def __init__(self, argv=None, environ=None, **kwargs):
        """Instantiates ConfigParser with defaults and ArgumentParser.

        Parameters:
        argv -- If not None, will be parsed instead of sys.argv[1:].
        environ -- If not None, will be used insted of os.environ.
        """
        super().__init__(**kwargs)
        self.argv = argv if argv is not None else sys.argv[1:]
        self.args = None  # This will hold the return value of parse_args().
        self.environ = environ if environ is not None else os.environ
        self.config = configparser.ConfigParser(
            defaults=DEFAULTS,
            default_section="default",
            )
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
        parser.add_argument("--print-rsync", "-p",
            help=("Also print the output of rsync to stdout. Otherwise, only "
                  "log its output to the log file. Ineffective if -v option "
                  "is not given."),
            action="store_true",
            )
        parser.add_argument("--configfile", "-c",
            help="Use this file rather than the default.",
            )
        parser.add_argument("--configdir", "-d",
            help="Use this directory rather than the default.",
            )
        parser.add_argument("--dry-run", "-n",
            help="Perform a trial run with no changes made.",
            action="store_true",
            )
        parser.add_argument("--force", "-f",
            help="Disable any bw_err trigger.",
            action="store_true",
            )
        parser.add_argument("-e",
            metavar="EXECUTABLE",
            help=argparse.SUPPRESS,
            const="echo",
            nargs="?",
            #help=("Executable to use instead of rsync. "
            #      "Use echo when debugging. "
            #      "echo is the default if this option is used but no "
            #      "executable is specified."),
            )
        parser.add_argument("hosts",
            nargs="*",
            help=("List of hosts to do a backup of. Hosts are defined through "
                  "configuration files in /etc/backup.d. If no hosts are "
                  "specified, all defined hosts are backed up sequentially."),
            metavar="host",
            )

    def configure(self):
        """Executes all the configurations tasks in the right order.

        Returns the ConfigParser object with all the collected options.
        """
        self._parse_environ()
        self._parse_args()
        self._do_early_logging_config()
        self._read_config()
        self._merge_args_with_config()
        self._logger.debug(
            "Hosts defined: {}".format(self.config.sections())
            )
        return self.config

    def _parse_environ(self):
        """Overrides some defaults with environment variables."""
        if 'BACKUP_CONFIGFILE' in self.environ:
            self.config.defaults()['configfile'] = \
                self.environ['BACKUP_CONFIGFILE']
            self._logger.debug(
                "From env: BACKUP_CONFIGFILE = {}".format(
                    self.environ['BACKUP_CONFIGFILE']
                    )
                )
        if 'BACKUP_CONFIGDIR' in self.environ:
            self.config.defaults()['configdir'] = \
                self.environ['BACKUP_CONFIGDIR']
            self._logger.debug(
                "From env: BACKUP_CONFIGDIR = {}".format(
                    self.environ['BACKUP_CONFIGDIR']
                    )
                )

    def _parse_args(self):
        """Adds arguments to the ArgumentParser instance and parses args."""
        self.args = self.argumentparser.parse_args(self.argv)
        self._logger.debug("Parsed args: {}".format(vars(self.args)))

    def _do_early_logging_config(self):
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
                _logging.handlers['stream'].setLevel(logging.DEBUG)
                lvl = "DEBUG"
            elif self.args.verbose == 1:
                _logging.handlers['stream'].setLevel(logging.INFO)
                lvl = "INFO"
        logger.addHandler(_logging.handlers['memory'])
        self._logger.debug("Log level set to {}".format(lvl))
        if self.args.print_rsync is False:
            # The logging FileHandler will be added to the "rsync" logger
            # by the Controller object.
            logging.getLogger("rsync").propagate = False

    def _read_config(self):
        """Finds and reads the config files. Uses the --configfile option."""
        if self.args.configfile:
            configfile = self.args.configfile
        else:
            configfile = self.config.defaults()['configfile']
        with open(configfile) as fh:
            self._logger.debug(
                "Reading configuration from {}.".format(configfile)
                )
            self.config.read_file(fh)

    def _merge_args_with_config(self):
        # --configfile has already been parsed in _read_config().
        if self.args.hosts:
            self.config.defaults()['hosts'] = " ".join(self.args.hosts)
        elif 'hosts' not in self.config.defaults():
            # If the hosts key in the default section is not defined and no
            # hosts were specified on the command line, build the hosts list
            # from the sections of the configuration file.
            self.config.defaults()['hosts'] = " ".join(self.config.sections())
        self.config.defaults()['dry-run'] = str(self.args.dry_run)
        if_not_dry_run.dry_run = self.args.dry_run
        if self.args.e is not None:
            self.config.defaults()['rsync'] = self.args.e
        self.config.defaults()['force'] = str(self.args.force)
