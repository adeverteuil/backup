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


"""Classes that actually perform the backups are declared within.

This module provides the following classes:

    rsyncWrapper
        Manages an rsync subprocess and threads that log its output streams.
    PipeLogger
        Logs lines of text recieved until the end of stream.
"""


import logging
import os
import os.path
import subprocess
import time
import threading


class rsyncWrapper:

    """Manages an rsync subprocess and threads that log its output streams."""

    def __init__(self, options):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        self.options = options
        # This event is passed to PipeLogger threads. While waiting for the
        # subprocess to finish, the main thread should handle KeyboardInterrupt
        # and set() it before re-raising. This will cause the threads to die.
        self.interrupt_event = threading.Event()

    @property
    def args(self):
        """Construct args list.

        The last item of the list -- the destination directory -- is left out.
        It will be passed as a parameter of the sync_to() method.
        """
        options = self.options
        args = [
            options['rsync'],
            "--delete",
            "--archive",
            "--one-file-system",
            "--partial-dir=.rsync-partial",
            "--out-format=%l %f",
            ]
        if 'bwlimit' in options:
            args.append("--bwlimit={}".format(options['bwlimit']))
        #TODO --exclude_from and --filter files
        #TODO --link-dest
        sourcedirs = options['sourcedirs'].split(":")
        if 'sourcehost' in options:
            # Transform this:  ["dir1", "dir2", "dir3"]
            # into this: ["sourcehost:dir1", ":dir2", ":dir3"]
            sourcedirs = [":"+dir for dir in sourcedirs]
            sourcedirs[0] = options['sourcehost']+sourcedirs[0]
        args += sourcedirs
        return args

    def sync_to(self, dest):
        """Invoke rsync and manage its outputs.

        This is where the parent class is initiated.
        """
        args = self.args + [dest]
        self._logger.debug(
            "Invoking rsync with arguments {}.".format(args)
            )
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            )
        self.loggers = {
            'stdout': PipeLogger(
                self.process.stdout,
                logging.getLogger("rsync.stdout").info,
                self.interrupt_event,
                ),
            'stderr': PipeLogger(
                self.process.stderr,
                logging.getLogger("rsync.stderr").warning,
                self.interrupt_event,
                ),
            }
        for logger in self.loggers.values():
            logger.start()

    def wait(self, timeout=None):
        """Wait on the subprocess and both logger threads."""
        start = time.perf_counter()
        self.process.wait(timeout=timeout)
        for logger in self.loggers.values():
            timeleft = time.perf_counter() - start
            start = time.perf_counter()
            if timeout is not None:
                timeout = timeleft
            logger.join(timeout=timeout)
            if logger.is_alive():
                raise subprocess.TimeoutExpired

    def close_pipes(self):
        """Close the stdout and stderr streams of the subprocess."""
        if hasattr(self, "process"):
            self.process.stdout.close()
            self.process.stderr.close()


class PipeLogger(threading.Thread):

    """Logs lines of text read from a stream."""

    def __init__(self, stream, method, interrupt_event, **kwargs):
        """PipeLogger constructor.

        Takes two positional arguments:
        stream -- a text stream (with a readline() method)
        method -- a function that takes a string argument
        interrupt_event -- a threading.Event() that causes the thread to exit
            when it is set.

        Typically, stream is either the stdout or stderr stream of a
        child process. method is a method of a Logger object.
        Here is a use case:
            p = subprocess.Popen(...)
            pl = PipeLogger(
                p.stdout,
                logging.getLogger("stdout").info,
                ... additionnal threading.Thread keyword arguments go here ...
                )
        """
        self.stream = stream
        self.method = method
        self.interrupt_event = interrupt_event
        super().__init__(**kwargs)

    def run(self):
        """Log lines from stream using method until empty read."""
        while not self.interrupt_event.is_set():
            line = self.stream.readline()
            if line:
                self.method(line.strip())
            else:
                return


# vim:cc=80
