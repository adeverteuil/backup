Alexandre's backup script
=========================

:Author: alexandre@deverteuil.net
:Date:   2014-10-01
:Copyright: GPL

Introduction
------------

This program does incremental backups of one or several machines using
rsync. Unchanged files are hard-linked so it can manage several hourly
and daily backups with minimal storage space increase. It is written in
Python 3 and has absolute minimal dependencies.

History
-------

This is a rewrite of my personal backup program that I have been using
and improving since 2010. I started with a new git history; the former
one contained sensitive information, such as passwords and names of my
relatives, and my coding has improved a lot over time. I think this is a
much more maintainable and readable code, and I am pretty confident that
the experience I gained from the legacy version makes this one quite
reliable.

Requirements
------------

* Python 3.x
* rsync
* ssh with an ssh-agent setup (for remote backups)

Features
--------

* Detailed logging to log files, but quiet on stdout unless something
  goes wrong.
* Configurable with global and host specific keys.
* Bandwidth cap protection, useful if you have a lame ISP and do backups
  over the Internet.
* One hourly call processes all hosts and backup intervals (hourly + daily).
* Dry run option.
* Locking mechanism and state files makes resuming after a crash trivial.
* Over 60 unit tests, + integration tests with ``behave``.

Development
-----------

Welcome contributions
~~~~~~~~~~~~~~~~~~~~~

Any comments, suggestions, bug reports, log message rewording or
corrections. Feel free to address me in french or english.

Running tests
~~~~~~~~~~~~~

Behavioral driven development is powered by ``behave``. Just install behave_
and run it from the project's root directory.

.. _behave: https://pypi.python.org/pypi/behave/

::

    cd project_dir
    pip install behave
    pip install -e .
    behave

Unit tests are also provided.

::

    cd project_dir
    python -m unittest

Installing
~~~~~~~~~~

The command line script may be installed for development purposes. In
your virtualenv, use "``pip install -e .``". I will be maintaining an
ArchLinux PKGBUILD when version 1.0 is out.

"Undocumented" ``-e`` option
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Besides the ``--dry-run`` option, useful for debugging and trying
things out, there is an ``-e EXECUTABLE`` option that takes the name
of an optional executable as an argument, and will swap it in place of
rsync. By default, this will be ``echo``. This will give a little less
output, but will make the dry-run finish much more quickly.

Trying it out on a small scale first
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ~/tmp, create a ``localhost`` directory and the ``backup``
configuration file with the following content:

::

    [default]
    configdir = /dev/null
    dest = /home/<your_username>/tmp

    [localhost]
    sourcedirs = <any directory you want to use for the purpose>

Get in your virtualenv, run ``pip install -e .`` from the project
directory, then run ``backup -c /home/<your_username>/tmp/backup -v``.

Short term goals
~~~~~~~~~~~~~~~~

* Experiment and improve user experience, output messages.
* Improve unit tests readability.
* Maybe use the ``--checksum`` rsync option once a month for every host.
* Read documentation produced with ``pydoc`` and make sure it's up to date and thorough.
* ``systemd`` unit files (backup.timer, backup.service).
* Unhide status and lock files?
* Package for Archlinux.
* Warn about stale backups (that are more than x days old).

Copying
-------

Copyright © 2014  Alexandre de Verteuil

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
