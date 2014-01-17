import datetime
import glob
import json
import os
import platform
import sys
import _thread
import time


folder = os.path.dirname(os.path.realpath(__file__))
folder = os.path.dirname(folder)
folder = os.path.dirname(folder)
sys.path.append(folder)

from   Utility.Utility import *
from   Utility.Actions import *
from   Utility.Win32.Service import *
from   Utility.Win32.Win32Utility import *

#-------------------------------------------------------------------------------------
# ActionService
#-------------------------------------------------------------------------------------
class ActionService(Service):

    StopEvent = None
    def __init__(self, *args):
        try:
            Log(r'ActionService:__init__')
            #SetLogFile(r'[Temp]\ActionService.[pid].log')
            SetLogFile(r'[Temp]\ActionService.log')
            RestoreEnvironment()
            Globals.RunningAsService = True

            Log('*' * 50)
            Log(r'* Starting [Action] Service')
            Log('*' * 50)
            Trace('ActionService for [Action]')

            PrettyPrintDict(Globals)
            Service.__init__(self, *args)
        except:
            ReportException()

    def start(self):
        try:
            self.log('ActionService.start: Starting [Action] within Service')
            Privates.Event = CreateActionEvent()
            ActionService.StopEvent = self.stop_event
            _thread.start_new_thread(ActionService.RunActionService, ())
            #FuncThread.RunFunc(ActionService.Run)
        except:
            ReportException()

    def stop(self):
        try:
            self.log(Expand('Stopping [Action] within Service'))
            CloseEvent(Privates.Event, Privates.EventName)
            Privates.Event = None
            Privates.EventName = None
            now = datetime.datetime.now()
        except:
            ReportException()

    @staticmethod
    def RunActionService():
        Log('RunActionService: started [Action]')

        try:
            import CommonActions
            Actions.Run()
        except:
            ReportException()
        Log('ActionService.start: Completed [Action]')
        ActionService.LogActionStop()
        SetEvent(ActionService.StopEvent, 'service.stop_event')

    @staticmethod
    def StartActionService(Action=r'[g:Action]', StopService=True):
        Trace(Globals.Action)
        ActionService.LogActionRemove(Action)
        if StopService:
            ActionService.StopActionService()
        Trace(Globals.Action)
        ActionService.LogActionStart()
        StartService(ActionService)

    @staticmethod
    def StopActionService(DeleteService=True):
        Trace(Globals.Action)
        ActionService.LogActionRemove()
        StopService()
        Log(r'--------------------------')

    @staticmethod
    def LogActionStart(Action=r'[g:Action]'):
        Trace(Action)
        Action = Expand(Action)
        now = datetime.datetime.now()
        data = {}
        data[Action] = {
            'start'         : now.strftime("%A %Y-%m-%d %H:%M:%S %I:%M:%S %p"),
            'Action'        : Action,
            'ServiceName'   : Expand(Globals.ServiceName),
            'pid'           : Privates.pid,
        }
        PrettyPrintDict(data)
        JSON.update_file(Globals.ServiceJSON, data)

    @staticmethod
    def LogActionStop(Action=r'[g:Action]'):
        Trace(Action)
        Action = Expand(Action)
        now = datetime.datetime.now()
        data = {}
        data[Action] = {
            'stop'          : now.strftime("%A %Y-%m-%d %H:%M:%S %I:%M:%S %p"),
            'Action'        : Action,
            'ServiceName'   : Globals.ServiceName,
            'pid'           : Privates.pid,
        }
        PrettyPrintDict(data)
        JSON.update_file(Globals.ServiceJSON, data)

    @staticmethod
    def LogActionRemove(Action=r'[g:Action]'):
        Trace(Action)
        Action = Expand(Action)
        JSON.delete_key_from_file(Globals.ServiceJSON, Action)
