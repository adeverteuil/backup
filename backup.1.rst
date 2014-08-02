========
 backup
========

---------------------------------------------------------
Perform hourly and daily backups of one or multiple hosts
---------------------------------------------------------

:Author: alexandre@deverteuil.net
:Date:   2014-07-28
:Copyright: GPL
:Manual section: 1

SYNOPSIS
========

  backup [--help] [--version] [-v|--verbose] [{-c|--configfile} CONFIGFILE] [{-d|--configdir} CONFIGDIR] [-n|--dry-run] [-f|--force] [host [host ...]]

DESCRIPTION
===========

``backup`` autonomously performs hourly and daily backups of one or
multiple hosts. It must be called hourly from a cron daemon or from a
``systemd`` timer unit. Usually, all the information it needs is read
from configuration files and no command line parameters are required.

OPTIONS
=======

--help, -h      Print a help summary and exit.
--version       Show program's version number and exit.
--verbose, -v   Set verbosity level to INFO. This option may be repeated
                once for verbosity level DEBUG. The default level is
                WARNING.
--print-rsync, -p
                Also print the output of rsync to stdout. Otherwise,
                only log its output to the log file. Ineffective if -v was
                not given.
--configfile CONFIGFILE, -c CONFIGFILE
                Use this file rather than the default.
--configdir CONFIGDIR, -d CONFIGDIR
                Use this directory rather than the default.
--dry-run, -n   Simulate all actions to perform, printing almost the same messages
                that would be printed in a normal run, but don't touch the
                filesystem.
--force, -f     Continue past any bandwidth caps set by the bw_err
                configuration key.

CONFIGURATION FILES
===================

/etc/backup
-----------

The default configuration file is /etc/backup. You may specify
a different one with the ``--configfile`` option or the
``BACKUP_CONFIGFILE`` environment variable. The format of the file is
the INI format as supported by default by the configparser Python 3
module. There must be a [default] section, which may be empty. Each
host must be defined with a section named after it. Options in a host
section override those in the default section. An empty host section is
acceptable and means this host uses the default options.

In this document section, keys are followed by letters in parenthesis,
such as (D, H). A "D" means the option may appear in the [default]
configuration. A "H" means the option may appear in a host specific
section. The hard-coded default value follows the equals (=) sign.

configdir (D) =/etc/backup.d
    Will override the default value, but will be overriden by the command line
    parameter --configdir.

rsync (D) =/usr/bin/rsync
    Test description data.

sourcedirs (D, H) =<root subdirectories except sys, proc, dev and lost+found>
    A colon separated list of directories to back up. You may give a value of "/".
    Keep in mind that ``rsync`` will receive the ``--one-filesystem`` option.
    Any mounpoints you want to descend into must be part of this list.

    Know the rsync syntax: directories ending with / copy the *content*
    of the directory. Directories *not* ending in / copy the directory
    itself.

dest (D, H) =/root/var/backups
    For each host sections defined in /etc/backup, create a directory in ``dest``
    named after it. Inside those host directories, ``backup`` will create
    "hourly.yyyy-mm-ddTHH:MM" and "daily.yyyy-mm-ddTHH:MM" snapshot directories.

hourlies (D, H) =24
    See dailies.

dailies (D, H) =31
    The number of hourly and daily snapshots to keep, respectively. A
    hourly backup will be created every time ``backup`` is called. You
    should logically call it on an hourly basis. A daily backup is
    created if the most recent daily backup is more than 1 day old at
    the moment ``backup`` is called. You may assign the value 0 to
    either of these configuration keys.

bw_warn (D, H) =0
    When a backup is completed, if the total size of changed files is larger than
    bw_warn, report the list of the 10 largest files at log level WARNING.

bw_err (D, H) =0
    In real time, while a backup is being created, if the total size of changed
    files is larger than bw_warn, report the list of 10 biggest files at log level
    ERROR, flag this snapshot and terminate the ``rsync`` process immediately.
    This is an if-all-else-fails protection against bugs that would cause a
    backup not to be linked to an existing snapshot, leading to an excessive
    consumption of bandwidth.

/etc/backup.d
-------------

