import argparse
import fnmatch
import glob
import inspect
import os
import pprint
import pythoncom
import re
import shutil
import sys
import tempfile
import threading
import time
from   win32com.client import DispatchWithEvents
from   win32com.client import Dispatch
import win32com
import win32con
import win32gui
import win32ui

from Utility.Utility import *

ReadyState = Enumerate(['READYSTATE_UNINITIALIZED', 'READYSTATE_LOADING', 'READYSTATE_LOADED', 'READYSTATE_INTERACTIVE', 'READYSTATE_COMPLETE'])

#-------------------------------------------------------------------------------------
# PushButton
#-------------------------------------------------------------------------------------
def PushButton(handle, label):
    if win32gui.GetWindowText(handle) == label:
        Log(r'Click %s' % (label))
        win32gui.SendMessage(handle, win32con.BM_CLICK, None, None)
        return True

#-------------------------------------------------------------------------------------
# ClickDlgButtonThread
#-------------------------------------------------------------------------------------
class ClickDlgButtonThread(threading.Thread):
    title = r''
    button = r''
    wnd = None

    def __init__(self, title, button):
        threading.Thread.__init__(self)
        self.title = title
        self.button = button

    def run(self):

        if self.wait_for_window(self.title):
            time.sleep(3)
            win32gui.EnumChildWindows(self.wnd.GetSafeHwnd(), PushButton, self.button);
            time.sleep(1)
            self.wnd = win32ui.GetForegroundWindow()

    def wait_for_window(self, title, timeout=30):
        self.wnd = None
        idx = 0
        while(self.wnd == None and idx < timeout):
            idx += 1
            time.sleep(1)
            try:
                self.wnd = win32ui.FindWindow(None, title)
            except:
                self.wnd = None

        if self.wnd:
            Log(r'wait_for_window: %s' % (title))
            return True

        Log(r'wait_for_window: Failed to find %s' % (title))
        return False

#-------------------------------------------------------------------------------------
# SaveHtmlPageThread
#-------------------------------------------------------------------------------------
class SaveHtmlPageThread(threading.Thread):
    ie = None
    wnd = None
    url = r''

    def __init__(self, url, title, outputfile):
        threading.Thread.__init__(self)
        self.url = url
        self.title = title
        self.outputfile = outputfile

    def run(self):
        Trace()
        pythoncom.CoInitialize()
        Log(r'Launching IE to page %s' % (self.url))
        self.ie = Dispatch("InternetExplorer.Application")
        self.ie.Visible = 1
        self.ie.Navigate(self.url)

        if self.wait_for_complete():
            time.sleep(3)
            self.save_page(self.outputfile)
        else:
            Log(r'Failed to find page: %s' % (self.title))
        time.sleep(3)
        Log(r'Terminating IE')
        self.ie.Quit()

    def save_page(self, filepath):
        Log(r'output file: %s' % (filepath))

        ClickDlgButtonThread(r'Save HTML Document', r'&Save').start()
        ClickDlgButtonThread(r'Confirm Save As', r'&Yes').start()

        self.ie.ExecWB(win32com.client.constants.OLECMDID_SAVEAS, win32com.client.constants.OLECMDEXECOPT_DONTPROMPTUSER, filepath, None)
        Log(r'Saved: %s' % (filepath))

    def wait_for_complete(self, timeout=30):
        idx = 0
        Log(r'wait_for_complete: %s' % (ReadyState.ToString(self.ie.ReadyState)), 3)
        while(self.ie.ReadyState != ReadyState.READYSTATE_COMPLETE and idx <= timeout):
            idx += 1
            time.sleep(1)
            Log(r'waiting: %s' % (ReadyState.ToString(self.ie.ReadyState)), 3)

        if self.ie.ReadyState == ReadyState.READYSTATE_COMPLETE:
            Log(r'wait_for_complete: success')
            return True

        Log(r'wait_for_complete: Navigation failed. IE readyState == %s - %s' % (self.ie.ReadyState, ReadyState.ToString(self.ie.ReadyState)))
        return False

    def wait_for_page(self, title, timeout=30):
        Log(r'wait_for_page: %s' % (title))

        self.wnd = None
        idx = 0
        while(self.wnd == None and idx < timeout):
            idx += 1
            time.sleep(1)
            try:
                self.wnd = win32ui.FindWindow(None, title)
            except:
                self.wnd = None

        if self.wnd:
            Log(r'wait_for_page: success %s' % (title))
            return True

        Log(r'wait_for_page: Failed to find page %s' % (title))
        return False

#-------------------------------------------------------------------------------------
# SaveHtmlPage
#-------------------------------------------------------------------------------------
def SaveHtmlPage(url, title, outputfile):

    url = Expand(url)
    outputfile = ExpandPath(outputfile)

    t = SaveHtmlPageThread(url, title, outputfile)
    t.start()
    t.join()

