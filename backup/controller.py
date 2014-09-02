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
import pprint
import subprocess
import time
import traceback

from . import *
from . import _logging
from .config import *
from .cycle import Cycle
from .dry_run import if_not_dry_run
from .engine import rsyncWrapper
from .version import __version__


def main():
    logging.getLogger().addHandler(_logging.handlers['stream'])
    exit(Controller(Configuration().configure()).run())


class Controller(_logging.Logging):

    """Makes sense of configuration options and orchestrates backups."""

    def __init__(self, config, **kwargs):
        super().__init__(**kwargs)
        self.config = config

    def run(self):
        self._logger.info("{} {}".format(sys.argv[0], __version__))
        start_time = time.monotonic()
        try:
            self._general_sanity_checks()
        except:
            self._log_exception(*sys.exc_info())
            return 1
        # Stop buffering log records. There will be a FileHandler created for
        # each host. All of them will have the content of the memory handler
        # flushed to them.
        logging.getLogger().removeHandler(_logging.handlers['memory'])
        hosts = self.config.defaults()['hosts'].split(" ")
        self._logger.info("Hosts to back up: {}".format(", ".join(hosts)))
        errors = []
        for host in hosts:
            try:
                self._run_host(host)
            except ResourceUnavailableException as err:
                self._logger.warning(err.args[0])
            except Exception:
                errors.append(host)
                self._log_exception(*sys.exc_info())
                self._close_logfile()
            except KeyboardInterrupt:
                errors.append(host)
                self._logger.error("Keyboard interrupt.")
                break
        run_time = time.monotonic() - start_time
        self._logger.info(
            "Total run time: {} minutes, {} seconds.".format(
                int(run_time / 60),
                int(run_time % 60),
                )
            )
        if errors:
            self._logger.error(
                "Exiting with errors from {}.".format(", ".join(errors))
                )
        else:
            self._logger.info("Exiting normally.")
        return 1 if errors else 0

    def _log_exception(self, errtype, errval, tb):
        self._logger.error(
            "{}{}".format(
                errtype.__name__,
                errval.args,
                )
            )
        self._logger.debug(
            "".join(["Traceback:\n"] + traceback.format_tb(tb))
            )

    def _run_host(self, host):
        start_time = time.monotonic()
        thisconfig = self.config[host]
        dest = os.path.join(thisconfig['dest'], host)
        hourlies = int(thisconfig['hourlies'])
        dailies = int(thisconfig['dailies'])
        self._open_logfile(dest)
        self._logger.info("Processing {}.".format(host))
        self._logger.debug(
            "Configuration for {}:\n{}".format(
                host, pprint.pformat(vars(thisconfig))
                )
            )
        self._host_sanity_checks(host)
        if hourlies > 0:
            self._logger.info("Starting hourly backup")
            cycle = Cycle(dest, "hourly")
            rsync = rsyncWrapper(thisconfig)
            cycle.create_new_snapshot(rsync, thisconfig.getboolean('force'))
            cycle.purge(hourlies)
            self._logger.info("Finished hourly backup")
            self._move_logfile(cycle.snapshots[0].path)
        if dailies > 0:
            cycle = Cycle(dest, "daily")
            a_day = datetime.timedelta(days=1)
            now = datetime.datetime.now()
            if (len(cycle.snapshots) > 0 and
                cycle.snapshots[0].timestamp + a_day >= now):
                self._logger.debug(
                    "Most recent daily snapshot is less than one day ago. "
                    "Not doing a daily backup."
                    )
            else:
                if hourlies > 0:
                    # dailies > 0 and hourlies > 0
                    # Create dailies by archiving hourlies.
                    self._logger.info("Starting daily archive")
                    cycle.archive_from(Cycle(dest, "hourly"))
                    self._logger.info("Finished daily archive")
                else:
                    # dailies > 0 but hourlies <= 0
                    # Create dailies with rsync.
                    self._logger.info("Starting daily backup")
                    rsync = rsyncWrapper(thisconfig)
                    cycle.create_new_snapshot(
                        rsync,
                        thisconfig.getboolean('force'),
                        )
                    self._logger.info("Finished daily backup")
                    self._move_logfile(cycle.snapshots[0].path)
                cycle.purge(dailies)
        run_time = time.monotonic() - start_time
        self._logger.info(
            "Run time for {}: {} minutes, {} seconds.".format(
                host,
                int(run_time / 60),
                int(run_time % 60),
                )
            )
        self._close_logfile()

    @if_not_dry_run
    def _open_logfile(self, path):
        """Create a log file handler and add it to the "rsync" logger.

        All the logging done so far was buffered. Just after the handler is
        created and before any further logging, we flush (actually, copy) the
        buffered records to the file handler.
        """
        logfile = os.path.join(path, "backup.log")
        handler = _logging.MovableFileHandler(logfile)
        handler.setFormatter(_logging.formatters['file'])
        handler.setLevel(logging.DEBUG)
        _logging.handlers['memory'].setTarget(handler)
        _logging.handlers['memory'].flush()
        _logging.handlers['memory'].setTarget(None)
        logging.getLogger("rsync").addHandler(handler)
        _logging.handlers['file'] = handler
        self._logger.debug("Log file {} created.".format(logfile))


    @if_not_dry_run
    def _move_logfile(self, path):
        """Move the log file to the snapshot directory.

        After the processing of Cycle().create_new_snapshot(), this method is
        called to close the file handler, and move the file to the snapshot
        directory.
        """
        path = os.path.join(path, "backup.log")
        self._logger.debug("Moving log file to {}.".format(path))
        handler = _logging.handlers['file']
        handler.move_to(path)

    @if_not_dry_run
    def _close_logfile(self):
        """Close the log file, remove the handler from the "rsync" logger."""
        self._logger.debug("Closing log file.")
        handler = _logging.handlers['file']
        logging.getLogger("rsync").removeHandler(handler)
        handler.acquire()
        try:
            handler.close()
        finally:
            handler.release()
        del _logging.handlers['file']

    def _general_sanity_checks(self):
        """Sanity checks applicable to the whole application."""
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
            if host not in config.sections():
                raise ValueError(
                    "{} not defined in {}.".format(
                        host,
                        config.defaults()['configfile'],
                        )
                    )

    def _host_sanity_checks(self, host):
        """Sanity checks specific to each host."""
        config = self.config[host]
        if config['sourcehost'] != DEFAULTS['sourcehost']:
            cmd = [
                config['ssh'],
                "-o", "BatchMode=yes",
                config['sourcehost'],
                "exit", "0",
                ]
            self._logger.debug("Calling {}".format(" ".join(cmd)))
            returncode = subprocess.call(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                )
            if returncode > 0:
                raise ResourceUnavailableException(
                    "Unable to connect to {}; ssh returned {}".format(
                        host,
                        returncode,
                        )
                    )
            else:
                self._logger.debug("Connection to host is a success.")
