import base64
import datetime
import glob
import json
import os
import platform
import sys
import _thread
import time
import abc

import Utility.Utility
from   Utility.Utility import *
import Utility.Actions as Actions
import Utility.WebServer as WebServer
import Utility.Sql as sql
import SdxActions

Globals.DevProjects = [
    #[ r'c:\temp\unused'                 , r'test' ,         [] ],
    [ r'[ScriptFolder]'                 , r'python'             ,[] ],
    [ r'[ScriptFolder]\..\CodeReviewer' , r'CodeReviewer'       ,[r'.git', '__pycache__', 'obj', 'bin', 'packages'] ],
    [ r'[ScriptFolder]\..\Html'         , r'html'               ,[] ],
    [ r'[ScriptFolder]\..\Komodo'       , r'komodo'             ,[] ],
    [ r'[XDEV_ROOT]'                    , r'dev'                ,[r'.git', '__pycache__'] ],
    [ r'~/Documents/workspace/BabyTracker', r'babytracker'      ,[] ]
]

@action
def DumpJson(FilePath):
    FilePath = ExpandPath(FilePath)
    Trace(FilePath)

    data = JSON.load_from_file(FilePath)
    PrettyPrintDict(data)

@action
def FolderSize(Folders=None, SubFolders=True):
    folder_size(Folders, SubFolders)

@action
def UnitTests(Name=None, Class=None, Module=None):
    import Utility.UnitTests
    Utility.UnitTests.RunUnitTests(Name, Class, Module)

@action
def Query(Query=None, Verbose=False):
    Trace()

    if not Query:
        Log('Missing query')
        return

    rows = sql.execute(Query)
    PrettyPrintList(rows, UseExpand=False)

@action
def Zip(ZipFile, PathList='', ZipFolderPrefix='', Append=False, ExcludeList=None):
    Trace(r'[ZipFile] [Append] [ZipFolderPrefix] [PathList]')
    mode = ternary(Append, 'a', 'w')
    EnsurePath(os.path.dirname(ZipFile))
    PathList = ternary(PathList != '', PathList.split(','), [])

    # Verify Current Working Directory
    cwd = os.path.abspath(os.getcwd())
    found = False
    for path in PathList:
        path = os.path.abspath(path)
        if path.lower().strip().startswith(cwd.lower().strip()):
            found = True
            break
    else:
        Error('Current Directory not in [found] [PathList]')

    zip_path_list(ZipFile, PathList, mode, ZipFolderPrefix=ZipFolderPrefix, ExcludeList=ExcludeList)

@action
def ZipFolders(ZipFolderRoot, PathList='', ZipFolderPrefix='', Append=False, ExcludeList=None):
    mode = ternary(Append, 'a', 'w')
    Trace(r'[ZipFolderRoot] [Append] [ZipFolderPrefix] [PathList]')
    EnsurePath(ZipFolderRoot)
    PathList = ternary(isinstance(PathList, str), PathList.split(','), [])
    zip_folders(ZipFolderRoot, PathList, ExcludeList=ExcludeList)

@action
def UnZip(ZipFile, DestFolder):
    ZipFile = os.path.abspath(ExpandPath(ZipFile))
    DestFolder = os.path.abspath(ExpandPath(DestFolder))
    Trace(ZipFile, DestFolder)
    ZipFile = ExpandPath(ZipFile)
    DestFolder = ExpandPath(DestFolder)
    unzip(ZipFile, DestFolder)

