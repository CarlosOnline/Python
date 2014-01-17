import filecmp
import os
import platform
import sys
import time
import _thread
import urllib

import Utility
from   Utility.Utility   import *
import Utility.HomeUtility as Home
import Utility.Sql as sql
import Utility.Email as email
import Utility.WebServer as WebServer
from . import Html
import FindDups
import TestResults

#-------------------------------------------------------------------------------------
# UnitTest decorator
#-------------------------------------------------------------------------------------
def unittest(fn):
    def unitest_exec():
        return UnitTest.RunUnitTest(fn)

    UnitTest.AddFunction(fn, unitest_exec)
    return unitest_exec

#-------------------------------------------------------------------------------------
# UnitTest
#-------------------------------------------------------------------------------------
class UnitTest():
    # TODO: Add Summary

    Name = None
    PassCount = 0
    FailCount = 0
    PendingResult = False
    Results = dictn()
    TestFunctions = dictn()

    @staticmethod
    def Start(TestName):
        UnitTest.Name = TestName
        UnitTest.PassCount = 0
        UnitTest.FailCount = 0
        UnitTest.PendingResult = False
        UnitTest.UpdateResults()
        EnsurePath(Globals.UnitTestOutputFolder)
        Globals.TestName = TestName
        Globals.TestOutputFolder = ExpandPath(r'[UnitTestOutputFolder]\%s' % TestName)
        RemovePath(Globals.TestOutputFolder)
        MakePath(Globals.TestOutputFolder)

        Log(r'----------------------------')
        Log(r'Start Test [TestName]', ConsoleColor=Fore.GREEN + Style.BRIGHT)

    @staticmethod
    def Step(StepName):
        if UnitTest.PendingResult:
            UnitTest.Verify(False, 'Missing verification from previous step')
        Log()
        Log(r'Step [StepName]', ConsoleColor=Fore.MAGENTA + Style.BRIGHT)

        UnitTest.PendingResult = True

    @staticmethod
    def UpdateResults():
        result = ternary(UnitTest.FailCount == 0 and UnitTest.PassCount > 0, 'PASSED', 'FAILED')
        UnitTest.Results[UnitTest.Name] = UnitTest.Results.get(UnitTest.Name, dictn())
        UnitTest.Results[UnitTest.Name].Name = UnitTest.Name
        UnitTest.Results[UnitTest.Name].PassCount = UnitTest.PassCount
        UnitTest.Results[UnitTest.Name].FailCount = UnitTest.FailCount
        UnitTest.Results[UnitTest.Name].Result = result

    @staticmethod
    def End():
        if UnitTest.PendingResult:
            UnitTest.Verify(False, 'Missing verification from previous step')
        UnitTest.UpdateResults()
        TestName = UnitTest.Name
        result = UnitTest.Results[UnitTest.Name].Result
        if result == 'PASSED':
            RemovePath(Globals.TestOutputFolder)
        color = ternary(result == 'PASSED', Style.RESET_ALL, Fore.RED + Style.BRIGHT)
        Log(r'End Test [TestName]')
        Log(r'TestResult: [result]', ConsoleColor=color)
        Log(r'----------------------------')
        JSON.update_file(Globals.UnitTestResultsFile, UnitTest.Results)

    @staticmethod
    def AddFunction(Function, UnitTestFunction):
        name = r'{0}.{1}.{2}'.format(Function.__module__, Function.__class__.__name__, Function.__name__)
        # Trace(name)
        UnitTest.TestFunctions[name] = dictn({
                'Name' : name,
                'Module' : Function.__module__,
                'Class' : Function.__class__.__name__,
                'Function' : UnitTestFunction,
            })

    @staticmethod
    def RunUnitTest(TestFunction):
        UnitTest.Start(TestFunction.__name__)
        IncreaseIndent()
        try:
            TestFunction()
        except:
            UnitTest.FailCount += 1
            try:
                ReportException()
                exception_info = sys.exc_info()
                exType, message, tbObject = exception_info
                message = str(message)
                Log('Verify.fail: exception [message]', ConsoleColor=Fore.RED)
            except:
                pass

        DecreaseIndent()
        UnitTest.End()


    @staticmethod
    def RunUnitTests(Name=None, Class=None, Module=None, UseRegEx=True):
        Trace('Module:[Module] - Class:[Class] - Name:[Name]')

        def IsMatch(Value, Pattern):
            if not Pattern or Value == Pattern:
                return True
            elif UseRegEx and re.search(Pattern, Value):
                return True
            return False

        for item in UnitTest.TestFunctions.values():
            if not IsMatch(item.Module, Module) or not IsMatch(item.Class, Class) or not IsMatch(item.Name, Name):
                continue

            Log('Module  : %s' % item.Module)
            Log('Class   : %s' % item.Class)
            Log('Name    : %s' % item.Name)
            item.Function()

    @staticmethod
    def Verify(cond, PassMessage='', SilentPass=False):
        UnitTest.PendingResult = False
        # PrettyPrint(info)
        if not PassMessage:
            info = Inspector.GetCallerInfo()
            if info and info.code and len(info.code):
                PassMessage = info.code[0].strip().replace('UnitTest.Verify(', '')
                if PassMessage.endswith(')'):
                    PassMessage = PassMessage[:-1].strip()
        if cond:
            if not SilentPass:
                Log('Verify.pass: %s' % PassMessage, UseExpand=False, ConsoleColor=Fore.YELLOW + Style.BRIGHT)
            UnitTest.PassCount += 1
            return True
        else:
            Log('Verify.fail: %s' % PassMessage, UseExpand=False, ConsoleColor=Fore.RED)
            UnitTest.FailCount += 1
            return False

    class VerifyMatch():
        def __init__(self, left, right, PassMessage='', title='', SilentPass=False):
            UnitTest.PendingResult = False
            self.SilentInnerPass = True
            self.failedCount = 0

            self.Verify(left, right, title)

            if not PassMessage:
                info = Inspector.GetCallerInfo()
                if info and info.code and len(info.code):
                    PassMessage = info.code[0].strip().replace('UnitTest.VerifyMatch(', '')
                    if PassMessage.endswith(')'):
                        PassMessage = PassMessage[:-1].strip()
            if self.failedCount == 0:
                Log('Verify.pass: %s' % PassMessage, UseExpand=False, ConsoleColor=Fore.YELLOW + Style.BRIGHT, Silent=SilentPass)
            else:
                Log('Verify.fail: %s' % PassMessage, UseExpand=False, ConsoleColor=Fore.RED + Style.BRIGHT, Silent=SilentPass)

        def Verify(self, left, right, title=''):
            if isinstance(left, list):
                self.VerifyListsMatch(left, right, title)
            elif isinstance(left, dict):
                self.VerifyDictsMatch(left, right, title)
            elif isinstance(left, str) and isinstance(right, str):
                left = ExpandPath(left)
                right = ExpandPath(right)
                self.failedCount += 0 == UnitTest.Verify(left == right, Expand(r'[title] [left] == [right]'), SilentPass=self.SilentInnerPass)
            else:
                self.failedCount += 0 == UnitTest.Verify(left == right, Expand(r'[title] [left] == [right]'), SilentPass=self.SilentInnerPass)

        def VerifyListsMatch(self, left, right, title):
            UnitTest.Verify(len(left) == len(right), SilentPass=self.SilentInnerPass)
            for leftItem, rightItem in zip(left, right):
                self.Verify(leftItem, rightItem, '%s.list' % (title))

        def VerifyDictsMatch(self, left, right, title=''):
            UnitTest.Verify(len(list(left.keys())) == len(list(right.keys())), SilentPass=self.SilentInnerPass)

            for key in left.keys():
                leftItem = left.get(key, None)
                rightItem = right.get(key, None)
                self.Verify(leftItem, rightItem, '%s.%s' % (title, key))

            for key in right.keys():
                leftItem = left.get(key, None)
                rightItem = right.get(key, None)
                self.Verify(leftItem, rightItem, '%s.%s' % (title, key))

    @staticmethod
    def VerifyFilesMatch(left, right, SilentPass=False):
        UnitTest.Verify(ListFromFile(left), ListFromFile(right))

    @staticmethod
    def VerifyDirectoriesMatch(left, right):
        left = ExpandPath(left)
        right = ExpandPath(right)

        def print_differences(comp):
            if len(comp.diff_files):
                UnitTest.Verify(len(comp.diff_files) == 0)
                PrettyPrint(comp.diff_files, 'Different files %s , %s' % (comp.left, comp.right))

            if len(comp.left_only):
                UnitTest.Verify(len(comp.left_only) == 0)
                PrettyPrint(comp.left_only, 'Left only files %s , %s' % (comp.left, comp.right))

            if len(comp.right_only):
                UnitTest.Verify(len(comp.right_only) == 0)
                PrettyPrint(comp.right_only, 'Right only files %s , %s' % (comp.left, comp.right))

            for subcmp in comp.subdirs.values():
                print_differences(subcmp)

        comp = filecmp.dircmp(left, right, ['.DS_Store'])
        UnitTest.Verify(len(comp.diff_files) == 0)
        print_differences(comp)

    @staticmethod
    def LoadExpectedResults(expectedResultsJson=r'[TestDataFolder]/ExpectedResults/[TestName].json'):
        Trace(expectedResultsJson)
        expectedResultsJson = ExpandPath(expectedResultsJson)
        fp = open(expectedResultsJson, 'r')
        contents = fp.read()
        fp.close()
        contents = contents.replace('[ScriptFolder]', Globals.ScriptFolder.replace('\\', r'/'))
        contents = contents.replace('[Temp]', Globals.Temp.replace('\\', r'/'))
        return JSON.load_from_string(contents)

    @staticmethod
    def SaveExpectedResults(data, expectedResultsJson=r'[TestDataFolder]/ExpectedResults/[TestName].json'):
        Trace(expectedResultsJson)
        expectedResultsJson = ExpandPath(expectedResultsJson)
        JSON.save_to_file(expectedResultsJson, data)
        fp = open(expectedResultsJson, 'r')
        contents = fp.read()
        fp.close()

        fp = open(expectedResultsJson, 'w')
        contents = contents.replace(Globals.ScriptFolder, '[ScriptFolder]')
        contents = contents.replace(Globals.Temp, '[Temp]')
        fp.write(contents)
        fp.close()


    @staticmethod
    def SummarizeResults():
        Log()
        Log(r'----------------------------')
        Log(r'Test Summary')
        Log()
        Log(r'Test Results File: [UnitTestResultsFile]')
        Log()
        total = 0
        passed = 0
        failed = 0
        for test in UnitTest.Results.values():
            total += 1
            if test.Result == 'PASSED':
                passed += 1
            else:
                failed += 1
            name = test.Name
            result = test.Result
            color = ternary(result == 'PASSED', Fore.CYAN + Style.BRIGHT, Fore.RED + Style.BRIGHT)
            Log('   [result] : [name]', ConsoleColor=color)
        Log()
        failedColor = ternary(failed == 0, Style.RESET_ALL, Fore.RED + Style.BRIGHT)
        Log(r'Total  : [total]')
        Log(r'Passed : [passed]')
        Log(r'Failed : [failed]', ConsoleColor=failedColor)
        Log(r'File   : [UnitTestResultsFile]')
        Log()

