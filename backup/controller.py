#!/usr/bin/python3
#
#   Alexandre's backup script
#   Copyright (C) 2010  Alexandre A. de Verteuil
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.
#   If not, see <http://www.gnu.org/licenses/>.


"""Controller classes that supervise backup routines."""


import logging

from .config import *


def main():
    logging.getLogger().addHandler(handlers['stream'])
    c = Controller()


class Controller:

    """Makes sense of configuration options and orchestrates backups."""

    def __init__(self):
        self._logger = logging.getLogger(__name__+"."+self.__class__.__name__)
        opt = Configuration().configure()


# vim:cc=80
