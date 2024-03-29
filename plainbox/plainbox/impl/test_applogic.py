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
plainbox.impl.test_applogic
===========================

Test definitions for plainbox.impl.applogic module
"""

from contextlib import contextmanager
from io import TextIOWrapper
from unittest import TestCase

import mock

from plainbox.impl.applogic import CompositeQualifier, NameJobQualifier
from plainbox.impl.applogic import IJobQualifier, RegExpJobQualifier
from plainbox.impl.applogic import PlainBoxConfig
from plainbox.impl.applogic import WhiteList
from plainbox.impl.applogic import get_matching_job_list
from plainbox.impl.config import Unset
from plainbox.impl.testing_utils import make_job


class JobQualifierTests(TestCase):

    def test_IJobQualifier_is_abstract(self):
        self.assertRaises(TypeError, IJobQualifier)

    def test_RegExpJobQualifier_smoke(self):
        qualifier = RegExpJobQualifier("foo")
        self.assertEqual(
            repr(qualifier), "<RegExpJobQualifier pattern:'foo'>")
        self.assertTrue(qualifier.designates(make_job("foo")))
        self.assertFalse(qualifier.designates(make_job("bar")))


class CompositeQualifierTests(TestCase):

    def test_empty(self):
        self.assertFalse(
            CompositeQualifier([], []).designates(
                make_job("foo")))

    def test_inclusive(self):
        self.assertTrue(
            CompositeQualifier(
                inclusive_qualifier_list=[RegExpJobQualifier('foo')],
                exclusive_qualifier_list=[]
            ).designates(make_job("foo")))
        self.assertFalse(
            CompositeQualifier(
                inclusive_qualifier_list=[RegExpJobQualifier('foo')],
                exclusive_qualifier_list=[]
            ).designates(make_job("bar")))

    def test_exclusive(self):
        self.assertFalse(
            CompositeQualifier(
                inclusive_qualifier_list=[],
                exclusive_qualifier_list=[RegExpJobQualifier('foo')]
            ).designates(make_job("foo")))
        self.assertFalse(
            CompositeQualifier(
                inclusive_qualifier_list=[RegExpJobQualifier(".*")],
                exclusive_qualifier_list=[RegExpJobQualifier('foo')]
            ).designates(make_job("foo")))
        self.assertTrue(
            CompositeQualifier(
                inclusive_qualifier_list=[RegExpJobQualifier(".*")],
                exclusive_qualifier_list=[RegExpJobQualifier('foo')]
            ).designates(make_job("bar")))


class WhiteListTests(TestCase):

    _name = 'whitelist.txt'

    _content = [
        "# this is a comment",
        "foo # this is another comment",
        "bar",
        ""
    ]

    @contextmanager
    def mocked_file(self, name, content):
        m_open = mock.MagicMock(name='open', spec=open)
        m_stream = mock.MagicMock(spec=TextIOWrapper)
        m_stream.__enter__.return_value = m_stream
        m_stream.__iter__.side_effect = lambda: iter(content)
        m_open.return_value = m_stream
        with mock.patch('plainbox.impl.applogic.open', m_open, create=True):
            yield
        m_open.assert_called_once_with(name, "rt", encoding="UTF-8")

    def test_load_patterns(self):
        with self.mocked_file(self._name, self._content):
            pattern_list = WhiteList._load_patterns(self._name)
        self.assertEqual(pattern_list, ['^foo$', '^bar$'])

    def test_smoke(self):
        with self.mocked_file(self._name, self._content):
            whitelist = WhiteList.from_file(self._name)
        self.assertEqual(
            repr(whitelist.inclusive_qualifier_list[0]),
            "<RegExpJobQualifier pattern:'^foo$'>")
        self.assertTrue(whitelist.designates(make_job('foo')))

    def test_repr(self):
        """
        verify that custom repr works
        """
        whitelist = WhiteList([], name="test")
        self.assertEqual(repr(whitelist), "<WhiteList name:'test'>")



class NameJobQualifierTests(TestCase):

    def test_smoke(self):
        self.assertTrue(NameJobQualifier('name').designates(make_job('name')))
        self.assertFalse(NameJobQualifier('nam').designates(make_job('name')))
        self.assertFalse(NameJobQualifier('.*').designates(make_job('name')))
        self.assertFalse(NameJobQualifier('*').designates(make_job('name')))

    def test_repr(self):
        self.assertEqual(
            repr(NameJobQualifier('name')), "<NameJobQualifier name:'name'>")


class FunctionTests(TestCase):

    def test_get_matching_job_list(self):
        job_list = [make_job('foo'), make_job('froz'), make_job('barg')]
        self.assertEqual(
            get_matching_job_list(job_list, RegExpJobQualifier('f.*')),
            [make_job('foo'), make_job('froz')])


class PlainBoxConfigTests(TestCase):

    def test_smoke(self):
        config = PlainBoxConfig()
        self.assertIs(config.secure_id, Unset)
        secure_id = "0123456789ABCDE"
        config.secure_id = secure_id
        self.assertEqual(config.secure_id, secure_id)
        with self.assertRaises(ValueError):
            config.secure_id = "bork"
        self.assertEqual(config.secure_id, secure_id)
        del config.secure_id
        self.assertIs(config.secure_id, Unset)
