import argparse
import base64
import collections
import colorama
import datetime
import distutils
import distutils.core
import fnmatch
import glob
import inspect
import itertools
import json
import logging
import mimetypes
import multiprocessing
import os
import platform
import pprint
import re
import shutil
import stat
import string
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import zipfile
from   colorama import Fore, Back, Style
from   functools import wraps
from   functools import reduce

if os.name == 'nt':
    import win32api, win32con

# Use for printing in color
colorama.init()

# ConsoleColor values for reference only - imported elsewhere
'''
if False:
    class Fore:
        BLACK = 30
        RED = 31
        GREEN = 32
        YELLOW = 33
        BLUE = 34
        MAGENTA = 35
        CYAN = 36
        WHITE = 37
        RESET = 39

    class Back:
        BLACK = 40
        RED = 41
        GREEN = 42
        YELLOW = 43
        BLUE = 44
        MAGENTA = 45
        CYAN = 46
        WHITE = 47
        RESET = 49

    class Style:
        BRIGHT = 1
        DIM = 2
        NORMAL = 22
        RESET_ALL = 0
'''

original_print = print

def ternary(cond, on_true, on_false):
    return {True: on_true, False: on_false}[cond is True]

Globals = {}

#-------------------------------------------------------------------------------------
# import globals into global space
#-------------------------------------------------------------------------------------
from Utility.Globals import *

class Expando(str):
    def __str__(self):
        return Expand(str.__str__(self))
    def __repr__(self):
        return str.__str__(self)

def decode(line):
    if isinstance(line, str):
        return line
    try:
        line = line.decode('utf-8')
    except:
        decoded = ''
        for ch in line:
            decoded += str(chr(ch))
        line = decoded
    return line
#-------------------------------------------------------------------------------------
# Enumerate
#-------------------------------------------------------------------------------------
class Enumerate(object):
    def __init__(self, names):
        idx = 0
        for name in names:
            setattr(self, name, idx)
            idx += 1

    def ToString(self, value):
        for key in list(self.__dict__.keys()):
            if self.__dict__[key] == value:
                return key

        Log(r'Failed to find value %s in Enumeration:' % (value))
        PrettyPrintList(list(self.__dict__.keys()))
        return r''

#-------------------------------------------------------------------------------------
# Trace
#-------------------------------------------------------------------------------------
class Trace:
    def __init__(self, *args, **kwargs):
        Message = ArgsToMessage(*args, **kwargs)
        if not Message:
            Message = r'{0:30}'.format(self.whosemydaddy())
        else:
            Message = r'{0:30} : {1}'.format(self.whosemydaddy(), Message)
        Log(Message, **kwargs)

    def whosemydaddy(self):
            funcName = 'NoFuncName'
            stack = inspect.stack()
            try:
                frame = stack[ternary(isinstance(self, TraceVerbose), 3, 2)]
                funcName = frame[3]
                f_locals = frame[0].f_locals
                self = f_locals.get('self', None)
                if self:
                    # Inspector.LogMembers(self)
                    className = self.__class__.__name__
                    funcName = r'{0}::{1}'.format(className, funcName)
            except:
                ReportException()
                pass

            del stack
            return funcName

class TraceVerbose(Trace):
    def __init__(self, Message=r'', *args, **kwargs):
        kwargs['Verbose'] = True
        Trace.__init__(self, Message, *args, **kwargs)

#-------------------------------------------------------------------------------------
# Arg & Options Functions
#-------------------------------------------------------------------------------------

class ArgParser():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    args = None
    argList = []
    epilog = ''

    @staticmethod
    def add_arg(Name, *args, **kwargs):
        realName = ternary(Name.startswith('-'), Name[1:], Name)
        if realName not in ArgParser.argList:
            ArgParser.argList.append(realName)
            ArgParser.parser.add_argument(Name, *args, **kwargs)

    @staticmethod
    def parse():
        import Utility.Actions

        epilog = '''Available Actions:
        '''

        for key in Utility.Actions.Actions().ActionNames:
            epilog += '''   %s
        ''' % (key)

        ArgParser.parser.epilog = epilog

        for key in list(Globals.keys()):
            value = Globals[key]
            if isinstance(value, bool):
                ArgParser.add_arg('-%s' % key, help=r'%s : True/False' % key, default=value, required=False, action='store_true', dest='boolean_switch')
            else:
                ArgParser.add_arg('-%s' % key, help=r'%s : %s' % (key, value), metavar='', default=value, required=False)

        ArgParser.args = ArgParser.parser.parse_args()

        args = vars(ArgParser.args)
        for key in args:
            Globals[key] = args[key]

        del ArgParser.args
        del ArgParser.argList
        del ArgParser.parser
        del ArgParser.epilog

        ArgParser.process_args()

    @staticmethod
    def process_args():

        Globals.MediaInfoJSON = r'[ScriptFolder]\json\MediaInfo.json'
        if os.path.exists(ExpandPath(r'[ScriptFolder]\json\MediaInfo.[HostName].json')):
            Globals.MediaInfoJSON = r'[ScriptFolder]\json\MediaInfo.[HostName].json'
        JSON.save_to_file(r'[Temp]\Globals.json', Globals)
        Globals.update(JSON.load_from_file(Globals.MediaInfoJSON))
        Globals.AllMediaTypes = ','.join(list(Globals.Media.keys()))
        Globals.DefaultMediaFolders = flatten([ media.DefaultFolders for media in Globals.Media.values() ])
        Globals.AllMediaExtensions = flatten([ media.Extensions for media in Globals.Media.values() ])

        action = Utility.Actions.Actions.GetActionObject(Globals.Action)
        if action:
            if not Globals.SkipCls:
                Globals.SkipCls = action.skipCls
            if not Globals.Terse:
                Globals.Terse = action.terse

        DeleteFile(Globals.LogFile)
        if Globals.cls and not Globals.SkipCls:
            cls()
        Log(r'Starting [ProgramName] - args: %s' % ' '.join(sys.argv[1:]))

    if Globals.Verbose:
        Trace()
        PrettyPrintDict(Globals)
        Log()

def lex(Value, Debug=False):
    return Expand(Value, True, 1, Debug)

