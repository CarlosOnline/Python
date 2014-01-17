import filecmp
import glob
import json
import operator
import os
import shutil
import sys
import time

from   Utility.Utility import *
import Utility.Sql as sql
import Utility.HomeUtility as Home


class ImportLog():
    fp = None

    @staticmethod
    def close():
        if ImportLog.fp:
            ImportLog.fp.close()
            ImportLog.fp = None
            Log('Generated %s' % (Globals.ImportLog))

    @staticmethod
    def log(src, dst):
        if not ImportLog.fp:
            EnsurePath(os.path.dirname(Globals.ImportLog))
            ImportLog.fp = open(Globals.ImportLog, 'a+', encoding='utf-8')
        try:
            ImportLog.fp.write('%s,%s\n' % (decode(src), decode(dst)))
        except:
            LogException()
            pass

#-------------------------------------------------------------------------------------
# FindDups class
#-------------------------------------------------------------------------------------
class FindDups():

    Columns = [
        ['idx'              , 'INTEGER primary key autoincrement'     ],
        ['filename'         , 'text'    ],
        ['path'             , 'text'    ],
        ['folder'           , 'text'    ],
        ['size'             , 'INTEGER' ],
        ['modified_date'    , 'real'    ],
        ['create_date'      , 'real'    ],
        ['original'         , 'INTEGER' ],
        ['type'             , 'text'    ]
    ]

    RegistryColumns = [
        ['folder'           , 'text UNIQUE' ],
        ['modified_date'    , 'real'    ],
        ['create_date'      , 'real'    ],
    ]

    RegistryTable = 'FindDupsRegistry'

    def __init__(self, Folder, DeleteTable=False, Verbose=False):
        Folder = ExpandPath(Folder)
        self.Folder = Folder
        self.Verbose = Verbose
        drive, folder = os.path.splitdrive(Folder)
        self.Table = 'FindDups_' + re.sub(r'\W+', '_', Folder)
        # Globals.IgnoreExpandErrors = True

        if DeleteTable:
            self.UnRegister()

    def ResetRegistry(self):
        sql.drop_table(FindDups.RegistryTable)

    def Register(self):
        row = None
        if sql.tables(FindDups.RegistryTable):
            row = sql.select(FindDups.RegistryTable, WhereClause=Expand(r"WHERE folder='[Folder]'"), Verbose=self.Verbose)
        now = time.time()
        if not row:
            row = [self.Folder, now, now]
        else:
            row = row[0]
            row[2] = now
        sql.write_to_table(FindDups.RegistryTable, [row], FindDups.RegistryColumns, UseExistingTable=True, IdentityIndex=True, Verbose=self.Verbose)

    def UnRegister(self):
        sql.drop_table(self.Table)
        if sql.tables(FindDups.RegistryTable):
            sql.execute(Expand("delete from {0} where folder='[Folder]'".format(FindDups.RegistryTable)), Verbose=self.Verbose)

    def ScanFiles(self, Types='[AllMediaTypes]'):
        TraceVerbose(Types, self.Folder)
        Types = to_list(Expand(Types))
        fileRows = []
        extensions = flatten([ Globals.Media[mediaType].Extensions for mediaType in Types ])

        self.Register()

        count = 0
        for root, dirnames, filenames in os.walk(self.Folder):
            for filename in filenames:
                basename, ext = os.path.splitext(filename)
                ext = ternary(ext.startswith('.'), ext[1:], ext)
                if ext.lower() not in extensions:
                    continue

                filepath = os.path.join(root, filename)
                count += 1
                dbg_print(count, filepath)
                try:
                    stats = os.stat(filepath)
                    mediaType = Home.MediaTypeFromExtension(ext)
                    fileRows.append([filename, filepath, root, stats.st_size, stats.st_mtime, stats.st_ctime, 0, mediaType])
                except (KeyboardInterrupt, SystemExit):
                    raise
                except:
                    LogPlainError('failed to process %s' % filepath)
                    pass
        print()
        Log(len(fileRows), r'files in [Folder]')

        sql.write_to_table(self.Table, fileRows, FindDups.Columns, UseExistingTable=True, SkipInsert=['idx'], Verbose=self.Verbose)
        Verbose('Inserted %d rows' % (len(fileRows)))

    def FindDups(self, Types='[AllMediaTypes]'):
        Trace(self.Folder, Types)
        if not sql.tables(self.Table):
            return []
        self.Verbose = True

        def FindDupsInSet(rowSet):
            dups = []
            foundIdx = []
            foundPathNames = []

            for idx, left in enumerate(rowSet):
                idxLeft = left[0]
                pathLeft = left[2]
                for right in rowSet[idx + 1 : ]:
                    idxRight = right[0]
                    if idxRight in foundIdx:
                        continue
                    pathRight = right[2]
                    if filecmp.cmp(pathLeft, pathRight, False):
                        dups.append([idxLeft, idxRight])
                        foundIdx.append(idxRight)
                        foundPathNames.append(pathRight)
            return dups, foundPathNames

        rows = self.select_rows('', Types, SortColumns=['size', 'modified_date ASC'])

        results = []
        dups = []
        found = 0
        Log('Total rows: %d' % (len(rows)))
        print('  Idx  Dups         Size')

        rowSet = []
        allSets = [rowSet]
        prev_size = 0
        for idx, row in enumerate(rows):
            print('\r%5d %5d' % (idx, found), end=' ')
            filepath = row[2]
            if not os.path.exists(filepath):
                Log('Error missing file: [filepath]')
                continue

            size = row[4]
            if idx == 0:
                prev_size = size
            
            if size == prev_size:
                rowSet.append(row)
            else:
                if len(rowSet):
                    rowSet = []
                    allSets.append(rowSet)
                prev_size = size
        print('')

        for rowSet in allSets:
            if not len(rowSet):
                continue
            dupsRowSet, pathsRowSet = FindDupsInSet(rowSet)
            dups.extend(dupsRowSet)
            results.extend(pathsRowSet)
            found += len(dupsRowSet)

        Log(r'Found %d duplicates' % (len(dups)))
        updated = sql.update(self.Table, dups, ['original=?'], "WHERE idx=?", Verbose=self.Verbose)
        Log(r'Updated %d duplicate rows' % (updated))

        return results

    def GetFileDups(self, FilePath):
        # Trace(FilePath)
        if not sql.tables(self.Table):
            return []

        stats = os.stat(FilePath)
        size = stats.st_size

        query = 'SELECT path from [Table] WHERE size=[size]'
        rows = sql.execute(Expand(query), Verbose=self.Verbose)

        dups = []
        for row in rows:
            path = row
            if not os.path.exists(path):
                Log(r'Error missing file: [path]')
                continue

            if filecmp.cmp(FilePath, path, False):
                dups.append(path)

        return dups

    def get_where_clause(self, Types='[AllMediaTypes]', Where=''):
        Types = to_list(Expand(Types))
        if len(Types) == 0:
            return ternary(Where, 'Where ' + Where, '')

        clauses = []
        for mediaType in Types:
            clauses.append("type='%s'" % (mediaType))

        if Where:
            return 'Where %s and (%s)' % (Where, ' or '.join(clauses))
        else:
            return 'Where %s' % (' or '.join(clauses))

    def select_rows(self, Where='', Types='[AllMediaTypes]', **kwargs):
        where = self.get_where_clause(Types, Where=Where)
        return sql.select(self.Table, WhereClause=where, Verbose=self.Verbose, **kwargs)

    def SetOldestOriginal(self):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return

        count = 0
        rows = sql.execute('select distinct original from %s where original <> 0' % (self.Table), Flatten=True)
        for original in rows:
            count += 1
            dbg_print(original, count)
            rows = sql.execute('select idx, modified_date, path from %s where idx=%d or original=%d order by modified_date ASC' % (self.Table, original, original))
            data = []
            for row in rows:
                filePath = row[2]
                if os.path.exists(filePath):
                    oldest = row
                    newOriginal = oldest[0]
                    sql.execute('update %s set original=%s where idx=%s or original=%s' % (self.Table, newOriginal, original, original))
                    break
        sql.execute('update %s set original=0  where idx=original' % (self.Table))

    def DegradeOriginalShowFolders(self, ExcludeFolder=[]):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return

        def is_excluded(folder):
            for cur in ExcludeFolder:
                if cur in folder:
                    return True
            if os.path.abspath(folder) == os.path.abspath(self.Folder):
                return True
            return False

        count = 0
        rows = sql.execute('select distinct original from %s where original <> 0' % (self.Table), Flatten=True)
        data = []
        for original in rows:
            count += 1
            dbg_print(original, count)
            rows = sql.execute('select idx, modified_date, path from %s where idx=%d or original=%d order by modified_date ASC' % (self.Table, original, original))
            included = []
            for row in rows:
                filePath = row[2]
                folder = os.path.dirname(filePath)
                basename, ext = os.path.splitext(os.path.basename(filePath))
                suffix = os.path.splitext(basename)[1].lstrip('.')
                #print(ext, suffix, basename)
                if is_number(suffix):
                    continue
                elif folder in ExcludeFolder or is_excluded(folder):
                    continue

                if folder not in included:
                    included.append(folder)
            if len(included) == 0:
                folder = os.path.dirname(rows[0][2])
                included.append(folder)

            for folder in included:
                if folder not in data:
                    data.append(folder)

        data.sort()
        PrettyPrint(data, 'Included Folders')
        Exit()

    def DegradeOriginalRows(self, ExcludeFolder=[]):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return

        def is_excluded(folder):
            for cur in ExcludeFolder:
                if cur in folder:
                    return True
            if os.path.abspath(folder) == os.path.abspath(self.Folder):
                return True
            return False

        rows = sql.execute('select distinct original from %s where original <> 0' % (self.Table), Flatten=True)
        for count, original in enumerate(rows):
            dbg_print(original, count)
            rows = sql.execute('select idx, modified_date, path from %s where idx=%d or original=%d order by modified_date ASC' % (self.Table, original, original))
            for idx, row in enumerate(rows):
                filePath = row[2]

                folder = os.path.dirname(filePath)
                if folder in ExcludeFolder or is_excluded(folder):
                    continue

                basename, ext = os.path.splitext(os.path.basename(filePath))
                suffix = os.path.splitext(basename)[1].lstrip('.')
                #print(ext, suffix, basename)
                if is_number(suffix):
                    continue

                if idx != 0:
                    print()
                    self.ChangeOriginal(original, row[0])
                break

    def ChangeOriginal(self, old, new):
        if not sql.tables(self.Table):
            return
        sql.execute('update %s set original=%s where idx=%s or original=%s' % (self.Table, new, old, old), Verbose=True)
        sql.execute('update %s set original=0 where idx=%s' % (self.Table, new), Verbose=True)

    def GetDups(self, Limit=None, Types='[AllMediaTypes]'):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return []

        return sql.execute('select A.idx, A.original, A.path, B.path from %s as A, %s as B where A.original <> 0 and B.idx = A.original' % (self.Table, self.Table))

    def GetOriginals(self, Limit=None, Types='[AllMediaTypes]'):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return []

        return sql.execute('select DISTINCT B.idx, B.path from %s as A, %s as B where A.original <> 0 and B.idx = A.original' % (self.Table, self.Table))

    def GetDuplicates(self, Original):
        #Trace(self.Folder)
        if not sql.tables(self.Table):
            return []

        return sql.execute('select idx, path from %s where original = %d' % (self.Table, Original))

    def PrintDups(self, Limit=None, Types='[AllMediaTypes]'):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return

        rows = sql.execute('select A.path, B.path from %s as A, %s as B where A.original <> 0 and B.idx = A.original' % (self.Table, self.Table))
        dups = []
        for row in rows:
            if os.path.exists(row[0]) and os.path.exists(row[1]):
                dups.append(row)
        rows = dups

        Log(r'Found %d dups' % (len(rows)))
        if len(rows) > 100:
            PrettyPrintList(rows, FilePath=ExpandPath(r'[Temp]\Dups.log'))
            Log(r'Generated [Temp]\Dups.log')
        else:
            PrettyPrintList(rows, UseExpand=False)

    def MoveDups(self, Types='[AllMediaTypes]'):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return
        Globals.IgnoreExpandErrors = True

        dups = self.select_rows('original!=0', Types, Columns=['idx', 'path', 'folder', 'original'])
        for dup in dups:
            idx, path, folder, original = dup

            query = 'SELECT idx, folder from [Table] where idx=[original]'
            orig = sql.execute(Expand(query), Verbose=self.Verbose)
            orig_idx, orig_folder = orig

            if folder != orig_folder:
                self.MoveFile(idx, path, orig_folder)

    def DeleteDups(self, DeleteFiles=False, Types='[AllMediaTypes]'):
        Trace(self.Folder)
        if not sql.tables(self.Table):
            return
        Globals.IgnoreExpandErrors = True

        query = 'SELECT idx, path from [Table] where original <> 0'
        dups = sql.execute(Expand(query), Verbose=self.Verbose)

        idxList = []
        for dup in dups:
            idx, path = dup
            try:
                destPath = os.path.dirname(path)
                destPath = destPath.replace(':\\', ':\\ServerName\dups\\')
                if not DeleteFiles:
                    self.MoveFile(idx, path, destPath, Update=False)
                else:
                    Log(r'Delete %s' % path)
                    DeleteFile(path)
                idxList.append([str(idx)])
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                LogPlainError('Delete failed for %s' % (path))

        query = r'DELETE FROM [Table] WHERE idx=?'
        sql.execute_many(Expand(query), idxList)

    def MoveFile(self, Idx, SourceFile, DestFolder, Update=True, KeepOriginals=False):
        if not sql.tables(self.Table):
            return False

        # Trace(r'[Idx] [SourceFile] [DestFolder]')
        try:
            uniqFile = ''
            if not KeepOriginals:
                uniqFile = MoveToUniqueFile(SourceFile, DestFolder, '')
            else:
                uniqFile = CopyToUniqueFile(SourceFile, DestFolder, '')
            ImportLog.log(SourceFile, uniqFile)
            if Update:
                query = r'UPDATE [Table] set path=?, folder=? WHERE idx=?'
                #print([uniqFile, DestFolder, Idx])
                sql.execute(Expand(query), Verbose=self.Verbose, Data=[uniqFile, DestFolder, Idx])
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            LogPlainError('move failed for [Idx]')
            ReportException()

    def AddNewFile(self, FilePath, DestFolder, KeepOriginals=False):
        if not sql.tables(self.Table):
            return False

        destFile = self.MoveFile(-1, FilePath, DestFolder, False, KeepOriginals=KeepOriginals)
        if not destFile:
            return False

        # add to Database
        filename = os.path.basename(destFile)
        folder = os.path.dirname(destFile)
        stats = os.stat(destFile)
        basename, ext = os.path.splitext(filename)
        rows = []
        rows.append([filename, destFile, folder, stats.st_size, stats.st_mtime, stats.st_ctime, 0, Home.MediaTypeFromExtension(ext)])
        sql.write_to_table(self.Table, rows, FindDups.Columns, UseExistingTable=True, SkipInsert=['idx'], Verbose=self.Verbose)
        return destFile

    def ConsolidateMusicDups(self):
        Trace(self.Folder)

        rows = sql.execute('select distinct original from %s where original <> 0' % (self.Table), Flatten=True)
        for count, original in enumerate(rows):
            #dbg_print(original, count)
            original_path = sql.execute('select path from %s where idx=%d' % (self.Table, original), Flatten=True)
            orig_dest = os.path.dirname(original_path[0])

            rows = sql.execute('select path from %s where original=%d' % (self.Table, original), Flatten=True)
            for idx, filePath in enumerate(rows):
                folder = os.path.dirname(filePath)

                query = 'SELECT path from [Table] where folder=?'
                files = sql.execute(Expand(query), Verbose=self.Verbose, Data=[folder], Flatten=True)
                for file in files:
                    query = r'SELECT idx from [Table] where path=?'
                    idx = sql.execute(Expand(query), Verbose=self.Verbose, Data=[file], Flatten=True)
                    idx = idx[0]

                    #print('MoveFile', idx, file, orig_dest)
                    self.MoveFile(idx, file, orig_dest)

    def ConsolidateMusicDupsOrig(self):
        Trace(self.Folder)
        Globals.IgnoreExpandErrors = True
        self.Verbose = True

        query = r'SELECT DISTINCT folder FROM [Table] WHERE original <> 0'
        dup_folders = sql.execute(Expand(query), Verbose=self.Verbose, Flatten=True)

        for folder in dup_folders:
            try:
                LogPlain(r'processing folder %s' % str(folder))
            except:
                LogPlain('cant process folder - check unicode')
                continue

            query = "SELECT DISTINCT original from [Table] where folder='%s' and original <> 0" % (folder)
            orig_idx = sql.execute(Expand(query), Verbose=self.Verbose, Flatten=True)
            if len(orig_idx) == 0:
                continue
            orig_idx_str = ','.join(map(str, orig_idx))
            print(orig_idx_str)

            query = 'SELECT DISTINCT folder from [Table] where idx in (?)'
            orig_folders = sql.execute(Expand(query), Verbose=self.Verbose, Data=[orig_idx_str])
            orig_dest = orig_folders[0]

            for orig_folder in orig_folders:
                if orig_folder == orig_dest:
                    # Log('Skipping [orig_folder] == [orig_dest]')
                    continue

                query = 'SELECT path from [Table] where folder=?'
                files = sql.execute(Expand(query), Verbose=self.Verbose, Data=[orig_folder])
                for file in files:
                    query = r'SELECT idx from [Table] where path=?'
                    idx = sql.execute(Expand(query), Verbose=self.Verbose, Data=[file])
                    idx = idx[0]

                    print('MoveFile', idx, file, orig_dest)
                    Exit()
                    self.MoveFile(idx, file, orig_dest)

    def IsDupFile(self, FilePath):
        #Trace(FilePath)
        if not sql.tables(self.Table):
            return False

        stats = os.stat(FilePath)
        size = stats.st_size

        query = 'SELECT path from [Table] WHERE size=[size]'
        rows = flatten(sql.execute(Expand(query), Verbose=self.Verbose))

        dups = []
        for row in rows:
            path = row
            if not os.path.exists(path):
                LogPlainError(r'Error missing file: %s' % (path))
                continue

            if filecmp.cmp(FilePath, path, False):
                return True

        return False

