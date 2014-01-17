import datetime
import glob
import json
import os
import platform
import sys
import _thread
import time
import abc


from   Utility.Utility import *
if platform.system() == 'Windows':
    import Utility.Win32 as Plat
    import Utility.Win32.ActionService
else:
    import Utility.OSX as Plat
    import Utility.OSX.ActionService

#-------------------------------------------------------------------------------------
# Actions
#-------------------------------------------------------------------------------------

class Actions():
    ActionList = DictN()

    def __init__(self):
        self.action = None

    @property
    def ActionNames(self):
        names = [ action.name for action in Actions.ActionList.values() ]
        names.sort()
        return names

    @staticmethod
    def AddAction(Function, RunAsService=False, ServiceMethod=None, Repeated=False, detailedLog=False, SkipCls=False, Terse=False):
        action = DictN()
        action.name = Function.__name__
        action.method = Function
        action.service = RunAsService
        action.serviceMethod = ServiceMethod
        action.repeated = Repeated
        action.detailedLog = detailedLog
        action.skipCls = SkipCls
        action.terse = Terse
        Actions.ActionList[Function.__name__.lower()] = action

    @staticmethod
    def Run():
        self = Actions()
        Trace(Globals.Action)
        IncreaseIndent()

        self.ValidateAction()
        self.SetupAction()

        Log(r'Run [Action] RepeatInterval=[RepeatInterval] RunningAsService=[RunningAsService]')

        if Globals.RunAsService and not Globals.RunningAsService:
            Plat.ActionService.ActionService.StartActionService()
        elif Globals.RepeatInterval:
            self.RunRepeatedAction()
        else:
            self.RunAction()

        DecreaseIndent()

    def GetAction(self, Name):
        return Actions.ActionList.get(Name.lower(), None)

    @staticmethod
    def GetActionObject(Name):
        return Actions.ActionList.get(Name.lower(), None)

    def GetActionName(self, Name='[Action]'):
        action = self.GetAction(Name)
        return action.name

    def ValidateAction(self):
        self.action = self.GetAction(Globals.Action)
        if self.action:
            Globals.Action = self.action.name
            return

        while True:
            Log('Missing Action. Choose action by number below:')
            Log()
            idx = 1
            actionNames = [action.name for action in Actions.ActionList.values()]
            actionNames.sort()
            for action in actionNames:
                Log('[idx] \t - [action]')
                idx += 1
            Log('q \t - quit')
            Log()

            selected = input('Enter Action Number/Name: ').strip()
            if selected.isdigit():
                selected = str(selected)
                selectedIdx = int(selected)
                if selectedIdx >= 1 and selectedIdx <= len(actionNames):
                    selected = actionNames[selectedIdx - 1]

            if selected.lower() == 'q':
                Exit(Expand('Quitting [ProgramName]'))
            else:
                self.action = self.GetAction(selected)
                if self.action:
                    Log(r'Selected: [selected]')
                    Globals.Action = self.action.name
                    return

            Log('ERROR: Incorrect selection.  Please specify a name/number from above.')

    def SetupAction(self):
        if self.action.service:
            Globals.RunAsService = True
            if self.action.serviceMethod:
                self.action = self.GetAction(self.action.serviceMethod)
                Globals.Action = self.action.name
            Log('Turning on RunAsService for [Action]')

        if self.action.repeated and not Globals.RepeatInterval:
            Globals.RepeatInterval = 30
            Log('Turning on RepeatInterval for [Action]')

        if Globals.RunAsService or Globals.RepeatInterval > 0:
            Globals.SkipAutoOpen = True

        if self.action.detailedLog or Globals.RunAsService or Globals.RunningAsService or Globals.RepeatInterval > 0:
            projectName = Globals.ProjectName.replace('\\', '.').replace('/', '.')
            SetLogFile(r'[Temp]\[Action].[projectName].log')
        else:
            SetLogFile(r'[Temp]\[Action].log')

        return Globals.Action

    def RunAction(self):
        Trace(Globals.Action)
        start_time = time.time()
        optionals = ReplaceTrueFalseWithBooleans(Globals.optionals)
        try:
            self.action = self.GetAction(Globals.Action)
            if len(optionals):
                Log(r'[Action]([optionals])')
                self.action.method(*optionals)
            else:
                self.action.method()
        except:
            ReportException()
            return Globals.ExitCode

        elapsedTime = secondsToStr(time.time() - start_time)
        Log('Completed [Action]')
        Log('Elapsed time: %s' % (elapsedTime))

    def RunRepeatedAction(self):
        Trace(Globals.Action)
        if not Privates.Event:
            Privates.Event = Plat.CreateActionEvent()

        while True:
            Trace(Globals.Action)
            try:
                self.RunAction()
            except:
                ReportException()

            # Backup Log file
            BackupFile(Globals.LogFile, Globals.BackupLogFolder)

            Log()
            Log("------------------------------------------------")
            Log('Completed [Action] repeating in [RepeatInterval] minutes')
            if Privates.Event:
                WaitForEvent(Privates.Event)
            else:
                time.sleep(int(Globals.RepeatInterval) * 60)
            Log('Awakened [Action] repeating now')

        CloseEvent(Privates.Event, Privates.EventName)
        Privates.Event = None
        Privates.EventName = None

    def StartAllServices(self, ExcludeList=''):
        Trace()
        myAction = Globals.Action

        ExcludeList = ExcludeList.split(',')

        for action in Actions.ActionList:
            if not action.service or action.name in ExcludeList:
                continue

            JSON.delete_key_from_file(Globals.ServiceJSON, action.name)

        for action in Actions.ActionList:
            if not action.service or action.name in ExcludeList:
                continue

            Log('Starting Service {0}'.format(action.name))
            Globals.Action = action.name
            Plat.ActionService.ActionService.StartActionService(action.name, False)
            Globals.Action = myAction

    def SignalActionEvent(self, ActionName='[Action]'):
        Trace(ActionName)
        SignalActionEvent(ActionName)
        return
        if not SignalActionEvent(ActionName):
            Plat.ActionService.ActionService.StartActionService(Globals.Action)
