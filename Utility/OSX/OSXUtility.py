from Utility.Utility import *

#-------------------------------------------------------------------------------------
# File functions
#-------------------------------------------------------------------------------------
def FolderSize(Folder):
    return FolderSize_Slow(Folder)

def ChangeFileCreationTime(fname, newtime):
    raise Exception(__name__)

#-------------------------------------------------------------------------------------
# Events
#-------------------------------------------------------------------------------------
def SetEvent(Event, EventName):
    raise Exception(__name__)

def OpenActionEvent(Action=r'[g:Action]', ReturnEvent=True):
    return False

def CreateActionEvent(Action=r'[g:Action]'):
    raise Exception(__name__)

def SignalActionEvent(Action=r'[g:Action]'):
    raise Exception(__name__)

def CloseEvent(Event, Name=''):
    raise Exception(__name__)

def WaitForEvent(Name, Interval='[RepeatInterval]'):
    raise Exception(__name__)

def FooBar():
    print('OSX.FooBar')
