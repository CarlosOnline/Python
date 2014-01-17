import ctypes
import collections
import datetime
import os
import platform
import re
import sys
import threading
import time
import win32api
import win32com.client as com
import win32event
import win32security
import pywintypes
import win32file
import win32con

from Utility.Utility import *
import Utility.Sql as sql

kernel32 = ctypes.windll.kernel32

#-------------------------------------------------------------------------------------
# File functions
#-------------------------------------------------------------------------------------
def FolderSize(Folder):
    fso = com.Dispatch("Scripting.FileSystemObject")
    data = fso.GetFolder(Folder)
    return data.Size

def add_timezone(date):
    import pytz

    date = datetime.datetime.fromtimestamp(time.mktime(date))
    local_tz = pytz.timezone('US/Pacific')
    #loc_dt = local_tz.localize(datetime.datetime(2002, 10, 27, 6, 0, 0))
    local_date = local_tz.localize(date, is_dst=None)
    return local_date

def ChangeFileCreationTime(fname, newtime):
    try:
        newtime = add_timezone(newtime)
        wintime = pywintypes.Time(newtime)
        winfile = win32file.CreateFile(
            fname, win32con.GENERIC_WRITE,
            win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
            None, win32con.OPEN_EXISTING,
            win32con.FILE_ATTRIBUTE_NORMAL, None)

        win32file.SetFileTime(winfile, wintime, None, None)

        winfile.close()
    except:
        ReportException()


#-------------------------------------------------------------------------------------
# Events
#-------------------------------------------------------------------------------------
def SetEvent(Event, EventName):
    EventName = Expand(EventName)
    event = Event
    Trace(r'[EventName] [Event]')
    if not event:
        try:
            event = win32event.OpenEvent(win32event.EVENT_MODIFY_STATE, False, EventName)
        except:
            Log(r'Failed to open [EventName]')
            return False

    win32event.SetEvent(event)
    Log('SetEvent completed for [EventName] [event]')
    if not Event:
        CloseEvent(event)
        event = None
    return True

def OpenActionEvent(Action=r'[g:Action]', ReturnEvent=True):
    TraceVerbose(r'[Action] [ActionEventName] ReturnEvent=[ReturnEvent]')

    event = None
    for name in [Globals.ActionEventName]:
        name = Expand(name)
        try:
            event = win32event.OpenEvent(win32event.EVENT_MODIFY_STATE, False, name)
        except:
            event = None
        if event:
            Verbose(r'OpenActionEvent opened [name] [event]')
            if ReturnEvent:
                return [event, name]
            CloseEvent(event, name)
            event = None
            return True, name

    Verbose(r'OpenActionEvent failed to open event for [Action] [event]')
    return None, None

def CreateActionEvent(Action=r'[g:Action]'):
    Trace(r'[Action] [ActionEventName] RunningAsService=[RunningAsService]')

    everyone, domain, type = win32security.LookupAccountName ("", "Everyone")
    admins, domain, type = win32security.LookupAccountName ("", "Administrators")
    user, domain, type = win32security.LookupAccountName ("", win32api.GetUserName ())

    dacl = win32security.ACL()
    everyoneAccess = win32event.EVENT_MODIFY_STATE if Globals.RunningAsService else win32event.EVENT_ALL_ACCESS
    dacl.AddAccessAllowedAce (win32security.ACL_REVISION, everyoneAccess, everyone)
    dacl.AddAccessAllowedAce (win32security.ACL_REVISION, win32event.EVENT_MODIFY_STATE, user)
    dacl.AddAccessAllowedAce (win32security.ACL_REVISION, win32event.EVENT_MODIFY_STATE, admins)

    desc = win32security.SECURITY_DESCRIPTOR()
    desc.Initialize()
    desc.SetSecurityDescriptorDacl(1, dacl, 0)

    attribs = win32security.SECURITY_ATTRIBUTES()
    attribs.Initialize()
    attribs.bInheritHandle = False
    attribs.SECURITY_DESCRIPTOR = desc

    event = None
    for name in [Globals.ActionEventName]:
        name = Expand(name)
        try:
            event = event = win32event.CreateEvent(attribs, 0, 0, name)
        except:
            pass
        if event:
            Log(r'CreateActionEvent created [name] [event]')
            Privates.Event = event
            return event

    Log(r'CreateActionEvent failed to create event for [Action]')
    return None

def SignalActionEvent(Action=r'[g:Action]'):
    TraceVerbose(r'[Action] [ActionEventName]')

    event, name = OpenActionEvent(Action, True)
    if event:
        Verbose('SignalActionEvent setting event for [Action] [event]')
        win32event.SetEvent(event)
        CloseEvent(event, name)
        event = None
        return True

    return False

def CloseEvent(Event, Name=''):
    if not Event:
        return
    try:
        Log(r'Closing Event [Name] [Event]')
        Event.Close()
        Log(r'Closed  Event [Name] [Event]')
    except:
        Log(r'Failed to close [Name] [Event]')
        ReportException()
        pass

def WaitForEvent(Name, Interval='[RepeatInterval]'):
    Interval = int(Expand(Interval))
    win32event.WaitForSingleObject(Name, Interval * 60 * 1000)

def get_volume_name(Drive):
    Drive = ExpandPath(Drive)
    if ':' not in Drive:
        Drive += ':'

    volumeNameBuffer = ctypes.create_unicode_buffer(1024)
    fileSystemNameBuffer = ctypes.create_unicode_buffer(1024)
    serial_number = None
    max_component_length = None
    file_system_flags = None

    rc = kernel32.GetVolumeInformationW(
        ctypes.c_wchar_p(Drive + "\\"),
        volumeNameBuffer,
        ctypes.sizeof(volumeNameBuffer),
        serial_number,
        max_component_length,
        file_system_flags,
        fileSystemNameBuffer,
        ctypes.sizeof(fileSystemNameBuffer)
    )

    return volumeNameBuffer.value

def get_drive_letters():
    drives = []
    bitmask = kernel32.GetLogicalDrives()
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if bitmask & 1:
            drives.append(letter + ':')
        bitmask >>= 1

    return drives

def get_drive_map():

    driveMap = dictn()
    driveMap.Names = dictn()
    driveMap.Drives = dictn()
    for drive in get_drive_letters():
        name = get_volume_name(drive)
        if name:
            driveMap.Names[name] = drive
        driveMap.Drives[drive] = name

    return driveMap