#-------------------------------------------------------------------------------------
# Import all of Utility for UnitTests registration
#-------------------------------------------------------------------------------------
import Utility
if platform.system() == 'Windows':
    import Utility.Win32.UnitTests
else:
    import Utility.OSX.UnitTests

def RunUnitTests(Name=None, Class=None, Module=None):
    Trace()
    Trace('[Module] - [Class] - [Name]')

    UnitTest.RunUnitTests(Name, Class, Module, UseRegEx=True)
    UnitTest.SummarizeResults()

#-------------------------------------------------------------------------------------
# Test functions
#-------------------------------------------------------------------------------------

@unittest
def SQL_UnitTest(GenerateTestData=False):
    Trace()

    data = [
        [ 55, 54, 53, 52, 51],
        [ 55, 44, 43, 42, 41],
        [ 35, 34, 33, 32, 31],
        [ 35, 34, 33, 22, 21],
        [ 15, 14, 13, 12, 11],
        [  5, 4, 3, 2, 1],
    ]

    columns = [
        [ 'col0', 'int' ],
        [ 'col1', 'int' ],
        [ 'col2', 'int' ],
        [ 'col3', 'int' ],
        [ 'col4', 'int' ],
    ]

    primaryKeys = ['col0', 'col1']

    sorted = sql.sort_data(data, [0, 1, 2, 3], columns)
    PrettyPrintList(sorted)

    for idx in range(0, len(data[0]), 1):
        UnitTest.Step('Check column [idx]')
        col = [row[idx] for row in data]

        sorted = [row[idx] for row in data]
        sorted.sort()
        sorted.reverse()

        UnitTest.Verify(col == sorted, 'Column [idx] is sorted correctly')
        Log('col:    %s' % col)
        Log('sorted: %s' % sorted)

    table = 'SQL_UnitTest'

    if GenerateTestData:
        jsonData = dictn()
        jsonData.expectedResultsJson = data
        UnitTest.SaveExpectedResults(jsonData)

    UnitTest.Step('Write & Read from table')
    sql.write_to_table(table, data, columns, Verbose=True)
    read = sql.select(table)
    UnitTest.Verify(data == read)

    UnitTest.Step('Update Tests')
    row = [
        [ 55, 54, 1, 1, 1]
    ]
    count = sql.update(table, row, WhereClause=r'Where col0=55 and col1=54', Verbose=True)
    Log('count=[count]')
    UnitTest.Verify(count == 1)

    updated = sql.select(table, WhereClause=r'Where col0=55 and col1=54', Verbose=True)
    UnitTest.VerifyMatch(updated, row)

    UnitTest.Step('Write & Read unique data')

    unique_data = []
    unique_data.append(list(range(100, 200, 20)))
    unique_data.append(list(range(200, 300, 20)))
    unique_data.append(list(range(300, 400, 20)))
    unique_data.append(list(range(400, 500, 20)))
    unique_data.append(list(range(500, 600, 20)))
    PrettyPrint(unique_data)

    sql.write_to_table(table, unique_data, columns, PrimaryKey=primaryKeys, UseExistingTable=False, IdentityIndex=False, Verbose=True)
    read = sql.select(table)
    PrettyPrint(read)
    UnitTest.Verify(unique_data == read)

    UnitTest.Step('Write & Read indexed unique data')
    sql.write_to_table(table, unique_data, columns, PrimaryKey=None, UseExistingTable=False, IdentityIndex=True, Verbose=True)
    read = sql.select(table)
    PrettyPrint(read)

    [row.insert(0, idx) for idx, row in enumerate(unique_data, 1)]
    UnitTest.Verify(unique_data == read)

