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
import logging

from time import strptime
from datetime import datetime

from checkbox.report import Report
from checkbox.reports.xml_report import (XmlReportManager, XmlReport,
    convert_bool)


class LaunchpadReportManager(XmlReportManager):

    def __init__(self, *args, **kwargs):
        super(LaunchpadReportManager, self).__init__(*args, **kwargs)
        self.add(HalReport())
        self.add(LsbReport())
        self.add(PackagesReport())
        self.add(ProcessorsReport())
        self.add(SummaryReport())
        self.add(QuestionsReport())


class HalReport(XmlReport):
    """Report for HAL related data types."""

    def register_dumps(self):
        for (dt, dh) in [("hal", self.dumps_hal)]:
            self._manager.handle_dumps(dt, dh)

    def register_loads(self):
        for (lt, lh) in [("hal", self.loads_hal)]:
            self._manager.handle_loads(lt, lh)

    def dumps_hal(self, obj, parent):
        logging.debug("Dumping hal")
        parent.setAttribute("version", obj["version"])
        for device in obj["devices"].values():
            element = self._create_element("device", parent)
            element.setAttribute("id", str(device.id))
            element.setAttribute("udi", device.info.udi)
            self.dumps_device(device, element)

    def dumps_device(self, obj, parent, keys=[]):
        from checkbox.registry import Registry

        for key, value in obj.items():
            if isinstance(value, Registry):
                self.dumps_device(value, parent, keys + [key])
            else:
                key = ".".join(keys + [key])
                self._manager.call_dumps({key: value}, parent)

    def loads_hal(self, node):
        logging.debug("Loading hal")
        hal = {}
        hal["version"] = node.getAttribute("version")
        hal["devices"] = []
        for device in (d for d in node.childNodes if d.localName == "device"):
            value = self._manager.call_loads(device)
            hal["devices"].append(value)
        return hal


class LsbReport(Report):

    def register_dumps(self):
        for (dt, dh) in [("lsbrelease", self.dumps_lsbrelease)]:
            self._manager.handle_dumps(dt, dh)

    def dumps_lsbrelease(self, obj, parent):
        logging.debug("Dumping lsbrelease")
        for key, value in obj.items():
            property = self._create_element("property", parent)
            property.setAttribute("name", key)
            self._manager.call_dumps(value, property)


class PackagesReport(Report):
    """Report for package related data types."""

    def register_dumps(self):
        self._manager.handle_dumps("packages", self.dumps_packages)

    def register_loads(self):
        self._manager.handle_loads("packages", self.loads_packages)

    def dumps_packages(self, obj, parent):
        logging.debug("Dumping packages")
        for package in obj:
            element = self._create_element("package", parent)
            element.setAttribute("id", str(package.id))

            package = dict(package)
            element.setAttribute("name", package.pop("name"))
            self._manager.call_dumps(package, element)

    def loads_packages(self, node):
        logging.debug("Loading packages")
        packages = []
        for package in (p for p in node.childNodes if p.localName == "package"):
            value = self._manager.call_loads(package)
            value["name"] = package.getAttribute("name")
            packages.append(value)

        return packages


class ProcessorsReport(Report):
    """Report for processor related data types."""

    def register_dumps(self):
        self._manager.handle_dumps("processors", self.dumps_processors)

    def register_loads(self):
        self._manager.handle_loads("processors", self.loads_processors)

    def dumps_processors(self, obj, parent):
        logging.debug("Dumping processors")
        for processor in obj:
            element = self._create_element("processor", parent)
            element.setAttribute("id", str(processor.id))

            processor = dict(processor)
            element.setAttribute("name", str(processor.pop("name")))
            self._manager.call_dumps(processor, element)

    def loads_processors(self, node):
        logging.debug("Loading processors")
        processors = []
        for processor in (p for p in node.childNodes if p.localName == "processor"):
            value = self._manager.call_loads(processor)
            value["name"] = processor.getAttribute("name")
            processors.append(value)

        return processors


class SummaryReport(Report):
    """Report for summary related data types."""

    def register_dumps(self):
        for (dt, dh) in [("live_cd", self.dumps_value),
                         ("system_id", self.dumps_value),
                         ("distribution", self.dumps_value),
                         ("distroseries", self.dumps_value),
                         ("architecture", self.dumps_value),
                         ("private", self.dumps_value),
                         ("contactable", self.dumps_value),
                         ("date_created", self.dumps_datetime),
                         ("client", self.dumps_client)]:
            self._manager.handle_dumps(dt, dh)

    def register_loads(self):
        for (lt, lh) in [("live_cd", self.loads_bool),
                         ("system_id", self.loads_str),
                         ("distribution", self.loads_str),
                         ("distroseries", self.loads_str),
                         ("architecture", self.loads_str),
                         ("private", self.loads_bool),
                         ("contactable", self.loads_bool),
                         ("date_created", self.loads_datetime),
                         ("client", self.loads_client)]:
            self._manager.handle_loads(lt, lh)

    def dumps_value(self, obj, parent):
        parent.setAttribute("value", str(obj))

    def dumps_datetime(self, obj, parent):
        parent.setAttribute("value", str(obj).split(".")[0])

    def dumps_client(self, obj, parent):
        parent.setAttribute("name", obj["name"])
        parent.setAttribute("version", obj["version"])

    def loads_bool(self, node):
        return convert_bool(node.getAttribute("value"))

    def loads_str(self, node):
        return str(node.getAttribute("value"))

    def loads_datetime(self, node):
        value = node.getAttribute("value")
        return datetime(*strptime(value, "%Y-%m-%dT%H:%M:%S")[0:7])

    def loads_client(self, node):
        name = node.getAttribute("name")
        version = node.getAttribute("version")
        return {"name": name, "version": version}


class QuestionsReport(Report):
    """Report for question related data types."""

    def register_dumps(self):
        for (dt, dh) in [("questions", self.dumps_questions)]:
            self._manager.handle_dumps(dt, dh)

    def register_loads(self):
        for (lt, lh) in [("questions", self.loads_questions),
                         ("answer", self.loads_data),
                         ("answer_choices", self.loads_none),
                         ("comment", self.loads_data)]:
            self._manager.handle_loads(lt, lh)

    def dumps_questions(self, obj, parent):
        logging.debug("Dumping questions")
        for question in obj:
            element = self._create_element("question", parent)
            element.setAttribute("name", question["name"])
            self.dumps_answer(question["result"]["status"], element)
            self.dumps_comment(question["result"]["data"], element)

    def dumps_answer(self, obj, parent):
        from checkbox.result import ALL_STATUS

        answer = self._create_element("answer", parent)
        answer.setAttribute("type", "multiple_choice")
        self._create_text_node(str(obj), answer)

        answer_choices = self._create_element("answer_choices", parent)
        for choice in ALL_STATUS:
            value = self._create_element("value", answer_choices)
            self._manager.call_dumps(choice, value)

    def dumps_comment(self, obj, parent):
        comment = self._create_element("comment", parent)
        self._create_text_node(str(obj), comment)

    def dumps_text(self, obj, parent):
        self._create_text_node(str(obj), parent)

    def loads_questions(self, node):
        logging.debug("Loading questions")
        questions = []
        for question in (q for q in node.childNodes if q.localName == "question"):
            value = self._manager.call_loads(question)
            value["name"] = question.getAttribute("name")
            questions.append(value)
        return questions

    def loads_none(self, node):
        return None

    def loads_data(self, node):
        return node.firstChild.data.strip()

