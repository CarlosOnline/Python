from xml.dom import minidom
from xml.sax.saxutils import escape
import imaplib
import email
import email.utils

from   Utility.Utility import *
import Utility.Actions as Actions
import CommonActions
import FindDups as DupUtil
import FindDupsUx
import FolderComp as FolderComp
import Utility.HomeUtility as Home
import Utility.Sql as sql
import Utility.MP3Rename as MP3
import GmailUx as GmailUx

def xml_escape(Value):
    Value = escape(Value)
    Value = Value.replace("'", "&apos;")
    return Value

@action
def SetupEnv(XPROJ, XPROJ_TYPE='', XPROJ_ARCH='x86', XPROJ_FLAVOR='fre'):

    outputFile = Expand(r'[XDEV_ROOT]\cmd\env\dev_[XPROJ]_[XPROJ_TYPE].cmd')
    ForeColor = 'White'
    BackColor = 'Black'

    if XPROJ.lower() == 'home':
        XPROJ_PROJECT = 'Home'
        BackColor = 'Black'
        if XPROJ_TYPE.lower() == 'livingroom':
            P4CLIENT=None
            XPROJ_ROOT = r'd:\dev'
        else:
            P4CLIENT='Carlos01'
            XPROJ_ROOT = r'c:\src'

    contents = """
set XDEV_ROOT=[XDEV_ROOT]
set XPROJ_ROOT=[XPROJ_ROOT]
set XPROJ=[XPROJ_ROOT]
set XPROJ_PROJECT=[XPROJ_PROJECT]
set XPROJ_TYPE=[XPROJ_TYPE]
set XPROJ_ARCH=[XPROJ_ARCH]
set XPROJ_FLAVOR=[XPROJ_FLAVOR]
set XPROJ_FOLDER=[XPROJ_ROOT]\[XPROJ_PROJECT]\[XPROJ_TYPE]
set XPROJ_SELF=[XDEV_ROOT]\env\[XPROJ_PROJECT]
set XPROJ_ENV_TITLE=%XPROJ_FOLDER% %XPROJ_ARCH% %XPROJ_FLAVOR%
set BackColor=[BackColor]
set ForeColor=[ForeColor]
call [XDEV_ROOT]\cmd\SetColor.cmd "[BackColor]" "[ForeColor]"
    """

    if P4CLIENT:
        contents += """
set P4CLIENT=[P4CLIENT]
    """

    EnsurePath(os.path.dirname(outputFile))
    fp = open(outputFile, 'w')
    fp.write(Expand(contents))
    fp.close
    Log(Expand(contents))
    Log('Generated [outputFile]')

@action
def BackupArchive(RemotePath='[RemoteArchiveFolder]'):
    Trace(RemotePath)
    RemotePath = ExpandPath(RemotePath)



@action
def RenameMusicFiles(Folder=r'd:\Music'):
    for file in FindFiles(Folder, '*.m*'):
        fileName = os.path.basename(file)
        folder = os.path.dirname(file)
        newFileName = fileName.lstrip('0123456789 -_.')
        newFileName = newFileName.strip()
        newFileName = newFileName.replace('[', '')
        newFileName = newFileName.replace(']', '')
        ch = newFileName[0]
        if ch.upper() == ch.lower() and ch not in  ['(', "'"]:
            try:
                print('error', ch, decode(newFileName), decode(fileName))
            except:
                #Exit()
                pass
        destFilePath = os.path.join(folder, newFileName)
        if os.path.exists(destFilePath):
            destFilePath = GenUniqueFileNamePlain(destFilePath, folder, '')

        os.chmod(file, stat.S_IRWXU)
        shutil.move(file, destFilePath)

        try:
            print('Renamed to ', newFileName)
            pass
        except:
            continue

@action
def GenerateColorHtml(FilePath=r'[Temp]\colors.txt', OutputFilePath=r'[Temp]\android_colors.htm'):
    Trace(FilePath, OutputFilePath)
    FilePath = ExpandPath(FilePath)
    OutputFilePath = ExpandPath(OutputFilePath)

    def getText(nodelist):
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

    xmldoc = minidom.parse(FilePath)
    colorList = xmldoc.getElementsByTagName('color')

    fp = open(OutputFilePath, 'w')
    fp.write(r'<html>' + '\n')

    for color in colorList:
        name = color.attributes['name'].value
        value = getText(color.childNodes)
        html = Expand(r'<input size=100 style="background-color: [value];"      value="[value] - [name]"/><br/>')
        fp.write(html + '\n')

    fp.write(r'</html>' + '\n')
    fp.close()
    Log(r'Generated [OutputFilePath]')

