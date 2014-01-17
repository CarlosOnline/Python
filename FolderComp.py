import filecmp
import glob
import json
import os
import re
import shutil
import sys
import time

from   Utility.Utility import *
import Utility.Sql as sql
import Utility.HomeUtility as Home

class FolderComp():
    Columns = [
        ['idx'              , 'INTEGER primary key autoincrement'     ],
        ['foldername'       , 'text'    ],
        ['folder'           , 'text'    ],
        ['parentFolder'     , 'text'    ],
        ['modified_date'    , 'real'    ],
        ['create_date'      , 'real'    ],
        ['original'         , 'INTEGER' ],
    ]

    RegistryColumns = [
        ['folder'           , 'text UNIQUE' ],
        ['modified_date'    , 'real'    ],
        ['create_date'      , 'real'    ],
    ]

    RegistryTable = 'FileCompRegistry'
    FolderTable = 'FileCompFolders'

    def __init__(self, Folder, DeleteTable=False, Verbose=False):
        Folder = ExpandPath(Folder)
        self.Folder = Folder
        self.Verbose = Verbose
        self.Table = re.sub(r'\W+', '_', Folder)

        if DeleteTable:
            self.UnRegister()

    @staticmethod
    def clear():
        sql.drop_table(FolderComp.FolderTable)

    def ResetRegistry(self):
        sql.drop_table(FolderComp.RegistryTable)

    def Register(self):
        row = None
        if sql.tables(FolderComp.RegistryTable):
            row = sql.select(FolderComp.RegistryTable, WhereClause=Expand(r"WHERE folder=?"), Verbose=self.Verbose, Data=[self.Folder])
        now = time.time()
        if not row:
            row = [self.Folder, now, now]
        else:
            row = row[0]
            row[2] = now
        sql.write_to_table(FolderComp.RegistryTable, [row], FolderComp.RegistryColumns, UseExistingTable=True, IdentityIndex=True, Verbose=self.Verbose)

    def UnRegister(self):
        sql.drop_table(self.Table)
        if sql.tables(FolderComp.RegistryTable):
            sql.execute(Expand("delete from {0} where folder=?".format(FolderComp.RegistryTable)), Verbose=self.Verbose, Data=[self.Folder])

    def ScanFolders(self):
        Trace(self.Folder)
        folderRows = []

        folderName = os.path.basename(self.Folder)
        root = os.path.dirname(self.Folder)
        if not os.path.exists(self.Folder):
            Error('Missing [Folder]')
        stats = os.stat(self.Folder)
        folderRows.append([folderName, self.Folder, root, stats.st_mtime, stats.st_ctime, 0])

        count = 0
        for folder in FindFolders(self.Folder):
            folderName = os.path.basename(folder)
            root = os.path.dirname(folder)
            stats = os.stat(folder)
            count += 1
            dbg_print('%d %s' % (count, folder))
            folderRows.append([folderName, folder, root, stats.st_mtime, stats.st_ctime, 0])
        print('')
        Log(len(folderRows), r'files in [Folder]')

        sql.write_to_table(self.Table, folderRows, FolderComp.Columns, UseExistingTable=True, SkipInsert=['idx'], Verbose=self.Verbose)
        sql.write_to_table(FolderComp.FolderTable, folderRows, FolderComp.Columns, UseExistingTable=True, SkipInsert=['idx'], Verbose=self.Verbose)
        Verbose('Inserted %d rows' % (len(folderRows)))

    def get_where_clause(self, Folder='', Where=''):
        folderClause = ''
        if Folder:
            folderClause = "foldername='%s'" % (os.path.basename(Folder))
        if Where:
            return "Where %s and %s" % ' and '.join([Where, folderClause])
        elif Folder:
            return 'Where %s' % folderClause
        return ''

    def select_rows(self, FolderName='', Where='', **kwargs):
        Data = None
        if FolderName:
            Data = [ FolderName ]
            if not Where:
                Where = "Where foldername=?" % (Data[0])
            else:
                Where += " and foldername=?" % (Data[0])
        return sql.select(self.Table, WhereClause=Where, Verbose=self.Verbose, **kwargs)

    def select_folder_rows(self, FolderName='', Where='', **kwargs):
        Data = None
        if FolderName:
            Data = [ FolderName ]
            if not Where:
                Where = "Where foldername=?" % (Data[0])
            else:
                Where += " and foldername=?" % (Data[0])
        return sql.select(FolderComp.FolderTable, WhereClause=Where, Data=Data, Verbose=self.Verbose, **kwargs)

    def FindDups(self):
        Trace()
        dups = dictn()
        for folderItem in self.select_rows():
            _, folderName, folder, *_ = folderItem

            sourceItems = os.listdir(folder)
            dups[folder] = []

            for candidate in self.select_folder_rows(folderName):
                _, extName, extFolder, *_ = candidate
                if extFolder.startswith(self.Folder):
                    continue

                extItems = os.listdir(extFolder)
                diff = list(set(sourceItems) - set(extItems))
                if (len(diff) or (len(sourceItems) != len(extItems))):
                    continue
                elif Compare(folder, extFolder):
                    dups[folder].append(extFolder)
        return dups

    def dump_children(self):
        PrettyPrint(self.select_rows())

    @staticmethod
    def dump():
        rows = sql.select(FolderComp.FolderTable)
        PrettyPrint(rows)

    @staticmethod
    def update_original(left, right):
        table = FolderComp.FolderTable
        query = r"select idx from %s Where folder=?" % (table)
        left_id = sql.execute(query, Flatten=True, Data=[left])
        left_id = left_id[0]

        query = r"UPDATE %s set original=%d WHERE folder=?" % (table, left_id)
        sql.execute(query, Data=[right])

    @staticmethod
    def find_all_dups():
        Trace()
        dups = []
        table = FolderComp.FolderTable
        query = Expand(r'select distinct foldername from [table] Where original=0')
        folderNames = sql.execute(query, Flatten=True)
        for folderName in folderNames:
            dbg_print(len(dups), folderName)
            query = Expand(r"select * from [table] Where foldername=?")
            rows = sql.execute(query, Data=[folderName])
            if len(rows) > 1:
                original_row = rows[0]
                oid = original_row[0]
                for dup_row in rows[1:]:
                    result = Compare(original_row[2], dup_row[2])
                    if result:
                        dups.append([oid, dup_row[0]])
        print('')

        if len(dups):
            count = sql.update(table, dups, ['original=?'], "WHERE idx=?", Verbose=True)
            Log('Updated [count] rows')

        return len(dups)

    @staticmethod
    def select_all_dups():
        Trace()
        table = FolderComp.FolderTable
        query = Expand(r'select folder from [table] Where original <> 0')
        return sql.execute(query, Flatten=True)

    @staticmethod
    def select_all_dups_by_folder():
        Trace()
        table = FolderComp.FolderTable
        query = Expand(r'select distinct original from [table] Where original <> 0')
        originals = sql.execute(query, Flatten=True)
        for original in originals:
            folder = sql.execute(r'select folder from %s Where idx=%d' % (table, original), Flatten=True)
            folder = folder[0]
            rows = sql.execute(r'select folder from %s Where original=%d' % (table, original), Flatten=True)
            dups = dictn()
            dups.folder = folder
            dups.dups = rows
            yield dups



    @staticmethod
    def remove_all_dups():
        Trace()
        table = FolderComp.FolderTable
        query = Expand(r'delete from [table] Where original <> 0')
        return sql.execute(query, Flatten=True)

def CompareFiles(left, right):
    # Trace(left, right)

    src_stats = os.stat(left)
    dst_stats = os.stat(right)
    if src_stats.st_size == dst_stats.st_size and filecmp.cmp(left, right, False):
        return True
    return False

def CompareFolders(left, right):
    left_items = set(os.listdir(left))
    right_items = set(os.listdir(right))

    if len(left_items) != len(right_items) or len(list(left_items - right_items)):
        return False

    left_items = [ os.path.join(left, left_item) for left_item in left_items ]
    right_items = [ os.path.join(right, right_item) for right_item in right_items ]

    for left_item, right_item in zip(left_items, right_items):
        if not Compare(left_item, right_item):
            return False
    else:
        FolderComp.update_original(left, right)
        return True

    return False

def Compare(left, right):
    # Trace(left, right)

    #dbg_print(right)
    try:
        if os.path.isfile(left) and os.path.isfile(right):
            return CompareFiles(left, right)
        elif os.path.isdir(left) and os.path.isdir(right):
            return CompareFolders(left, right)
    except:
        LogError('Failed to compare %s vs %s' % (left, right), UseExpand=False)

    return False
