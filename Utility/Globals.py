import collections
import getpass
import os
import platform
import sys

from   Utility.Utility import *
import Utility.Utility

Globals = {}

#-------------------------------------------------------------------------------------
# Path string for converting os.sep
#-------------------------------------------------------------------------------------
class Path(str):
    def __new__(cls, value):
        return str.__new__(cls, value.replace('/', os.sep).replace('\\', os.sep))

#-------------------------------------------------------------------------------------
# Plain string for converting os.sep
#-------------------------------------------------------------------------------------
class Plain(str):
    def __new__(cls, value):
        return str.__new__(cls, value.replace('/', os.sep).replace('\\', os.sep))

#-------------------------------------------------------------------------------------
# DictN for Globals
#-------------------------------------------------------------------------------------
class DictN(collections.OrderedDict):

    def __init__(self, StartDict=None, *args, **kwargs):
        collections.OrderedDict.__init__(self, *args, **kwargs)

        if StartDict:
            Utility.Utility.dict_update(self, StartDict)

    def __str__(self):
        return json.dumps(self)

    # def __getitem__(self, key):
    #     value = dict.__getitem__(self, key)
    #     if isinstance(value, Expando) or isinstance(value, Path):
    #         return value.__repr__()

    # def __setitem__(self, key, value):
    #     self.check_key(key)
    #     dict.__setitem__(self, key, value)

    def check_key(self, name):
        if name not in self:
            for key in self.keys():
                if key.lower() == name.lower():
                    Error('Key already exists with different case key:%s != name:%s' % (name, key))

    def __getattr__(self, name):
        save = Globals.get(r'UseExpand', True)
        Utility.Globals.UseExpand = True
        value = None
        try:
            value = collections.OrderedDict.__getattr__(self, name)
            return value
        except:
            if name.startswith(r'_OrderedDict__'):
                raise AttributeError(name)

            self.check_key(name)
            value = self.convertValue(self.get(name, ''))

        if isinstance(value, str):
            value = Utility.Utility.Expand(value)
        elif isinstance(value, DictN):
            pass
        elif isinstance(value, dict):
            value = DictN(value)
        elif isinstance(value, datetime.datetime):
            value = '%s' % value
        Utility.Globals.UseExpand = save
        return value

    def __setattr__(self, name, value):
        if name.startswith('__') or name.startswith('_OrderedDict__'):
            value = collections.OrderedDict.__setattr__(self, name, value)
        else:
            self.check_key(name)
            self[name] = value

    def __delattr__(self, name):
        if name in DictN:
            del self[name]

    def update(self, value):
        Utility.Utility.dict_update(self, value)

    def getNested(self, name, default={}):
        value = self.convertValue(self.get(name, default))
        if isinstance(value, str):
            value = Utility.Utility.Expand(value)
        elif isinstance(value, dict):
            value = DictN(value)
        return value

    def getNode(self, Path, default={}):
        Path = Utility.Utility.ExpandPath(Path)
        currentNode = self
        for node in Path.split(os.sep):
            if node not in currentNode:
                currentNode[node] = DictN()
            currentNode = currentNode[node]
        return currentNode

    def convertValue(self, value):
        if value == None:
            return None
        elif value == 'True':
            return True
        elif value == 'False':
            return False
        elif isinstance(value, list):
            return value
        elif isinstance(value, int):
            return int(value)
        elif isinstance(value, float):
            return float(value)
        else:
            return value

    @staticmethod
    def get_key(data, key, Default=None):
        if key in data:
            return key

        key = key.lower()
        for dataKey in data:
            if dataKey.lower() == key:
                return dataKey

        return Default

    @staticmethod
    def get_value(data, key, Default=None):
        key = DictN.get_key(data, key, None)
        return data.get(key, Default)

    @staticmethod
    def del_key(data, key):
        key = DictN.get_key(data, key)
        if key:
            del data[key]

    @staticmethod
    def lower_keys(data):
        lowered = DictN()
        for key, value in data.items():
            if isinstance(value, dict):
                value = DictN.lower_keys(value)
            lowered[key.lower()] = value
        return lowered

dictn = DictN

#-------------------------------------------------------------------------------------
# Globals
#-------------------------------------------------------------------------------------
Privates = dictn()
Privates.pid = os.getpid()
Privates.Event = None
Privates.EventName = None

Temps = dictn()
Globals = dictn()

