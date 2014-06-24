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

This module declares the following classes:

    HardCodedConfigurator
        Contains default values for all options.
    BackupConfigParser
        Parses configuration files.
    BackupArgumentParser
        Parses command line arguments.
    BackupConfigurator
        Calls all the previously named classes and produces a complete
        options set. Some command line arguments override options found
        in configuration files which in turn override defaults.

Configuration options are read from many sources and override eachother
in this order:

    Command line arguments
    Configuration file
    Environment variables
    Source code

However, the configuration file path may be specified on the command line.
Therefore, the command line arguments must be parsed first, then the
configuration file is read, then the overriding happens.
"""


import os
import os.path
import logging

from .version import __version__


class HardCodedConfiguration():

    """Base class for configuration gathering.

    Attribute access is customized by implemented __getattr__() and
    __setattr__() methods.

    __setattr__() checks well-formedness of input values and logs at
        debug level.
    __getattr__() raises AttributeError if an option is not set.
    """

    @staticmethod
    def _validate_sources(sources):
        for f in sources:
            if not os.access(f, os.F_OK):
                raise ValueError(
                    "Source file or directory {} does not exist.".format(f)
                    )
            if not os.access(f, os.R_OK):
                raise ValueError(
                    "Source file or directory {} is inaccessible.".format(f)
                    )
        return True

    @staticmethod
    def _well_formed_sources(sources):
        for f in sources:
            if f != os.path.abspath(f):
                raise ValueError("Not an absolute path: {}".format(f))
        return True

    def __init__(self):
        super().__setattr__("_options", dict())
        super().__setattr__(
            "_logger",
            logging.getLogger(__name__+"."+self.__class__.__name__)
            )
        good_form = {
            # Each key is the name of an option to check for good form.
            # Each value is a list of tests to perform.
            # Each test is a tuple of a test function that returns a boolean
            # and, for lambda functions, an error message.
            'sources': [
                (lambda l: list(l), "Sources must be listable : {}."),
                (self._well_formed_sources,),
                ],
            'configfile': [
                (lambda f: f == os.path.abspath(f), "Not an absolute path: {}"),
                ],
            'dest': [
                (lambda f: f == os.path.abspath(f), "Not an absolute path: {}"),
                ],
            }
        super().__setattr__("_good_form", good_form)
        # Save validation for Configuration().__init__().
        validation = {
            # This follows the same structure as good_form.
            'sources': [
                (self._validate_sources,)
                ],
            'configfile': [
                (lambda f: os.access(f, os.F_OK),
                    "configfile {} does not exist."),
                (lambda f: os.access(f, os.R_OK),
                    "configfile {} isn't readable."),
                ],
            }
        super().__setattr__("_validation", validation)
        self.sources = self.make_sources_list()
        self.configfile = "/etc/backup"
        self.dest = "/root/var/backups"

    def make_sources_list(self):
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

    def __getattr__(self, name):
        try:
            return self._options[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        # Check if input is well formed.
        try:
            for check in self._good_form[name]:
                if not check[0](value):
                    raise ValueError(check[1].format(value))
        except KeyError as err:
            err.args = (
                "No well-formedness check found for option {}.".format(name),
                )
            raise
        # Log debug data.
        try:
            old = " (was {})".format(self.__getattr__(name))
        except AttributeError:
            old = ""
        self._logger.debug("Option {} = {}{}".format(name, value, old))
        # Actually set the value.
        self._options[name] = value

    def __dir__(self):
        return self._options


class BackupEnvironmentCollector(HardCodedConfiguration):

    """Override hard-coded configs with environment variables."""

    # This allows unit tests to set a reproducible environment.
    environ = os.environ

    def __init__(self):
        # Pull hard-coded defaults.
        super().__init__()
        # Override them.
        self.parse_environ()

    def parse_environ(self):
        if 'BACKUP_CONFIGFILE' in self.environ:
            self.configfile = self.environ['BACKUP_CONFIGFILE']


class BackupConfigParser():

    """Parse configuration files, fallback on BackupEnvironmentCollector."""

    def __init__(self, configfile):
        pass


class BackupArgumentParser(BackupEnvironmentCollector, BackupConfigParser):

    """Parse command line arguments, then the configuration file.
    Although command line arguments override the configuration file,
    they must be parsed first and saved for later because there might be
    a --configfile argument present.

    The file to be parsed is the first one found among the following :
    1. The configfile argument of the;
    2. The value of the BACKUP_CONFIG_FILE environment variable;
    3. The hard-coded value.
    """

    def __init__(self):
        # Pull environment configuration.
        super().__init__()
        # Parse arguments, save in temporary dict.
        #TODO
        # Parse configuration file.
        BackupConfigParser.__init__(self, self._options['configfile'])
        # Override options with those saved from the command line arguments.
        #TODO


class Configuration(BackupArgumentParser):

    """Collects options from other classes of the config module.

    validate(name) performs validation checks according to the validation
        class variable.
    """

    def __init__(self):
        super().__init__()
        for k in dir(self):
            self.validate(k)

    def validate(self, name):
        try:
            value = self._options[name]
            for check in self._validation[name]:
                if not check[0](value):
                    raise ValueError(check[1].format(value))
        except KeyError:
            self._logger.warning("No validation check for "+name)

# vim:cc=80
