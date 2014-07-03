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

This module declares the following classes, which are in linear hierarchy all
inheriting from BaseConfiguration:

    BaseConfiguration
        Contains default hard coded values for all options.
    EnvironmentReader
        Reads configuration from environment variables.
    PartialArgumentParser
        Parses command line arguments for the configfile option only.
    ConfigParser
        Parses configuration files.
    ArgumentParser
        Parses command line arguments.
    Configuration
        Calls all the previously named classes and produces a complete
        options set. Some command line arguments override options found
        in configuration files which in turn override defaults.

The backup script only needs to instantiate Configuration. When requesting the
value of an option, the following sources are looked at in order:

    Constructor arguments (useful for unit testing)
    Command line arguments
    Configuration files
    Environment variables
    Hard coded default values
"""


import argparse
import collections.abc
import logging
import os
import os.path
import sys

from .version import __version__


class BaseConfiguration(collections.abc.MutableMapping):

    """Base class for configuration gathering.

    Contains hard coded defaults.
    Implements the MutableMapping API.
    Validates input.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._options = dict()
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self._logger.debug("START initializing hard coded configuration.")
        self['sources'] = self.make_sources_list()
        self['configfile'] = "/etc/backup"
        self['dest'] = "/root/var/backups"
        self._logger.debug("DONE initializing hard coded configuration.")

    @staticmethod
    def make_sources_list():
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
        return sorted(["/"+s for s in sources])

    def __getitem__(self, name):
        return self._options[name]

    def __setitem__(self, name, value):
        # Log debug information.
        if name in self:
            old = " (was {})".format(self[name])
        else:
            old = ""
        self._logger.debug("{} = {}{}".format(name, value, old))
        # Actually set the value.
        self._options[name] = value

    def __delitem__(self, key):
        del self_options[key]

    def __iter__(self):
        for k in self._options.keys():
            yield k

    def __len__(self):
        return len(self._options)


class EnvironmentReader(BaseConfiguration):

    """Override hard-coded configs with environment variables."""

    def __init__(self, environ=None, **kwargs):
        if not environ:
            self._environ = os.environ
        else:
            self._environ = environ
        # Pull hard-coded defaults.
        super().__init__(**kwargs)
        # Override them.
        self._logger.debug("START reading configuration from environment.")
        self.parse_environ()
        self._logger.debug("DONE reading configuration from environment.")

    def parse_environ(self):
        if 'BACKUP_CONFIGFILE' in self._environ:
            self['configfile'] = self._environ['BACKUP_CONFIGFILE']


class PartialArgumentParser(EnvironmentReader):

    """Parse a subset of command line arguments.

    Although command line arguments override the configuration file,
    the --configfile argument must be parsed first.
    """

    def __init__(self, args=None, **kwargs):
        # Pull file config, environment, and default configuration.
        super().__init__(**kwargs)
        # Parse command line arguments.
        if args is None:
            args = sys.argv[1:]
        self._logger.debug("START parsing command line arguments (partial).")
        parser = argparse.ArgumentParser()
        parser.add_argument("--configfile", "-c",
                            help="Use this file rather than the default.",
                            type=open,
                            )
        options, extra_args = parser.parse_known_args(args)
        # Replace contents of args with that of extra_args for further
        # parsing by parent backup.config.ArgumentParser class.
        # It's a mutable type, so change in place.
        args.clear()
        for arg in extra_args:
            args.append(arg)
        self.argumentparser = parser
        self._logger.debug("DONE parsing command line arguments (partial).")


class ConfigParser(PartialArgumentParser):

    """Parse configuration files, fallback on EnvironmentReader."""

    def __init__(self, configfile=None, **kwargs):
        super().__init__(**kwargs)
        self._logger.debug("START reading configuration from file.")
        self._logger.debug("Nothing to do yet.")
        self._logger.debug("DONE reading configuration from file.")


class ArgumentParser(ConfigParser):

    """Parse remaining command line arguments.

    Although command line arguments override the configuration file,
    the --configfile argument must be parsed first. This was done by
    PartialArgumentParser. This class parses the remaining arguments.
    """

    def __init__(self, args=None, **kwargs):
        if not args:
            args = sys.argv[1:]
        # Pull file config, environment, and default configuration.
        super().__init__(args=args, **kwargs)
        # Parse command line arguments.
        self._logger.debug("START parsing command line arguments.")
        parser = self.argumentparser
        parser.parse_args(args)
        self._logger.debug("DONE parsing command line arguments.")


class Configuration(ArgumentParser):

    """Collects options from other classes of the config module.

    validate(name) performs validation checks according to the validation
        class variable.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger.debug("START validating configuration values.")
        self._logger.debug("Nothing to do yet.")
        self._logger.debug("DONE validating configuration values.")


# vim:cc=80