def Expand(Value, UseLocal=True, StartFrame=0, Debug=False):

    if not Globals.UseExpand:
        return Value

    #if str(type(Value)) != "<class 'str'>":
    #    print(type(Value), Value)
    if isinstance(Value, Utility.Globals.Plain):
        return Value

    ignoreList = []
    if Debug:
        Log('Expand: "%s"' % Value, UseExpand=False)

    def GetLocalValue(Key, StartFrame=0):
        if Debug:
            Trace(r'%s %d' % (Key, StartFrame))
        stack = inspect.stack()
        stackList = stack[StartFrame + 2:]

        found = False
        value = ''
        try:
            for frame in stackList:
                f_locals = frame[0].f_locals
                if frame[3] != r'<module>':
                    if Debug:
                        Log(r'Frame: %s' % (frame[3]))

                    if Key in list(f_locals.keys()):
                        if Debug:
                            Log(r'found %s in %s' % (Key, frame[3]))
                        value = f_locals[Key]
                        found = True
                        break;

                classObj = f_locals.get('self', None)
                if classObj:
                    try:
                        classDict = classObj.__dict__
                        if Key in list(classDict.keys()):
                            if Debug:
                                Log(r'found %s in %s : class %s' % (Key, frame[3], classObj.__name__))
                            value = classDict[Key]
                            found = True
                            break;
                    except KeyError:
                        pass
        finally:
            del stack

        return [found, value]

    def GetGlobalValue(Key):
        if Debug:
            Trace(Key)

        if Key in list(Globals.keys()):
            if Debug:
                Log(r'found %s in Globals %s' % (Key, Globals[Key]), UseExpand=False)
            value = Globals[Key]
            return [True, value]

        if Debug:
            Log(r'did not find %s in Globals' % (Key), UseExpand=False)

        return [False, None]

    def GetPrivateValue(Key):
        if Debug:
            Trace(Key)

        if Key in list(Privates.keys()):
            if Debug:
                Log(r'found %s in Privates %s' % (Key, Privates[Key]), UseExpand=False)
            value = Privates[Key]
            return [True, value]

        if Debug:
            Log(r'did not find %s in Privates' % (Key), UseExpand=False)

        return [False, None]

    def GetPrefixValue(key):

        if key.startswith(r'l:'):
            key = key.replace(r'l:', '')
            return GetLocalValue(key, StartFrame + 1)

        if key.startswith(r'g:'):
            key = key.replace(r'g:', '')
            return GetGlobalValue(key)

        if key.startswith(r'p:'):
            key = key.replace(r'p:', '')
            return GetPrivateValue(key)

        if key.startswith(r'e:'):
            key = key.replace(r'e:', '')
            if key.upper() in list(os.environ.keys()):
                keyValue = os.environ[key.upper()]
                return [True, keyValue]

        return [False, None]

    def GetEnvironmentValue(key):
        if key.upper() in os.environ.keys():
            keyValue = os.environ[key.upper()]
            return [True, keyValue]

        return [False, None]

    def GetValue(key):
        #print(key, Value)

        if key == 'True':
            return [True, True]

        if key == 'False':
            return [True, False]

        if key == 'None':
            return [True, None]

        if len(key) > 2 and key[1] == ':':
            return GetPrefixValue(key)

        if UseLocal:
            found, keyValue = GetLocalValue(key, StartFrame + 1)
            if found:
                return [found, keyValue]

        found, keyValue = GetGlobalValue(key)
        if found:
            return [found, keyValue]

        found, keyValue = GetEnvironmentValue(key)
        if found:
            return [found, keyValue]

        return GetPrivateValue(key)

    def GetWholePattern():
        m = re.search('\[[a-zA-Z0-9_():<>]+\]', Value)
        if not m:
            return None

        groups = [m.group(0)]
        groups.extend(m.groups())
        for pat in groups:
            # dbg_print(pat)
            if pat not in ignoreList:
                return pat

        return None

    if isinstance(Value, list) or isinstance(Value, dict):
        return Value

    while True:
        formatting = ''
        wholePattern = GetWholePattern()
        if not wholePattern:
            break

        key = wholePattern.strip('[]')
        if Debug:
            Log('Expand: "%s"' % key)

        colon = key.rfind(':')
        if colon != -1 and colon > 2:
            key, formatting = key.rsplit(':', 1)

        found, keyValue = GetValue(key)

        if isinstance(keyValue, Path):
            keyValue = keyValue.replace('\\', os.sep).replace('/', os.sep)

        if not found:
            if not Globals.IgnoreExpandErrors:
                if Globals.ReportExpandErrors:
                    info = Inspector.GetCallerInfo()
                    code = ternary(info and info.code, info.code, '')
                    # Log(r'Expand Error: "%s" not found for "%s"' % (key, Value), UseExpand=False)
                    Log(r'Expand Error: "%s" not found for "%s" %s' % (key, Value, code), UseExpand=False)
                    if Debug:
                        LogCallStack()
                        # Error('Debug Expand Error for %s on %s' % (key, code), UseExpand=False)
                        return

                    Log(r'***************************************')
                    Log(r'Debug Expand for %s' % (key))
                    Log(r'***************************************')

                    keyValue = key
                    Expand(Value, UseLocal, StartFrame + 1, True)
                else:
                    keyValue = key
            else:
                keyValue = wholePattern
                ignoreList.append(wholePattern)

        if Debug:
            Log(r'replacing %s with %s in text: %s' % (wholePattern, keyValue, Value), UseExpand=False)

        if formatting:
            fmt = '{0:%s}' % (formatting)
            keyValue = fmt.format(str(keyValue))
        if Value == wholePattern:
            if isinstance(keyValue, list):
                Value = keyValue
                return Value

        Value = Value.replace(wholePattern, str(keyValue))

    #print(Value)
    return Value

def ExpandPath(FilePath):
    is_plain = ternary(isinstance(FilePath, Utility.Globals.Plain), True, False)
    FilePath = os.path.expanduser(FilePath)
    FilePath = Expand(FilePath)
    FilePath = FilePath.replace('\\', os.sep).replace('/', os.sep)
    return ternary(is_plain, Plain(FilePath), FilePath)

def ExpandPathPlain(FilePath):
    FilePath = os.path.expanduser(FilePath)
    FilePath = FilePath.replace('\\', os.sep).replace('/', os.sep)
    return Plain(FilePath)

def flatten(List):
    return list(itertools.chain.from_iterable(List))

def to_list(Object):
    if isinstance(Object, list):
        return Object
    elif not Object or len(Object) == 0:
        return []
    elif isinstance(Object, str):
        return Object.split(',')
    else:
        return [Object]

def is_number(s):
    try:
        n = str(float(s))
        if n == "nan" or n == "inf" or n == "-inf" : return False
    except ValueError:
        try:
            complex(s)  # for complex
        except ValueError:
            return False
    return True

def os_path_ext(file_name):
    basename, ext = os.path.splitext(file_name)
    return ext

os.path.ext = os_path_ext

def CopyFile(SourcePath, DestPath):
    SourcePath = ExpandPath(SourcePath)
    DestPath = ExpandPath(DestPath)
    if SourcePath == DestPath:
        return
    TraceVerbose('[SourcePath] [DestPath]')
    DeleteFile(DestPath)
    if not os.path.exists(SourcePath):
        return
    EnsurePath(os.path.dirname(DestPath))
    shutil.copy2(SourcePath, DestPath)

def MoveFile(SourcePath, DestPath, Silent=False):
    SourcePath = ExpandPath(SourcePath)
    DestPath = ExpandPath(DestPath)
    if SourcePath == DestPath:
        return
    if not Silent:
        LogPlain('MoveFile %s %s' % (SourcePath, DestPath))
    DeleteFile(DestPath)
    if not os.path.exists(SourcePath):
        return
    EnsurePath(Plain(os.path.dirname(DestPath)))
    os.chmod(SourcePath, stat.S_IRWXU)
    shutil.move(SourcePath, DestPath)

def CopyDirectory(SourcePath, DestPath):
    SourcePath = ExpandPath(SourcePath)
    DestPath = ExpandPath(DestPath)
    Trace('[SourcePath] [DestPath]')
    #RemovePath(DestPath)
    #shutil.copytree(SourcePath, DestPath)
    distutils.dir_util.copy_tree(SourcePath, DestPath)

def DeleteFile(FilePath):
    FilePath = ExpandPath(FilePath)
    if os.path.isfile(FilePath):
        os.chmod(FilePath, stat.S_IRWXU)
        os.remove(FilePath)

def RemovePath(FolderPath):
    FolderPath = ExpandPath(FolderPath)
    if os.path.exists(FolderPath):
        Trace(FolderPath)
        shutil.rmtree(FolderPath, True)

def RemoveFolder(FolderPath):
    RemovePath(FolderPath)

