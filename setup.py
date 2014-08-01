#!/usr/bin/python3

import os.path
from setuptools import setup

def find_version():
    version = {}
    with open("backup/version.py") as f:
        exec(f.read(), version)
    assert version['__version__']
    return version['__version__']

setup(
    name='backup',
    version=find_version(),
    description='Wrapper for rsync.  Does local and remote backups.',
    author='Alexandre de Verteuil',
    author_email='claudelepoisson@gmail.com',
    url='http://alexandre.deverteuil.net/',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
        ],
    packages=['backup'],
    entry_points={
        'console_scripts': ["backup=backup.controller:main"],
        },
    #data_files=[
    #    ('/etc', ['config/backup']),
    #    ('/etc/backup.d', ['config/example.exclude']),
    #    ],
    )