@unittest
def Pushd_UnitTests():
    Trace()

    cwd = os.getcwd()
    Log('cwd = [cwd]')

    tempFolders = [
        ExpandPath(r'[TestOutputFolder]\Test1\SubA'),
        ExpandPath(r'[TestOutputFolder]\Test1\SubB'),
        ExpandPath(r'[TestOutputFolder]\Test1\SubC'),
    ]

    for folder in tempFolders:
        folder = folder
        UnitTest.Step('[folder] from [cwd]')

        UnitTest.Verify(os.getcwd() == cwd)

        EnsurePath(folder)
        pushd(folder)
        UnitTest.Verify(os.getcwd() == folder)
        popd()
        UnitTest.Verify(os.getcwd() == cwd)
        RemovePath(folder)

    UnitTest.Step('Final popd(s)')
    popd()
    UnitTest.Verify(os.getcwd() == cwd)

    popd()
    UnitTest.Verify(os.getcwd() == cwd)

    popd()
    UnitTest.Verify(os.getcwd() == cwd)

@unittest
def Expand_Tests():
    Trace()

    UnitTest.Verify(Expand('[True]') == str(True))
    testVariable = '123456789'
    UnitTest.Verify(Expand('[testVariable:>30]') == '{0:>30}'.format(testVariable))
    UnitTest.Verify(Expand('[testVariable:<30]') == '{0:<30}'.format(testVariable))
    UnitTest.Verify(Expand('[testVariable:>15]') == '{0:>15}'.format(testVariable))
    UnitTest.Verify(Expand('[testVariable:<15]') == '{0:<15}'.format(testVariable))

    Globals.testVariable = testVariable + '_global'
    UnitTest.Verify(Expand('[testVariable]') == testVariable)
    UnitTest.Verify(Expand('[g:testVariable]') == testVariable + '_global')
    UnitTest.Verify(Expand('[l:testVariable]') == testVariable)
    UnitTest.Verify(Globals.testVariable == testVariable + '_global')

    testPath = ExpandPath(r'[Temp]\Foo\bar/left/right.pst')
    raw = r'%s/Foo/bar/left/right.pst' % Expand('[Temp]')
    raw = raw.replace('/', os.sep).replace('\\', os.sep)
    UnitTest.Verify(testPath == raw)