@action
def GenHtmlColors(Start= -1, Step= -1, Count=100, FilePath=r'[Temp]\colors.txt', OutputFilePath=r'[Temp]\colors.htm'):
    Trace(FilePath, OutputFilePath)
    FilePath = ExpandPath(FilePath)
    OutputFilePath = ExpandPath(OutputFilePath)
    Start = int(Start, 16)
    Step = int(Step)
    Count = int(Count)

    fp = open(OutputFilePath, 'w')
    fp.write(r'<html>' + '\n')

    step = -100
    for idx, value in enumerate(range(Count)):
        name = Start
        value = hex(Start).rstrip("L").lstrip("-0x")
        html = Expand(r'<input size=30 value="#[value] - [name]"/>  <input size=100 style="background-color: #[value];"      value="#[value] - [name]"/><br/>')
        fp.write(html + '\n')
        Start += Step

    fp.write(r'</html>' + '\n')
    fp.close()
    Log(r'Generated [OutputFilePath]')


@action
def FixPlaylistPaths(Folder=r'D:\Music\My Playlists'):
    Trace('[Folder]')
    Folder = ExpandPath(Folder)
    rootFolder = os.path.dirname(Folder)

    for playListFile in FindFiles(Folder, '*.wpl'):
        #destFile = CopyToUniqueFile(playListFile, os.path.dirname(playListFile), '')
        destFile = playListFile
        fp = open(playListFile, 'r')
        contents = fp.read()
        fp.close()

        folder = os.path.dirname(playListFile)

        xmldoc = minidom.parse(playListFile)
        mediaList = xmldoc.getElementsByTagName('media')

        mediaFiles = []
        for media in mediaList :
            mediaPath = media.attributes['src'].value
            mediaFiles.append(os.path.normpath(str(r'%s\%s' % (folder, mediaPath))))

        for file in mediaFiles:
            if not os.path.exists(file):
                fileName = os.path.basename(file)
                newFileName = fileName.lstrip('0123456789 -_.')
                newFileName = newFileName.strip()
                newFileName = newFileName.replace('[', '')
                newFileName = newFileName.replace(']', '')
                newFile = os.path.join(os.path.dirname(file), newFileName)
                if os.path.exists(newFile):
                    old = xml_escape(file[len(rootFolder) : ])
                    new = xml_escape(newFile[len(rootFolder) : ])
                    #LogPlain('Index %d' % contents.find(old))
                    if not old in contents:
                        LogPlain('bad escape %s' % (old))
                        LogPlain('Replace %s' % old)
                        LogPlain('With    %s' % new)
                        continue
                    contents = contents.replace(old, new)

        fp = open(destFile, 'w')
        fp.write(contents)
        fp.close()
        Log('Generated [destFile]')

@action
def ExtractMusicFiles(Playlist=r'D:\Music\My Playlists\CarCD.wpl', DestFolder=r'd:\MusicCD\CarCD', Replace=False):
    Trace('[Playlist] [DestFolder]')
    if not DestFolder:
        Error('Missing DestFolder parameter')

    Playlist = ExpandPath(Playlist)
    DestFolder = ExpandPath(DestFolder)
    EnsurePath(DestFolder)

    folder = os.path.dirname(Playlist)

    xmldoc = minidom.parse(Playlist)
    mediaList = xmldoc.getElementsByTagName('media')

    mediaFiles = []
    for media in mediaList :
        mediaPath = media.attributes['src'].value
        mediaFiles.append(os.path.normpath(str(r'%s\%s' % (folder, mediaPath))))

    for file in mediaFiles:
        if not os.path.exists(file):
            folder = os.path.dirname(file)
            fileName = os.path.basename(file)
            newFileName = fileName.lstrip('0123456789 -_.')
            newFileName = newFileName.strip()
            newFileName = newFileName.replace('[', '')
            newFileName = newFileName.replace(']', '')
            newFile = os.path.join(folder, newFileName)
            if not os.path.exists(newFile):
                LogPlain('Missing %s' % (file))
                LogPlain('Missing %s' % (newFile))
                continue
            else:
                file = newFile

        filename = os.path.basename(file)
        dest = r'%s\%s' % (DestFolder, filename)
        if Replace and os.path.exists(dest):
            os.remove(dest)
        if not os.path.exists(dest):
            LogPlain('Copy %s to %s' % (file, dest))
            CopyFile(file, dest)

