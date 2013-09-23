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
:mod:`plainbox.impl.service` -- DBus service for PlainBox
=========================================================
"""

from threading import Thread
import collections
import functools
import itertools
import logging
import random

try:
    from inspect import Signature
except ImportError:
    try:
        from plainbox.vendor.funcsigs import Signature
    except ImportError:
        raise SystemExit("DBus parts require 'funcsigs' from pypi.")
from plainbox.vendor import extcmd

from plainbox.impl import dbus
from plainbox.impl.dbus import OBJECT_MANAGER_IFACE
from plainbox.impl.result import DiskJobResult
from plainbox.impl.runner import JobRunner
from plainbox.impl.signal import Signal


logger = logging.getLogger("plainbox.service")

_BASE_IFACE = "com.canonical.certification."

SERVICE_IFACE = _BASE_IFACE + "PlainBox.Service1"
SESSION_IFACE = _BASE_IFACE + "PlainBox.Session1"
PROVIDER_IFACE = _BASE_IFACE + "PlainBox.Provider1"
JOB_IFACE = _BASE_IFACE + "PlainBox.JobDefinition1"
JOB_RESULT_IFACE = _BASE_IFACE + "PlainBox.Result1"
JOB_STATE_IFACE = _BASE_IFACE + "PlainBox.JobState1"
WHITELIST_IFACE = _BASE_IFACE + "PlainBox.WhiteList1"
CHECKBOX_JOB_IFACE = _BASE_IFACE + "CheckBox.JobDefinition1"
RUNNING_JOB_IFACE = _BASE_IFACE + "PlainBox.RunningJob1"


class PlainBoxObjectWrapper(dbus.service.ObjectWrapper):
    """
    Wrapper for exporting PlainBox object over DBus.

    Allows to keep the python object logic separate from the DBus counterpart.
    Has a set of utility methods to publish the object and any children objects
    to DBus.
    """

    # Use a different logger for the translate decorator.
    # This is just so that we don't spam people that want to peek
    # at the service module.
    _logger = logging.getLogger("plainbox.dbus.service.translate")

    def __init__(self,
                 native,
                 conn=None, object_path=None, bus_name=None,
                 **kwargs):
        super(PlainBoxObjectWrapper, self).__init__(
            native, conn, object_path, bus_name)
        logger.debug("Created DBus wrapper for: %r", self.native)
        self.__shared_initialize__(**kwargs)

    def __shared_initialize__(self, **kwargs):
        """
        Optional initialize method that can use any unused keyword arguments
        that were originally passed to __init__(). This makes it far easier to
        subclass as __init__() is rather complicated.

        Inspired by STANDARD GENERIC FUNCTION SHARED-INITIALIZE
        See hyperspec page: http://clhs.lisp.se/Body/f_shared.htm
        """

    def _get_preferred_object_path(self):
        """
        Return the preferred object path of this object on DBus
        """
        return "/plainbox/{}/{}".format(
            self.native.__class__.__name__, id(self.native))

    def publish_self(self, connection):
        """
        Publish this object to the connection
        """
        object_path = self._get_preferred_object_path()
        self.add_to_connection(connection, object_path)
        logger.debug("Published DBus wrapper for %r as %s",
                     self.native, object_path)

    def publish_related_objects(self, connection):
        """
        Publish this and any other objects to the connection

        Do not send ObjectManager events, just register any additional objects
        on the bus. By default only the object itself is published but
        collection managers are expected to publish all of the children here.
        """
        self.publish_self(connection)

    def publish_managed_objects(self):
        """
        This method is specific to ObjectManager, it basically adds children
        and sends the right events. This is a separate stage so that the whole
        hierarchy can first put all of the objects on the bus and then tell the
        world about it in one big signal message.
        """

    @classmethod
    def translate(cls, func):
        """
        Decorator for Wrapper methods.

        The decorated method does not need to manually lookup objects when the
        caller (across DBus) passes an object path. Type information is
        provided using parameter annotations.

        The annotation accepts DBus type expressions (but in practice it is
        very limited). For the moment it cannot infer the argument types from
        the decorator for dbus.service.method.
        """
        sig = Signature.from_function(func)

        def translate_o(object_path):
            try:
                obj = cls.find_object_by_path(object_path)
            except KeyError as exc:
                raise dbus.exceptions.DBusException((
                    "object path {} does not designate an existing"
                    " object").format(exc))
            else:
                return obj.native

        def translate_ao(object_path_list):
            try:
                obj_list = [cls.find_object_by_path(object_path)
                            for object_path in object_path_list]
            except KeyError as exc:
                raise dbus.exceptions.DBusException((
                    "object path {} does not designate an existing"
                    " object").format(exc))
            else:
                return [obj.native for obj in obj_list]

        def translate_return_o(obj):
            try:
                return cls.find_wrapper_by_native(obj)
            except KeyError:
                raise dbus.exceptions.DBusException(
                    "(o) internal error, unable to lookup object wrapper")

        def translate_return_ao(object_list):
            try:
                return dbus.types.Array([
                    cls.find_wrapper_by_native(obj)
                    for obj in object_list
                ], signature='o')
            except KeyError:
                raise dbus.exceptions.DBusException(
                    "(ao) internal error, unable to lookup object wrapper")

        def translate_return_a_brace_so_brace(mapping):
            try:
                return dbus.types.Dictionary({
                    key: cls.find_wrapper_by_native(value)
                    for key, value in mapping.items()
                }, signature='so')
            except KeyError:
                raise dbus.exceptions.DBusException(
                    "(a{so}) internal error, unable to lookup object wrapper")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            cls._logger.debug(
                "wrapped %s called with %s", func, bound.arguments)
            for param in sig.parameters.values():
                if param.annotation is Signature.empty:
                    pass
                elif param.annotation == 'o':
                    object_path = bound.arguments[param.name]
                    bound.arguments[param.name] = translate_o(object_path)
                elif param.annotation == 'ao':
                    object_path_list = bound.arguments[param.name]
                    bound.arguments[param.name] = translate_ao(
                        object_path_list)
                elif param.annotation in ('s', 'as'):
                    strings = bound.arguments[param.name]
                    bound.arguments[param.name] = strings
                else:
                    raise ValueError(
                        "unsupported translation {!r}".format(
                            param.annotation))
            cls._logger.debug(
                "unwrapped %s called with %s", func, bound.arguments)
            retval = func(**bound.arguments)
            cls._logger.debug("unwrapped %s returned %r", func, retval)
            if sig.return_annotation is Signature.empty:
                pass
            elif sig.return_annotation == 'o':
                retval = translate_return_o(retval)
            elif sig.return_annotation == 'ao':
                retval = translate_return_ao(retval)
            elif sig.return_annotation == 'a{so}':
                retval = translate_return_a_brace_so_brace(retval)
            else:
                raise ValueError(
                    "unsupported translation {!r}".format(
                        sig.return_annotation))
            cls._logger.debug("wrapped %s returned  %r", func, retval)
            return retval
        return wrapper


class JobDefinitionWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing JobDefinition objects on DBus
    """

    HIDDEN_INTERFACES = frozenset([
        OBJECT_MANAGER_IFACE,
    ])

    # Some internal helpers

    def __shared_initialize__(self, **kwargs):
        self._checksum = self.native.get_checksum()

    def _get_preferred_object_path(self):
        # TODO: this clashes with providers, maybe use a random ID instead
        return "/plainbox/job/{}".format(self._checksum)

    # PlainBox properties

    @dbus.service.property(dbus_interface=JOB_IFACE, signature="s")
    def name(self):
        return self.native.name

    @dbus.service.property(dbus_interface=JOB_IFACE, signature="s")
    def description(self):
        return self.native.description or ""

    @dbus.service.property(dbus_interface=JOB_IFACE, signature="s")
    def checksum(self):
        # This is a bit expensive to compute so let's keep it cached
        return self._checksum

    @dbus.service.property(dbus_interface=JOB_IFACE, signature="s")
    def requires(self):
        return self.native.requires or ""

    @dbus.service.property(dbus_interface=JOB_IFACE, signature="s")
    def depends(self):
        return self.native.depends or ""

    @dbus.service.property(dbus_interface=JOB_IFACE, signature="d")
    def estimated_duration(self):
        return self.native.estimated_duration or -1

    # PlainBox methods

    @dbus.service.method(dbus_interface=JOB_IFACE,
                         in_signature='', out_signature='as')
    def GetDirectDependencies(self):
        return self.native.get_direct_dependencies()

    @dbus.service.method(dbus_interface=JOB_IFACE,
                         in_signature='', out_signature='as')
    def GetResourceDependencies(self):
        return self.native.get_resource_dependencies()

    @dbus.service.method(dbus_interface=CHECKBOX_JOB_IFACE,
                         in_signature='', out_signature='as')
    def GetEnvironSettings(self):
        return self.native.get_environ_settings()

    # CheckBox properties

    @dbus.service.property(dbus_interface=CHECKBOX_JOB_IFACE, signature="s")
    def plugin(self):
        return self.native.plugin

    @dbus.service.property(dbus_interface=CHECKBOX_JOB_IFACE, signature="s")
    def via(self):
        return self.native.via or ""

    @dbus.service.property(
        dbus_interface=CHECKBOX_JOB_IFACE, signature="(suu)")
    def origin(self):
        if self.native.origin is not None:
            return dbus.Struct([
                self.native.origin.filename,
                self.native.origin.line_start,
                self.native.origin.line_end
            ], signature="suu")
        else:
            return dbus.Struct(["", 0, 0], signature="suu")

    @dbus.service.property(dbus_interface=CHECKBOX_JOB_IFACE, signature="s")
    def command(self):
        return self.native.command or ""

    @dbus.service.property(dbus_interface=CHECKBOX_JOB_IFACE, signature="s")
    def environ(self):
        return self.native.environ or ""

    @dbus.service.property(dbus_interface=CHECKBOX_JOB_IFACE, signature="s")
    def user(self):
        return self.native.user or ""


class WhiteListWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing WhiteList objects on DBus
    """

    HIDDEN_INTERFACES = frozenset([
        OBJECT_MANAGER_IFACE,
    ])

    # Some internal helpers

    def _get_preferred_object_path(self):
        # TODO: this clashes with providers, maybe use a random ID instead
        return "/plainbox/whitelist/{}".format(self.native.name.replace("-", "_"))

    # Value added

    @dbus.service.property(dbus_interface=WHITELIST_IFACE, signature="s")
    def name(self):
        """
        name of this whitelist
        """
        return self.native.name or ""

    @dbus.service.method(
        dbus_interface=WHITELIST_IFACE, in_signature='', out_signature='as')
    def GetPatternList(self):
        """
        Get a list of regular expression patterns that make up this whitelist
        """
        return [qualifier.pattern_text
                for qualifier in self.native.inclusive_qualifier_list]

    @dbus.service.method(
        dbus_interface=WHITELIST_IFACE, in_signature='o', out_signature='b')
    @PlainBoxObjectWrapper.translate
    def Designates(self, job: 'o'):
        return self.native.designates(job)


class JobResultWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing JobResult objects on DBus
    """

    HIDDEN_INTERFACES = frozenset([
        OBJECT_MANAGER_IFACE,
    ])

    def __shared_initialize__(self, **kwargs):
        self.native.on_comments_changed.connect(self.on_comments_changed)
        self.native.on_outcome_changed.connect(self.on_outcome_changed)

    def __del__(self):
        self.native.on_comments_changed.disconnect(self.on_comments_changed)
        self.native.on_outcome_changed.disconnect(self.on_outcome_changed)

    # Value added

    @dbus.service.property(dbus_interface=JOB_RESULT_IFACE, signature="s")
    def outcome(self):
        """
        outcome of the job

        The result is one of a set of fixed strings
        """
        # XXX: it would be nice if we could not do this remapping.
        return self.native.outcome or "none"

    @outcome.setter
    def outcome(self, new_value):
        """
        set outcome of the job to a new value
        """
        # XXX: it would be nice if we could not do this remapping.
        if new_value == "none":
            new_value = None
        self.native.outcome = new_value

    @Signal.define
    def on_outcome_changed(self, old, new):
        logger.debug("on_outcome_changed(%r, %r)", old, new)
        self.PropertiesChanged(JOB_RESULT_IFACE, {
            self.__class__.outcome._dbus_property: new
        }, [])

    @dbus.service.property(dbus_interface=JOB_RESULT_IFACE, signature="d")
    def execution_duration(self):
        """
        The amount of time in seconds it took to run this jobs command.

        :returns:
            The value of execution_duration or -1.0 if the command was not
            executed yet.
        """
        execution_duration = self.native.execution_duration
        if execution_duration is None:
            return -1.0
        else:
            return execution_duration

    @dbus.service.property(dbus_interface=JOB_RESULT_IFACE, signature="v")
    def return_code(self):
        """
        return code of the called program
        """
        value = self.native.return_code
        if value is None:
            return ""
        else:
            return value

    # comments are settable, useful thing that

    @dbus.service.property(dbus_interface=JOB_RESULT_IFACE, signature="s")
    def comments(self):
        """
        Comment added by the operator
        """
        return self.native.comments or ""

    @comments.setter
    def comments(self, value):
        self.native.comments = value

    @Signal.define
    def on_comments_changed(self, old, new):
        logger.debug("on_comments_changed(%r, %r)", old, new)
        self.PropertiesChanged(JOB_RESULT_IFACE, {
            self.__class__.comments._dbus_property: new
        }, [])

    @dbus.service.property(
        dbus_interface=JOB_RESULT_IFACE, signature="a(dsay)")
    def io_log(self):
        """
        The input-output log.

        Contains a record of all of the output (actually,
        it has no input logs) that was sent by the called program.

        The format is: array<struct<double, string, array<bytes>>>
        """
        return dbus.types.Array(self.native.get_io_log(), signature="(dsay)")


class JobStateWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing JobState objects on DBus
    """

    HIDDEN_INTERFACES = frozenset([
        OBJECT_MANAGER_IFACE,
    ])

    def __shared_initialize__(self, **kwargs):
        self._result_wrapper = JobResultWrapper(self.native.result)

    def publish_related_objects(self, connection):
        super(JobStateWrapper, self).publish_related_objects(connection)
        self._result_wrapper.publish_related_objects(connection)

    # Value added

    @dbus.service.method(
        dbus_interface=JOB_STATE_IFACE, in_signature='', out_signature='b')
    def CanStart(self):
        """
        Quickly check if the associated job can run right now.
        """
        return self.native.can_start()

    @dbus.service.method(
        dbus_interface=JOB_STATE_IFACE, in_signature='', out_signature='s')
    def GetReadinessDescription(self):
        """
        Get a human readable description of the current readiness state
        """
        return self.native.get_readiness_description()

    @dbus.service.property(dbus_interface=JOB_STATE_IFACE, signature='o')
    @PlainBoxObjectWrapper.translate
    def job(self) -> 'o':
        """
        Job associated with this state
        """
        return self.native.job

    @dbus.service.property(dbus_interface=JOB_STATE_IFACE, signature='o')
    @PlainBoxObjectWrapper.translate
    def result(self) -> 'o':
        """
        Result of running the associated job
        """
        return self.native.result

    @Signal.define
    def on_result_changed(self):
        result_wrapper = JobResultWrapper(self.native.result)
        try:
            result_wrapper.publish_related_objects(self.connection)
        except KeyError:
            logger.warning("Result already exists for: %r", result_wrapper)
            self.PropertiesChanged(JOB_STATE_IFACE, {
                self.__class__.result._dbus_property:
                result_wrapper._get_preferred_object_path()
            }, [])
        else:
            self.PropertiesChanged(JOB_STATE_IFACE, {
                self.__class__.result._dbus_property: result_wrapper
            }, [])

    @dbus.service.property(dbus_interface=JOB_STATE_IFACE, signature='a(isss)')
    def readiness_inhibitor_list(self):
        """
        The list of readiness inhibitors of the associated job

        The list is represented as an array of structures. Each structure
        has a integer and two strings. The integer encodes the cause
        of inhibition.

        Cause may have one of the following values:

        0 - UNDESIRED:
            This job was not selected to run in this session

        1 - PENDING_DEP:
           This job depends on another job which was not started yet

        2 - FAILED_DEP:
            This job depends on another job which was started and failed

        3 - PENDING_RESOURCE:
            This job has a resource requirement expression that uses a resource
            produced by another job which was not started yet

        4 - FAILED_RESOURCE:
            This job has a resource requirement that evaluated to a false value

        The next two strings are the name of the related job and the name
        of the related expression. Either may be empty.
        """
        return dbus.types.Array([
            (inhibitor.cause,
             inhibitor.cause_name,
             (inhibitor.related_job.name
              if inhibitor.related_job is not None else ""),
             (inhibitor.related_expression.text
              if inhibitor.related_expression is not None else ""))
            for inhibitor in self.native.readiness_inhibitor_list
        ], signature="(isss)")


class SessionWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing SessionState objects on DBus
    """

    HIDDEN_INTERFACES = frozenset()

    # XXX: those will change to SessionManager later and session state will be
    # a part of that (along with session storage)

    def __shared_initialize__(self, **kwargs):
        self._job_state_map_wrapper = {
            job_name: JobStateWrapper(job_state)
            for job_name, job_state in self.native.job_state_map.items()
        }

    def publish_related_objects(self, connection):
        self.publish_self(connection)
        for job_state in self._job_state_map_wrapper.values():
            job_state.publish_related_objects(connection)

    def publish_managed_objects(self):
        wrapper_list = list(self._iter_wrappers())
        self.add_managed_object_list(wrapper_list)
        for wrapper in wrapper_list:
            wrapper.publish_managed_objects()

    def _iter_wrappers(self):
        return itertools.chain(
            # Get all of the JobResult wrappers
            self._job_state_map_wrapper.values(),
            # And all the JobDefinition wrappers
            [self.find_wrapper_by_native(job_state_wrapper.native.result)
             for job_state_wrapper in self._job_state_map_wrapper.values()])

    def check_and_wrap_new_jobs(self):
        # Since new jobs may have been added, we need to create and publish
        # new JobDefinitionWrappers for them.
        for job in self.native.job_list:
            key = id(job)
            if not key in self._native_id_to_wrapper_map:
                logger.debug("Creating a new JobDefinitionWrapper for %s",
                             job.name)
                wrapper = JobDefinitionWrapper(job)
                wrapper.publish_related_objects(self.connection)
                #Newly created jobs also need a JobState.
                #Note that publishing the JobState also should automatically
                #publish the MemoryJobResult.
                self._job_state_map_wrapper[job.name] = JobStateWrapper(
                        self.native.job_state_map[job.name])
                self._job_state_map_wrapper[job.name].publish_related_objects(
                        self.connection)

    # Value added

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='ao', out_signature='as')
    @PlainBoxObjectWrapper.translate
    def UpdateDesiredJobList(self, desired_job_list: 'ao'):
        logger.info("UpdateDesiredJobList(%r)", desired_job_list)
        problem_list = self.native.update_desired_job_list(desired_job_list)
        # Do the necessary housekeeping for any new jobs
        self.check_and_wrap_new_jobs()
        # TODO: map each problem into a structure (check which fields should be
        # presented). Document this in the docstring.
        return [str(problem) for problem in problem_list]

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='oo', out_signature='')
    @PlainBoxObjectWrapper.translate
    def UpdateJobResult(self, job: 'o', result: 'o'):
        self.native.update_job_result(job, result)

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='', out_signature='(dd)')
    def GetEstimatedDuration(self):
        automated, manual = self.native.get_estimated_duration()
        if automated is None:
            automated = -1.0
        if manual is None:
            manual = -1.0
        return automated, manual

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='', out_signature='s')
    def PreviousSessionFile(self):
        previous_session_file = self.native.previous_session_file()
        if previous_session_file:
            return previous_session_file
        else:
            return ''

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='', out_signature='')
    def Resume(self):
        #FIXME TODO XXX KLUDGE ALERT
        #The way we replace restored job definitions with the ones from the
        #freshly-initialized session is extremely kludgy. This implementation
        #needs to be revisited at some point and made cleaner. It was done this
        #way to unblock usage of this API under time pressure.
        #
        #First, we take a snapshot of job definitions from the "pristine"
        #session. These already have JobStateWrappers over DBus pointing to
        #the ones created when the provider was exposed.
        old_jobs = [state.job for state in self.native.job_state_map.values()]
        #Now, native resume. This is the only non-kludgy line in this method.
        self.native.resume()
        #After the native resume completes, we need to "synchronize"
        #the new job_list and job_state_map over DBus. This is very similar
        # to what we do
        #when adding jobs from a local job, with the exception that here,
        #*all* the jobs need a JobStateWrapper because since they weren't
        #known when the session was created, they don't have one yet.
        # Also, we need to take the jobs as contained in the job_state_map,
        #rather than job_list, otherwise they won't point to the correct
        #dbus JobDefinition.
        #Finally, the KLUDGE is that we look at the job definitions for each
        #JobState. These were reconstructed from restored session information,
        #and unfortunately they don't map to the exposed-over-dbus JobDefs.
        #However, we can't just create the JobDefinition because since they're
        #exposed over DBus using their unique checksum, trying to expose an
        #identical JobDefinition will create a clash and a crash.
        #The solution, then, is to replace each JobState's "job" attribute
        #with the equivalent job from the old_jobs map. Those *should* be
        #identical value-wise but point to the correct, already-exposed
        #JobDefinition and their wrapper.
        for job_state in self.native.job_state_map.values():
            job = job_state.job
            #Find old equivalent of this job
            if job in old_jobs:
                 index = old_jobs.index(job)
                 #Next three statements are for debugging only, they further
                 #underline the kludgy nature of this section of code.
                 old_id = id(job)
                 new_id = id(old_jobs[index])
                 logger.debug("Replacing object %s with %s for job %s" %
                              (old_id, new_id, job.name))
                 job_state.job = old_jobs[index]
            else:
                #Here we just create new JobDefinitionWrappers, like we
                #do in check_and_wrap_new_jobs, in case the session contained
                #a job whose definition we don't have (i.e. one created by
                #local jobs). I haven't seen this happen yet.
                if not id(job) in self._native_id_to_wrapper_map:
                    logger.debug("Creating a new JobDefinitionWrapper for %s",
                                 job.name)
                    wrapper = JobDefinitionWrapper(job)
                    wrapper.publish_related_objects(self.connection)

            #By here, either job definitions already exist, or they
            #have been created. Create and publish the corresponding
            #JobStateWrapper. Note that the JobStates already  had their
            #'job' attribute pointed to an existing, mapped JobDefinition
            #object.
            self._job_state_map_wrapper[job.name] = JobStateWrapper(
                    self.native.job_state_map[job.name])
            self._job_state_map_wrapper[job.name].publish_related_objects(
                    self.connection)

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='', out_signature='')
    def Clean(self):
        self.native.clean()

    @dbus.service.method(
        dbus_interface=SESSION_IFACE, in_signature='', out_signature='')
    def PersistentSave(self):
        self.native.persistent_save()

    @dbus.service.property(dbus_interface=SESSION_IFACE, signature='ao')
    @PlainBoxObjectWrapper.translate
    def job_list(self) -> 'ao':
        return self.native.job_list

    # TODO: signal<run_list>

    @dbus.service.property(dbus_interface=SESSION_IFACE, signature='ao')
    @PlainBoxObjectWrapper.translate
    def desired_job_list(self) -> 'ao':
        return self.native.desired_job_list

    # TODO: signal<run_list>

    @dbus.service.property(dbus_interface=SESSION_IFACE, signature='ao')
    @PlainBoxObjectWrapper.translate
    def run_list(self) -> 'ao':
        return self.native.run_list

    # TODO: signal<run_list>

    @dbus.service.property(dbus_interface=SESSION_IFACE, signature='a{so}')
    @PlainBoxObjectWrapper.translate
    def job_state_map(self) -> 'a{so}':
        return self.native.job_state_map

    @Signal.define
    def on_job_state_map_changed(self):
        self.PropertiesChanged(SESSION_IFACE, {
            self.__class__.job_state_map._dbus_property: self.job_state_map
        }, [])

    @dbus.service.property(dbus_interface=SESSION_IFACE, signature='a{sv}')
    def metadata(self):
        return dbus.types.Dictionary({
            'title': self.native.metadata.title or "",
            'flags': dbus.types.Array(
                sorted(self.native.metadata.flags), signature='s'),
            'running_job_name': self.native.metadata.running_job_name or ""
        }, signature="sv")

    @metadata.setter
    def metadata(self, value):
        self.native.metadata.title = value['title']
        self.native.metadata.running_job_name = value['running_job_name']
        self.native.metadata.flags = value['flags']

    # TODO: signal<metadata>


class ProviderWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing Provider1 objects on DBus
    """

    HIDDEN_INTERFACES = frozenset()

    def __shared_initialize__(self, **kwargs):
        self._job_wrapper_list = [
            JobDefinitionWrapper(job)
            for job in self.native.get_builtin_jobs()]
        self._whitelist_wrapper_list = [
            WhiteListWrapper(whitelist)
            for whitelist in self.native.get_builtin_whitelists()]

    def _get_preferred_object_path(self):
        return "/plainbox/provider/{}".format(self.native.name)

    def publish_related_objects(self, connection):
        super(ProviderWrapper, self).publish_related_objects(connection)
        wrapper_list = list(self._iter_wrappers())
        for wrapper in wrapper_list:
            wrapper.publish_related_objects(connection)

    def publish_managed_objects(self):
        wrapper_list = list(self._iter_wrappers())
        self.add_managed_object_list(wrapper_list)

    def _iter_wrappers(self):
        return itertools.chain(
            self._job_wrapper_list,
            self._whitelist_wrapper_list)

    # Value added

    @dbus.service.property(dbus_interface=PROVIDER_IFACE, signature="s")
    def name(self):
        """
        name of this provider
        """
        return self.native.name

    @dbus.service.property(dbus_interface=PROVIDER_IFACE, signature="s")
    def description(self):
        """
        description of this provider
        """
        return self.native.description


class ServiceWrapper(PlainBoxObjectWrapper):
    """
    Wrapper for exposing Service objects on DBus
    """

    HIDDEN_INTERFACES = frozenset()

    # Internal setup stuff

    def __shared_initialize__(self, on_exit, **kwargs):
        self._on_exit = on_exit
        self._provider_wrapper_list = [
            ProviderWrapper(provider)
            for provider in self.native.provider_list]

    def _get_preferred_object_path(self):
        return "/plainbox/service1"

    def publish_related_objects(self, connection):
        super(ServiceWrapper, self).publish_related_objects(connection)
        for wrapper in self._provider_wrapper_list:
            wrapper.publish_related_objects(connection)

    def publish_managed_objects(self):
        # First publish all of our providers
        self.add_managed_object_list(self._provider_wrapper_list)
        # Then ask the providers to publish their own objects
        for wrapper in self._provider_wrapper_list:
            wrapper.publish_managed_objects()

    # Value added

    @dbus.service.property(dbus_interface=SERVICE_IFACE, signature="s")
    def version(self):
        """
        version of this provider
        """
        return self.native.version

    @dbus.service.method(
        dbus_interface=SERVICE_IFACE, in_signature='', out_signature='')
    def Exit(self):
        """
        Shut down the service and terminate
        """
        # TODO: raise exception when job is in progress
        self._on_exit()

    @dbus.service.method(
        dbus_interface=SERVICE_IFACE, in_signature='', out_signature='a{sas}')
    def GetAllExporters(self):
        """
        Get all exporters names and their respective options
        """
        return self.native.get_all_exporters()

    @dbus.service.method(
        dbus_interface=SERVICE_IFACE, in_signature='osas', out_signature='s')
    @PlainBoxObjectWrapper.translate
    def ExportSession(self, session: 'o', output_format: 's',
                      option_list: 'as'):
        return self.native.export_session(session, output_format, option_list)

    @dbus.service.method(
        dbus_interface=SERVICE_IFACE, in_signature='osass', out_signature='s')
    @PlainBoxObjectWrapper.translate
    def ExportSessionToFile(self, session: 'o', output_format: 's',
                      option_list: 'as', output_file: 's'):
        return self.native.export_session_to_file(session, output_format, option_list,
                                          output_file)

    @dbus.service.method(
        dbus_interface=SERVICE_IFACE, in_signature='ao', out_signature='o')
    @PlainBoxObjectWrapper.translate
    def CreateSession(self, job_list: 'ao'):
        # Create a session
        session_obj = self.native.create_session(job_list)
        # Wrap it
        session_wrp = SessionWrapper(session_obj)
        # Publish all objects
        session_wrp.publish_related_objects(self.connection)
        # Announce the session is there
        self.add_managed_object(session_wrp)
        # Announce any session children
        session_wrp.publish_managed_objects()
        # Return the session wrapper back
        return session_wrp

    @dbus.service.method(
        dbus_interface=SERVICE_IFACE, in_signature='oo', out_signature='')
    @PlainBoxObjectWrapper.translate
    def RunJob(self, session: 'o', job: 'o'):
        running_job_wrp = RunningJob(job, session, conn=self.connection)
        self.native.run_job(session, job, running_job_wrp)


class UIOutputPrinter(extcmd.DelegateBase):
    """
    Delegate for extcmd that redirect all output to the UI.
    """

    def __init__(self, runner):
        self._lineno = collections.defaultdict(int)
        self._runner = runner

    def on_line(self, stream_name, line):
        # FIXME: this is not a line number,
        # TODO: tie this into existing code in runner.py (the module)
        self._lineno[stream_name] += 1
        self._runner.IOLogGenerated(self._lineno[stream_name],
                                    stream_name, line)


class RunningJob(dbus.service.Object):
    """
    DBus representation of a running job.
    """

    def __init__(self, job, session, conn=None, object_path=None,
                 bus_name=None):
        if object_path is None:
            object_path = "/plainbox/jobrunner/{}".format(id(self))
        self.path = object_path
        dbus.service.Object.__init__(self, conn, self.path, bus_name)
        self.job = job
        self.session = session
        self.result = {}
        self.ui_io_delegate = UIOutputPrinter(self)

    @dbus.service.method(
        dbus_interface=RUNNING_JOB_IFACE, in_signature='', out_signature='')
    def Kill(self):
        pass

    @dbus.service.property(dbus_interface=RUNNING_JOB_IFACE, signature="s")
    def outcome_from_command(self):
        if self.result.get('return_code') is not None:
            if self.result.get('return_code') == 0:
                return "pass"
            else:
                return "fail"
        else:
            return ""

    @dbus.service.method(
        dbus_interface=RUNNING_JOB_IFACE, in_signature='ss', out_signature='')
    def SetOutcome(self, outcome, comments=None):
        self.result['outcome'] = outcome
        self.result['comments'] = comments
        job_result = DiskJobResult(self.result)
        self.emitJobResultAvailable(self.job, job_result)

    def _command_callback(self, return_code, record_path):
        self.result['return_code'] = return_code
        self.result['io_log_filename'] = record_path
        self.emitAskForOutcomeSignal()

    def _run_command(self, session, job, parent):
        """
        Run a Job command in a separate thread
        """
        ui_io_delegate = UIOutputPrinter(self)
        runner = JobRunner(session.session_dir, session.jobs_io_log_dir,
                           command_io_delegate=ui_io_delegate)
        return_code, record_path = runner._run_command(job, None)
        parent._command_callback(return_code, record_path)

    @dbus.service.method(
        dbus_interface=RUNNING_JOB_IFACE, in_signature='', out_signature='')
    def RunCommand(self):
        # FIXME: this thread object leaks, it needs to be .join()ed
        runner = Thread(target=self._run_command,
                        args=(self.session, self.job, self))
        runner.start()

    @dbus.service.signal(
        dbus_interface=SERVICE_IFACE, signature='dsay')
    def IOLogGenerated(self, offset, name, data):
        pass

    # XXX: Try to use PlainBoxObjectWrapper.translate here instead of calling
    # emitJobResultAvailable to do the translation
    @dbus.service.signal(
        dbus_interface=SERVICE_IFACE, signature='oo')
    def JobResultAvailable(self, job, result):
        pass

    @dbus.service.signal(
        dbus_interface=SERVICE_IFACE, signature='o')
    def AskForOutcome(self, runner):
        pass

    def emitAskForOutcomeSignal(self, *args):
        self.AskForOutcome(self.path)

    def emitJobResultAvailable(self, job, result):
        result_wrapper = JobResultWrapper(result)
        result_wrapper.publish_related_objects(self.connection)
        job_path = PlainBoxObjectWrapper.find_wrapper_by_native(job)
        result_path = PlainBoxObjectWrapper.find_wrapper_by_native(result)
        self.JobResultAvailable(job_path, result_path)

    def update_job_result_callback(self, job, result):
        self.emitJobResultAvailable(job, result)
