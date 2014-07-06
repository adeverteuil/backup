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


class rsyncWarning(Warning): pass
class FatalException(Exception): pass
class LockfileException(FatalException): pass
class ResourceUnavailableException(FatalException): pass


E_CODES = {
    "success" : 0,
    "fatal" : 1,
    "lockfile" : 2,
    "eagain" : 11,
    }
SSH = "/usr/bin/ssh"
RSYNC = "/usr/bin/rsync"
RSYNC_E_CODES = {
    # From the rsync(1) manpage
    1 : FatalException("Syntax or usage error"),
    2 : FatalException("Protocol incompatibility"),
    3 : FatalException("Errors selecting input/output files, dirs"),
    4 : FatalException("Requested action not supported: an attempt was made "
                       "to manipulate 64-bit files on a platform that cannot "
                       "support them; or an option was specified that is "
                       "supported by the client and not by the server."),
    5 : FatalException("Error starting client-server protocol"),
    6 : rsyncWarning("Daemon unable to append to log-file"),
    10 : FatalException("Error in socket I/O"),
    11 : FatalException("Error in file I/O"),
    12 : FatalException("Error in rsync protocol data stream"),
    13 : rsyncWarning("Errors with program diagnostics"),
    14 : rsyncWarning("Error in IPC code"),
    20 : FatalException("Received SIGUSR1 or SIGINT"),
    21 : FatalException("Some rsyncWarning returned by waitpid()"),
    22 : FatalException("Error allocating core memory buffers"),
    23 : FatalException("Partial transfer due to rsyncWarning"),
    24 : rsyncWarning("Partial transfer due to vanished source files"),
    25 : rsyncWarning("The --max-delete limit stopped deletions"),
    30 : FatalException("Timeout in data send/receive"),
    35 : FatalException("Timeout waiting for daemon connection"),
    }