@action
def ZipAllFolders(Force=True, ZipFolderRoot=r'[ZipFolder]\[Date].[HostName]', ExcludeList=[r'.git', '__pycache__', 'obj']):

    def CompareZipHistory(left, right):
        if (len(left.keys()) != len(right.keys())):
            return False

        keys = list(left.keys())
        keys.extend(list(right.keys()))
        for key in left.keys():
            leftItem = left.get(key, None)
            rightItem = right.get(key, None)
            if leftItem != rightItem:
                return False

        return True

    def GenerateZipHistory(key, zipFilePath, backupZipFile, zipFiles):
        historyData = DictN()
        historyData['key'] = key
        historyData['zipFile'] = zipFilePath
        historyData['backupZipFile'] = backupZipFile
        for file in zipFiles:
            file = file.lower().strip()
            modTime = DateTime.stats_latest_time(file)
            historyData[file] = modTime
        return historyData

    Trace(ZipFolderRoot)
    ZipFolderRoot = ExpandPath(ZipFolderRoot)
    EnsurePath(ZipFolderRoot)

    history = JSON.load_from_file(Globals.BackupArchiveJson)

    allFolders = []
    for folder, name, excludes in Globals.DevProjects:
        folder = os.path.abspath(ExpandPath(folder)).lower().strip()
        allFolders.append(folder)

    results = []
    for folder, name, excludes in Globals.DevProjects:
        folder = os.path.abspath(ExpandPath(folder))
        name = Expand(name)
        zipFile = ExpandPath(r'[ZipFolderRoot]\[name].zip')
        if not os.path.exists(folder):
            results.append(['-', 'missing', zipFile, folder])
            continue
        excludeList = ExcludeList
        excludeList.extend(excludes)
        excludeList.extend(allFolders)
        excludeList.remove(folder.lower().strip())

        # history check
        key = folder.lower().strip()
        backupFolder = key.replace(':', '.').replace('/', '.').replace('\\', '.')
        backupFolder = backupFolder.lower().strip()
        backupZipFile = ExpandPath(r'[BackupArchiveFolder]\[backupFolder]\[name].zip')

        previousFileData = history.get(key, {})
        if not Force and previousFileData and len(previousFileData.keys()) and os.path.exists(backupZipFile):
            currentFiles = zip_get_path_list(folder, ExcludeList=excludeList)
            currentFileData = GenerateZipHistory(key, zipFile, backupZipFile, currentFiles)
            if CompareZipHistory(previousFileData, currentFileData):
                CopyFile(backupZipFile, zipFile)
                results.append([file_size_string(zipFile), 'no change', zipFile, folder])
                continue

        zippedFiles = []
        zip_folder(zipFile, folder, ExcludeList=excludeList, ZippedFiles=zippedFiles)
        results.append([file_size_string(zipFile), '', zipFile, folder])

        # Backup and history
        CopyFile(zipFile, backupZipFile)
        zippedFileData = GenerateZipHistory(key, zipFile, backupZipFile, zippedFiles)
        history = JSON.load_from_file(Globals.BackupArchiveJson)
        history[key] = zippedFileData
        JSON.save_to_file(Globals.BackupArchiveJson, history)

    Log()

    if Globals.RemoteArchiveFolder:
        Log(r'Attempting to backup to [RemoteArchiveFolder]')
        if os.path.exists(Globals.RemoteArchiveFolder):
            Log(r'robocopy [ZipFolderRoot] [RemoteArchiveFolder]')
            robocopy(ZipFolderRoot, Globals.RemoteArchiveFolder)

    if Globals.RemoteArchiveFolder2:
        Log(r'Attempting to backup to [RemoteArchiveFolder2]')
        if os.path.exists(Globals.RemoteArchiveFolder2):
            Log(r'robocopy [ZipFolderRoot] [RemoteArchiveFolder2]')
            robocopy(ZipFolderRoot, Globals.RemoteArchiveFolder2)

    PrettyPrint(results, 'Created Zip Files')

@action
def SaveEnv(OutputFile):
    Trace(OutputFile)
    OutputFile = ExpandPath(OutputFile)
    EnsurePath(os.path.dirname(OutputFile))
    JSON.save_to_file(OutputFile, os.environ)

@action
def WebServer():
    Trace()
    Utility.WebServer.RunWebServer()

@action_ex(True, "WebServer")
def WebService(self):
    Trace()
    WebServer.RunWebServer()

@action
def EncodePassword(account, password=None):
    Trace()

    if not password:
        password = getpass.getpass(Expand('Enter password for [account]: '))
    passwordFile = ExpandPath(r'[Temp]\[account]').replace('@', '.')
    Log(passwordFile)

    fp = open(passwordFile, 'wb')
    encoded = base64.b64encode(bytes(password, 'utf-8'))
    fp.write(encoded)
    fp.close()
    Log('Password was encoded successfully [encoded]')

@action
def Tables(Table=''):
    PrettyPrint(sql.tables(Table))

@action
def RemoveEmptyFolders(Folder):
    removeEmptyFolders(Folder)

@action
def CleanVSFolders(Folder, Exts='bin,obj,sql'):
    Folder = os.path.abspath(ExpandPath(Folder))
    remo = []
    Exts = Exts.split(',')

    for root, dirs, files in os.walk(Folder):
        dirs.sort()
        for dir in dirs:
            dir = dir.lower().strip()
            #print(dir)
            if dir in ['debug', 'release', 'x86']:
                folder = os.path.basename(root).lower()
                if folder in Exts:
                    root = root.lower()
                    if root not in remo:
                        remo.append(root)

    PrettyPrint(remo)
    if len(remo) == 0:
        Log('No folders to remove')
        return

    line = input('Press Y,y to delete directories above: ')
    if line.strip().lower() == 'y':
        for folder in remo:
            RemoveFolder(folder)

