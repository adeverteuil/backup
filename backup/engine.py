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


"""Actually performs the backups.

This module provides the following classes:

    rsyncWrapper
        Manages an rsync subprocess and threads that log its output streams.
    PipeLogger
        Logs lines of text recieved until the end of stream
"""


import time
import logging
import subprocess
import threading


class rsyncWrapper(subprocess.Popen):

    """Manages an rsync subprocess and threads that log its output streams."""

    def __init__(self, options):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self._options = options

    def execute(self):
        """Invoke rsync and manage it's outputs.

        This is where the parent class is initiated.
        """
        self._logger.debug(
            "Invoking rsync with arguments {}.".format(self.args)
            )
        super().__init__(
            self.args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        self.loggers = {
            'stdout': PipeLogger(
                self.stdout,
                logging.getLogger("rsync.stdout").info
                ),
            'stderr': PipeLogger(
                self.stderr,
                logging.getLogger("rsync.stderr").warning
                ),
            }
        for logger in self.loggers:
            logger.start()

    def wait(self, timeout=None):
        """Wait on the subprocess and both logger threads."""
        start = time.perf_counter()
        super().wait(timeout=timeout)
        for logger in self.loggers.values():
            timeleft = time.perf_counter() - start
            start = time.perf_counter()
            if timeout is not None:
                timeout = timeleft
            logger.join(timeout=timeout)
            if logger.is_alive():
                raise subprocess.TimeoutExpired


class PipeLogger(threading.Thread):

    """Logs lines of text recieved until the end of stream."""

    def __init__(self, stream, method, **kwargs):
        """PipeLogger constructor.

        Takes two positional arguments:
        stream -- a text stream (with a readline() method)
        method -- a function that takes a string argument

        Typically, stream is either the stdout or stderr of a
        subprocess. method belongs to a Logger object. A PipeLogger
        might be instantiated thus:
            p = subprocess.Popen(...)
            pl = PipeLogger(
                p.stdout,
                logging.getLogger("stdout").info,
                ... threading.Thread keyword arguments go here ...
                )
        """
        self.stream = stream
        self.method = method
        super().__init__(**kwargs)

    def run(self):
        """Log lines from stream using method until empty read."""
        while True:
            line = self.stream.readline()
            if line:
                self.method(line.strip())
            else:
                return


# vim:cc=80
