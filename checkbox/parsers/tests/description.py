# -*- coding: utf-8 -*-
#
# This file is part of Checkbox.
#
# Copyright 2012 Canonical Ltd.
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
from StringIO import StringIO

from unittest import TestCase

from checkbox.parsers.description import DescriptionParser


class DescriptionResult:

    purpose = None
    steps = None
    verification = None
    info = None

    def setDescription(self, purpose, steps, verification, info):
        self.purpose = purpose
        self.steps = steps
        self.verification = verification
        self.info = info


class TestDescriptionParser(TestCase):

    def getParser(self, string):
        stream = StringIO(string)
        return DescriptionParser(stream)

    def getResult(self, string):
        parser = self.getParser(string)
        result = DescriptionResult()
        parser.run(result)
        return result

    def assertResult(
        self, result, purpose=None, steps=None, verification=None, info=None):
        self.assertEquals(result.purpose, purpose)
        self.assertEquals(result.steps, steps)
        self.assertEquals(result.verification, verification)
        self.assertEquals(result.info, info)

    def test_empty(self):
        result = self.getResult("")
        self.assertEquals(result.purpose, None)

    def test_purpose(self):
        result = self.getResult("""
PURPOSE:
    foo
""")
        self.assertResult(result)

    def test_purpose_steps(self):
        result = self.getResult("""
PURPOSE:
    foo
STEPS:
    bar
""")
        self.assertResult(result)

    def test_purpose_steps_verification(self):
        result = self.getResult("""
PURPOSE:
    foo
STEPS:
    bar
VERIFICATION:
    baz
""")
        self.assertResult(result, "foo\n", "bar\n", "baz\n")

    def test_purpose_steps_info_verification(self):
        result = self.getResult("""
PURPOSE:
    foo
STEPS:
    bar
INFO:
    $output
VERIFICATION:
    baz
""")
        self.assertResult(result, "foo\n", "bar\n", "baz\n", "$output\n")

    def test_purpose_steps_verification_other(self):
        result = self.getResult("""
PURPOSE:
    foo
STEPS:
    bar
VERIFICATION:
    baz
OTHER:
    blah
""")
        self.assertResult(result)

    def test_es(self):
        result = self.getResult(u"""
PROPÓSITO:
     Esta prueba verifica los diferentes modos de vídeo detectados
PASOS:
     1. Se han detectado las siguientes pantallas y modos de vídeo
INFORMACIÓN:
     $ salida
VERIFICACIÓN:
     ¿Son las pantallas y los modos de vídeo correctos?
""")
        self.assertNotEquals(result.purpose, None)
        self.assertNotEquals(result.steps, None)
        self.assertNotEquals(result.verification, None)
        self.assertEquals(result.info, "$output\n")

    def test_ru(self):
        result = self.getResult(u"""
ЦЕЛЬ:
    Эта проверка позволит убедиться в работоспособности штекера наушников
ДЕЙСТВИЯ:
    1. Подсоедините наушники к вашему звуковому устройству
    2. Щёлкните кнопку Проверить для воспроизведения звукового сигнала через звуковое устройство
ПРОВЕРКА:
    Был ли слышен звук в наушниках и был ли он воспроизведён в ваших наушниках без искажений, щелчков или других искажённых звуков?"
""")
        self.assertNotEquals(result.purpose, None)
        self.assertNotEquals(result.steps, None)
        self.assertNotEquals(result.verification, None)
        self.assertEquals(result.info, None)