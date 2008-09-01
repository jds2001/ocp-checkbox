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
import os

from checkbox.lib.safe import safe_make_directory

from checkbox.plugin import Plugin
from checkbox.reports.launchpad_report import LaunchpadReportManager


class LaunchpadReport(Plugin):

    required_attributes = ["filename"]

    def register(self, manager):
        super(LaunchpadReport, self).register(manager)
        self._report = {
            "summary": {
                "private": False,
                "contactable": False,
                "live_cd": False},
            "hardware": {},
            "software": {
                "packages": []},
            "questions": []}

        # Launchpad report should be generated last.
        self._manager.reactor.call_on("report", self.report, 100)
        for (rt, rh) in [
             ("report-architecture", self.report_architecture),
             ("report-client", self.report_client),
             ("report-datetime", self.report_datetime),
             ("report-distribution", self.report_distribution),
             ("report-hal", self.report_hal),
             ("report-packages", self.report_packages),
             ("report-processors", self.report_processors),
             ("report-system_id", self.report_system_id),
             ("report-results", self.report_results)]:
            self._manager.reactor.call_on(rt, rh)

    def report_architecture(self, message):
        self._report["summary"]["architecture"] = message

    def report_hal(self, message):
        self._report["hardware"]["hal"] = message

    def report_client(self, message):
        self._report["summary"]["client"] = message

    def report_datetime(self, message):
        self._report["summary"]["date_created"] = message

    def report_distribution(self, message):
        self._report["software"]["lsbrelease"] = dict(message)
        self._report["summary"]["distribution"] = message.distributor_id
        self._report["summary"]["distroseries"] = message.release

    def report_packages(self, message):
        self._report["software"]["packages"].extend(message)

    def report_processors(self, message):
        self._report["hardware"]["processors"] = message

    def report_system_id(self, message):
        self._report["summary"]["system_id"] = message

    def report_results(self, message):
        self._report["questions"].extend(message)

    def report(self):
        # Prepare the payload and attach it to the form
        report_manager = LaunchpadReportManager("system", "1.0")
        payload = report_manager.dumps(self._report).toprettyxml("")

        filename = self.config.filename
        directory = os.path.dirname(filename)
        safe_make_directory(directory)

        open(filename, "w").write(payload)
        self._manager.reactor.fire("exchange-report", filename)


factory = LaunchpadReport
