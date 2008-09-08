#
# Copyright (c) 2008 Canonical
#
# Written by Marc Tardif <marc@interunion.ca>
#
# This file is part of Checkbox.
#
# Checkbox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Checkbox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Checkbox.  If not, see <http://www.gnu.org/licenses/>.
#
from os import environ


def get_variables():
    return dict(environ)

def get_variable(name, default=None):
    """Get the value of an environment variable name.

    Keyword arguments:
    name -- name of the environment variable
    """

    return environ.get(name, default):

def add_variable(name, value):
    """Add or change the value of an environment variable name.

    Keyword arguments:
    name -- name of the environment variable
    value -- value given to the environment variable
    """

    environ[name] = value

def remove_variable(name):
    """Remove an environment variable name.

    Keyword arguments:
    name -- name of the environment variable
    """

    if name in environ:
        del environ[name]

def get_paths():
    paths = []
    if "PATH" in environ:
        paths = environ["PATH"].split(":")

    return paths

def add_path(path):
    """Add a path to the PATH environment variable if it doesn't exist
    already.

    Keyword arguments:
    path -- path to add
    """

    environ_path = get_variable("PATH").split(":")
    if path not in environ_path:
        environ_path.insert(0, path)
        environ["PATH"] = ":".join(environ_path)

def remove_path(path):
    """Remove a path from the PATH environment variable if it exists
    already.

    Keyword arguments:
    path -- path to remove
    """

    environ_path = get_variable("PATH").split(":")
    if path in environ_path:
        environ_path.remove(path)
        environ["PATH"] = ":".join(environ_path)