@unittest
def JSON_UnitTest():
    Trace()

    def compare_dicts(left, right):
        if left.keys() != right.keys():
            diff = list(set(right.keys()) - set(left.keys()))
            Log('Missing Keys on left:')
            PrettyPrint(diff)
            UnitTest.Verify(left.keys() == right.keys())

        failures = 0
        for key in left.keys():
            value = left[key]
            if key not in right:
                Log('key error.  "[key]" not in right')
                UnitTest.Verify(key in right)
            elif isinstance(value, dict):
                failures += compare_dicts(left[key], right[key])
            elif left[key] != right[key]:
                Log('error {0} != {1}'.format(left[key], right[key]))
                UnitTest.Verify(left[key] == right[key])
                failures += 1
        return failures

    data = dictn()
    data.TrueBool = True
    data.FalseBool = False
    data.int1 = 1
    data.int2 = 2
    data.int3 = 3
    data.str1 = "string 1"
    data.str3 = "string 2"
    data.str2 = "string 3"
    data.list = [ 1, 2, 3, 4, 5, 6]
    nestedDict = dictn({
        'int1' : 1,
        'int2' : 2,
        })
    data.dictA = nestedDict
    data.dictA = nestedDict
    data.listDict = [ nestedDict, nestedDict, nestedDict ]
    PrettyPrint(data)

    jsonFile = ExpandPath(r'[TestOutputFolder]\JsonUnitTest.json')

    UnitTest.Step('Basic saving')
    JSON.save_to_file(jsonFile, data)
    loaded = JSON.load_from_file(jsonFile)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)

    UnitTest.Step('Update existing json')
    data.int1 = 4
    data.int2 = 5
    data.int3 = 6
    loaded = JSON.update_file(jsonFile, data)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)
    loaded = JSON.load_from_file(jsonFile)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)

    UnitTest.Step('Update existing json 2')
    data.node = dictn()
    data.node.int4 = 4
    data.node.int5 = 5
    data.node.int6 = 6
    loaded = JSON.update_file(jsonFile, data)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)
    loaded = JSON.load_from_file(jsonFile)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)

    UnitTest.Step('.update method')
    foo = dictn()
    foo.from_update = dictn()
    foo.from_update.int1 = 1
    foo.from_update.int2 = 2
    foo.from_update.int3 = 3
    data.update(foo)
    loaded = JSON.update_file(jsonFile, data)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)
    loaded = JSON.load_from_file(jsonFile)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)

    UnitTest.Step('update with getNode')
    node = data.getNode(r'A\B\C')
    node.int1 = 1
    node.int2 = 2
    node.int3 = 3
    loaded = JSON.update_file(jsonFile, data)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)
    loaded = JSON.load_from_file(jsonFile)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)

    UnitTest.Step('delete node')
    del data['A']['B']
    loaded = JSON.save_to_file(jsonFile, data)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)
    loaded = JSON.load_from_file(jsonFile)
    UnitTest.Verify(compare_dicts(data, loaded) == 0)

