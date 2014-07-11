Alexandre's backup script
=========================

This script is a work in progress. It is not usable at this point.

It is intended to perform backups of several machines with snapshot at
different time intervals. A rigid and flexible mechanism will make it
easy to monitor your backups in permanence.

.. note:: To do: make this more like a man page.

Requirements
------------

* Python 3.x
* rsync
* ssh with an ssh-agent setup (for remote backups)

Directory rationale
-------------------

The default directory used as a destination for backups is
``/root/var/backups``. This is to make it as read-only as possible. You
should bind-mount this directory to ``/var/backups`` with option ``ro``
using these commands in your ``rc.local`` or whatever script is called
after the system boots :

::

    mount -o bind /root/var/backups /var/backups
    mount -o remount,ro /var/backups

This has to be done in two steps because a bind mount has the same
options as the origin filesystem even if you specify other options. i.e.
``-o bind,ro`` will result in a writable filesystem.

``systemd`` unit files that accomplish this are provided in the project
directory under "systemd". For a local installation, these files may
be placed in ``/etc/systemd/system``. Package maintainers may install
these files in ``/usr/lib/systemd/system``. Then, the command ``systemctl
enable var-backups.automount`` must be executed as root.

File "NOT_MOUNTED"
------------------

If the destination directory is the root of a mount point, create a file
named "``NOT_MOUNTED``" before mounting the filesystem. When the filesystem
is mounted, this file will not be visible. If this file is seen, backup
will assume the destination media is not mounted and will abort with
exit code 11.

.. note:: Not yet implemented.

``locate`` hint
---------------

Using locate to look for a file will result in a flood of hits from the
``/var/backups`` filesystem. I suggest pruning ``/var/backups`` from
the ``mlocate.db`` and constructing a ``backup.db`` specifically for
searching a file in the backup directory.

1.  Append "``/var/backups``" to the ``PRUNEPATHS`` variable

    ::

        in /etc/updatedb.conf. Example :
        PRUNEPATHS = "/media /mnt /tmp […] /var/backups"

2.  Put this command in a script in ``/etc/cron.daily`` :

    ::

        [ -x /usr/bin/updatedb ] && \
        /usr/bin/updatedb --prunepaths "" -U /var/backups \
        -o /var/lib/mlocate/backups.db

3.  add this alias to your bashrc :

    ::

        alias baklocate="locate -d /var/lib/mlocate/backup.db"

Multiple intervals of rotation
------------------------------

.. note:: To do.

Development
-----------

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

The command line script may be installed for development purposes. In  .
your virtualenv, use ``pip install -e .``. I will be maintaining an     .
ArchLinux PKGBUILD when version 1.0 is out                             .