@action
def CopyMusicFiles(SourceFolder, DestFolder, Replace=True):
    Trace('[SourceFolder] [DestFolder]')
    SourceFolder = ExpandPath(SourceFolder)
    DestFolder = ExpandPath(DestFolder)

    fileList = FindFiles(SourceFolder, r'*')

    for file in fileList:
        if not os.path.isfile(file):
            LogPlain('Skipping folder %s' % (file))
            continue

        relPath = os.path.relpath(file, SourceFolder)

        dest = r'%s\%s' % (DestFolder, relPath)
        if Replace and os.path.exists(dest):
            os.remove(dest)
        if not os.path.exists(dest):
            LogPlain('Move %s to %s' % (file, dest))
            shutil.move(file, dest)

@action
def BackupFiles(*args):
    Trace()
    Silent = True
    TestMode = False
    PrettyPrintList(Globals.BackupFolders)
    PrettyPrintList(Globals.BackupDrives)
    if TestMode:
        args = args + ('/L',)
    args = args + ('/MIR /NJH /NJS /NDL',)

    drives = [ map_volume_to_drive(drive) for drive in Globals.BackupDrives ]
    for driveInfo in drives:
        volume = driveInfo[0]
        drive = driveInfo[1]
        if not os.path.exists(lex(r'[drive]\.')):
            Log(lex('ERROR - [drive] is not online.'))
            continue

        Log('*************************************************')
        Log('Backing up to [drive] == [volume]')
        Log('*************************************************')

        folders = Globals.BackupFolders
        folders.extend(Globals.ArchiveFolders)

        excludeFolders = [ ExpandPath(folder) for folder in Globals.BackupExcludeFolders ]
        excludeFiles = [ ExpandPath(filePath) for filePath in Globals.BackupExcludeFiles ]
        excludeFoldersSet = set([ os.path.splitdrive(folder)[1] for folder in excludeFolders ])

        for folder in folders:
            srcDrive = os.path.splitdrive(folder)[0]
            folderName = os.path.basename(folder)
            subFolders = GetSubFolders(folder)

            # Exclude folders in the ExcludeFoldersSet
            # Excluded folders also include the archived folders
            subFoldersSet = set([ os.path.splitdrive(item)[1] for item in subFolders ])
            subFolders = list(subFoldersSet - excludeFoldersSet)
            subFolders = [ srcDrive + subFolder for subFolder in subFolders ]

            for subFolder in subFolders:
                subFolderName = os.path.basename(subFolder)
                if Silent:
                    dbg_print('\r%s' % (subFolder))
                robocopy(subFolder,
                         r'[drive]\[folderName]\[subFolderName]',
                         *args,
                         #TraceOnly=TestMode,
                         Silent=Silent,
                         ExcludeFolders=excludeFolders,
                         ExcludeFiles=excludeFiles)
            if TestMode:
                selected = input('Continue').strip()
                if selected.lower() == 'n':
                    return

@action
def CopySaoriMacPictures(Year=r'2012', DestRoot=r'd:\Pictures\Kai'):
    Trace()

    # D:\Backup Files\SaoriMac\Users\soka\Pictures\iPhoto Library\Masters\2012\06\05\20120605-215126\'
    picturesRoot = r'D:\Backup Files\SaoriMac\Users\soka\Pictures\iPhoto Library\Masters'
    searchMask = Expand(r'[picturesRoot]\[Year]\*\*\*\*.jpg', True)
    for file in glob.glob(searchMask):
            fileName = os.path.basename(file)
            folder = file
            folder = os.path.dirname(folder)  # date
            folder = os.path.dirname(folder)  # day
            folder = os.path.dirname(folder)  # month
            month = os.path.basename(folder)

            dest = Expand(r'[DestRoot]\[Year]\Kai-[month]-[Year]\[fileName]', True)
            CopyFile(file, dest)

    Log()
    Log(r'Results in  [LogFile]')
    Run(r'[LogFile]')

