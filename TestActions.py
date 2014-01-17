import glob
import stat
from tkinter import *
from   Utility.Utility import *
import Utility.Actions as Actions
import CommonActions
import FindDups as DupUtil
import FindDupsUx
import FolderComp as FolderComp
import Utility.HomeUtility as Home
import Utility.Sql as sql
import Utility.MP3Rename as MP3Rename

#import Utility.id3reader as id3reader

@action
def Test():

    data = '188 (X-GM-LABELS (work "\\\\Important" "\\\\Sent") UID 44662)'
    pattern_label = re.compile('\d+ \(X-GM-LABELS \(([\w\\\\ "]+)\) (?P<uid>\d+)\)')

    data = '(X-GM-LABELS (work "\\\\Important" "\\\\Sent") UID 44662)'
    pattern_label = re.compile('\(X-GM-LABELS \(([\w\\\\ "]+)\) UID (?P<uid>\d+)\)')

    match = pattern_label.findall(data)
    #match = pattern_label.match(data)
    #print(match)
    for g in match:
        for x in g:
            print('group', x)


def DegradeOriginal(Folders='', ShowFolders=False):
    exclude = [
        r'd:\Pictures\2007\Downloard',
        r'd:\Pictures\2010\Download',
        r'd:\Pictures\iPhoto Library',
        r'.picasaoriginals',
        r'.temp_3',
        r'.temp',
        r'd:\Pictures\Picasa Exports',
        r'd:\Pictures\SaoriMac',
        r'd:\Pictures\SlideShow',
        r'd:\Pictures\2010\Birth.Kai',
        r'SlideShow',
        r'd:\music\iTunes',
        r'd:\music\My eMusic\My EMusic',
        r'iTunes',
        r'd:\music\Sequoia Groove Presents',
        r'd:\Videos\download',
        r'd:\Videos\2011\download',
        r'Download',
        #r'',
        #r'',
        #r'',
        #r'',
    ]
    Folders = ternary(not Folders, Globals.DefaultMediaFolders, ExpandPath(Folders).split(','))
    for folder in Folders:
        finder = DupUtil.FindDups(folder)
        if ShowFolders:
            finder.DegradeOriginalShowFolders(exclude)
        else:
            finder.DegradeOriginalRows(exclude)

def Test6(ImportLogFile='[ImportLog]'):
    ImportLogFile = ExpandPath(ImportLogFile)

    moved = []
    fp = open(ImportLogFile, 'r', encoding='utf-8')
    for line in fp:
        values = line.split(',')
        if len(values) == 2:
            _, dst = line.split(',')
        else:
            idx = int(len(values) / 2)
            dst = ','.join(values[idx : ])
        moved.append(dst.lower().strip())
    fp.close()

    for table in ['FindDups_d_Pictures', 'FindDups_d_Music', 'FindDups_d_Videos' ]:
        print(table)
        query = r'select distinct original from %s where original <> 0' % (table)
        originals = sql.execute(query, Flatten=True)

        count = 0
        rows = []
        for oid in originals:
            dbg_print(count)
            query = r'select path from %s where idx=%d' % (table, oid)
            path = sql.execute(query, Flatten=True)
            for row in path:
                row = row.lower().strip()
                if row in moved:
                    count += 1
                    DeleteFile(row)
        print()

        query = r'select path from %s where original <> 0' % (table)
        rows = sql.execute(query, Flatten=True)

        count = 0
        for row in rows:
            dbg_print(count)
            if row.lower() in moved:
                count += 1
        print()


def GenImportLog():
    count = 0
    for filePath in FindFiles(Globals.Temp, r'MovedAlready*.log'):
        Log('Processing [filePath]')
        fp = open(filePath, 'rb')
        for line in fp:
            count += 1
            if b'MoveFile' in line:
                line = decode(line)
                try:
                    start = line.find('MoveFile')
                    line = line[start + 8:]
                    line = line.strip()
                    line = line.lstrip(' :')

                    #print(count, line)
                    idx = line.find('d:', 3)
                    src = line[:idx]
                    src = src.strip()

                    dst = line[idx:]
                    dst = dst.strip()
                    DupUtil.ImportLog.log(src, dst)
                except:
                    LogError('line', count)
                    ReportException()
                    pass
        fp.close()
    DupUtil.ImportLog.close()


