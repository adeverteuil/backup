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


RSYNC_E_CODES = {
    # From the rsync(1) manpage
    1 : "Syntax or usage error",
    2 : "Protocol incompatibility",
    3 : "Errors selecting input/output files, dirs",
    4 : "Requested action not supported: an attempt was made "
        "to manipulate 64-bit files on a platform that cannot "
        "support them; or an option was specified that is "
        "supported by the client and not by the server.",
    5 : "Error starting client-server protocol",
    6 : "Daemon unable to append to log-file",
    10 : "Error in socket I/O",
    11 : "Error in file I/O",
    12 : "Error in rsync protocol data stream",
    13 : "Errors with program diagnostics",
    14 : "Error in IPC code",
    20 : "Received SIGUSR1 or SIGINT",
    21 : "Some rsyncWarning returned by waitpid()",
    22 : "Error allocating core memory buffers",
    23 : "Partial transfer due to error",
    24 : "Partial transfer due to vanished source files",
    25 : "The --max-delete limit stopped deletions",
    30 : "Timeout in data send/receive",
    35 : "Timeout waiting for daemon connection",
    }


class ResourceUnavailableException(RuntimeError):

    """Raised when unable to access remote host.

    This exception should not cause the program to return an error exit code.
    It is quite normal that remote hosts are sometimes offline. It shoult be
    caught and an INFO message logged.

    However, there should be a mechanism to detect problem that makes
    online hosts unreachable, such as a wrong hostname or IP address, a
    missing ssh-agent identity, or the public key is not copied over to
    the remote host. Backup directories should be monitored for stale backups.
    """

    pass


class FlaggedSnapshotError(RuntimeError):

    """This exception halts a backup to prevent excessive bandwidth usage.

    This exception is raise on two occasions:
    1.  PipeLogger counts the number of bytes transferred in real
        time. When that number exceeds bw_err, it sets an event, which
        is checked by Cycle, which in turn raises FlaggedSnapshotError.
    2.  Cycle notices that the status of the last backup is flagged.

    If the --force option was given on the command line, the Controller
    instance will catch the exception and suppress it.
    """

    pass