def FolderSize_Slow(start_path='.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        dbg_print(total_size)
        for f in filenames:
            try:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
            except:
                pass
    return total_size

def folder_size(Folders=None, SubFolders=True):
    if platform.system() == "Windows":
        import Utility.Win32.Win32Utility as PlatUtility
    else:
        import Utility.OSX.OSXUtility as PlatUtility
    import Utility.Sql as sql

    if not Folders:
        Folders = os.path.abspath(os.curdir)
    Trace(Folders)
    Folders = Folders.split(',')
    MB = 1024 * 1024.0
    GB = 1024 * MB
    if SubFolders:
        for folder in Folders:
            results = []
            subFolderList = GetSubFolders(folder)
            for subfolder in subFolderList:
                try:
                    dbg_print(subfolder)
                    try:
                        size = PlatUtility.FolderSize(subfolder)
                    except:
                        size = FolderSize_Slow(subfolder)
                    factor, suffix = ternary(size > GB, [GB, 'GB'], [MB, 'MB'])
                    foldername = subfolder[-50:]
                    results.append([str(foldername), "{:10.2f} MB".format(size / MB), "{:10.2f}".format(size / factor), suffix])
                except:
                    LogError(subfolder)
                    ReportException()
                    pass
            print()

            results = sql.sort_data(results, [1])
            Log('[folder] contents:')
            Log('-----------------')
            PrettyPrintList(results)
            Log()

    if len(Folders) > 1:
        results = []
        for folder in Folders:
            try:
                size = PlatUtility.FolderSize(folder)
            except:
                size = FolderSize_Slow(folder)
            try:
                factor, suffix = ternary(size > GB, [GB, 'GB'], [MB, 'MB'])
                results.append([str(folder), "{:10.2f}".format(size / factor), suffix])
            except:
                results.append([str(folder), "{:10.2f}".format(-1), 'Exception'])
        PrettyPrintList(results, "Folders")

def robocopy(SourceFolder, DestFolder, *args, TraceOnly=False, ExcludeFolders=[], ExcludeFiles=[], Silent=False, **kwargs):
    SourceFolder = ExpandPath(SourceFolder)
    DestFolder = ExpandPath(DestFolder)
    # Trace('[SourceFolder] [DestFolder]')

    arg = Expand('/MT:%d' % multiprocessing.cpu_count())
    args += (arg,)

    if len(ExcludeFolders):
        arg = '/XD %s' % (' '.join(map(lambda x: '"' + x + '"', ExcludeFolders)))
        args += (arg,)

    if len(ExcludeFiles):
        arg = '/XD %s' % (' '.join(map(lambda x: '"' + x + '"', ExcludeFiles)))
        args += (arg,)

    if os.path.exists(SourceFolder):
        if platform.system() == "Windows":
            robocopy_exe = ExpandPath(r'c:\windows\system32\robocopy.exe')
            # cmd = r'[robocopy_exe] /E /W:2 /R:2 /NP /NJH /NJS %s "[SourceFolder]" "[DestFolder]"' % (' '.join(args))
            cmd = r'[robocopy_exe] "[SourceFolder]" "[DestFolder]"  /E /W:2 /R:2 /NS %s' % (' '.join(args))
        else:
            #r'--dry-run'
            cmd = r'rsync --archive --recursive --times --delete --force [SourceFolder] [DestFolder]'
        if TraceOnly:
            Log(cmd)
            return
        EnsurePath(DestFolder)
        Run(cmd, Silent=Silent)

def is_hidden_file(FilePath):
    if platform.system() == "Windows":
        attribute = win32api.GetFileAttributes(FilePath)
        return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
    else:
        return FilePath.startswith('.')  #linux

def map_volume_to_drive(Volume):
    if platform.system() == "Windows":
        import Utility.Win32.Win32Utility as Win32Util
        driveMap = Win32Util.get_drive_map()
        return [ Volume, driveMap.Names.get(Volume, Volume) ]

    return [ Volume, Volume ]

def EnsurePath(FolderPath):
    FolderPath = ExpandPath(FolderPath)
    if not os.path.exists(FolderPath):
        Verbose(FolderPath)
        os.makedirs(FolderPath)

def MakePath(FolderPath):
    Verbose(FolderPath)
    FolderPath = ExpandPath(FolderPath)
    if not os.path.exists(FolderPath):
        os.makedirs(FolderPath)

def GlobByDate(PathMask):
    PathMask = Expand(PathMask)
    Trace(PathMask)

    fileList = [(os.stat(file).st_mtime, file) for file in glob.glob(PathMask)]
    fileList.sort()
    files = [file[1] for file in fileList]

    return files

def sort_files_by_date(FileList):
    fileList = [(os.stat(file).st_mtime, file) for file in FileList]
    fileList.sort()
    files = [file[1] for file in fileList]

    return files

def ListFromFile(FileName):
    FileName = ExpandPath(FileName)
    if not os.path.exists(FileName):
        return []

    items = []
    f = open(FileName, 'rt')
    for line in f:
        line = line.strip()
        if line:
            items.append(line)
    f.close()
    return items

def is_hidden(p):
    if os.name == 'nt':
        attribute = win32api.GetFileAttributes(p)
        return attribute & (win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM)
    else:
        return p.startswith('.')  #linux

def FindInFile(Text, FileName, Mode='rt'):
    Text = Expand(Text.lower())
    FileName = ExpandPath(FileName)
    items = []
    f = open(FileName, Mode)
    for line in f:
        line = str(line)
        if Text in line.lower():
            # line = str(line, "utf-8")
            items.append(str(line.rstrip('\r\n')))
    f.close()
    return items

def FindInFileRegEx(Text, FileName):
    FileName = ExpandPath(FileName)
    items = []
    f = open(FileName, 'r')
    for line in f:
        m = re.search(Text, line)
        if m and m.group(0):
            items.append(line.rstrip('\r\n'))
    f.close()
    return items

def FindInLines(Text, Lines):
    Text = Expand(Text.lower())
    items = []
    for line in Lines:
        if Text in line.lower():
            items.append(line.rstrip('\r\n'))
    return items

def FindFilesByDate(directory, pattern='*', ExcludeList=[], Desc=True):
    fileList = [(os.stat(file).st_mtime, file) for file in FindFiles(directory, pattern, ExcludeList)]
    fileList.sort()
    if Desc:
        fileList.reverse()
    files = [file[1] for file in fileList]
    return files

def FindFiles(directory, pattern='*', ExcludeList=[]):

    def ExcludeFile(filename, folder, ExcludeList):
        filename = filename.lower()
        if filename in ExcludeList:
            return True
        folder = os.path.basename(folder)
        if folder in ExcludeList:
            return True
        for exclude in ExcludeList:
            if filename.endswith(exclude):
                return True
        return False

    pattern = Expand(pattern)
    if not pattern:
        pattern = '*'

    regex_pattern = re.compile(fnmatch.translate(pattern), re.IGNORECASE)

    ExcludeList = list(map(str.lower, ExcludeList))

    directory = ExpandPath(directory)
    directory = os.path.abspath(directory)
    if directory:
        for root, dirs, files in os.walk(directory):
            for folder in dirs:
                absFolder = ExpandPath(r'[root]\%s' % (folder.lower()))
                if folder.lower() in ExcludeList or absFolder in ExcludeList:
                    #Log('Excluded [absFolder]')
                    dirs.remove(folder)

            for basename in files:
                if ExcludeFile(basename, root, ExcludeList):
                    continue
                elif fnmatch.fnmatch(basename, pattern) or regex_pattern.match(basename):
                    filename = os.path.join(root, basename)
                    if not is_hidden(filename):
                        yield filename

def FindFolders(directory, pattern='*', ExcludeList=[r'.git', '__pycache__']):

    pattern = Expand(pattern)
    if not pattern:
        pattern = '*'

    regex_pattern = re.compile(fnmatch.translate(pattern), re.IGNORECASE)

    ExcludeList = list(map(str.lower, ExcludeList))

    directory = ExpandPath(directory)
    directory = os.path.abspath(directory)
    if directory:
        for root, dirs, files in os.walk(directory):
            for folder in dirs:
                folderPath = os.path.join(root, folder)
                basename = os.path.basename(folder)
                if folder.lower() in ExcludeList or folderPath.lower() in ExcludeList:
                    dirs.remove(folder)
                    continue

                elif fnmatch.fnmatch(basename, pattern) or regex_pattern.match(basename):
                    yield folderPath

def ReplaceInFile(FilePath, SourcePattern, Subst, UseRegEx=False):
    FilePath = ExpandPath(FilePath)
    LogPlain('Processing UseRegEx:%d %s , "%s"' % (UseRegEx, FilePath, SourcePattern))

    fh, abs_path = tempfile.mkstemp()
    temp_file = open(abs_path, 'w')
    old_file = open(FilePath)
    for line in old_file:
        if SourcePattern in line:
            LogPlain('Before ' + line.strip('\r\n'))
            line = line.replace(SourcePattern, Subst)
            LogPlain('After  ' + line.strip('\r\n'))
        elif UseRegEx:
            m = re.search(SourcePattern, Subst)
            if m:
                found = line[m.start():m.stop()]
                LogPlain('RE-Before ' + line.strip('\r\n'))
                line = line.replace(found, Subst)
                LogPlain('RE-After  ' + line.strip('\r\n'))

        temp_file.write(line)
    temp_file.close()
    os.close(fh)
    old_file.close()
    os.remove(FilePath)
    shutil.move(abs_path, FilePath)

def BackupFile(SourceFile, DestPath, MaxBackups=10):
    Trace(r'[SourceFile] [DestPath]')
    SourceFile = ExpandPath(SourceFile)
    DestPath = ExpandPath(DestPath)

    fileName, ext = os.path.splitext(os.path.basename(SourceFile))

    EnsurePath(DestPath)
    backupFile = ''
    for idx in range(1, MaxBackups):
        tempFile = Expand(r'[DestPath]\[fileName].[ProjectName].[idx].log')
        if not os.path.exists(tempFile):
            backupFile = tempFile
            break

    if not backupFile:
        files = GlobByDate(r'[DestPath]\[fileName].[ProjectName].*.log')
        files.append(Expand(r'[DestPath]\[fileName].[ProjectName].1.log'))
        backupFile = files[0]

    if os.path.exists(backupFile):
        DeleteFile(backupFile)

    CopyFile(SourceFile, backupFile)

def GenUniqueFileName(SourceFile, DestPath, Suffix=r'.[ProjectName]'):
    # Trace(r'[SourceFile] [DestPath]')
    #dbg_print(SourceFile)
    SourceFile = ExpandPath(SourceFile)
    print(DestPath)
    DestPath = ExpandPath(DestPath)

    fileName, ext = os.path.splitext(os.path.basename(SourceFile))

    EnsurePath(DestPath)
    tempFile = ExpandPath(r'[DestPath]\[fileName][ext]')
    if not os.path.exists(tempFile):
        return Plain(tempFile)

    destFile = ''
    idx = 1
    while True:
        tempFile = ExpandPath(r'[DestPath]\[fileName][Suffix].[idx][ext]')
        if not os.path.exists(tempFile):
            destFile = tempFile
            break
        idx += 1

    if not destFile:
        files = GlobByDate(r'[DestPath]\[fileName].[Suffix].*[ext]')
        files.append(ExpandPath(r'[DestPath]\[fileName].[Suffix].1[ext]'))
        destFile = files[0]

    if os.path.exists(destFile):
        Error('Not a unique file [destFile]')

    return Plain(destFile)

def GenUniqueFileNamePlain(SourceFile, DestPath, Suffix=r'.[ProjectName]'):
    # Trace(r'[SourceFile] [DestPath]')
    #dbg_print(SourceFile)
    SourceFile = ExpandPathPlain(SourceFile)
    DestPath = ExpandPathPlain(DestPath)

    fileName, ext = os.path.splitext(os.path.basename(SourceFile))

    if not os.path.exists(DestPath):
        os.makedirs(DestPath)

    tempFile = ExpandPathPlain(r'%s\%s%s' % (DestPath, fileName, ext))
    if not os.path.exists(tempFile):
        return Plain(tempFile)

    destFile = ''
    idx = 1
    while True:
        tempFile = ExpandPathPlain(r'%s\%s%s.%s%s' % (DestPath, fileName, Suffix, idx, ext))
        if not os.path.exists(tempFile):
            destFile = tempFile
            break
        idx += 1

    if not destFile:
        files = GlobByDate(r'%s\%s.%s.*%s' % (DestPath, fileName, Suffix, ext))
        files.append(ExpandPathPlain(r'%s\%s.%s.1%s' % (DestPath, fileName, Suffix, ext)))
        destFile = files[0]

    if os.path.exists(destFile):
        Error('Not a unique file %s' % (destFile))

    return Plain(destFile)

def CopyToUniqueFile(SourceFile, DestPath, Suffix=r'[ProjectName]'):
    destFile = GenUniqueFileName(SourceFile, DestPath, Suffix)
    CopyFile(SourceFile, destFile)
    return destFile

def CopyToUniqueFilePlain(SourceFile, DestPath, Suffix=r'[ProjectName]'):
    SourceFile = Plain(SourceFile)
    DestPath = Plain(DestPath)
    destFile = GenUniqueFileNamePlain(SourceFile, DestPath, Suffix)
    CopyFile(SourceFile, destFile)
    return destFile

def CheckPaths(file):
    fileName = os.path.basename(file)
    folder = os.path.dirname(file)
    folderName = os.path.basename(folder)
    #dbg_print(file)
    if fileName.lower() == folderName.lower():
        return True
    else:
        return False

def MoveToUniqueFile(SourceFile, DestPath, Suffix=r'[ProjectName]'):
    destFile = GenUniqueFileName(SourceFile, DestPath, Suffix)
    MoveFile(SourceFile, destFile)
    return destFile

def MoveToUniqueFilePlain(SourceFile, DestPath, Suffix=r'[ProjectName]'):
    SourceFile = Plain(SourceFile)
    DestPath = Plain(DestPath)
    destFile = GenUniqueFileNamePlain(SourceFile, DestPath, Suffix)
    MoveFile(SourceFile, destFile)
    return destFile

def FileListFromPathList(PathList=[], ExcludeList=[]):
    if not isinstance(PathList, list):
        PathList = [PathList]

    for path in PathList:
        path = ExpandPath(path)
        if not path.strip():
            continue
        path = os.path.abspath(path)
        for found in FindFiles(path, '*', ExcludeList):
            yield found

def GetSubFolders(Folder):
    # Trace(Folder)
    subFolders = []
    for item in os.listdir(Folder):
        item = os.path.join(Folder, item)
        if os.path.isdir(item):
            subFolders.append(item)
    return subFolders

def GetSubFiles(Folder):
    subFiles = []
    for item in os.listdir(Folder):
        item = os.path.join(Folder, item)
        if os.path.isfile(item):
            subFiles.append(item)
    return subFiles

def zip_folder(ZipFilePath, Folder='', *args, **kwargs):
    Folder = ExpandPath(Folder)
    Folder = ternary(len(Folder) == 0, os.getcwd(), Folder)
    pushd(Folder)
    zip_path_list(ZipFilePath, Folder, *args, **kwargs)
    popd()

def file_size_string(FilePath):
    FilePath = Expand(FilePath)
    MB = 1024 * 1024.0
    GB = 1024 * MB
    size = os.path.getsize(FilePath)
    factor, suffix = ternary(size > GB, [GB, 'GB'], [MB, 'MB'])
    file_size = "{:12.2f} ".format(size / factor) + suffix
    return file_size.strip()

def zip_path_list(ZipFilePath, PathList=[], Mode='w', ZipFolderPrefix='', ExcludeList=None, ZippedFiles=None):
    TraceVerbose('[ZipFilePath] [Mode] [PathList] from ' + os.getcwd())
    ZipFilePath = ExpandPath(ZipFilePath)
    if ExcludeList == None:
        ExcludeList = Globals.ZipExcludeList

    EnsurePath(os.path.dirname(ZipFilePath))

    if not isinstance(PathList, list):
        PathList = [PathList]
    Folder = ternary(len(PathList) == 0, [os.getcwd()], PathList)

    if ZipFolderPrefix:
        ZipFolderPrefix = ZipFolderPrefix + r'\\'

    def MakeZipFolderName(FilePath):
        for folder in PathList:
            folder = os.path.abspath(ExpandPath(folder))
            if folder in FilePath:
                return ZipFolderPrefix + FilePath[len(folder) + 1:]
        return ZipFolderPrefix + os.path.basename(FilePath)

    zipFile = zipfile.ZipFile(ZipFilePath, Mode)

    Terse(r'Zipping   [ZipFilePath:<40] from %s' % os.getcwd())
    for folder in PathList:
        mask = '*'
        folderName = os.path.basename(folder)
        if '*' in folderName:
            folder = os.path.dirname(folder)
            mask = folderName
        for path in FindFiles(folder, mask, ExcludeList):
            zipPath = MakeZipFolderName(path)
            if ZippedFiles != None:
                ZippedFiles.append(path)
            #Verbose(r'   Zipping {0:40} from {1}'.format(zipPath, path))
            zipFile.write(path, zipPath)
    zipFile.close()
    Verbose(r'Completed [ZipFilePath]')

def zip_get_path_list(PathList=[], ExcludeList=None):
    TraceVerbose('[PathList] from ' + os.getcwd())
    if ExcludeList == None:
        ExcludeList = Globals.ZipExcludeList

    if not isinstance(PathList, list):
        PathList = [PathList]
    Folder = ternary(len(PathList) == 0, [os.getcwd()], PathList)

    zippedFiles = []

    for folder in PathList:
        mask = '*'
        folderName = os.path.basename(folder)
        if '*' in folderName:
            folder = os.path.dirname(folder)
            mask = folderName
        for path in FindFiles(folder, mask, ExcludeList):
            zippedFiles.append(path)

    return zippedFiles

def zip_folders(ZipFolderRoot, Folders=[], *args, **kwargs):
    Folders = ternary(len(Folders) == 0, [os.getcwd()], Folders)
    Trace(Folders)

    results = []
    for folder in Folders:
        folder = os.path.abspath(ExpandPath(folder))
        folderName = os.path.basename(folder)
        subFolderList = GetSubFolders(folder)
        for subfolder in subFolderList:
            os.chdir(subfolder)
            subFolderName = os.path.basename(subfolder)
            zipFilePath = Expand(r'[ZipFolderRoot]\[folderName]\[subFolderName].zip')
            zip_path_list(zipFilePath, subfolder, *args, **kwargs)
            results.append([file_size_string(zipFilePath), zipFilePath, folder])

    for folder in Folders:
        folder = os.path.abspath(ExpandPath(folder))
        fileList = GetSubFiles(folder)
        folderName = os.path.basename(folder)
        zipFilePath = Expand(r'[ZipFolderRoot]\[folderName].zip')
        pushd(folder)
        zip_path_list(zipFilePath, fileList, *args, **kwargs)
        popd()
        results.append([file_size_string(zipFilePath), zipFilePath, folder])

    Log()
    PrettyPrint(results, 'Zip Files')

def unzip(ZipFilePath, DestFolder):
    Trace(ZipFilePath, DestFolder)

    ZipFilePath = ExpandPath(ZipFilePath)
    DestFolder = ExpandPath(DestFolder)
    if not os.path.exists(DestFolder):
        os.makedirs(DestFolder)
    pushd(DestFolder)

    zipFile = zipfile.ZipFile(ZipFilePath)
    for path in zipFile.namelist():
        abspath = os.path.abspath(path)
        folder = os.path.dirname(abspath)
        if not os.path.exists(folder):
            Log('makedirs  [folder]')
            os.makedirs(folder)
        Log('unzipping [abspath]')
        zipFile.extract(path)

    popd()

def SetLogFile(DestPath, SourcePath=r'[LogFile]'):
    TraceVerbose(DestPath, 'from', SourcePath)
    DestPath = ExpandPath(DestPath)
    SourcePath = ExpandPath(SourcePath)
    if DestPath == SourcePath:
        return

    folder = os.path.dirname(SourcePath)
    filebasename, ext = os.path.splitext(os.path.basename(SourcePath))
    sourceVerbosePath = Expand(r'[folder]\[filebasename].Verbose[ext]')

    folder = os.path.dirname(DestPath)
    filebasename, ext = os.path.splitext(os.path.basename(DestPath))
    destVerbosePath = Expand(r'[folder]\[filebasename].Verbose[ext]')

    FileLog(Expand(r'SetLogFile [DestPath] from [SourcePath]'), Silent=True)
    if Globals.RunningAsService:
        if os.path.exists(SourcePath):
            # mode = 'a' if os.path.exists(DestPath) else 'w'
            with open(DestPath, 'a') as fp:
                file = open(SourcePath, 'r')
                fp.write(file.read())
                file.close()
            os.remove(SourcePath)

        if os.path.exists(sourceVerbosePath):
            # mode = 'a' if os.path.exists(DestPath) else 'w'
            with open(destVerbosePath, 'a') as fp:
                file = open(sourceVerbosePath, 'r')
                fp.write(file.read())
                file.close()
            os.remove(sourceVerbosePath)

    else:
        while True:
            try:
                MoveFile(SourcePath, DestPath, Silent=True)
                MoveFile(sourceVerbosePath, destVerbosePath, Silent=True)
                break
            except:
                pass

    Globals.LogFile = DestPath

#-------------------------------------------------------------------------------------
# Path Functions
#-------------------------------------------------------------------------------------

class pushd():
    directory_stack = []

    def __init__(self, DestPath=""):
        if not DestPath:
            PrettyPrintList(DestPath)
            return

        pushd.directory_stack.append(os.getcwd())
        os.chdir(ExpandPath(DestPath))
        Verbose('pushd ' + os.getcwd())

class popd():
    def __init__(self):
        if len(pushd.directory_stack):
            dest = pushd.directory_stack[-1]
            del pushd.directory_stack[-1]
            os.chdir(dest)
            Verbose('popd ' + os.getcwd())

#-------------------------------------------------------------------------------------
# Logging Functions
#-------------------------------------------------------------------------------------

def IncreaseIndent(Indent=3):
    Globals.Indent += Indent

def DecreaseIndent(Indent=3):
    Globals.Indent -= Indent
    if Globals.Indent < 0:
        Globals.Indent = 0

def GenerateIndent(Indent=0):
    global_indent = Globals.get('Indent', 0)
    return (global_indent * ' ') + (Indent * ' ')

def ArgsToMessage(*args, **kwargs):
    is_plain = False
    for arg in args:
        if isinstance(arg, Utility.Globals.Plain):
            is_plain = True
    msgFromArgs = [ternary(is_plain, Plain(str(arg)), str(arg)) for arg in args]
    if not isinstance(msgFromArgs, list):
        msgFromArgs = [msgFromArgs]
    msgFromArgs = ' '.join(msgFromArgs).strip()
    msgFromArgs = ternary(is_plain, Plain(msgFromArgs), msgFromArgs)
    if kwargs.get('UseExpand', True):
        return Expand(msgFromArgs)
    else:
        return msgFromArgs

def dbgprint(*args, **kwargs):
    #original_print(Fore.RED + Style.BRIGHT, *args, end='')
    #original_print(Style.RESET_ALL)
    #original_print(*args, **kwargs)
    pass

def dbg_print(*args, **kwargs):
    try:
        kwargs['UseExpand'] = False
        Message = ArgsToMessage(*args, **kwargs)
        print('\r', Message, '                                                 ', end=' ')
    except:
        try:
            Message = ''.join(filter(lambda x: x in string.printable, Message))
            print('\r', Message, '                                                 ', end=' ')
        except:
            pass

def LogJSON(DataObj={}, UseExpand=False, *args, **kwargs):
    # print(DataObj)
    if DataObj and len(DataObj):
        message = json.dumps(DataObj, sort_keys=True, indent=4)
        LogNoIndent(message, UseExpand=UseExpand, *args, **kwargs)

def LogNoIndent(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)
    DecreaseIndent()
    Log(Message, **kwargs)
    IncreaseIndent()

def LogPlain(*args, **kwargs):
    if 'UseExpand' not in kwargs:
        kwargs['UseExpand'] = False
    Message = ArgsToMessage(*args, **kwargs)
    Log(Message, **kwargs)

def Log(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)

    if 'OpenMode' not in kwargs:
        kwargs['OpenMode'] = 'a'

    if 'Silent' not in kwargs and Globals.Terse:
        kwargs['Silent'] = True

    FileLog(Message, **kwargs)

def LogError(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)
    kwargs['ConsoleColor'] = Fore.RED
    info = Inspector.GetCallerInfo()
    trace = '%s(%d) ' % (info.callerName, info.lineno)
    Log(trace + Message, **kwargs)

def LogPlainError(*args, **kwargs):
    kwargs['UseExpand'] = False
    Message = ArgsToMessage(*args, **kwargs)
    kwargs['ConsoleColor'] = Fore.RED
    info = Inspector.GetCallerInfo()
    trace = '%s(%d) ' % (info.callerName, info.lineno)
    Log(trace + Message, **kwargs)

def Error(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)
    raise ExitErrorException(Message, **kwargs)

def Warning(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)
    kwargs['ConsoleColor'] = Fore.CYAN
    info = Inspector.GetCallerInfo()
    trace = '%s(%d) ' % (info.callerName, info.lineno)
    Log(trace + Message, **kwargs)

def Verbose(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)

    if not Globals.Verbose and 'Silent' not in kwargs:
        kwargs['Silent'] = True

    FileLog(Message, Verbose=True, **kwargs)

def Terse(*args, **kwargs):
    Message = ArgsToMessage(*args, **kwargs)
    FileLog(Message, Terse=True, **kwargs)

def Exit(*args, ExitCode=1, **kwargs):
    kwargs['UseExpand'] = False
    Message = ArgsToMessage(*args, **kwargs)

    Log(r'Exit %d %s' % (ExitCode, Message), **kwargs)
    Globals.ExitCode = ExitCode
    sys.exit(ExitCode)
    # raise ExitErrorException(Message)

def FileLog(Message='',
            FilePath='[LogFile]',
            Indent=0,
            OpenMode='a',
            Silent=False,
            Verbose=False,
            Terse=False,
            ConsoleColor=Style.RESET_ALL,
            **kwargs):  # kwargs are for unused args passed in b/c of caller
    try:

        if False:  # Include caller / code info
            info = Inspector.GetCallerInfo(4)
            if info:
                trace = '%s(%d) - %s' % (info.callerName, info.lineno, info.code[0].strip())
                Message = '{0:<100} CODE: {1}'.format(Message, trace)

        try:
            if not Silent and Globals.ConsoleEcho and not Globals.RunningAsService:
                if Globals.Terse:
                    if Terse:
                        original_print(ConsoleColor + GenerateIndent(Indent) + Message)
                elif Verbose:
                    if Globals.Verbose:
                        original_print(ConsoleColor + GenerateIndent(Indent) + Message)
                else:
                    original_print(ConsoleColor + GenerateIndent(Indent) + Message)

            # if Globals.Service:
            #    try:
            #        Globals.Service.eventLog(Message)
            #    except:
            #        pass
        except:
            pass

        FilePath = ExpandPath(FilePath)
        logFile = Globals.LogFile
        try:
            if not Verbose:
                f = open(FilePath, OpenMode)
                f.write(GenerateIndent(Indent) + Message + '\n')
                f.close()
            else:
                folder = os.path.dirname(FilePath)
                filename = os.path.basename(FilePath)
                filebasename, ext = os.path.splitext(filename)
                verboseFile = Expand(r'[folder]\[filebasename].Verbose[ext]')
                f = open(verboseFile, OpenMode)
                f.write(GenerateIndent(Indent) + Message + '\n')
                f.close()
        except:
            pass

        try:
            if FilePath != logFile:
                f = open(logFile, 'a')
                f.write(GenerateIndent(Indent) + Message + '\n')
                f.close()
        except:
            pass

        try:
            if Globals.DebugMode:
                fp = open(Expand(r'[Temp]\debug.log'), 'a')
                fp.write(str(Privates.pid) + ':' + GenerateIndent(Indent) + Message + '\n')
                fp.close()
        except:
            pass

        try:
            if Globals.DebugPidMode:
                fp = open(Expand(r'[Temp]\debug.[pid].log'), 'a')
                fp.write(GenerateIndent(Indent) + Message + '\n')
                fp.close()
        except:
            pass

    except IOError:
        pass

def LogCallStack():
    stack = []
    for tb in traceback.extract_stack():
        stack.append([ tb[0], tb[1], tb[2] ])
    PrettyPrint(stack, 'CallStack')
    input('Expand Error.  Press any key to continue')

def PrettyPrint(Object, Header='', Prefix=r'', *args, **kwargs):
    if not Object or len(Object) == 0:
        return

    # traceback.print_stack()

    if Header:
        Log(Header)
        Log('------------')

    if isinstance(Object, str) or isinstance(Object, str):
        Log(Object, Prefix, *args, **kwargs)
    elif isinstance(Object, dict):
        PrettyPrintDict(Object, Prefix, *args, **kwargs)
    elif isinstance(Object, list):
        PrettyPrintList(Object, Prefix, *args, **kwargs)
    else:
        PrettyPrintList(list(Object), Prefix, *args, **kwargs)

def PrettyPrintList(ItemList, Prefix=r'', Join=' ', *args, **kwargs):
    if len(ItemList) == 0:
        return

    if 'Silent' not in kwargs and 'FilePath' in kwargs:
        kwargs['Silent'] = True

    if 'Indent' not in kwargs:
        kwargs['Indent'] = 3

    if 'UseExpand' not in kwargs:
        kwargs['UseExpand'] = False

    if Prefix != r'':
        Prefix += ' '

    if type(ItemList[0]) is not list:
        for item in ItemList:
            if type(item) is not dict and type(item) is not DictN:
                Log(r'%s%s' % (Prefix, item), *args, **kwargs)
            else:
                PrettyPrintDict(item, *args, **kwargs)
    else:
        columnWidths = []
        for idx in range(0, len(ItemList[0])):
            widths = []
            for item in ItemList:
                widths.append(len(str(item[idx])))
            columnWidths.append(max(widths))

        for item in ItemList:
            line = []
            for idx in range(0, len(ItemList[0])):
                line.append(r'%-*s' % (columnWidths[idx], item[idx]))
            message = r'%s%s' % (Prefix, Join.join(line))
            Log(message.rstrip(), *args, **kwargs)

def PrettyPrintDict(DictObj, Prefix=r'', *args, **kwargs):
    if len(list(DictObj.keys())) == 0:
        return

    if Prefix != '':
        Log(r'[Prefix]:')
    LogJSON(DictObj, *args, **kwargs)

#-------------------------------------------------------------------------------------
# Run Command Functions
#-------------------------------------------------------------------------------------
def Run(Cmd, DirectoryPath='', UseExpand=True, ConsoleColor=Style.RESET_ALL, Silent=False, ThrowOnError=False):
    if UseExpand:
        Cmd = Expand(Cmd)
    if not Silent:
        Log(Cmd, UseExpand=UseExpand, ConsoleColor=ConsoleColor)

    if DirectoryPath:
        pushd(DirectoryPath)

    try:
        subprocess.check_call(Cmd)
    except:
        if DirectoryPath:
            popd()
        if ThrowOnError:
            raise
        else:
            return -1

    if DirectoryPath:
        popd()

def RunUIApp(Cmd, DirectoryPath='', *args, **kwargs):
    Cmd = ExpandPath(Cmd)
    Log(Cmd, *args, **kwargs)

    if DirectoryPath:
        pushd(DirectoryPath)

    p = subprocess.Popen(Cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if DirectoryPath:
        popd()

def RunChecked(Cmd, *args, **kwargs):
    if 'ThrowOnError' not in kwargs:
        kwargs['ThrowOnError'] = True
    Run(Cmd, *args, **kwargs)

def RunExOld(Cmd, DirectoryPath='', *args, **kwargs):
    Log(Cmd, *args, **kwargs)
    Cmd = ExpandPath(Cmd)

    if DirectoryPath:
        pushd(DirectoryPath)

    my_env = os.environ
    p = subprocess.Popen(Cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=my_env)
    while(True):
        retcode = p.poll()  # returns None while subprocess is running
        line = p.stdout.readline().strip()
        if line:
            yield line
        if(retcode is not None):
            yield 'retCode=%d' % retcode
            break

    if DirectoryPath:
        popd()

def RunEx(Cmd, DirectoryPath='', UseExpand=True, *args, **kwargs):
    Log(Cmd, *args, **kwargs)
    if UseExpand:
        Cmd = Expand(Cmd)

    if DirectoryPath:
        pushd(DirectoryPath)

    my_env = os.environ
    output = subprocess.check_output(Cmd, stderr=subprocess.STDOUT)

    if DirectoryPath:
        popd()

    if not isinstance(output, str):
        output = output.decode('utf-8')
    return output.split('\r\n')

def IsProcessRunning(PID):
    Trace(PID)
    PID = Expand(str(PID))

    for line in RunEx(Expand(r'tasklist.exe /NH /FI "PID eq [PID]"'), Silent=True):
        if PID in line:
            return True

    return False

#-------------------------------------------------------------------------------------
# Misc
#-------------------------------------------------------------------------------------
def rreplace(s, old, new, occurrence):
    li = s.rsplit(old, occurrence)
    return new.join(li)

def secondsToStr(t):
    return "%d:%02d:%02d.%03d" % \
        reduce(lambda ll, b : divmod(ll[0], b) + ll[1:],
            [(t * 1000,), 1000, 60, 60])

def cls():
    if Globals.cls and not Globals.SkipCls:
        if platform.system() == 'Windows':
            os.system('cls')
        else:
            Run('clear')

def ReplaceTrueFalseWithBooleans(ItemList):
    results = []
    for item in ItemList:
        if item.lower() == 'true':
            results.append(True)
        elif item.lower() == 'false':
            results.append(False)
        elif item.lower() == 'none':
            results.append(None)
        else:
            results.append(item)
    return results

def dict_update(d, u):
    for k, v in list(u.items()):
        if isinstance(v, collections.Mapping):
            r = dict_update(d.get(k, {}), v)
            d[k] = DictN(r)
        elif isinstance(v, dict):
            r = dict_update(d.get(k, {}), v)
            d[k] = DictN(r)
        else:
            d[k] = u[k]
    return d

def ListToHtmlTableColumns(Row, Prefix='   ', TDClass=''):
    if TDClass:
        TDClass = r"class='%s'" % (TDClass)
    contents = []
    for col in Row:
        contents.append('%s<td %s><span>%s</span></td>' % (Prefix, TDClass, str(col).strip()))
    return '\n'.join(contents)

def ListToHtmlTableRows(Data, Prefix='   ', TDClass=''):
    if len(Data) == 0:
        return '\n'

    # Make sure we have a list of rows
    rowSet = Data
    if isinstance(Data, list) and not isinstance(Data[0], list):
        rowSet = []
        for item in Data:
            rowSet.append([item])

    contents = []
    for idx, row in enumerate(rowSet):
        tdData = ListToHtmlTableColumns(row, Prefix, TDClass)
        if idx == 0 and len(rowSet) > 1:
            tdData = tdData.replace('<td', '<th').replace('</td', '</th')
        contents.append(r'%s<tr>%s%s</tr>' % (Prefix, tdData, Prefix))

    return '\n'.join(contents)

def CSV_SaveToFile(FilePath, CsvData, Append=False, IncludeIndex=False):
    Trace(FilePath)
    FilePath = ExpandPath(FilePath)

    idx = 0
    file = open(FilePath, ternary(Append, 'a', 'w'))
    for csv in CsvData:
        if IncludeIndex:
            idx += 1
            file.write('%d,%s\n' % (idx, ','.join(csv)))
        else:
            file.write('%s\n' % (','.join(csv)))
    file.close()

class JSON():
    @staticmethod
    def load_from_file(FilePath, PrettyPrint=True):
        TraceVerbose(r'[FilePath] [PrettyPrint] [Verbose]')
        FilePath = ExpandPath(FilePath)

        data = {}
        if os.path.exists(FilePath):
            file = open(FilePath, 'r')
            if PrettyPrint:
                data = file.read()
                data = data.replace('\r\n', '')
                data = data.replace('\n', '')
                if data.strip():
                    data = json.loads(data)
            else:
                data = json.load(file)
            file.close()
            if Verbose:
                Verbose('Loaded JSON data:')
                LogJSON(data, Verbose=True)

        if len(data) == 0 or len(list(data.keys())) == 0:
            data = DictN()
        else:
            data = DictN(data)

        return data

    @staticmethod
    def load_from_string(Data, PrettyPrint=True, Verbose=False):
        TraceVerbose(r'[PrettyPrint] [Verbose]')

        data = Data
        if PrettyPrint:
            data = data.replace('\r\n', '')
            data = data.replace('\n', '')
            # useful for debugging
            #fp = open(ExpandPath(r'[Temp]\json_debug.json'), 'w')
            #fp.write(data)
            #fp.close()

        if data.strip():
            data = json.loads(data)
        else:
            data = DictN()

        if Verbose:
            Verbose('Loaded JSON data:')
            LogJSON(data, Verbose=True)

        if len(data) == 0 or len(list(data.keys())) == 0:
            data = DictN()
        else:
            data = DictN(data)

        return data

    @staticmethod
    def update_file(FilePath, NewData={}, PrettyPrint=True):
        return JSON.save_to_file(FilePath, NewData, Update=True, PrettyPrint=PrettyPrint)

    @staticmethod
    def save_to_file(FilePath, NewData={}, Update=False, PrettyPrint=True):
        FilePath = ExpandPath(FilePath)
        TraceVerbose(r'[FilePath] [Update] [PrettyPrint] [Verbose]')

        data = DictN()
        if Update:
            data = JSON.load_from_file(FilePath)

        # Update
        dict_update(data, NewData)
        Verbose(r'New Data:')
        PrettyPrintDict(data, UseExpand=False, Verbose=True)

        # Save new data
        file = open(FilePath, 'w')
        if PrettyPrint:
            lines = json.dumps(data, sort_keys=True, indent=4)
            file.write(lines)
        else:
            JSON.dump(data, file)

        file.close()

        Verbose(r'Final Data:')
        LogJSON(data, Verbose=True)

        return data

    @staticmethod
    def delete_key_from_file(FilePath, Key, *args, **kwargs):
        Silent = False
        TraceVerbose(r'[FilePath] [Key]')
        data = JSON.load_from_file(FilePath, *args, **kwargs)
        if len(data) == 0 or len(list(data.keys())) == 0:
            return
        if Key in list(data.keys()):
            del data[Key]
        JSON.save_to_file(FilePath, data, *args, **kwargs)

def SaveEnvironment():
    Trace(r'[Action] [LogFile]')
    JSON.save_to_file(Globals.GlobalSaveFile, Globals)
    JSON.save_to_file(Globals.TempsSaveFile, Temps)
    JSON.save_to_file(Globals.EnvironSaveFile, os.environ)

def RestoreEnvironment():
    Trace(r'[Action] [LogFile]')
    Temps.update(JSON.load_from_file(Globals.TempsSaveFile))
    Temps.update(JSON.load_from_file(Globals.EnvironSaveFile))

    currentLogFile = Globals.LogFile
    Globals.update(JSON.load_from_file(Globals.GlobalSaveFile))
    SetLogFile(Globals['LogFile'], currentLogFile)

#-------------------------------------------------------------------------------------
# Error Functions
#-------------------------------------------------------------------------------------
class ExitErrorException(Exception):

    def __init__(self, ErrorMessage, IsError=True, UseExpand=True):
        if UseExpand:
            ErrorMessage = Expand(ErrorMessage)

        self.ExitError = True
        self.IsError = IsError
        self.ErrorMessage = ErrorMessage

        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, ErrorMessage)

def iterate_traceback(tb):
    while tb is not None:
        yield tb
        tb = tb.tb_next

def LogExceptionCallStack():
    IncreaseIndent()
    Log("-" * 30, UseExpand=False)

    exception_info = sys.exc_info()
    tracebackObj = exception_info[2]

    ex_list = []
    # ex_list.append(['Source', 'Function', 'Code', 'SourceEx'])
    # ex_list.append(['------', '--------', '----', '--------'])
    for ex in traceback.extract_tb(tracebackObj):
        ex = list(ex)
        file, line, function, code = ex
        ex_list.append([r'%s(%d)' % (os.path.basename(file), line), function, code, r'%s(%d)' % (file, line)])
    PrettyPrintList(ex_list, Indent=0, UseExpand=False)

    Log("-" * 30, UseExpand=False)
    DecreaseIndent()

saveExceptionList = []

def CacheException():
    exData = []
    exception_info = sys.exc_info()
    tracebackObj = exception_info[2]
    for ex in traceback.extract_tb(tracebackObj):
        ex = list(ex)
        file, line, function, code = ex
        data = [os.path.basename(file), line]
        exData.append(data)

    if exData not in saveExceptionList:
        saveExceptionList.append(exData)
        return True
    else:
        return False

def LogException():
    exception_info = sys.exc_info()
    exType, message, tbObject = exception_info
    message = str(message)
    Log(exType, message, Fore.RED, UseExpand=False)

def ReportException():
    #if not CacheException():
    #    # skip exception already seen
    #    return

    exception_info = sys.exc_info()
    Log()
    exType, message, tbObject = exception_info
    message = str(message)
    try:
        ex = exception_info[1]
        if isinstance(ex, SystemExit):
            return

        Log('#### EXCEPTION ####', ConsoleColor=Fore.RED + Style.BRIGHT, UseExpand=False)
        Log()
        Log(message, ConsoleColor=Fore.RED + Style.BRIGHT, UseExpand=False)
        Log()
        LogExceptionCallStack()
        Log()
        Log(message, ConsoleColor=Fore.RED + Style.BRIGHT, UseExpand=False)

        if not Globals.RunningAsService:
            # email.send_email(Subject='Error: %s' % str(sys.exc_info()[1]), Attachments=[Globals.LogFile])
            Globals.ExitCode = 1

    except:
        Log('Failed to print exception_info info', ConsoleColor=Fore.RED + Style.BRIGHT, UseExpand=False)
        if not Globals.RunningAsService:
            print(exception_info)

    if sys.flags.debug:
        raise Exception('Break for debugger attached')

class Inspector:
    @staticmethod
    def LogMembers(ClassObj):
        results = []
        for data in inspect.getmembers(ClassObj):
            if not inspect.ismethod(data[1]):
                results.append([data[0], data[1]])
        PrettyPrint(results)

    @staticmethod
    def GetMembers(ClassObj):
        results = []
        for data in inspect.getmembers(ClassObj):
            results.append(data[0])
        return results

    @staticmethod
    def GetMethods(ClassObj):
        results = []
        for data in inspect.getmembers(ClassObj, predicate=inspect.ismethod):
            results.append(data[0])
        return results

    @staticmethod
    def GetFunctions(ClassObj):
        results = []
        for data in inspect.getmembers(ClassObj, predicate=inspect.isfunction):
            if not inspect.ismethod(data[1]):
                results.append(data[0])
        return results

    @staticmethod
    def GetFunctionsObjects(ClassObj):
        results = []
        for data in inspect.getmembers(ClassObj, predicate=inspect.isfunction):
            if not inspect.ismethod(data[1]):
                results.append(data[1])
        return results

    @staticmethod
    def GetDescriptors(ClassObj):
        results = []
        for data in inspect.getmembers(ClassObj):
                if not inspect.ismethoddescriptor(data[1]) or inspect.ismemberdescriptor(data[1]):
                    results.append(data[0])
        return results

    @staticmethod
    def GetCallerInfo(Depth=2):
        funcName = 'NoFuncName'
        stack = inspect.stack()
        info = DictN()
        try:
            idx = ternary(Depth < len(stack), Depth, -1)
            frame = stack[idx]
            info.file = frame[1]
            info.lineno = frame[2]
            info.callerName = frame[3]
            info.code = frame[4]
            funcName = frame[3]
            f_locals = frame[0].f_locals
            self = f_locals.get('self', None)
            if self:
                className = self.__class__.__name__
                funcName = r'{0}::{1}'.format(className, funcName)
        except:
            ReportException()
            pass

        del stack
        info.name = funcName
        return info

#-------------------------------------------------------------------------------------
# Threading
#-------------------------------------------------------------------------------------
class FuncThread(threading.Thread):
    def __init__(self, Func, *args, **kwargs):
        self.Func = Func
        self.args = args
        self.kwargs = kwargs
        threading.Thread.__init__(self)

    def run(self):
        Trace(r'[Func] [args] [kwargs]')
        self.Func()
        # self.Func(*self.args, **self.kwargs)

    @staticmethod
    def RunFunc(Func, *args, **kwargs):
        Trace(Func)
        thread = FuncThread(Func, *args, **kwargs)
        thread.start()
        thread.join()
        return thread

#-------------------------------------------------------------------------------------
# Action decorator
#-------------------------------------------------------------------------------------
import Utility.Actions

def action(fn, *args, **kwargs):
    Utility.Actions.Actions.AddAction(fn)
    return fn

def tool_action(fn, *args, **kwargs):
    Utility.Actions.Actions.AddAction(fn, SkipCls=True, Terse=True)
    return fn

class action_ex():
    def __init__(self, service=False, serviceMethod=None, repeated=False, detailedLog=False):
        self.service = service
        self.serviceMethod = serviceMethod
        self.repeated = repeated
        self.detailedLog = detailedLog

    def __call__(self, fn):
        Utility.Actions.Actions.AddAction(fn, self.service, self.serviceMethod, self.repeated, self.detailedLog)
        return fn

class Password():
    @staticmethod
    def encode(account, password=None, Prompt=True):
        Trace()

        if not password:
            if Prompt:
                password = getpass.getpass(Expand('Enter password for [account]: '))
            else:
                Error('Missing password for [account]')
        passwordFile = ExpandPath(r'[Temp]\[account]').replace('@', '.')
        Log(passwordFile)

        fp = open(passwordFile, 'wb')
        encoded = base64.b64encode(bytes(password, 'utf-8'))
        fp.write(encoded)
        fp.close()

    @staticmethod
    def decode(account, Prompt=False, SilentError=False):
        if not account:
            if not SilentError:
                Error('No account was specified')
            return ''

        passwordFile = ExpandPath(r'[Temp]\[account]').replace('@', '.')
        if not os.path.exists(passwordFile) and Prompt:
            Password.encode(account, None, True)

        if not os.path.exists(passwordFile):
            if not SilentError:
                Error('Missing password for [account]')
            return ''

        fp = open(passwordFile, 'rb')
        encoded = fp.read()
        password = base64.b64decode(encoded)
        fp.close()

        return str(password, 'utf-8')

class DateTime():
    FileTimeFormat = "%Y:%m:%d %H:%M:%S"
    TouchTimeFormat = "%Y%m%d%H%M.%S"

    @staticmethod
    def to_struct_time(date):
        if isinstance(date, time.struct_time):
            return date
        elif isinstance(date, str):
            return time.strptime(date, DateTime.FileTimeFormat)
        elif isinstance(date, datetime.datetime):
            return date.timetuple()
        elif isinstance(date, float):
            return time.localtime(date)
        return None

    @staticmethod
    def to_secs(date):
        if isinstance(date, float):
            return date
        if not isinstance(date, time.struct_time):
            date = DateTime.to_struct_time(date)
        if date:
            return time.mktime(date)
        return None

    @staticmethod
    def to_localtime(date):
        if not isinstance(date, float):
            date = DateTime.to_secs(date)
        if date:
            return time.localtime(date)
        return None

    @staticmethod
    def to_file_date_str(date):
        # 2011:06:18 16:35:37
        if not date:
            return date
        try:
            date_ts = DateTime.to_localtime(date)
            if date_ts:
                #print(time.strftime(DateTime.FileTimeFormat, date_ts))
                return time.strftime(DateTime.FileTimeFormat, date_ts)
        except:
            ReportException()
        return None

    @staticmethod
    def to_touch_date_str(date):
        # 201106181635.37
        if not date:
            return date
        try:
            date_ts = DateTime.to_localtime(date)
            if date_ts:
                return time.strftime(DateTime.TouchTimeFormat, date_ts)
        except:
            ReportException()

    @staticmethod
    def stats_ctime(FilePath):
        stats = os.stat(FilePath)
        return DateTime.to_file_date_str(stats.st_ctime)

    @staticmethod
    def stats_mtime(FilePath):
        stats = os.stat(FilePath)
        return DateTime.to_file_date_str(stats.st_mtime)

    @staticmethod
    def stats_latest_time(FilePath):
        stats = os.stat(FilePath)

        return DateTime.to_file_date_str(max([stats.st_ctime, stats.st_mtime]))

def encode_to_mp3(file_path, output_folder):
    Exit()
    subprocess.call([
        r"d:\tools\ffmpeg\bin\ffmpeg.exe", "-i",
        file_path,
        "-acodec", "libmp3lame", "-ab", "256k",
        os.path.join(output_folder, '%s.mp3' % file_path[:-4])
        ])

def removeEmptyFolders(path):
    if not os.path.isdir(path):
        return

    def list_dir(path):
        data = []
        for f in os.listdir(path):
            fullpath = os.path.join(path, f)
            if not is_hidden_file(fullpath):
                data.append(fullpath)
        return data

    try:
        # remove empty subfolders
        files = list_dir(path)
        if len(files):
            for fullpath in files:
                if os.path.isdir(fullpath):
                    removeEmptyFolders(fullpath)

        # if folder empty, delete it
        files = list_dir(path)
        if len(files) == 0:
            LogPlain("Removing empty folder:", path)
            shutil.rmtree(path, False)
    except:
        LogPlainError('Exception on %s' % path)
        LogException()