def MoveBackupMediaFiles():
    fp = open(r'c:\temp\MovedAlready2.log', 'rb')
    try:
        count = 0
        for line in fp:
            count += 1
            if b'MoveFile' in line:
                try:
                    line = line.decode('utf-8')
                    if 'video' in line.lower():
                        pass

                    start = line.find('MoveFile')
                    line = line[start + 8:]
                    line = line.strip()
                    line = line.lstrip(' :')

                    #print(count, line)
                    idx = line.find('d:', 3)
                    src = line[:idx]
                    src = src.strip()

                    dst = line[idx:]
                    dst = dst.strip()
                    if not os.path.exists(dst):
                        continue
                    if dst.startswith(r'd:\music'):
                        continue
                        pass

                    if 'kai' in src.lower() and 'kai' in dst.lower():
                        print('KAI file', dst, src)
                        continue

                    if 'albumart' in src.lower():
                        print('delete albumart file', dst, src)
                        os.chmod(dst, stat.S_IRWXU)
                        #os.remove(dst)
                        continue

                    if 'thumbnails' in src.lower():
                        print('delete thumbnails file', dst, src)
                        os.chmod(dst, stat.S_IRWXU)
                        #os.remove(dst)
                        continue

                    mediaType = Home.MediaTypeFromExtension(os.path.splitext(dst)[1])
                    destRoot = ExpandPath(Globals.Media[mediaType].DefaultFolders[0])
                    for key in Globals.Media.keys():
                        key = key.lower()
                        if mediaType.lower() == key:
                            if 'music' in src.lower():
                                print('delete art music file', dst, src)
                                os.chmod(dst, stat.S_IRWXU)
                                #os.remove(dst)
                                continue

                            pattern = r'%s' % (mediaType.lower())
                            path = src.lower()
                            idx = path.find(pattern)
                            if idx == -1:
                                pattern += 's'
                                idx = path.find(pattern)
                                if idx == -1:
                                    continue
                            folder = src[idx + len(pattern):]
                            newPath = destRoot + folder
                            print('original   ', src)
                            print('FixedxxMove', dst, newPath)
                            #MoveFile(dst, newPath)


                    #print('ReverseMove', dst, src)
                except:
                    pass
    except:
        ReportException()
        pass
    fp.close()



def DeleteSimilarMusicFiles():
    for file in FindFiles(r'd:\Music'):
        fileName = os.path.basename(file)
        folder = os.path.dirname(file)
        basename, ext = os.path.splitext(fileName)
        try:
            files = glob.glob(r'%s\%s.*' % (folder, basename))
        except:
            print()
            LogPlainError('glob error', file)
            continue
        if len(files) > 1:
            maxSize = 0
            maxFile = ''
            for filePath in files:
                size = os.path.getsize(filePath)
                if size > maxSize:
                    maxSize = size
                    maxFile = filePath
            for filePath in files:
                if filePath != maxFile:
                    os.chmod(filePath, stat.S_IRWXU)
                    os.remove(filePath)


def MoveBackIntoFolders():

    for file in FindFiles(r'd:\Music'):
        fileName = os.path.basename(file)
        folder = os.path.dirname(file)
        folderName = os.path.basename(folder)
        #dbg_print(file)
        if fileName.lower() == folderName.lower():
            #print(file)
            destFolder = os.path.dirname(folder)
            destFile = os.path.join(destFolder, fileName)
            if not os.path.exists(destFile):
                MoveFile(file, destFile)
            elif os.path.isdir(destFile):
                tempFilePath = Expand(r'[Temp]\[fileName]')
                MoveFile(file, tempFilePath)
                RemovePath(folder)
                MoveFile(tempFilePath, destFile)
            else:
                Log('duplicate', destFile)


def DropOldTables():

    tables = [
        "Music_Table",
        "Pictures_Table",
        "SortData",
        "Video_Table",
        "_Backup_Files_CarlosMac",
        "_Backup_Files_Code",
        "_Backup_Files_GigaByteMotherBoard",
        "_Backup_Files_SaoriMac",
        "_Media",
        "_Pictures",
        "_Temp_FolderComp",
        "_Temp_FolderComp2",
        "_music",
        "_videos",
        "c_Temp_FolderComp",
        "c_Temp_FolderComp2",
        "d_Pictures",
        "d_music",
        "d_videos",
        "g_Backup_Files",
        "g_Backup_Files_CarlosMac",
        "g_Backup_Files_Code",
        "g_Backup_Files_GigaByteMotherBoard",
        "g_Backup_Files_Samsung_GS2",
        "g_Backup_Files_SaoriMac",
        "g_Backup_Files__CCC_Archives",
        "sort_data",
    ]

    for table in tables:
        sql.drop_table(table.strip())


def Test5():
    folders = []
    fp = open(r'c:\temp\BackupImages.txt', 'r')
    for line in fp:
        line = line.strip()
        folder = os.path.dirname(line)
        if folder not in folders:
            match = folder.lower()
            save = ''
            while 'music' in match or 'video' in match or 'picture' in match:
                save = match
                match = os.path.dirname(match)
            if save:
                folder = folder[0:len(save)]
                if folder not in folders:
                    folders.append(folder)

    PrettyPrint(folders)


def Test4():
    max = 150456

    query = "select * from _Pictures where filename='sound_activation_level_dialog_basic7.png'"
    #query = r'select path from _Pictures where idx > 150456 order by idx'
    rows = sql.execute(query, Flatten=True)
    print(rows)
    #fp = open(r'c:\temp\_Pictures.log', 'w')
    #for path in rows:
    #    fp.write(path + '\n')
    #fp.close()

    print(len(rows))

    query = r'select max(idx) from _Pictures order by idx'
    rows = sql.execute(query)
    print(rows)

    query = r'select idx from d_Pictures order by idx'
    rows = sql.execute(query)
    print(len(rows))

    query = r'select max(idx) from d_Pictures order by idx'
    rows = sql.execute(query)
    print(rows)