#-------------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------------

def FindFolderDups(Folders='[DefaultMediaFolders]', DeleteTable=True):
    Folders = Expand(Folders)
    Trace(Folders)

    for folder in Folders:
        Log('Scanning [folder]')
        find = FindDups(folder, DeleteTable=DeleteTable)
        IncreaseIndent()
        find.ScanFiles(Home.MediaTypeFromFolder(folder))
        DecreaseIndent()

    for folder in Folders:
        FindDups(folder, DeleteTable=False).FindDups()

def ScanFiles(Folders=r'[DefaultMediaFolders]'):
    Folders = Expand(Folders)
    Folders = [ ExpandPath(folder) for folder in Folders ]
    Trace(Folders)

    for folder in Folders:
        find = FindDups(folder)
        IncreaseIndent()
        find.ScanFiles()
        DecreaseIndent()

def GetFileDups(FilePath, Folders=r'[DefaultMediaFolders]'):
    # Trace(FilePath)
    FilePath = ExpandPath(FilePath)
    Folders = ExpandPath(Folders)
    Folders = Folders.split(',')
    mediaType = Home.MediaTypeFromFile(FilePath)
    if not mediaType:
        return []

    folder = os.path.dirname(FilePath)
    if folder.lower() not in map(str.lower, Folders):
        Folders.insert(0, folder)

    dups = []
    for folder in Folders:
        find = FindDups(folder)
        find.ScanFiles()
        dups.extend(find.GetFileDups(FilePath))

    return dups