@action
def Import(Folder=r"d:\Download", ImportAll=False, KeepOriginals=False, TestMode=False):
    Folder = ExpandPath(Folder);
    Trace(Folder)

    DupUtil.Import(Folder, ImportAll, KeepOriginals=KeepOriginals, TestMode=TestMode)
    DupUtil.ImportLog.close()

    Log()
    Log(r'Results in  [LogFile]')

@action
def FixMediaPaths(Folder=r"d:\pictures\Kai", TestMode=True):
    Folder = ExpandPath(Folder);
    Trace(Folder)

    DupUtil.MoveMediaToFolder(Folder, True, False, FromFileNameOnly=True, TestMode=TestMode)
    DupUtil.ImportLog.close()

    Log()
    Log(r'Results in  [LogFile]')


@action
def CopyStarredPictures(FileList=r"C:\Users\[USERNAME]\AppData\Local\Google\Picasa2\db3\starlist.txt", MoveAll=False):
    Trace(FileList)
    FileList = ExpandPath(FileList);

    Globals.update(JSON.load_from_file(Globals.StarredPicturesJSON))

    def IsDupFile(FilePath):
        for item in Globals.AllMediaTypes.split(','):
            finder = DupUtil.FindDups(item)
            if len(finder.GetFileDups(FilePath)) > 0:
                return True

        return False

    for mediaType in list(Globals.Media.keys()):
        extensions = Globals.Media[mediaType].Extensions
        destRoot = Globals.Media[mediaType].Folders[0]

        finder = DupUtil.FindDups(mediaType)

        Log(lex(r'Processing: [mediaType] Dest=[destRoot]'))
        fpList = open(FileList, 'r')
        for filepath in fpList:
            filepath = filepath.strip()

            try:
                Home.change_file_creation_time_to_picture_date(filepath)
            except:
                pass

            try:
                filename = os.path.basename(filepath)
                stats = os.stat(filepath)
                creation_date = time.strftime('20%y-%m-%d', time.localtime(stats.st_ctime))
                year, month, day = creation_date.split('-')

                if not MoveAll and IsDupFile(filepath):
                    Log('Skipping dup [filepath]')
                    continue

                destFolder = Expand(r'[destRoot]\[year]', True)
                finder.AddNewFile(filepath, destFolder, True)
            except:
                Log(r'ERROR [filepath]')
                ReportException()
    DupUtil.ImportLog.close()
    Log()
    Log(r'Results in  [LogFile]')
    #Run(r'[LogFile]')

@action
def CopyThemePictures(SourceFolder=r'C:\Users\Me\AppData\Local\Microsoft\Windows\Themes', DestFolder=r'd:\Pictures\DesktopThemes', Replace=True):
    Trace(r'[SourceFolder] [DestFolder]')
    SourceFolder = ExpandPath(SourceFolder)
    DestFolder = ExpandPath(DestFolder)

    fileList = FindFiles(SourceFolder, r'*.jpg')
    for file in fileList:
        if not os.path.isfile(file):
            LogPlain('Skipping folder %s' % (file))
            continue

        relPath = os.path.relpath(file, SourceFolder)
        destFolderName = os.path.dirname(os.path.dirname(relPath))
        dest = r'%s\%s.%s' % (DestFolder, destFolderName, os.path.basename(file))
        if Replace and os.path.exists(dest):
            os.remove(dest)
        if not os.path.exists(dest):
            LogPlain('Copy %s to %s' % (file, dest))
            CopyFile(file, dest)

@action
def FindExtensions(Type='[AllMediaTypes]'):
    Trace(Type)
    Type = Expand(Type)
    for key in Type.split(','):
        extList = []

        for folder in Globals.Media[key].Folders:
            Log(r'Processing: %s' % (folder))
            for root, dirnames, filenames in os.walk(folder):
                for filename in fnmatch.filter(filenames, '*.*'):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext != '' and ext not in extList:
                        extList.append(ext)

        #PrettyPrintList(extList)

        for ext in extList:
            print("'%s'," % (ext.strip('.')), end=' ')
        print()

