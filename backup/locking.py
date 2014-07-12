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


"""This module provides locking facilities.

The Lockable class may be inherited by classes that must implement a
locking mechanism over shared resources.

Exceptions:

    Error -- base class for other exceptions
        LockError -- base class for all locking exceptions
            AlreadyLocked -- Another object, thread or process already holds
                             the lock
            LockFailed -- Lock failed for some other reason
        UnlockError -- base class for all unlocking exceptions
            AlreadyUnlocked -- File was not locked.
            NotMyLock -- File was locked but not by the current thread/process

Some code was taken from <https://github.com/smontanaro/pylockfile>.
Gratitude is owed to smontanaro.
"""


import errno
import os
import os.path
import sys
import threading


class Error(Exception):
    """Base class for other exceptions."""
    pass

class LockError(Error):
    """Base class for error arising from attempts to acquire the lock."""
    pass

class LockTimeout(LockError):
    """Raised when lock creation fails within a user-defined period of time."""
    pass

class AlreadyLocked(LockError):
    """Some other object/thread/process is locking the file."""
    pass

class LockFailed(LockError):
    """Lock file creation failed for some other reason."""
    pass

class UnlockError(Error):
    """Base class for errors arising from attempts to release the lock."""
    pass

class AlreadyUnlocked(UnlockError):
    """Raised when an attempt is made to unlock an unlocked file."""
    pass

class NotMyLock(UnlockError):
    """Raised when an attempt is made to unlock a file someone else locked."""
    pass


class Lockable:

    """An object that can be locked to limit access to a shared resource.

    Unless the subclass overrides __enter__() and __exit__(), this base
    class makes the subclass usable as a context manager.

    Subclasses are expected to define the lockfile and path instance
    attributes before calling methods defined here.

    Lockable has no constructor.
    """

    @property
    def _unique_name(self):
        return os.path.join(
            self.lockfile,
            "{}.{}.{}".format(
                os.getpid(),
                hash(threading.current_thread()),
                hash(self)
                )
            )

    def acquire(self):
        try:
            os.mkdir(self.lockfile)  # Atomic operation.
        except OSError as err:
            err = sys.exc_info()[1]
            if err.errno == errno.EEXIST:
                # Already locked.
                if os.access(self._unique_name, os.F_OK):
                    # Already locked by me.
                    return
                else:
                    msg = "{} is already locked.".format(self.path)
                    raise AlreadyLocked(msg)
            else:
                msg = "Failed to lock {}.".format(self.path)
                raise LockFailed(msg) from err
        else:
            open(self._unique_name, "wb").close()
            if hasattr(self, "_logger"):
                self._logger.debug(
                    "Lock created: {}.".format(self._unique_name)
                    )

    def release(self):
        if not self.is_locked():
            raise AlreadyUnlocked("{} is not locked".format(self.path))
        elif not os.access(self._unique_name, os.F_OK):
            raise NotMyLock("{} is locked, but not by me.".format(self.path))
        else:
            os.remove(self._unique_name)
            os.rmdir(self.lockfile)
            if hasattr(self, "_logger"):
                self._logger.debug(
                    "Lock released: {}.".format(self._unique_name)
                    )

    def is_locked(self):
        return os.access(self.lockfile, os.F_OK)

    def i_am_locking(self):
        return self.is_locked() and os.access(self._unique_name, os.F_OK)

    def break_lock(self):
        if os.access(self.lockfile, os.F_OK):
            for name in os.listdir(self.lockfile):
                os.remove(os.path.join(self.lockfile, name))
            os.rmdir(self.lockfile)
            if hasattr(self, "_logger"):
                self._logger.debug(
                    "Lock broken: {}.".format(self._unique_name)
                    )

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