def IsDupFile(FilePath, Folders='[DefaultMediaFolders]', ScanFiles=False):
    #Trace(FilePath)
    Folders = Expand(Folders)
    Folders = [ ExpandPath(folder) for folder in Folders ]
    FilePath = ExpandPath(FilePath)

    mediaType = Home.MediaTypeFromExtension(os.path.splitext(FilePath)[1])
    if not mediaType:
        return False

    for folder in Folders:
        finder = FindDups(folder)
        if ScanFiles:
            finder.ScanFiles()
        if finder.IsDupFile(FilePath):
            return True

    return False

def DeleteDups(Folders=[], DeleteFiles=False):
    Trace(Folders, DeleteFiles)
    Folders = [ ExpandPath(folder) for folder in Folders ]

    for folder in Folders:
        finder = FindDups(folder)
        finder.DeleteDups(DeleteFiles)
    ImportLog.close()

def Import(Folder=r"d:\pictures\Download", ImportAll=False, KeepOriginals=False, TestMode=False, DoScan=False):

    Folder = ExpandPath(Folder);
    Trace(Folder)

    if DoScan:
        ScanFiles(Globals.DefaultMediaFolders)
        FindFolderDups([Folder])
        DeleteDups([Folder], True)

    imported = MoveMediaToFolder(Folder, ImportAll, KeepOriginals, TestMode)
    Exit()
    if DoScan:
        ScanFiles(Globals.DefaultMediaFolders)
    ImportLog.close()
    return imported

