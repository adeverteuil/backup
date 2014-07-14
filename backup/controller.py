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


"""Controller classes that supervise backup routines."""


import datetime
import logging
import os.path
import traceback

from . import _logging
from .config import *
from .cycle import Cycle
from .engine import rsyncWrapper


def main():
    logging.getLogger().addHandler(_logging.handlers['stream'])
    exit(Controller(Configuration().configure()).run())


class Controller:

    """Makes sense of configuration options and orchestrates backups."""

    def __init__(self, config):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.config = config

    def run(self):
        errors = 0
        try:
            self._sanity_checks()
            self._run()
        except:
            errtype, errval, tb = sys.exc_info()
            self._logger.error(
                "{}({})".format(
                    errtype.__name__,
                    errval.args[0],
                    )
                )
            self._logger.debug(
                "".join(["Traceback:\n"] + traceback.format_tb(tb))
                )
            errors = 1
        self._logger.info("Exiting normally")
        return errors

    def _run(self):
        config = self.config
        # Save all the logging done so far. There will be a FileHandler
        # created for each host. All of them will have the content of
        # log_header written to them.
        self.log_header = _logging.handlers['memory'].stream.read()
        for host in config.defaults()['hosts'].split(" "):
            thisconfig = config[host]
            dest = os.path.join(thisconfig['dest'], host)
            hourlies = int(thisconfig['hourlies'])
            dailies = int(thisconfig['dailies'])
            self._prepare_logfile(dest)
            self._logger.info("Processing {}.".format(host))
            if hourlies > 0:
                self._logger.info("Starting hourly cycle")
                cycle = Cycle(dest, "hourly")
                rsync = rsyncWrapper(thisconfig)
                cycle.create_new_snapshot(rsync)
                cycle.purge(hourlies)
                self._move_logfile(cycle.snapshots[0].path)
            if dailies > 0:
                self._logger.info("Starting daily cycle")
                cycle = Cycle(dest, "daily")
                a_day = datetime.timedelta(days=1)
                now = datetime.datetime.now()
                if (len(cycle.snapshots) > 0 and
                    cycle.snapshots[0].timestamp + a_day >= now):
                    self._logger.debug(
                        "Most recent daily snapshot is less than one day ago. "
                        "Not doing a daily backup."
                        )
                    break
                if hourlies > 0:
                    # dailies > 0 and hourlies > 0
                    # Create dailies by archiving hourlies.
                    cycle.archive_from(Cycle(dest, "hourly"))
                else:
                    # dailies > 0 but hourlies <= 0
                    # Create dailies with rsync.
                    rsync = rsyncWrapper(thisconfig)
                    cycle.create_new_snapshot(rsync)
                    self._move_logfile(cycle.snapshots[0].path)
                cycle.purge(dailies)

    def _prepare_logfile(self, path):
        """Create a log file handler and add it to the root logger.

        All the logging done so far was memorized. Just after the handler is
        created and before any further logging, we write this log header in
        the log file.
        """
        logfile = os.path.join(path, "backup.log")
        handler = logging.FileHandler(logfile)
        handler.logfile = logfile
        handler.setFormatter(_logging.formatters['file'])
        handler.setLevel(logging.DEBUG)
        handler.acquire()
        try:
            handler.stream.write(self.log_header)
        finally:
            handler.release()
        logging.getLogger().addHandler(handler)
        _logging.handlers['file'] = handler
        self._logger.debug("Log file {} created.".format(path))


    def _move_logfile(self, path):
        """Move the log file to the snapshot directory.

        After the processing of Cycle().create_new_snapshot(), this method is
        called to close the file handler, and move the file to the snapshot
        directory.
        """
        self._logger.debug("Moving log file to {}.".format(path))
        handler = _logging.handlers['file']
        logging.getLogger().removeHandler(handler)
        handler.acquire()
        try:
            handler.close()
            os.rename(
                handler.logfile,  # Set by me in _prepare_logfile.
                os.path.join(path, "backup.log"),
                )
        finally:
            handler.release()
        del _logging.handlers['file']

    def _sanity_checks(self):
        config = self.config
        if not config.sections():
            raise ValueError(
                "No hosts defined in {}.".format(
                    config.defaults()['configfile']
                    )
                )
        if not config.defaults()['hosts']:
            raise ValueError(
                "No default hosts to back up are defined in {} and none were "
                "listed in the command line arguments.".format(
                    config.defaults()['configfile']
                    )
                )
        for host in config.defaults()['hosts'].split(" "):
            self._logger.info("Backing up host {}.".format(host))
            if host not in config.sections():
                raise ValueError(
                    "{} not defined in {}.".format(
                        host,
                        config.defaults()['configfile'],
                        )
                    )
            #TODO:
            # - Check that /dest/host directory exists and is writeable.
            # - If it is a mountpoint, check that it is mounted.
            # - If it is a remote backup, check for SSH_AGENT_PID and
            #    SSH_AUTH_SOCK environment variables?
