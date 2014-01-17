import datetime
import glob
import json
import os
import platform
import re
import sqlite3
import sys
import _thread
import time


import Utility.Utility
from   Utility.Utility import *


class SQL():
    MYSQL_OPTION_MULTI_STATEMENTS_ON = 0
    MYSQL_OPTION_MULTI_STATEMENTS_OFF = 1

    def __init__(self):
        self.conn = sqlite3.connect(ExpandPath(Globals.DatabasePath))
        self.conn.text_factory = str
        # fetch multiple results
        #self.conn.set_server_option(MYSQL_OPTION_MULTI_STATEMENTS_ON)
        self.cur = self.conn.cursor()

    def execute(self, Query, Data=None):
        try:
            if Data:
                self.cur.execute(Query, Data)
            else:
                self.cur.execute(Query)
        except:
            LogPlain('sql.execute execption on %s' % Query)
            raise

    def executemany(self, Query, Data):
        try:
            self.cur.executemany(Query, Data)
        except:
            LogPlain('sql.executemany execption on %s' % Query)
            raise

    def fetchall(self):
        return self.cur.fetchall()

        # fetch multiple results
        # while more:
        #     print db.fetchall()
        #     more = db.nextset()

    @property
    def description(self):
        return self.cur.description

    @property
    def rowcount(self):
        return self.cur.rowcount

    def close(self, Commit=True):
        if Commit:
            self.conn.commit()
        self.cur.close()

        # fetch multiple results
        #self.conn.set_server_option(MYSQL_OPTION_MULTI_STATEMENTS_OFF)

#-------------------------------------------------------------------------------------
# tables
#-------------------------------------------------------------------------------------
def tables(Table='', **kwargs):
    Table = Expand(Table)
    where = ternary(not Table, '', Expand("AND name LIKE '[Table]'"))

    query = """ SELECT name FROM sqlite_master
    WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' [where]
    UNION ALL
    SELECT name FROM sqlite_temp_master
    WHERE type IN ('table','view')
    ORDER BY 1"""

    return execute(Expand(query), **kwargs)

#-------------------------------------------------------------------------------------
# drop_table
#-------------------------------------------------------------------------------------
def drop_table(Table, Verbose=False):
    Table = Expand(Table)
    query = Expand(r'DROP TABLE IF EXISTS [Table]')
    if Verbose:
        LogPlain(query)

    sql = SQL()
    sql.execute(query)
    sql.close(Commit=True)

#-------------------------------------------------------------------------------------
# write_to_table
#-------------------------------------------------------------------------------------
def write_to_table(Table, Data, Columns=None, PrimaryKey=None, UseExistingTable=False, SkipInsert=[], IdentityIndex=False, Verbose=False):
    Table = Expand(Table)

    if not Data or len(Data) == 0:
        return []

    sql = SQL()

    #Columns = [column for column in Columns]
    if not Columns:
        Columns = []
        for idx in range(len(Data[0])):
            col = r'col%d' % (idx)
            Columns.append([col, 'text'])

    columnCreateText = []
    insertColumns = []
    for column, type in Columns:
        columnCreateText.append(r'%s %s' % (column, type))
        if column not in SkipInsert:
            insertColumns.append(column)

    primaryKeyClause = r''
    if PrimaryKey:
        primaryKeyColumns = []
        for column in PrimaryKey:
            if isinstance(column, int):
                primaryKeyColumns.append(Columns[column])
            else:
                primaryKeyColumns.append(column)
        primaryKeyClause = r', PRIMARY KEY (%s)' % (','.join(primaryKeyColumns))

    if IdentityIndex:
        columnCreateText.insert(0, r'idx INTEGER PRIMARY KEY AUTOINCREMENT')
        # cannot add idx column on insert case, only update case
        # no way to know if it's an insert or update without querying
        # check if data contains an extra column and 1st column is an int
        firstRow = Data[0]
        if len(firstRow) > len(insertColumns) and isinstance(firstRow[0], int):
            insertColumns.insert(0, 'idx')

    if not UseExistingTable:
        # Drop Table
        query = r'DROP TABLE IF EXISTS %s' % (Table)
        if Verbose:
            LogPlain(query)
        sql.execute(query)

    query = r"CREATE TABLE IF NOT EXISTS %s (%s %s)" % (Table, ','.join(columnCreateText), primaryKeyClause)
    if Verbose:
        LogPlain(query)
    sql.execute(query)

    questionMarks = ['?'] * len(insertColumns)
    query = 'insert or replace into %s(%s) values (%s)' % (Table, ','.join(insertColumns), ','.join(questionMarks))
    if Verbose:
        LogPlain(query)
    sql.executemany(query, Data)
    sql.close(Commit=True)