@unittest
def HTML_UnitTest1():
    Trace()

    data = dictn({
        'html' : [
            {
                'head' : {
                    'title' : 'Foo Title was Here',
                    'style' : {
                        'type' : 'text/css',
                        'content' : """
                            br { clear:both; }
                        """,
                    },
                },
            },
            {
                'body' : [
                    {
                        'h1' : 'Hi There',
                    },
                    {
                        'table' : [
                            [ 1, 2, 3],
                            [ 4, 5, 6],
                        ],
                    },
                    {
                        'table' : {
                            'tr' : {
                                'td' : [
                                    1,
                                    2,
                                    3,
                                    4
                                ]
                            },
                        },
                    },
                ]
            }
        ]
    })
    PrettyPrint(data)

    fileName = r'HTML.Test1.htm'
    outputFile = ExpandPath(r'[TestOutputFolder]\[fileName]')
    Html.HTML.encode_to_file(data, outputFile)
    UnitTest.VerifyFilesMatch(ExpandPath(r'[TestDataFolder]\Html\[fileName]'), outputFile)

@unittest
def HTML_UnitTest2():
    Trace()

    data = dictn({
        'table' : {
            'style' : "display:visible;",
            'id' : 'table2',
            'content' : [
                {
                    'th' : [
                            "column1",
                            "column2",
                            {
                                'style' : "display:visible;",
                                'b' : "column3",
                            },
                            "column4",
                    ],
                },
                {
                    'content' : [
                        "data1",
                        "data2",
                        {
                            'style' : "display:visible;",
                            'b' : "data3",
                        },
                        "data4",
                    ],
                },
            ]
        }
    })
    PrettyPrint(data)

    fileName = r'HTML.Test2.htm'
    outputFile = r'[TestOutputFolder]\[fileName]'
    Html.HTML.encode_to_file(data, outputFile)
    UnitTest.VerifyFilesMatch(ExpandPath(r'[TestDataFolder]\Html\[fileName]'), outputFile)

# DISABLED @unittest
def HTML_UnitTest3():
    Trace()

    data = dictn({
        'html' : {
            'table' : [
                {
                    'th' : [
                            "column1",
                            "column2",
                            {
                                'style' : "display:visible;",
                                'b' : "column3",
                            },
                            "column4",
                    ],
                },
                {
                    'content' : [
                        "column1",
                        "column2",
                        {
                            'style' : "display:visible;",
                            'b' : "column3",
                        },
                        "column4",
                    ],
                },
            ]
        }
    })
    PrettyPrint(data)

    fileName = r'HTML.Test3.htm'
    outputFile = ExpandPath(r'[TestOutputFolder]\[fileName]')
    Html.HTML.encode_to_file(data, outputFile)
    UnitTest.VerifyFilesMatch(ExpandPath(r'[TestDataFolder]\Html\[fileName]'), outputFile)