@action
def FindDups(Folders='', DeleteTable=True):
    Trace(Folders)
    Folders = ternary(not Folders, Globals.DefaultMediaFolders, ExpandPath(Folders).split(','))
    DupUtil.FindFolderDups(Folders, DeleteTable=DeleteTable)

@action
def PrintDups(Folders='', Limit=None):
    Trace()
    Folders = ternary(not Folders, Globals.DefaultMediaFolders, ExpandPath(Folders).split(','))

    for folder in Folders:
        finder = DupUtil.FindDups(folder)
        finder.PrintDups(Limit)

@action
def ShowDups(Folders='', Limit=None):
    Trace()
    Folders = ternary(not Folders, Globals.DefaultMediaFolders, ExpandPath(Folders).split(','))

    ux = FindDupsUx.DuplicateUx()
    ux.add_folders(Folders)
    ux.run()
    return

    for folder in Folders:
        finder = DupUtil.FindDups(folder)
        originals = finder.GetOriginals(folder)
        ux.add_originals(originals)
        #dups = finder.GetDups(Limit)
        #ux.add_dups(dups)

    ux.run()

@action
def MoveDups(Folders=''):
    Trace(Folders)
    Folders = ternary(not Folders, Globals.DefaultMediaFolders, ExpandPath(Folders).split(','))

    for folder in Folders:
        finder = DupUtil.FindDups(folder)
        finder.MoveDups()
    DupUtil.ImportLog.close()

@action
def DeleteDups(Folders='', DeleteFiles=False):
    Trace(Folders)
    Folders = ternary(not Folders, Globals.DefaultMediaFolders, ExpandPath(Folders).split(','))

    for folder in Folders:
        finder = DupUtil.FindDups(folder)
        finder.DeleteDups(DeleteFiles)
    DupUtil.ImportLog.close()

@action
def ConsolidateMusicDups(DeleteTable=True):
    Trace()
    for folder in Globals.Media['Music'].DefaultFolders:
        finder = DupUtil.FindDups(folder, DeleteTable)
        finder.ScanFiles('Music')
        finder.FindDups()
        finder.ConsolidateMusicDups()
    DupUtil.ImportLog.close()

@action
def RemoveMusicDups(DeleteTable=True):
    Trace()
    Error('broken type filter needed')
    for folder in Globals.Media['Music'].DefaultFolders:
        finder = DupUtil.FindDups(folder, DeleteTable)
        finder.ScanFiles('Music')
        finder.FindDups()
        finder.ConsolidateMusicDups()
        finder.MoveDups()
        finder.DeleteDups()
    DupUtil.ImportLog.close()

@action
def GetFileDups(FilePath, Type='[AllMediaTypes]'):
    Trace(Type)
    dups = []
    for item in Type.split(','):
        finder = DupUtil.FindDups(item)
        dups.extend(finder.GetFileDups(FilePath))

    Log('List of Dups:')
    PrettyPrintList(dups)

@action
def FixPictureCreationDate(Folder=r"d:\pictures\Download"):
    Trace()
    Folder = Expand(Folder);

    for mediaType in list(Globals.Media.keys()):
        extensions = Globals.Media[mediaType].Extensions
        destRoot = Globals.Media[mediaType].Folders[0]

        Log(lex(r'Processing: [mediaType] Dest=[destRoot]'))
        for root, dirnames, filenames in os.walk(Folder):
            for ext in extensions:
                for filename in fnmatch.filter(filenames, '*.' + ext):
                    filepath = os.path.join(root, filename)

                    Home.change_file_creation_time_to_picture_date(filepath)

@action
def GenAutoComplete(OutputFile=r'[ProgramFiles(x86)]\Notepad++\plugins\APIs\python.xml'):
    Trace(OutputFile)
    OutputFile = ExpandPath(OutputFile)
    if os.path.exists(OutputFile):
        folder = os.path.dirname(OutputFile)
        CopyToUniqueFile(OutputFile, r'[folder]\backup', '')

    importsFile = Expand(r'[ScriptFolder]\my_imports.py')
    if not os.path.exists(importsFile):
        Error('Missing imports file: [importsFile]')
    Log(r'Generate from [importsFile]')
    python_xml = ''
    if True:
        Run(r'c:\python27\python.exe [ScriptFolder]\generate_python_autocomplete.py < [importsFile] > "[OutputFile]"')
    else:
        # Doesn't work
        #python_xml = generate_python_autocomplete.generate_python_autocomplete(importsFile) #, [namespace=False], [private=False], [no_builtin=False], [level=2])

        #if python_xml[1]:
        #    PrettyPrint(python_xml[1])
        #python_xml = python_xml[0]
        #fp = open(OutputFile, 'w')
        #fp.write(python_xml)
        #fp.close()
        pass

    Log(r'Generated len=%d [OutputFile]' % len(python_xml))

