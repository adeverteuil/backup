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


"""This module provides tools to add support for the dry_run option.

Classes:
    modifies_filesystem
        Decorator + descriptor for methods that modify the filesystem.
        The program must set its dry_run class attribute to True to
        "disable" decorated methods.
"""


class modifies_filesystem:

    """Decorator + descriptor for flagging methods that modify the filesystem.

    If the dry_run class attribute is set to True, decorated methods
    become NOOPs.

    For each decorated method, it is also possible to provide an
    alternative method to call instead of the NOOP when dry_run is True.

    For example:
    >>> class Spam:
    ...
    ...     def creates(self, path):
    ...         print("creating", path, ".")
    ...         self._create(path)
    ...         print(path, "created.")
    ...
    ...     @modifies_filesystem
    ...     def _create(self, path):
    ...         open(path, "w").close()
    ...
    ...     @_create.alternative
    ...     def _create(self, path):
    ...         print("(not actually creating", path, "…)")
    """

    dry_run = False

    def __init__(self, func):  # On @ decorator.
        self.func = func
        self.alternative = None

    def __call__(self, *args, **kwargs):  # On call to original function.
        if self.dry_run:
            if self.alternative is not None:
                return self.alternative(*args, **kwargs)
            else:
                return
        else:
            return self.func(*args, **kwargs)

    def __get__(self, instance, owner):  # On method attribute fetch.
        return _wrapper(self, instance)


class _wrapper:

    def __init__(self, desc, subj):  # Save both instances.
        self.desc = desc  # Route calls back to decorator/descriptor.
        self.subj = subj

    def __call__(self, *args, **kwargs):
        # Runs modifies_filesystem.__call__
        return self.desc(self.subj, *args, **kwargs)

    def alternative(self, func):  # On @wrapped_func.alternative
        self.desc.alternative = func
        return self.desc