@unittest
def ZIP_UnitTest(GenerateTestData=False):
    Trace()

    zipFile = ExpandPath(r'[TestOutputFolder]\ZipTest.zip')
    testDataFolder = Globals.TestDataFolder
    zipOutputFolder1 = ExpandPath(r'[TestOutputFolder]\ZipTest\1')
    zipOutputFolder2 = ExpandPath(r'[TestOutputFolder]\ZipTest\2')

    CopyDirectory(testDataFolder, zipOutputFolder1)

    zip_folder(zipFile, zipOutputFolder1)
    unzip(zipFile, zipOutputFolder2)

    UnitTest.VerifyDirectoriesMatch(zipOutputFolder1, zipOutputFolder2)

@unittest
def FindDups_UnitTest(GenerateResults=False):
    Trace()

    mediaFolder = ExpandPath(r'[TestDataFolder]\Media')
    mediaFolders = [ r'[mediaFolder]\Music', r'[mediaFolder]\Pictures', r'[mediaFolder]\Videos' ]

    mediaResults = ternary(GenerateResults, dictn(), UnitTest.LoadExpectedResults())

    UnitTest.Step('Test FindDups for default folders')
    for folder in mediaFolders:
        finder = FindDups.FindDups(folder, DeleteTable=True)
        IncreaseIndent()
        finder.ScanFiles()
        DecreaseIndent()

    for folder in mediaFolders:
        dups = FindDups.FindDups(folder, DeleteTable=False).FindDups()
        PrettyPrint(dups, folder)
        if GenerateResults:
            mediaResults[folder] = dups
        UnitTest.VerifyMatch(dups, mediaResults[folder])

    UnitTest.Step('Test IsDupFile for copied media files')

    outputFolder = ExpandPath(r'[TestOutputFolder]\Media')
    CopyDirectory(mediaFolder, outputFolder)

    for media in ['Music', 'Pictures', 'Videos']:
        folder = ExpandPath(r'[outputFolder]\[media]')
        finder = FindDups.FindDups(folder, DeleteTable=True)
        finder.ScanFiles()

    for media in ['Music', 'Pictures', 'Video']:
        folder = ExpandPath(r'[outputFolder]\[media]')
        for mediaFile in FileListFromPathList(folder):
            UnitTest.Verify(FindDups.IsDupFile(mediaFile, mediaFolders, ScanFiles=False), Expand(r'IsDupFile([mediaFile]) == True'))

    if GenerateResults:
        JSON.save_to_file(mediaResults)

@unittest
def TestResults_UnitTest(GenerateResults=False):
    Trace()

    testLists = [
        ['x86chk', 'BarTests', '02.12.7890.AA'],
        ['x86fre', 'FooTests', '01.01.8888.00'],
        ['armchk', 'BananaTests', '01.01.5555.00'],
    ]

    for Target, BranchName, BuildVersion in testLists:

        Globals.WebDataFileStore = ExpandPath(r'[TestOutputFolder]\WebSite')
        Globals.WebDataFileStore2 = ExpandPath(r'[TestOutputFolder]\WebSite2')
        Globals.ResultsOutputFolder = ExpandPath(r'[TestOutputFolder]\TestResults\[BranchName]\[Target]')
        Globals.NetworkRootFolder = ExpandPath(r'[TestDataFolder]\Results')

        reproOutputFolder = ExpandPath(r'[NetworkRootFolder]\[BranchName]\[BuildVersion]\[Target]\ReproResults')

        EnsurePath(Globals.WebDataFileStore)
        _thread.start_new_thread(EnsurePath, (Globals.WebDataFileStore2,))

        UnitTest.Step('Get Network Test Results')

        testResults = TestResults.GetNetworkTestResults(Target, BranchName, BuildVersion)
        allResults = UnitTest.LoadExpectedResults()
        expectedResults = allResults.getNode(Expand('[BranchName]\[Target]\[BuildVersion]'))
        UnitTest.VerifyMatch(expectedResults.ExpectedResults, testResults, 'ExpectedResults')

        UnitTest.Step('Get ReRun Results')

        # Get results before running tests
        lastBuildVersion = TestResults.History.version_list(Target, BranchName)[-1]
        previousRun = TestResults.History.results(Target, BranchName, lastBuildVersion)

        TestResults.Investigations.update_from_results(reproOutputFolder)
        TestResults.History.update_results(Target, BranchName, BuildVersion)

        # Get results after running tests
        currentRun = TestResults.History.results(Target, BranchName, BuildVersion)

        diff1 = list(set(previousRun.Failed) - set(currentRun.Failed))
        diff1.extend(list(set(currentRun.Bugs) - set(previousRun.Bugs)))
        PrettyPrint(diff1, 'Test Differences')
        PrettyPrint(expectedResults.Diff1, 'Expected Differences')
        UnitTest.VerifyMatch(expectedResults.Diff1, diff1)

        UnitTest.Step('Get 2nd ReRun Results')
        # Get results after running tests2
        previousRun = currentRun
        currentRun = TestResults.History.results(Target, BranchName, BuildVersion)

        diff2 = list(set(previousRun.Failed) - set(currentRun.Failed))
        diff2.extend(list(set(currentRun.Bugs) - set(previousRun.Bugs)))
        PrettyPrint(diff2, 'Test Differences')
        UnitTest.VerifyMatch(expectedResults.Diff2, diff2)

        UnitTest.Step('Generate Summary Report')
        reportFile = ExpandPath(r'[TestOutputFolder]\Summary.htm')
        TestResults.GenSummaryReportHtml(reportFile, ExpandPath(r'[TestOutputFolder]\NetworkResults'))
        UnitTest.Verify(os.path.exists(reportFile), Expand('Summary Report [reportFile] was generated'))

        foundVersions = []
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, -1))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, -2))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, -3))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, -4))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, -5))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, 1))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, 2))
        foundVersions.append(TestResults.BuildVersions.latest(Target, BranchName, 3))
        UnitTest.VerifyMatch(expectedResults.FoundVersions, foundVersions)

        if GenerateResults:
            allResults[BranchName][Target][BuildVersion] = {
                'ExpectedResults' : testResults,
                'Diff1' : diff1,
                'Diff2' : diff2,
                'FoundVersions' : foundVersions,
                }
            UnitTest.SaveExpectedResults(allResults)