@action
def TransferToNewDrive(Folders='', SourceDrive='d:', DestDrive='g:'):
    Trace(Folders)
    cmd = """
        robocopy "[sourceFolder]" "[destFolder]" /S /W:2 /R:2 /NS /NFL /NDL /MOVE /NJS /NJH ^
            /L ^
            /XD ^
            "__pycache__" ^
            "Temporary Internet Files" ^
            /XF ^
            "*.pyc" ^
            ".DS_Store" ^
            "thumbs.db" ^
            "pagefile.sys" ^
            "hiberfil.sys" ^
            %*
    """

    excludeFolders = [
        r"d:\$RECYCLE.BIN",
        r"d:\9e9818c24cb947f8dfcc12a7d2520c",
        r"d:\ad00b47e83cda26ae61d93ed0e03",
        r"d:\ad00b47e83cda26ae61d93ed0e03",
        r"d:\RECYCLER",
        r"d:\System Volume Information",
    ]

    Folders = ternary(Folders, Folders.split(','), GetSubFolders(SourceDrive + '\\'))
    Folders = list(set(Folders) - set(excludeFolders))

    for folder in Folders:
        sourceFolder = folder
        destFolder = folder.replace(SourceDrive, DestDrive)
        Log('robocopy', sourceFolder, destFolder)
        Run(Expand(cmd), Silent=True)

@action
def FindFolderDups(Folders, DeleteAllTables=False):

    Trace(Folders)
    Folders = ExpandPath(Folders).split(',')
    if DeleteAllTables:
        FolderComp.FolderComp.clear()

    for folder in Folders:
        if not os.path.exists(folder):
            Error('Missing [folder]')
        comp = FolderComp.FolderComp(folder, True)
        comp.ScanFolders()

    FolderComp.FolderComp.find_all_dups()
    dups = FolderComp.FolderComp.select_all_dups()
    PrettyPrint(dups)

@action
def FindBackupFolderDups(FindOnly=False, DeleteAllTables=False):

    if FindOnly:
        FolderComp.FolderComp.find_all_dups()
        dups = FolderComp.FolderComp.select_all_dups()
        PrettyPrint(dups)
        return

    Folders = [
        r'g:\Backup Files\CarlosMac',
        r'g:\Backup Files\SaoriMac',
        r'g:\Backup Files\Code',
        r'g:\Backup Files\GigaByteMotherBoard',
        r'g:\Backup Files\Samsung.GS2',
        r'g:\Backup Files\_CCC Archives',
    ]
    FindFolderDups(','.join(Folders), DeleteAllTables=DeleteAllTables)

@action
def DeleteFolderDups(Delete=False, FindDups=False):

    if FindDups:
        FolderComp.FolderComp.find_all_dups()
    dups = FolderComp.FolderComp.select_all_dups()
    for folder in dups:
        if Delete:
            if os.path.exists(folder):
                shutil.rmtree(folder, True)
                dbg_print(folder)
    print()

    if Delete:
        FolderComp.FolderComp.remove_all_dups()
        dups = FolderComp.FolderComp.select_all_dups()
        PrettyPrint(dups, 'Remaining Dups')

        date = Globals.Date.replace('-', '_')
        sql.execute('ALTER TABLE %s RENAME TO DupFolders_%s' % (FolderComp.FolderComp.FolderTable, date))

@action
def DumpFolderDups():
    date = Globals.Date.replace('-', '_')
    print(Expand('ALTER TABLE %s RENAME TO DupFolders_%s' % (FolderComp.FolderComp.FolderTable, date)))
    return

    count = 0
    dups = FolderComp.FolderComp.select_all_dups_by_folder()
    for dup in dups:
        Log(dup.folder)
        PrettyPrint(dup.dups)
        count += 1
        if count >= 1:
            count = 0
            input('Press any key to continue')