The ``configdir``, /etc/backup.d by default, is where filter and exclude
files, as defined in man 1 rsync, are placed. For each host_section,
if a file "<configdir>/<host_section>.exclude" exists, it will be
used as an argument to the --exclude-from rsync option. If a file
"<configdir>/<host_section>.filter" exists, it will be used as an
argument to the --filter=merge rsync option.

TIP: The "<host_section>.filter" file can contain the line "dir-merge
.backup". With this syntax, any ".backup" file found in the filesystem
is parsed by rsync and used as a filter file rooted where the file is
located. See man 1 rsync for more details.

MONITORING
==========

It is a good idea to monitor your backup jobs, but this becomes tedious
really quickly. By default, ``backup`` will not print messages, but
always provides detailed log files for post-debugging.

When ``backup`` is called on the command line, you might want to use
the --verbose option, otherwise nothing will be printed on the terminal
unless something goes wrong, which is fine when ``backup`` is run as a
cron job or from a ``systemd`` timer unit.

It is trivial to obtain emailed output from most cron daemons. For
systemd-based systems, I recommend altering the backup.service
file as suggested by ushi <ushi+arch at honkgong.info> in
https://mailman.archlinux.org/pipermail/arch-general/2014-February/035037.html

bw_err and bw_warn
------------------

One design concern is in regards to remote backups where
a limited Internet monthly transfer cap and several Gb of files to
back up is a risk factor for excess data transfer fees.

The first backup is done locally. The subsequent, remote backups are
incremental, but bugs have caused excess data transfer fees in the
past. This has been fixed with lock files, state files, better coding
style, and the ``bw_err`` and ``bw_warn`` features.

``bw_warn`` is useful for a few weeks after setting up a backup
routine. It will help you identify directories that contain large files
that change often and that could be considered for exclusion from the backup.

``bw_err`` is an if-all-else-fails protection that will immediately
terminate a running backup if the total size of changed files exceeds
its value. ``backup`` will then refuse to resume for this host until the
--force command line parameter is given. You may manually run a backup
for one specific host by naming it on the command line. For example:
"backup --verbose --force host_name".

FILES AND DIRECTORIES STRUCTURE
===============================

The ``dest`` directory (/root/var/backups by default) must
contain one directory named after each host section in the
``configfile``. When ``backup`` creates a new snapshot, it
will use the format "<dest>/<host>/<interval>.wip", for
example: "/root/var/backups/my_server/hourly.wip". Wip stands
for Work In Progress. It also writes a log to the file
"<dest>/<host>/backup.log". When the backup completes, the snapshot is
renamed using the format "<dest>/<host>/<interval>.yyyy-mm-ddTHH:MM" and
the log file is moved inside the snapshot directory.

Convention over configuration
-----------------------------

The default directory used as a destination for backups is
``/root/var/backups``. This is to make it as read-only as possible. You
should bind-mount this directory to ``/var/backups`` with option ``ro``
using these commands in your ``rc.local`` or whatever script is called
after the system boots:

::

    mount -o bind /root/var/backups /var/backups
    mount -o remount,ro /var/backups

This has to be done in two steps because a bind mount has the same
options as the origin filesystem even if you specify other options. i.e.
``-o bind,ro`` will result in a writable filesystem.

``systemd`` unit files that accomplish this are provided in the project
directory under "systemd". For a local installation, these files may
be placed in /etc/systemd/system. Package maintainers may install
these files in /usr/lib/systemd/system. Then, the command "systemctl
enable var-backups.automount" must be executed as root.

``locate`` hint
---------------

Using ``locate`` to look for a file will result in a flood of hits from
the /var/backups filesystem. I suggest pruning /var/backups from
the mlocate.db and building a backup.db specifically for
searching a file in the backup directory.

1.  Append "/var/backups" to the PRUNEPATHS variable in
    /etc/updatedb.conf. Example:

    ::

        PRUNEPATHS = "/media /mnt /tmp […] /var/backups"

2.  Put this command in a script in /etc/cron.daily:

    ::

        [ -x /usr/bin/updatedb ] && \
        /usr/bin/updatedb --prunepaths "" -U /var/backups \
        -o /var/lib/mlocate/backups.db

3.  add this alias to your bashrc:

    ::

        alias baklocate="locate -d /var/lib/mlocate/backup.db"
