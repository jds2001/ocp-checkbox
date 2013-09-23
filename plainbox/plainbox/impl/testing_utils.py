# This file is part of Checkbox.
#
# Copyright 2012 Canonical Ltd.
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
:mod:`plainbox.impl.testing_utils` -- plainbox specific test tools
==================================================================

.. warning::

    THIS MODULE DOES NOT HAVE STABLE PUBLIC API
"""

from functools import wraps
from gzip import GzipFile
from io import TextIOWrapper
from mock import Mock
from tempfile import NamedTemporaryFile
import inspect
import warnings

from plainbox.impl.job import JobDefinition
from plainbox.impl.result import IOLogRecordWriter
from plainbox.impl.result import MemoryJobResult
from plainbox.impl.rfc822 import Origin


def MockJobDefinition(name, *args, **kwargs):
    """
    Mock for JobDefinition class
    """
    job = Mock(*args, spec_set=JobDefinition, **kwargs)
    job.name = name
    return job


def make_io_log(io_log, io_log_dir):
    """
    Make the io logs serialization to json and return the saved file pathname
    WARNING: The caller has to remove the file once done with it!
    """
    with NamedTemporaryFile(
        delete=False, suffix='.record.gz', dir=io_log_dir) as byte_stream, \
            GzipFile(fileobj=byte_stream, mode='wb') as gzip_stream, \
            TextIOWrapper(gzip_stream, encoding='UTF-8') as text_stream:
        writer = IOLogRecordWriter(text_stream)
        for record in io_log:
            writer.write_record(record)
    return byte_stream.name


def make_job(name, plugin="dummy", requires=None, depends=None, **kwargs):
    """
    Make and return a dummy JobDefinition instance
    """
    # Jobs are usually loaded from RFC822 records and use the
    # origin tracking to understand which file they came from.
    #
    # Here we can create a Origin instance that pinpoints the
    # place that called make_job(). This aids in debugging as
    # the origin field is printed by JobDefinition repr
    caller_frame, filename, lineno = inspect.stack(0)[1][:3]
    try:
        # XXX: maybe create special origin subclass for such things?
        origin = Origin(filename, lineno, lineno)
    finally:
        # Explicitly delete the frame object, this breaks the
        # reference cycle and makes this part of the code deterministic
        # with regards to the CPython garbage collector.
        #
        # As recommended by the python documentation:
        # http://docs.python.org/3/library/inspect.html#the-interpreter-stack
        del caller_frame
    # Carefully add additional data into the job definition so that we
    # don't add any spurious None-valued keys that change the checksum.
    data = {'name': name}
    if plugin is not None:
        data['plugin'] = plugin
    if requires is not None:
        data['requires'] = requires
    if depends is not None:
        data['depends'] = depends
    # Add any custom key-value properties
    data.update(kwargs)
    return JobDefinition(data, origin)


def make_job_result(outcome="dummy"):
    """
    Make and return a dummy JobResult instance
    """
    return MemoryJobResult({
        'outcome': outcome
    })


def suppress_warnings(func):
    """
    Suppress all warnings from the decorated function
    """
    @wraps(func)
    def decorator(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return func(*args, **kwargs)
    return decorator