curDateTime = datetime.datetime.now()
# System data
Globals.HostName = platform.node()
Globals.COMPUTERNAME = platform.node()
Globals.USERNAME = getpass.getuser()
Globals.Temp = ternary(platform.system() == 'Darwin', '/private/tmp', 'c:\Temp')  # /tmp maps to /private/tmp on mac
Globals.ExitCode = 0
Globals.DateTime = datetime.datetime.strftime(curDateTime, "%Y-%m-%d %H:%M")
Globals.Date = str(datetime.datetime.date(curDateTime))
Globals.Time = time.strftime("%H:%M", time.localtime())
Globals.DateTimeStamp = datetime.datetime.strftime(curDateTime, "%Y.%m.%d")
Globals.TimeStamp = datetime.datetime.strftime(curDateTime, "%H.%M")
# Environment data
Globals.ProjectName = Path('%s%s' % (os.environ.get('SDX_PROJECT', 'Folder'), os.environ.get('SDX_FOLDER', 'Folder')))
Globals.BackupArchiveFolder = Path(r'[Temp]\zip\Backup')
Globals.BackupArchiveJson = Path(r'[BackupArchiveFolder]\history.json')
Globals.RemoteArchiveFolder = ternary(platform.system() == 'Darwin', r'/Volumes/DDrive/data/Archive/', '')
Globals.RemoteArchiveFolder2 = ternary(platform.system() == 'Darwin', r'', '')
# Actions data
Globals.ProgramName = r'Utility'
Globals.ProgramDescription = r'Utility Program'
Globals.Action = r'Toolkit'
Globals.optionals = []
# Log Data
Globals.BackupLogFolder = Path(r'[Temp]\Logs')
Globals.LogFile = Path(r'[Temp]\[ProgramName].log')
Globals.Indent = 0
Globals.UseExpand = True
Globals.IgnoreExpandErrors = False
Globals.ReportExpandErrors = True
Globals.ConsoleEcho = os.environ.get('ConsoleMode', False)
Globals.DebugMode = True
Globals.DebugPidMode = False
Globals.Verbose = False
# Tools data
Globals.GlobalSaveFile = Path(r'[Temp]\Globals.json')
Globals.TempsSaveFile = Path(r'[Temp]\Temps.json')
Globals.EnvironSaveFile = Path(r'[Temp]\Environment.json')
# Service data
Globals.Service = None
Globals.ServiceName = r'Py[Action]Service'
Globals.ServiceDescription = r'Python [Action] Service'
Globals.RunningAsService = False
Globals.ActionEventName = Path(r'Global\[Action].[ProjectName]')
Globals.ServiceJSON = Path(r'[Temp]\Services.json')
#Import Dups data
Globals.ImportLog = Path(r'[Temp]\Imports\Import.[Date].log')
# Tools data
Globals.DatabasePath = Path(r'[Temp]\[ProgramName].db')
Globals.WindowsTools = Path(r'[ScriptFolder]\..\bin')
Globals.SendMailExe = Path(r'[WindowsTools]\SendEmail.exe')
Globals.To = ternary(platform.system() == 'Windows', r'[USERNAME]@microsoft.com', 'cgomes@iinet.com')
Globals.SMTPServer = ternary(platform.system() == 'Windows', r'smtp.microsoft.com', 'smtp.iinet.com')
Globals.SMTPUserID = ternary(platform.system() == 'Windows', r'', 'cgomes@iinet.com')
Globals.SendMailFolder = Path(r'[Temp]\SendEmail')
Globals.SendMailJSON = Path(r'[SendMailFolder]\SendMail.json')
Globals.ZipExcludeList = [ r'__pycache__', '.pyc', '.obj', '.DS_Store', 'pylint-0.26.0' ]
Globals.ZipFolder = ternary(platform.system() == 'Windows', '[Temp]\zip\Archive', '/data/Archive')
# Web data
if platform.system() == 'Windows':
    if os.environ.get('USERNAME', '') == 'a-cgomes':
        Globals.WebDataFileStore = r'\\ServerName\public\a-cgomes\WebSite'
    else:
        Globals.WebDataFileStore = Path(r'c:\web\WebDataFiles')
else:
    Globals.WebDataFileStore = Path(r'[Temp]\WebDataFiles')
Globals.WebDataFileStore2 = Path(ternary(platform.system() == 'Windows', r'c:\web\WebDataFiles', r'[Temp]\WebDataFiles'))
Globals.ResultsWebDataFile = Path(r'[WebDataFileStore]\Result.json')
Globals.ResultsWebDataFile2 = Path(r'[WebDataFileStore2]\Result.json')
# UnitTest data
Globals.TestDataFolder = Path(r'[ScriptFolder]\TestData')
Globals.UnitTestOutputFolder = Path(r'[Temp]\Python\UnitTests')
Globals.UnitTestResultsFile = Path(r'[UnitTestOutputFolder]\UnitTest.Results.json')

#-------------------------------------------------------------------------------------
# Temp
#-------------------------------------------------------------------------------------
class Temp:
    def __init__(self, key, value=None):
        self.key = key
        self.value = value

    def __enter__(self):
        Temps.push_value(self.key, self.value)

    def __exit__(self, type, value, traceback):
        Temps.pop_value(self.key)
