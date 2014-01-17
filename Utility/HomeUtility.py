import datetime
import filecmp
import glob
import json
import os
import platform
import re
import shutil
import sys
import time

from Utility.Utility import *
import Utility.EXIF as EXIF
if platform.system() == "Windows":
    import Utility.Win32.Win32Utility as PlatUtil
else:
    import Utility.OSX.OSXUtility as PlatUtil

def MediaTypeFromFolder(Folder):
    Folder = Folder.lower()
    for key in Globals.Media.keys():
        for defaultFolder in Globals.Media[key].DefaultFolders:
            defaultFolder = defaultFolder.lower()
            if Folder == defaultFolder:
                return key
    return Globals.Media.keys()

def MediaTypeFromExtension(Ext):
    ext = Ext.lower()
    ext = ternary(ext.startswith('.'), ext[1:], ext)

    for key in Globals.Media.keys():
        if ext in Globals.Media[key].Extensions:
            return key

    return None

def MediaTypeFromFile(FilePath):
    FilePath = ExpandPath(FilePath)
    basename, ext = os.path.splitext(FilePath)
    return MediaTypeFromExtension(ext)

#-------------------------------------------------------------------------------------
# MediaDateTime class
#-------------------------------------------------------------------------------------
class MediaDateTime():
    DebugMode = False

    def __init__(self, FilePath):
        self.filePath = FilePath

    @property
    def stats_ctime(self):
        stats = os.stat(self.filePath)
        ctime = min([stats.st_ctime, stats.st_atime, stats.st_mtime])
        date_str = DateTime.to_file_date_str(ctime)
        if MediaDateTime.DebugMode:
            Trace(date_str, self.filePath)
        return [ date_str, DateTime.to_struct_time(ctime) ]

    @property
    def date_from_exif(self):
        file = open(self.filePath, 'rb')
        try:
            self.exif = EXIF.process_file(file, details=False, debug=False)
        except:
            ReportException()
            self.exif = {}
        file.close()
        date_str = self.exif.get('EXIF DateTimeOriginal', None)
        if date_str:
            date_str = str(date_str).lstrip("b'").strip("'")
            if MediaDateTime.DebugMode:
                Trace(date_str, self.filePath)
        return [ date_str, DateTime.to_struct_time(date_str) ]

    @property
    def date_from_path(self):
        # 20120723_202707
        filename = os.path.basename(self.filePath)
        basename = os.path.splitext(filename)[0]

        try:
            st_create = datetime.datetime.strptime(basename, '%Y%m%d_%H%M%S')
            date_str = DateTime.to_file_date_str(st_create)
            if MediaDateTime.DebugMode:
                if date_str:
                    Trace(date_str, self.filePath)

            return [ date_str, st_create ]
        except:
            #ReportException()
            return [ None, None ]

    @staticmethod
    def get_creation_date(FilePath):
        mdt = MediaDateTime(FilePath)
        date_str, date_st = mdt.date_from_path
        if date_str:
            return [date_str, date_st]

        date_str, date_st = mdt.date_from_exif
        if date_str:
            return [date_str, date_st]

        return mdt.stats_ctime

    @staticmethod
    def get_media_filename_creation_date(FilePath):
        mdt = MediaDateTime(FilePath)
        date_str, date_st = mdt.date_from_path
        if date_str:
            return date_str, date_st

        return mdt.stats_ctime

def set_file_date_time(FilePath, date):
    if platform.system() == "Darwin":
        timestamp = DateTime.to_secs(date)
        os.utime(FilePath, (timestamp, timestamp))
        #touchDate = DateTime.to_touch_date_str(date)
        #Run(r'touch -amt [touchDate] [FilePath]', Silent=False)
    else:
        st_date = DateTime.to_struct_time(date)
        PlatUtil.ChangeFileCreationTime(FilePath, st_date)

def change_file_creation_time_to_picture_date(FilePath, TestMode=False, DebugMode=False):
    MediaDateTime.DebugMode = DebugMode
    date_str, date_st = MediaDateTime.get_creation_date(FilePath)
    #Warning(date_str, FilePath)
    if date_str == DateTime.stats_ctime(FilePath):
        return date_str  # same date

    if TestMode:
        return date_str
    else:
        set_file_date_time(FilePath, date_st)

    return date_str

def change_file_creation_time_to_date_from_path(FilePath, TestMode=False):
    date_str, date_st = MediaDateTime.get_media_filename_creation_date(FilePath)
    if date_str == MediaDateTime(FilePath).stats_ctime[0]:
        return date_str  # same date

    if TestMode:
        return date_str
    else:
        set_file_date_time(FilePath, date_st)

def dump_media_date_info(FilePath):
    Trace(FilePath)
    mdt = MediaDateTime(FilePath)
    date_str, date_st = mdt.date_from_path
    print('date_from_path', 'date_str', date_str)
    print('date_from_path', 'date_st', date_st)
    print()
    date_str, date_st = mdt.date_from_exif
    print('date_from_exif', 'date_str', date_str)
    print('date_from_exif', 'date_st', date_st)
    print()
    date_str, date_st = mdt.stats_ctime
    print('stats_ctime', 'date_str', date_str)
    print('stats_ctime', 'date_st', date_st)
    print()