@unittest
def WebServer_UnitTest():
    Trace()

    Globals.WebDataFileStore = ExpandPath(r'[TestOutputFolder]')
    Globals.WebDataFileStore2 = ExpandPath(r'[TestOutputFolder]')

    def send_request(url, data=None):
        postData = b''
        if data:
            # postData = bytes(urllib.parse.urlencode(data), 'utf8')
            postData = json.dumps(data).encode('utf-8')
        headers = {'Content-Type' : 'application/json'}
        request = urllib.request.Request(url, postData, headers)
        response = urllib.request.urlopen(request)
        return str(response.read(), 'utf8')

    # Start Web Server
    _thread.start_new_thread(WebServer.RunWebServer, ())
    Log('Sleeping for server to start')
    time.sleep(2)

    UnitTest.Step('Get File')

    testFile = ExpandPath(r'[TestDataFolder]/Branch1.json')
    expectedData = JSON.load_from_file(testFile)

    url = Expand("http://127.0.0.1:3000/Results?LoadData=True&fileUrl=///[testFile]".replace('\\', '/'))
    Log('Navigate to [url]')
    response = urllib.request.urlopen(url)
    data = JSON.load_from_string(str(response.read(), 'utf8'))
    UnitTest.VerifyMatch(data, expectedData)

    UnitTest.Step('Post Save File')
    expectedData = {
        "New1" : 1,
        "New2" : 2,
        "New3" : 3,
    }
    testFile = ExpandPath(r'[TestOutputFolder]\Save.Branch1.json')
    url = Expand("http://127.0.0.1:3000/Results?SaveFile=True&fileUrl=///[testFile]".replace('\\', '/'))
    response = send_request(url, expectedData)
    UnitTest.Verify(response == 'OK')

    data = JSON.load_from_file(testFile)
    UnitTest.VerifyMatch(data, expectedData)

    UnitTest.Step('LoadFile')
    url = Expand("http://127.0.0.1:3000/Results?LoadFile=True&fileUrl=///[testFile]".replace('\\', '/'))
    response = send_request(url)
    data = json.loads(response)
    UnitTest.VerifyMatch(data, expectedData, 'data == expectedData response')

    data = JSON.load_from_file(testFile)
    UnitTest.VerifyMatch(data, expectedData, 'data == expectedData from file on disk')

    UnitTest.Step('LoadData')
    url = Expand("http://127.0.0.1:3000/Results?LoadData=True&fileUrl=///[testFile]".replace('\\', '/'))
    response = send_request(url)
    data = json.loads(response)
    UnitTest.VerifyMatch(data, expectedData)

    UnitTest.Step('UpdateData')
    newData = {
        "New2" : 9999,
        "NestA" : {
            "Val30" : 30,
            "Foo" : {
                "Bar" : True
            }
        }
    }
    expectedData.update(newData)
    url = Expand("http://127.0.0.1:3000/Results?UpdateData=True&fileUrl=///[testFile]".replace('\\', '/'))
    response = send_request(url, newData)
    UnitTest.Verify(response == 'OK')

    data = JSON.load_from_file(testFile)
    UnitTest.VerifyMatch(data, expectedData)

    UnitTest.Step('SendEmail')
    emailData = {
        'to' : 'cgomes@iinet.com',
        'subject' : 'UnitTest: WebServer',
        'body' : 'Something Fun'
    }

    url = Expand("http://127.0.0.1:3000/Results?UpdateData=True&fileUrl=///[testFile]".replace('\\', '/'))
    response = send_request(url, emailData)
    UnitTest.Verify(response == 'OK')

