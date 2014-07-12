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

from .config import *
from .cycle import Cycle
from .engine import rsyncWrapper


def main():
    logging.getLogger().addHandler(handlers['stream'])
    Controller(Configuration().configure()).run()


class Controller:

    """Makes sense of configuration options and orchestrates backups."""

    def __init__(self, config):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.config = config

    def run(self):
        try:
            self._sanity_checks()
            self._run()
        except:
            errtype, errval, traceback = sys.exc_info()
            self._logger.error(errval.args[0])

    def _run(self):
        config = self.config
        for host in config.defaults()['hosts'].split(" "):
            thisconfig = config[host]
            dest = os.path.join(thisconfig['dest'], host)
            hourlies = int(thisconfig['hourlies'])
            dailies = int(thisconfig['dailies'])
            if hourlies > 0:
                cycle = Cycle(dest, "hourly")
                rsync = rsyncWrapper(thisconfig)
                cycle.create_new_snapshot(rsync)
                cycle.purge(hourlies)
            if dailies > 0:
                cycle = Cycle(dest, "daily")
                a_day = datetime.timedelta(days=1)
                now = datetime.datetime.now()
                if (len(cycle.snapshots) > 0 and
                    cycle.snapshots[0].timestamp + a_day >= now):
                    self._logger.debug(
                        "Most recent daily snapshot is less than one day ago."
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
                cycle.purge(dailies)

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
