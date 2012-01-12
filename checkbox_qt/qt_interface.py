#
# This file is part of Checkbox.
#
# Copyright 2008 Canonical Ltd.
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
import re, sys, time
import posixpath
import inspect
import gobject
import os

from gettext import gettext as _

from checkbox.job import UNINITIATED
from checkbox.user_interface import (UserInterface,
    NEXT, YES_ANSWER, NO_ANSWER, SKIP_ANSWER,
    ANSWER_TO_STATUS, STATUS_TO_ANSWER)
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import QObject, QVariant
from PyQt4.QtGui import QApplication, QProgressDialog, QLabel, QStandardItemModel, QStandardItem
from PyQt4.QtGui import QMessageBox
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from threading import Thread

class FrontEndThread(Thread):
   def __init__ (self):
      Thread.__init__(self)
   def run(self):
       os.system("python checkbox_qt/qt_front.py")

runAllTests = True
testsRunning = False

def funcname():
    return inspect.stack()[1][3]

class QTInterface(UserInterface):
    app = None
    formWindow = None
    def __init__(self, title, data_path):
        super(QTInterface, self).__init__(title, data_path)
        print "My name is: %s" % funcname()
        self.frontThread = FrontEndThread()
        self.frontThread.start()
        self._app_title = title
        notReady = True
        while notReady:
            try:
                self.bus = dbus.SessionBus(mainloop=DBusGMainLoop())
                self.qtfront = self.bus.get_object('com.canonical.QtCheckbox', '/com/canonical/qt_checkbox')
                self.qtiface = dbus.Interface(self.qtfront, dbus_interface='com.canonical.QtCheckbox')
                self.loop = gobject.MainLoop()
                notReady = False
            except:
                time.sleep(0.5)

    def _set_main_title(self, test_name=None):
        print "My name is: %s" % funcname()
        title = self._app_title
        if test_name:
            title += " - %s" % test_name
        self.qtiface.setWindowTitle(title)

    def show_progress_start(self, message):
        self.qtiface.startProgressBar(message)

    def show_progress_stop(self):
        self.qtiface.stopProgressBar()

    def show_progress_pulse(self):
        # not used if we have a main event loop
        pass

    def show_text(self, text, previous=None, next=None):
        print "My name is: %s" % funcname() + text
        def onFullTestsClicked():
            self.loop.quit()
        def onCustomTestsClicked():
            self.loop.quit()
        #Reset window title
        self._set_main_title()

        self.qtiface.showText(text)
        self.qtiface.connect_to_signal("onFullTestsClicked", onFullTestsClicked)
        self.qtiface.connect_to_signal("onCustomTestsClicked", onCustomTestsClicked)
        self.loop.run()
        #self.bus.remove_signal_receiver(onFullTestsClicked, "onFullTestsClicked")

    def show_entry(self, text, value, previous=None, next=None):
        print "My name is: %s" % funcname()
        return False

    def show_check(self, text, options=[], default=[]):
        print "My name is: %s" % funcname()
        return False

    def show_radio(self, text, options=[], default=None):
        print "My name is: %s" % funcname()
        return False

    def show_tree(self, text, options={}, default={}):
        print "My name is: %s" % funcname()
        def onStartTestsClicked():
            self.loop.quit()

        self._set_main_title()
        newOptions = {}
        for section in options:
            newTests = {}
            for test in options[section]:
                newTests[str(test)] = str("")

            newOptions[section] = newTests

        self.qtiface.showTree(text, newOptions)
        self.qtiface.connect_to_signal("onStartTestsClicked", onStartTestsClicked)

        self.loop.run()
        newOptions = {}
        for section in self.qtiface.getTestsToRun():
            newTests = {}
            for test in options[section]:
                newTests[str(test)] = {}
            newOptions[section] = newTests

        return newOptions

    def _run_test(self, test, runner):
        print "My name is: %s" % funcname()
        return False

    def show_test(self, test, runner):
        print "My name is: %s" % funcname()
        return False

    def show_info(self, text, options=[], default=None):
        print "My name is: %s" % funcname()
        return self.qtiface.showInfo(text, options, default)

    def show_error(self, text):
        self.qtiface.showError(text)

    def draw_image_head(self, widget, data):
        print "My name is: %s" % funcname()
        return False