#-------------------------------------------------------------------------------------
# table_columns
#-------------------------------------------------------------------------------------
def table_columns(Table):
    sql = SQL()
    sql.execute("SELECT * FROM %s" % (Table))
    results = [tuple[0] for tuple in sql.description]
    sql.close()
    return results

def table_info(Table):
    sql = SQL()
    sql.cur.execute(Expand('PRAGMA table_info([Table])'))
    results = sql.cur.fetchall()
    results = [ list(row) for row in results ]
    sql.close()
    return results

#-------------------------------------------------------------------------------------
# select
#-------------------------------------------------------------------------------------
def select(Table, Columns=None, SortColumns=None, WhereClause=r'', GroupColumns=None, Limit=None, Data=None, Verbose=False):
    sql = SQL()

    if not Columns or len(Columns) == 0:
        sql.execute(Expand('SELECT * FROM [Table]'))
        Columns = [tuple[0] for tuple in sql.description]
    columns_str = ','.join(Columns)

    orderBy = ''
    if SortColumns and len(SortColumns) > 0:
        col_name_list = []
        for column in SortColumns:
            if isinstance(column, int):
                col_name_list.append(Columns[column])
            else:
                col_name_list.append(column)
        orderBy = 'ORDER BY %s' % (','.join(col_name_list))

    groupBy = ''
    if GroupColumns and len(GroupColumns) > 0:
        col_name_list = []
        for column in GroupColumns:
            if isinstance(column, int):
                col_name_list.append(Columns[column])
            else:
                col_name_list.append(column)
        groupBy = 'GROUP BY %s' % (','.join(col_name_list))

    limitText = ''
    if Limit:
        limitText = r'LIMIT %d' % (Limit)
    query = r'SELECT %s FROM %s %s %s %s %s' % (columns_str, Table, WhereClause, orderBy, groupBy, limitText)
    LogPlain(query, Silent=not Verbose)

    sql.execute(query, Data)
    rows = [list(row) for row in sql.fetchall()]
    sql.close()

    return rows

#-------------------------------------------------------------------------------------
# update
#-------------------------------------------------------------------------------------
def update(Table, Data, Columns=None, WhereClause=r'', Verbose=False):
    sql = SQL()

    if not Columns or len(Columns) == 0:
        sql.execute("SELECT * FROM %s" % (Table))
        Columns = [tuple[0] + '=?' for tuple in sql.description]

    columns_str = ','.join(Columns)

    query = r'UPDATE %s SET %s %s' % (Table, columns_str, WhereClause)
    LogPlain(query, Silent=not Verbose)
    sql.executemany(query, Data)
    rowcount = sql.rowcount
    sql.close(Commit=True)
    return rowcount

#-------------------------------------------------------------------------------------
# execute
#-------------------------------------------------------------------------------------
def execute(Query, Data=None, Verbose=False, Flatten=False):

    LogPlain(Query, Silent=not Verbose)

    sql = SQL()
    sql.execute(Query, Data)
    rows = [list(row) for row in sql.fetchall()]
    sql.close(Commit=True)

    if Flatten:
        return flatten(rows)

    return rows

#-------------------------------------------------------------------------------------
# execute_many
#-------------------------------------------------------------------------------------
def execute_many(Query, Data):
    Verbose(Query, UseExpand=False)

    sql = SQL()
    sql.executemany(Query, Data)
    rowcount = sql.rowcount
    sql.close(Commit=True)
    return rowcount

#-------------------------------------------------------------------------------------
# sort_data
#-------------------------------------------------------------------------------------
def sort_data(Data, SortColumns, Columns=None):
    if not Data or len(Data) == 0:
        return []

    splitIntoRows = False
    # Make sure we have a list of rows
    rowSet = Data
    if isinstance(Data, list) and not isinstance(Data[0], list):
        splitIntoRows
        rowSet = []
        for item in Data:
            rowSet.append([item])

    write_to_table('sort_data', rowSet, Columns=Columns)
    sorted = select('sort_data', None, SortColumns)
    if splitIntoRows:
        sorted = [item for item in sorted]
    return sorted

def copy_table(Source, Dest, SkipColumns=[], PrimaryColumns=[]):
    col_info = table_info(Source)
    if len(SkipColumns):
        for idx, row in enumerate(col_info):
            if row[1] in SkipColumns:
                del col_info[idx]
    columns = [ [row[1], row[2]] for row in col_info ]
    column_names = [ row[0] for row in columns ]
    column_names = ','.join(column_names)

    rows = execute(Expand(r"select [column_names] from [Source]"))
    Log('Original Row Count %d' % len(rows))

    write_to_table(Dest, rows, columns, PrimaryColumns)
    rows = execute(Expand(r"select * from [Dest]"))
    Log('New Row Count %d' % len(rows))