def Test3(Folder=r'[Temp]\20120723_202707.jpg'):
    FilePath = r'c:\temp\test.tif'
    Home.dump_media_date_info(FilePath)

    return

    Folder = ExpandPath(r'[Temp]\FolderComp')
    Folder2 = ExpandPath(r'[Temp]\FolderComp2')
    RemovePath(Folder)
    RemovePath(Folder2)
    CopyDirectory(r'[ScriptFolder]\..\Html', Folder)
    CopyDirectory(r'[ScriptFolder]\..\Html', Folder2)

    import FolderComp as FolderComp
    FolderComp.FolderComp.clear()

    comp = FolderComp.FolderComp(Folder, True)
    comp.ScanFolders()
    FolderComp.FolderComp.find_all_dups()
    dups = FolderComp.FolderComp.select_all_dups()
    PrettyPrint(dups)

    comp = FolderComp.FolderComp(Folder2, True)
    comp.ScanFolders()
    dups = FolderComp.FolderComp.find_all_dups()
    dups = FolderComp.FolderComp.select_all_dups()
    PrettyPrint(dups)
    return


def Test2(Folder=''):
    #FilePath = r"g:\Backup Files\CarlosMac\Applications\Carbon Copy Cloner.app\Contents\MacOS\ccc_helper.app\Contents\Resources\arrow.tif "
    FilePath = r'c:\temp\test.tif'
    date_str, date_st = Home.MediaDateTime.get_creation_date(FilePath)
    ctime = DateTime.stats_ctime(FilePath)
    Log(date_str, ctime, date_st)
    return


    mediaFolder = ExpandPath(r'[Temp]\Media')
    mediaFolder2 = ExpandPath(r'[Temp]\Media2')
    CopyDirectory(r'[ScriptFolder]\TestData\Media', mediaFolder)
    CopyDirectory(r'[ScriptFolder]\TestData\ImportMedia', mediaFolder2)

    fileList = list(FindFiles(mediaFolder))
    fileList.extend(list(FindFiles(mediaFolder2)))
    for filePath in fileList:
        stats = os.stat(filePath)
        Log('before ctime', DateTime.to_file_date_str(stats.st_ctime))
        Log('before atime', DateTime.to_file_date_str(stats.st_atime))
        Log('before mtime', DateTime.to_file_date_str(stats.st_mtime))
        date_str = Home.change_file_creation_time_to_picture_date(filePath)
        stats = os.stat(filePath)
        Log('after  ctime', DateTime.to_file_date_str(stats.st_ctime))
        Log('after  atime', DateTime.to_file_date_str(stats.st_atime))
        Log('after  mtime', DateTime.to_file_date_str(stats.st_mtime))
        Log()
    Exit()


    filePath = r'/Users/cgomes/Pictures/2011/Download/Latest/DSC00157.JPG'
    stats = os.stat(filePath)
    Log('ctime', DateTime.to_file_date_str(stats.st_ctime))
    Log('atime', DateTime.to_file_date_str(stats.st_atime))
    Log('mtime', DateTime.to_file_date_str(stats.st_mtime))
    print(Home.change_file_creation_time_to_picture_date(filePath, TestMode=True))
    #Exit()

    CopyDirectory(r'[ScriptFolder]/TestData/Media/', r'[Temp]/Media')
    testFiles = [
        ExpandPath(r'[Temp]/Test.jpg'),
        ExpandPath(r'[Temp]/20120723_202707.jpg')
    ]
    for testFile in testFiles:
        CopyFile(r'[ScriptFolder]/TestData/Media/Pictures/IMG_0004.JPG', testFile)
        print(Home.change_file_creation_time_to_picture_date(testFile))

    folders = [
        r'/Users/cgomes/Pictures/Kai/2010'
    ]
    for folder in folders:
        robocopy(folder, r'[Temp]\Media')
        for filePath in FindFiles(r'[Temp]\Media'):
            date_str = Home.change_file_creation_time_to_picture_date(filePath, TestMode=False)
            folder = os.path.dirname(filePath)
            dirname = os.path.basename(folder)
            dirname_split = dirname.split('-')
            if len(dirname_split) == 3:
                prefix, folderMonth, folderYear = dirname_split
                year, month, day = (date_str.split(' ')[0]).split(':')
                if int(month) != int(folderMonth) or int(year) != int(folderYear):
                    Home.change_file_creation_time_to_picture_date(filePath, TestMode=True, DebugMode=False)
                    Warning(r'folder mismatch [date_str] [month]-[year] != [folderMonth]-[folderYear] for [filePath]')

                    stats = os.stat(filePath)
                    ctime = DateTime.stats_ctime(filePath)
                    atime = DateTime.to_file_date_str(stats.st_atime)
                    mtime = DateTime.to_file_date_str(stats.st_mtime)
                    if ctime != date_str:
                        Warning('ctime  mismatch [date_str] != [ctime] [atime] [mtime] - [filePath]')
                        pass
            Exit()

    DupUtil.Import(r'[Temp]/Media', TestMode=True)