def MoveMediaToFolder(Folder, ImportAll=False, KeepOriginals=False, TestMode=False, KeepPath=False):
    Folder = ExpandPath(Folder);
    Trace(Folder)

    extensions = flatten([ media.Extensions for media in Globals.Media.values() ])
    extensions = list(map(str.lower, extensions))

    moved = 0
    for filepath in FindFiles(Folder):
        try:
            filepath = Plain(filepath)
            mediaType = Home.MediaTypeFromExtension(os.path.splitext(filepath)[1])
            if not mediaType:
                continue

            if not ImportAll and IsDupFile(filepath, ScanFiles=False):
                if TestMode:
                    LogPlain('TestMode: Duplicate', filepath)
                    continue
                LogPlain('Skipping dup %s' % filepath)
                if not KeepOriginals:
                    DeleteFile(filepath)
                continue

            moved += 1
            destRoot = ExpandPath(Globals.Media[mediaType].DefaultFolders[0])
            if not KeepPath and mediaType in [ 'Pictures', 'Video' ]:
                ctime = Home.change_file_creation_time_to_picture_date(filepath, TestMode=TestMode, DebugMode=False)
                date, _ = ctime.split(' ')
                year, month, day = date.split(':')

                destFolder = ExpandPath(r'[destRoot]\[MediaPrefix]\[year]\[MediaPrefix]-[month]-[year]')
            else:
                destFolder = os.path.dirname(filepath)
                destFolder = destFolder[len(Folder):]
                destFolder = '%s%s' % (destRoot, destFolder)

            destFolder = Plain(destFolder)
            uniqFile = ''
            srcFolder = os.path.dirname(filepath)
            if srcFolder.lower() == destFolder.lower():
                LogPlain('Already in destination folder' , filepath)
            elif TestMode:
                LogPlain('TestMode: AddNewFile', filepath, destFolder)
            elif KeepOriginals:
                uniqFile = CopyToUniqueFilePlain(filepath, destFolder)
            else:
                uniqFile = MoveToUniqueFilePlain(filepath, destFolder, '')
            if uniqFile:
                ImportLog.log(filepath, uniqFile)

        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            ReportException()
            return
            LogPlainError('Failed to move %s' % (filepath))
    return moved
