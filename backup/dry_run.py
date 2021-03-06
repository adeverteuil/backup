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

# With code taken from:
# Lutz, Mark. 2013. Learning Python, 5th Edition. O'Reilly Media Inc.
# http://proquestcombo.safaribooksonline.com.res.banq.qc.ca/book/programming/python/9781449355722
# (Subscription to banq.qc.ca or safaribooksonline.com required)


"""This module provides tools to add support for the dry_run option.

Classes:
    modifies_filesystem
        Decorator + descriptor for methods that modify the filesystem.
        The program must set its dry_run class attribute to True to
        "disable" decorated methods.
"""


class if_not_dry_run:

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
    ...     @writes_to_filesystem
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
        self.alt_func = lambda *args, **kwargs: None

    def __call__(self, *args, **kwargs):  # On call to original function.
        if self.dry_run:
            return self.alt_func(*args, **kwargs)
        else:
            return self.func(*args, **kwargs)

    def __get__(self, instance, owner):  # On method attribute fetch.
        return _wrapper(self, instance)

    def alternative(self, func):  # On @wrapped_func.alternative
        self.alt_func = func
        return self


class _wrapper:

    def __init__(self, desc, subj):  # Save both instances.
        self.desc = desc  # Route calls back to decorator/descriptor.
        self.subj = subj

    def __call__(self, *args, **kwargs):
        # Runs writes_to_filesystem.__call__
        return self.desc(self.subj, *args, **kwargs)