@action
def ImportBackupFolderMedia(DoScan=True):
    #Globals.IgnoreExpandErrors = True
    Globals.ReportExpandErrors = False


    Folders = [

        r'd:\Backup Files\Saori.IPod\Music',
        r'd:\Backup Files\SaoriMac\Users\soka\Music',
        r'd:\Backup Files\SaoriMac\Users\soka\Music\iTunes\iTunes Media\Music',
        r'd:\Backup Files\SaoriMac\_CCC Archives\2012-06-10 (June 10) 14-10-29\Users\soka\Music',
        r'd:\Backup Files\SaoriMac\_CCC Archives\2012-10-01 (October 01) 09-59-29\Users\soka\Music',
        r'd:\Backup Files\_CCC Archives\2011-09-05 (September 05) 08-04-35\2011\Saori.Sony.Vaio\Favorites\Music',
        r'd:\Backup Files\_CCC Archives\2011-09-05 (September 05) 08-04-35\2011\Saori.Sony.Vaio\My Documents\My Music\iTunes\iTunes Music\Music',
        r'd:\Backup Files\_CCC Archives\2011-09-05 (September 05) 08-04-35\Saori.Laptop.Backup2\Documents and Settings\Saori  Oka\Favorites\Music',
        r'd:\Backup Files\_CCC Archives\Users\soka\Music',
        r'd:\Backup Files\_CCC Archives\Users\soka\Music\iTunes\iTunes Media\Music',


        r"d:\Backup Files\CarlosMac\Users\cgomes\Pictures\Photo Booth Library\Pictures",
        r"d:\Backup Files\SaoriMac\Users\soka\Pictures",
        r"d:\Backup Files\SaoriMac\Users\soka\Library\Caches\com.apple.iChat\Pictures",
        r"d:\Backup Files\SaoriMac\Users\soka\Library\Caches\com.apple.iLifeSlideshow\Pictures",
        r"d:\Backup Files\SaoriMac\_CCC Archives\2012-06-10 (June 10) 14-10-29\Users\soka\Pictures",
        r"d:\Backup Files\SaoriMac\_CCC Archives\2012-10-01 (October 01) 09-59-29\Users\soka\Pictures",
        r"d:\Backup Files\_CCC Archives\2011-09-05 (September 05) 08-04-35\2008\data\Pictures",
        r"d:\Backup Files\_CCC Archives\2011-09-05 (September 05) 08-04-35\JoyfulCarlos.Laptop.Backup\data\Pictures",

        r'd:\Backup Files\CarlosMac\Users\cgomes\Music\Movies',
        r'd:\Backup Files\MusicToImport\iTunes\iTunes Music\Movies',
        r'd:\Backup Files\PicturesToImport\Picasa\Movies',
        r'd:\Backup Files\SaoriMac\Users\soka\Movies',
        r'd:\Backup Files\SaoriMac\Users\soka\Music\iTunes\iTunes Media\Movies',
        r'd:\Backup Files\_CCC Archives\Users\soka\Movies',

        r"d:\Backup Files\_CCC Archives\Users\soka\Pictures",
        r'd:\Backup Files\CarlosMac\Users\cgomes\Pictures',
        r'd:\Backup Files\CarlosMac\Users\cgomes\Music',
        r'd:\Backup Files\CarlosMac\Users\cgomes\Movies',
        r'd:\Backup Files\CarlosMac\Users\cgomes\Videos',
        r'd:\Backup Files\MusicToImport',
        r'd:\Backup Files\MoviesToImport',
        r'd:\Backup Files\PicturesToImport',
        r'd:\Backup Files\_CCC Archives\2011-09-05 (September 05) 08-04-35\2011\OldD_Drive\Data\Videos',

        r'd:\Backup Files\CarlosMac\Users\cgomes\Pictures',
        r'd:\Backup Files\SaoriMac\Users\soka\Pictures',
        r'd:\Backup Files\CarlosMac\Users\cgomes\Music',
    ]

    if DoScan:
        DupUtil.ScanFiles(Globals.DefaultMediaFolders)

    for folder in Folders:
        DupUtil.Import(folder, DoScan=False)

    if DoScan:
        DupUtil.ScanFiles(Globals.DefaultMediaFolders)
    DupUtil.ImportLog.close()

