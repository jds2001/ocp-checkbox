#
# This file is part of Checkbox.
#
# Copyright 2011 Canonical Ltd.
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
import re

from os import uname

from checkbox.lib.conversion import string_to_type


class CpuinfoParser:
    """Parser for the /proc/cpuinfo file."""

    def __init__(self, stream, machine=None):
        self.stream = stream
        self.machine = machine or uname()[4].lower()

    def getAttributes(self):
        count = 0
        attributes = {}
        cpuinfo = self.stream.read()
        for block in re.split(r"\n{2,}", cpuinfo):
            block = block.strip()
            if not block:
                continue

            count += 1
            if count > 1:
                continue

            for line in block.split("\n"):
                if not line:
                    continue
                key, value = line.split(":", 1)
                key, value = key.strip(), value.strip()

                # Handle bogomips on sparc
                if key.endswith("Bogo"):
                    key = "bogomips"

                attributes[key.lower()] = value

        if attributes:
            attributes["count"] = count

        return attributes

    def run(self, result):
        attributes = self.getAttributes()
        if not attributes:
            return

        # Default values
        machine = self.machine
        processor = {
            "platform": machine,
            "count": 1,
            "type": machine,
            "model": machine,
            "model_number": "",
            "model_version": "",
            "model_revision": "",
            "cache": 0,
            "bogomips": 0,
            "speed": -1,
            "other": ""}

        # Conversion table
        platform_to_conversion = {
            ("i386", "i486", "i586", "i686", "x86_64",): {
                "type": "vendor_id",
                "model": "model name",
                "model_number": "cpu family",
                "model_version": "model",
                "model_revision": "stepping",
                "cache": "cache size",
                "other": "flags",
                "speed": "cpu mhz"},
            ("alpha", "alphaev6",): {
                "count": "cpus detected",
                "type": "cpu",
                "model": "cpu model",
                "model_number": "cpu variation",
                "model_version": ("system type", "system variation",),
                "model_revision": "cpu revision",
                "other": "platform string",
                "speed": "cycle frequency [Hz]"},
            ("armv7l",): {
                "type": "hardware",
                "model": "processor",
                "model_number": "cpu variant",
                "model_version": "cpu architecture",
                "model_revision": "cpu revision",
                "other": "features"},
            ("ia64",): {
                "type": "vendor",
                "model": "family",
                "model_version": "archrev",
                "model_revision": "revision",
                "other": "features",
                "speed": "cpu mhz"},
            ("ppc64", "ppc",): {
                "type": "platform",
                "model": "cpu",
                "model_version": "revision",
                "speed": "clock"},
            ("sparc64", "sparc",): {
                "count": "ncpus probed",
                "type": "type",
                "model": "cpu",
                "model_version": "type",
                "speed": "bogomips"}}

        processor["count"] = attributes.get("count", 1)
        bogompips_string = attributes.get("bogomips", "0.0")
        processor["bogomips"] = int(round(float(bogompips_string)))
        for platform, conversion in platform_to_conversion.items():
            if machine in platform:
                for pkey, ckey in conversion.items():
                    if isinstance(ckey, (list, tuple)):
                        processor[pkey] = "/".join([attributes[k]
                                                    for k in ckey])
                    elif ckey in attributes:
                        processor[pkey] = attributes[ckey]

        # Adjust platform
        if machine[0] == "i" and machine[-2:] == "86":
            processor["platform"] = "i386"
        elif machine[:5] == "alpha":
            processor["platform"] = "alpha"

        # Adjust cache
        if processor["cache"]:
            processor["cache"] = string_to_type(processor["cache"])

        # Adjust speed
        try:
            if machine[:5] == "alpha":
                speed = processor["speed"].split()[0]
                processor["speed"] = int(round(float(speed))) / 1000000
            elif machine[:5] == "sparc":
                speed = processor["speed"]
                processor["speed"] = int(round(float(speed))) / 2
            else:
                if machine[:3] == "ppc":
                    # String is appended with "mhz"
                    speed = processor["speed"][:-3]
                else:
                    speed = processor["speed"]
                processor["speed"] = int(round(float(speed)) - 1)
        except ValueError:
            processor["speed"] = -1

        # Adjust count
        try:
            processor["count"] = int(processor["count"])
        except ValueError:
            processor["count"] = 1
        else:
            # There is at least one processor
            if processor["count"] == 0:
                processor["count"] = 1

        result.setProcessor(processor)
