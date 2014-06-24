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


import os
import os.path
import logging

from .version import __version__


class BaseConfiguration():

    """Base class for configuration gathering. Contains hard coded defaults.

    Access to options is customized by implementing __getitem__() and
    __setitem__() methods.

    __setattr__() checks well-formedness of input values and logs at
        debug level.
    __getattr__() raises KeyError if an option is not set.
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._options = dict()
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
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
        self._good_form = good_form
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
        self._validation = validation
        self._logger.debug("START initializing hard coded configuration.")
        self['sources'] = self.make_sources_list()
        self['configfile'] = "/etc/backup"
        self['dest'] = "/root/var/backups"
        self._logger.debug("DONE initializing hard coded configuration.")

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

    def __getitem__(self, name):
        return self._options[name]

    def __setitem__(self, name, value):
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
            old = " (was {})".format(self[name])
        except KeyError:
            old = ""
        self._logger.debug("{} = {}{}".format(name, value, old))
        # Actually set the value.
        self._options[name] = value

    def __dir__(self):
        return self._options


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

    def __init__(self, **kwargs):
        # Pull file config, environment, and default configuration.
        super().__init__(**kwargs)
        # Parse command line arguments.
        self._logger.debug("START parsing command line arguments (partial).")
        self._logger.debug("Nothing to do yet.")
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

    def __init__(self, **kwargs):
        # Pull file config, environment, and default configuration.
        super().__init__(**kwargs)
        # Parse command line arguments.
        self._logger.debug("START parsing command line arguments.")
        self._logger.debug("Nothing to do yet.")
        self._logger.debug("DONE parsing command line arguments.")


class Configuration(ArgumentParser):

    """Collects options from other classes of the config module.

    validate(name) performs validation checks according to the validation
        class variable.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logger.debug("START validating configuration values.")
        for k in dir(self):
            self.validate(k)
        self._logger.debug("DONE validating configuration values.")

    def validate(self, name):
        try:
            value = self._options[name]
            for check in self._validation[name]:
                if not check[0](value):
                    raise ValueError(check[1].format(value))
        except KeyError:
            self._logger.warning("No validation check for "+name)

# vim:cc=80