# DISABLED - to slow @unittest
def Email_UnitTest():
    Trace()
    email.send_email(To=[Globals.To], Subject='UnitTest: Email_UnitTest Subject [Date] - [COMPUTERNAME]', Body='Hi', Attachments=Path(r'[TestDataFolder]\File2.txt'), Strict=True)
    UnitTest.Verify(True, 'Sent Email')

@unittest
def MediaImport_UnitTest(GenerateResults=False):
    Trace()

    ImportMediaFolder = ExpandPath(r'[TestOutputFolder]\ImportMedia')
    ImportMediaFolder2 = ExpandPath(r'[TestOutputFolder]\ImportMedia2')
    ImportMediaFolder3 = ExpandPath(r'[TestOutputFolder]\ImportMedia3')
    ChangeMediaFolder = ExpandPath(r'[TestOutputFolder]\ChangeMedia')
    Globals.MediaPrefix = 'Test'
    Globals.DefaultMediaFolders = [
        ExpandPath('[TestOutputFolder]\Media\Pictures'),
        ExpandPath('[TestOutputFolder]\Media\Music'),
        ExpandPath('[TestOutputFolder]\Media\Videos')
    ]
    Globals['Media']['Pictures']['DefaultFolders'] = [ Globals.DefaultMediaFolders[0] ]
    Globals['Media']['Music']['DefaultFolders'] = [ Globals.DefaultMediaFolders[1] ]
    Globals['Media']['Video']['DefaultFolders'] = [ Globals.DefaultMediaFolders[2] ]

    CopyDirectory(r'[ScriptFolder]\TestData\Media', r'[TestOutputFolder]\Media')
    CopyDirectory(r'[ScriptFolder]\TestData\ImportMedia', ImportMediaFolder)
    CopyDirectory(r'[ScriptFolder]\TestData\ImportMedia', ImportMediaFolder2)
    CopyDirectory(r'[ScriptFolder]\TestData\Media', ImportMediaFolder3)
    CopyDirectory(r'[ScriptFolder]\TestData\ImportMedia', ChangeMediaFolder)

    expectedData = UnitTest.LoadExpectedResults()

    UnitTest.Step('Change File Creation Time')
    actualResults = dictn()
    actualResults['change'] = dictn()
    for filePath in FindFiles(ChangeMediaFolder):
        Home.change_file_creation_time_to_picture_date(filePath, DebugMode=True)
        stats = os.stat(filePath)
        actualResults['change'][filePath] = {
            #'atime' : DateTime.to_file_date_str(stats.st_atime),
            #'ctime' : DateTime.to_file_date_str(stats.st_ctime),
            'mtime' : DateTime.to_file_date_str(stats.st_mtime),
        }

    if not GenerateResults:
        UnitTest.VerifyMatch(actualResults.change, expectedData.change)

    UnitTest.Step('Import Media')
    actualResults['imported'] = dictn()
    FindDups.FindFolderDups()

    imported = FindDups.Import(ImportMediaFolder)
    actualResults['imported'][ImportMediaFolder] = { 'count' : imported }

    imported = FindDups.Import(ImportMediaFolder2)
    actualResults['imported'][ImportMediaFolder2] = { 'count' : imported }

    imported = FindDups.Import(ImportMediaFolder3)
    actualResults['imported'][ImportMediaFolder3] = { 'count' : imported }

    for folder in Globals.DefaultMediaFolders:
        for filePath in FindFiles(folder):
            stats = os.stat(filePath)
            actualResults['imported'][filePath] = {
                #'atime' : DateTime.to_file_date_str(stats.st_atime),
                #'ctime' : DateTime.to_file_date_str(stats.st_ctime),
                'mtime' : DateTime.to_file_date_str(stats.st_mtime),
            }
    # PrettyPrint(actualResults)
    if not GenerateResults:
        UnitTest.VerifyMatch(actualResults.imported, expectedData.imported)

    if GenerateResults:
        UnitTest.SaveExpectedResults(actualResults)

