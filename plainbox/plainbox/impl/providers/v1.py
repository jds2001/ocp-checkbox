# This file is part of Checkbox.
#
# Copyright 2013 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
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

"""
:mod:`plainbox.impl.providers.v1` -- Implementation of V1 provider
==================================================================
"""

import logging
import os
import io

from plainbox.abc import IProvider1, IProviderBackend1
from plainbox.impl.applogic import WhiteList
from plainbox.impl.job import JobDefinition
from plainbox.impl.plugins import PlugInCollection
from plainbox.impl.rfc822 import load_rfc822_records


logger = logging.getLogger("plainbox.providers.v1")


class Provider1(IProvider1, IProviderBackend1):
    """
    A v1 provider implementation.

    This base class implements a checkbox-like provider object. Subclasses are
    only required to implement a single method that designates the base
    location for all other data.
    """

    def __init__(self, base_dir, name, description):
        """
        Initialize the provider with the associated base directory.

        All of the typical v1 provider data is relative to this directory. It
        can be customized by subclassing and overriding the particular methods
        of the IProviderBackend1 class but that should not be necessary in
        normal operation.
        """
        self._base_dir = base_dir
        self._name = name
        self._description = description

    @property
    def name(self):
        """
        name of this provider
        """
        return self._name

    @property
    def description(self):
        """
        description of this provider
        """
        return self._description

    @property
    def jobs_dir(self):
        """
        Return an absolute path of the jobs directory
        """
        return os.path.join(self._base_dir, "jobs")

    @property
    def scripts_dir(self):
        """
        Return an absolute path of the scripts directory

        .. note::
            The scripts may not work without setting PYTHONPATH and
            CHECKBOX_SHARE.
        """
        return os.path.join(self._base_dir, "scripts")

    @property
    def whitelists_dir(self):
        """
        Return an absolute path of the whitelist directory
        """
        return os.path.join(self._base_dir, "data", "whitelists")

    @property
    def CHECKBOX_SHARE(self):
        """
        Return the required value of CHECKBOX_SHARE environment variable.

        .. note::
            This variable is only required by one script.
            It would be nice to remove this later on.
        """
        return self._base_dir

    @property
    def extra_PYTHONPATH(self):
        """
        Return additional entry for PYTHONPATH, if needed.

        This entry is required for CheckBox scripts to import the correct
        CheckBox python libraries.

        .. note::
            The result may be None
        """
        return None

    @property
    def extra_PATH(self):
        """
        Return additional entry for PATH

        This entry is required to lookup CheckBox scripts.
        """
        # NOTE: This is always the script directory. The actual logic for
        # locating it is implemented in the property accessors.
        return self.scripts_dir

    def get_builtin_whitelists(self):
        logger.debug("Loading built-in whitelists...")
        whitelist_list = []
        for name in os.listdir(self.whitelists_dir):
            if name.endswith(".whitelist"):
                whitelist_list.append(
                    WhiteList.from_file(os.path.join(
                        self.whitelists_dir, name)))
        return sorted(whitelist_list, key=lambda whitelist: whitelist.name)

    def get_builtin_jobs(self):
        logger.debug("Loading built-in jobs...")
        job_list = []
        for name in os.listdir(self.jobs_dir):
            if name.endswith(".txt") or name.endswith(".txt.in"):
                job_list.extend(
                    self.load_jobs(
                        os.path.join(self.jobs_dir, name)))
        return sorted(job_list, key=lambda job: job.name)

    def load_jobs(self, somewhere):
        """
        Load job definitions from somewhere
        """
        if isinstance(somewhere, str):
            # Load data from a file with the given name
            filename = somewhere
            with open(filename, 'rt', encoding='UTF-8') as stream:
                return self.load_jobs(stream)
        if isinstance(somewhere, io.TextIOWrapper):
            stream = somewhere
            logger.debug("Loading jobs definitions from %r...", stream.name)
            record_list = load_rfc822_records(stream)
            job_list = []
            for record in record_list:
                job = JobDefinition.from_rfc822_record(record)
                job._provider = self
                logger.debug("Loaded %r", job)
                job_list.append(job)
            return job_list
        else:
            raise TypeError(
                "Unsupported type of 'somewhere': {!r}".format(
                    type(somewhere)))


class DummyProvider1(IProvider1, IProviderBackend1):
    """
    Dummy provider useful for creating isolated test cases
    """

    def __init__(self, job_list=None, whitelist_list=None, **extras):
        self._job_list = job_list or []
        self._whitelist_list = whitelist_list or []
        self._extras = extras
        self._patch_provider_field()

    def _patch_provider_field(self):
        # NOTE: each v1 job needs a _provider attribute that points to the
        # provider. Since many tests use make_job() which does not set it for
        # obvious reasons it needs to be patched-in.
        for job in self._job_list:
            if job._provider is None:
                job._provider = self

    @property
    def name(self):
        return self._extras.get('name', "dummy")

    @property
    def description(self):
        return self._extras.get(
            'description', "A dummy provider useful for testing")

    @property
    def CHECKBOX_SHARE(self):
        return self._extras.get('CHECKBOX_SHARE', "")

    @property
    def extra_PYTHONPATH(self):
        return self._extras.get("PYTHONPATH")

    @property
    def extra_PATH(self):
        return self._extras.get("PATH", "")

    def get_builtin_whitelists(self):
        return self._whitelist_list

    def get_builtin_jobs(self):
        return self._job_list


# Collection of all providers
all_providers = PlugInCollection('plainbox.provider.v1')
