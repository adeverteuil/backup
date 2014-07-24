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


"""Classes that actually perform the backups are declared within.

This module provides the following classes:

    rsyncWrapper
        Manages an rsync subprocess and threads that log its output streams.
    PipeLogger
        Logs lines of text recieved until the end of stream.
"""


#TODO for adding trigger support.
# [] Test the wait method with timeout argument.
# [] Add keyword arguments bw_warn and bw_err to PipeLogger constructor.
# [] Create the FLAGGED status.
# [] Create the --force command line argument.
# [] Add the configuration keys bw_warn and bw_err.
# [] Make the Cycle instances loop between wait(timeout) and checking for
#        exception raised in PipeLogger thread.
# [] Write the warning and error methods in the PipeLogger class.
# [] Make PipeLogger build a biggest files list and bytes transferred tally.


import logging
import os
import os.path
import subprocess
import time
import threading

from . import _logging


class rsyncWrapper(_logging.Logging):

    """Manages an rsync subprocess and threads that log its output streams."""

    def __init__(self, options, **kwargs):
        """
        options -- one section of a ConfigParser.
        """
        super().__init__(**kwargs)
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
            "--verbose",
            "--out-format=#%l#%f",  # Format: "#" + file_size + "#" + file_name
            ]
        if 'bwlimit' in options:
            args.append("--bwlimit={}".format(options['bwlimit']))
        if options.getboolean('dry-run'):
            args.append("--dry-run")
        # Append --filter=merge filterfile
        filterfile = os.path.join(
            options['configdir'],
            options._name + ".filter",  # The name of the config section.
            )
        if os.access(filterfile, os.F_OK):
            args.append("--filter=merge {}".format(filterfile))
        # Append --exclude-from=excludefile
        excludefile = os.path.join(
            options['configdir'],
            options._name + ".exclude",  # The name of the config section.
            )
        if os.access(excludefile, os.F_OK):
            args.append("--exclude-from={}".format(excludefile))
        # Append source directories.
        sourcedirs = options['sourcedirs'].split(":")
        if 'sourcehost' in options:
            args.append("--rsh=ssh -o BatchMode=yes")
            # Transform this:  ["dir1", "dir2", "dir3"]
            # into this: ["sourcehost:dir1", ":dir2", ":dir3"]
            sourcedirs = [":"+dir for dir in sourcedirs]
            sourcedirs[0] = options['sourcehost']+sourcedirs[0]
        args += sourcedirs
        return args

    def sync_to(self, dest, linkdest=None):
        """Invoke rsync and log its outputs.

        All the information rsyncWrapper needs to build the arguments list is
        contained in the config object recieved as it's constructor argument,
        except dest and link-dest.

        Parameters:
            dest -- The destination directory.
            linkdest -- If not None, the directory to hardlink unchanged
                files from.
        """
        args = self.args
        if linkdest is not None:
            # Insert rather than append because the source directories are
            # already appended to the args list.
            args.insert(1, "--link-dest={}".format(linkdest))
        args.append(dest)
        self._logger.debug(
            "Invoking rsync with arguments {}.".format(args)
            )
        self.process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
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
        returncode = self.process.wait(timeout=timeout)
        for logger in self.loggers.values():
            timeleft = time.perf_counter() - start
            start = time.perf_counter()
            if timeout is not None:
                timeout = timeleft
            logger.join(timeout=timeout)
            if logger.is_alive():
                raise subprocess.TimeoutExpired
        return returncode

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
            if line == "":
                return
            elif line.startswith("#"):
                # Extract the file size.
                # Because of the --out-format option passed to rsync.
                # Format is: "#" + file_size + "#" + file_name
                size, line = line[1:].split("#", 1)
                size = int(size)  # in bytes
            self.method(line.strip())

    def count_bytes(self, line):
        """Count bytes transferred and build list of biggest files transferred.

        Parameters:
        line -- one line of the stdout stream of the rsync process.
        """
        # Extract the file size.
        # Because of the --out-format option passed to rsync.
        # Format is: "#" + file_size + "#" + file_name
        size, line = line[1:].split("#", 1)
        size = int(size)  # in bytes
