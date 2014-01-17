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

@tool_action
def sd_opened(args=''):
    files = []

    serverFiles = []

    for output in RunEx('p4.exe opened %s' % (args)):
        data = output.split('#')
        serverFile = data[0]
        if not serverFile.strip():
            continue
        serverFiles.append(serverFile)

    for serverFile in serverFiles:
        whereOutput = RunEx('p4.exe where "%s"' % (serverFile), UseExpand=False)
        for item in whereOutput:
            #print(item)
            idx = item.find(':\\')
            if idx != -1:
                local_path = (item[ idx -1 : ])
                Terse(local_path)

def sd_description_worker(Change):
    description = []
    foundChange = False
    foundAffected = False
    changeLine = Expand('Change [Change]')
    for output in RunEx('p4.exe describe -s [Change]'):
        #print(output)
        if not isinstance(output, str):
            output = output.decode('utf-8')
        if output.startswith('Affected files ...') or output.startswith('retCode='):
            break
        if not foundChange:
            if output.startswith(changeLine):
                foundChange = True
        else:
            description.append(output.strip())
    return '\n'.join(description)

def sd_get_files_from_description(Change):
    data = []
    foundChange = False
    foundAffected = False
    changeLine = Expand('Change [Change]')
    for output in RunEx('p4.exe describe -s [Change]'):
        #print(output)
        if not isinstance(output, str):
            output = output.decode('utf-8')
        output = output.strip()
        if not output:
            continue
        if output.startswith('retCode='):
            break
        if output.startswith('Affected files ...'):
            foundAffected = True
            continue
        if not foundAffected:
            continue
        data.append(output.strip())
    return data

@tool_action
def sd_description(Change):
    Terse(sd_description_worker(Change))

@tool_action
def sd_integrate(Change, IntegrateChangeList, SrcBranch='Fusion_Next', TgtBranch='Main'):
    description = sd_description_worker(Change)

    Run('p4.exe integrate -c [IntegrateChangeList] -o //[Depot]/[SrcBranch]/...@[Change],@[Change] //[Depot]/[TgtBranch]/...' )
    Run('p4.exe resolve -a')

    Terse()
    Terse()
    Terse('Integrate Change [Change] [description]')
    Terse()
    Terse()

@tool_action
def change_files(change):

    allFiles = []
    files = sd_get_files_from_description(change)
    for file in files:
        file = file.strip('...')
        file = file.split('#')[0]
        file = file.strip()
        if not file in allFiles:
            allFiles.append(file)

    for file in allFiles:
        Terse(file)

@action
def changes(user, count=30, SrcBranch='//[Depot]/Fusion_Next', TgtBranch='//[Depot]/Main'):

    allRevisions = []
    allFiles = []
    output = RunEx('p4.exe changes -m [count] -u [user] [SrcBranch]/...')
    for line in output:
        if not line.strip():
            continue
        change = line.split()[1]
        Terse(change)
        files = sd_get_files_from_description(change)
        for file in files:
            file = file.strip()
            file = file.strip('...')
            revision = file.strip(' add').strip(' edit').strip(' integra')
            allRevisions.append(revision)
            file = file.split('#')[0]
            file = file.strip()
            Terse(file)
            if not file in allFiles:
                allFiles.append(file)

    Terse('  ')
    Terse('  ---------------------- ')
    Terse('  ')
    mergePaths = []
    allFiles = sorted(allFiles)
    for file in allFiles:
        Terse(file)
        if SrcBranch in file:
            mergePaths.append([file, file.replace(SrcBranch, TgtBranch)])

    for file in mergePaths:
        #Terse(file)
        pass

    PrettyPrint(sorted(allRevisions), "All Revisions")

@tool_action
def list_changelists(changeList, SrcBranch='//[Depot]/Fusion_Next', TgtBranch='//[Depot]/Main'):

    changeList = changeList.split(',')
    allFiles = []
    for change in changeList:
        files = sd_get_files_from_description(change)
        for file in files:
            file = file.strip('...')
            file = file.split('#')[0]
            file = file.strip()
            if not file in allFiles:
                allFiles.append(file)

    mergePaths = []
    allFiles = sorted(allFiles)
    for file in allFiles:
        Terse(file)
        if SrcBranch in file:
            mergePaths.append([file, file.replace(SrcBranch, TgtBranch)])

    for file in mergePaths:
        #Terse(file)
        pass