@action
def RenameMusicFilesEx(Folder=r'd:\music'):
    Folder = ExpandPath(Folder)
    for file in FindFiles(Folder, '*.m*'):
        fileName = os.path.basename(file)
        folder = os.path.dirname(file)
        newFileName = fileName.lstrip('0123456789 -_.')
        newFileName = newFileName.strip()
        newFileName = newFileName.replace('[', '')
        newFileName = newFileName.replace(']', '')
        ch = newFileName[0]
        if ch.upper() == ch.lower() and ch not in  ['(', "'"]:
            print('error', newFileName, fileName)
            #Exit()
        #destFilePath = os.path.join(folder, newFileName)
        if fileName == newFileName:
            continue
        destFilePath = GenUniqueFileName(newFileName, folder, '')
        if not os.path.exists(destFilePath):
            os.chmod(file, stat.S_IRWXU)
            shutil.move(file, destFilePath)

            try:
                dbg_print('new', newFileName)
                pass
            except:
                continue

@action
def MP3Rename(Folder, AddFiles=True, Debug=False):
    mp3 = MP3.MP3Rename(Folder)
    if AddFiles:
        mp3.add_files(Debug)
        mp3.fix_various_artists()
    mp3.fix_album_names()
    mp3.fix_album_names2()
    mp3.move_to_new_paths()

def get_email(uid, mail):
    if not isinstance(uid, str):
        uid = str(uid, 'utf-8')
    result, fetched = mail.uid('fetch', uid, '(RFC822)')
    if result != "OK":
        return dictn()

    try:
        raw_email = fetched[0][1]
        str_email = str(raw_email, 'utf-8')
        email_message = email.message_from_string(str_email)
        email_data = dictn()
        email_data.uid = uid.strip()
        email_data.From = email_message['From'].strip()
        email_data.To = email_message['To'].strip()
        email_data.Subject = email_message['Subject'].strip()
        email_data.Date = email_message['Date'].strip()
        #PrettyPrint(email_message.items())
        return email_data

    except:
        return dictn()

@action
def GetGmail():
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login('carlos.bear@gmail.com', 'Boa Vista123;')
    PrettyPrint(mail.list())
    # Out: list of "folders" aka labels in gmail.
    inbox = mail.select("inbox")  # connect to inbox.

    gmail = dictn()
    gmail.senders = []
    gmail.emails = dictn()
    result, data = mail.uid('search', None, "ALL")
    if result != "OK":
        Error('Failed to search')
    uid_list = data[0].split()
    Log('found %d emails' % (len(uid_list)))
    for idx, msg in enumerate(uid_list):
        uid = msg.split()[-1]
        uid = str(uid, 'utf-8')
        dbg_print(idx, uid)
        email_data = get_email(uid, mail)
        if len(email_data.keys()) == 0:
            continue

        gmail.emails[uid] = email_data
        sender = email_data.From.strip()
        if sender and sender not in gmail.senders:
            gmail.senders.append(sender)

    gmail.sender_emails = dictn()
    for idx, sender in enumerate(gmail.senders):
        sender_emails = []
        dbg_print(idx)
        for uid, email in gmail.emails.items():
            if email.From == sender:
                sender_emails.append(email.uid)
        if len(sender_emails):
            gmail.sender_emails[sender] = sender_emails

    gmail_log_file = ExpandPath(r'[Temp]\Senders.json')
    JSON.save_to_file(gmail_log_file, gmail)
    Log(r'Log File: [gmail_log_file]')

@action
def DeleteOldGmail():
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login('carlos.bear@gmail.com', 'Boa Vista123;')
    #mail.list()
    inbox = mail.select("inbox")  # connect to inbox.
    result, data = mail.uid('search', None, "ALL")

    mail.uid('STORE', '42043' , '+FLAGS', '(\Deleted)')
    mail.expunge()

    mail.uid('STORE', '42043' , '+FLAGS', '(\Deleted)')
    uid = '42043'
    email_data = get_email(uid, mail)

@action
def DeleteGmail():
    ux = GmailUx.GmailUx()
    ux.run()


