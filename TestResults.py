import datetime
import glob
import os
import sys
import urllib.request
import _thread

from   Utility.Utility import *
import Utility.Email as email
import Utility.Sql as sql

Globals.ResultsFetcherExe = Path(r'[PUBLIC_SHARE]\..\ResultsFetcher\ResultsFetcher.exe')
Globals.ResultsHistoryFile  = Path(r'[WebDataFileStore]\ResultsHistory.json')
Globals.ResultsHistoryFile2 = Path(r'[WebDataFileStore2]\ResultsHistory.json')
Globals.ResultsOutputFolder = Path(r'[Temp]\WTTResults\[BranchName]\[BuildVersion]\[Target]')
Globals.ResultsTestDataFile = Path(r'[ResultsOutputFolder]\TestData.json')
Globals.ResultsReproPs1File = Path(r'[ResultsOutputFolder]\repro.ps1')
Globals.ResultsReproFile    = Path(r'[ResultsOutputFolder]\repro.cmd')
Globals.ResultsTestDataJavaScriptFile  = Path(r'[ResultsOutputFolder]\TestData.js')
Globals.NetworkRootFolder   = Path(r'\\ServerName\public\TestResults\Sixshot')
Globals.NetworkResultsFolder = Path(r'[NetworkRootFolder]\[BranchName]\[BuildVersion]\[Target]')
Globals.DatabaseCsvFile     = Path(r'[Temp]\TestResults.csv')
Globals.PassedOnRerun       = r'Passed on Rerun'

#-------------------------------------------------------------------------------------
# TestResults class
#-------------------------------------------------------------------------------------
class TestResults:

    def __init__(self, LocalResultsFolder, ResetDatabase=False):
        Trace(r'[LocalResultsFolder]')

        EnsurePath(Globals.WebDataFileStore)

        self.LocalResultsFolder = ExpandPath(LocalResultsFolder)
        self.Target = 'UnknownTarget'
        self.BranchName = 'UnknownBranchName'
        self.BuildVersion = 'UnknownBuildVersion'

        self.TestData = []
        self.AllTestIDs = []
        self.NetworkLogFiles = []
        self.PassedTestData = DictN()
        self.TestTable = r'WTTTestResults'
        self.TestTableColumns = [
            ['assembly'                , 'text'     ],
            ['suite'                   , 'text'     ],
            ['name'                    , 'text'     ],
            ['networkLogFile'          , 'text'     ],
            ['networkResultsFolder'    , 'text'     ],
            ['logFile'                 , 'text'     ],
            ['resultsFolder'           , 'text'     ],
            ['target'                  , 'text'     ],
            ['branchName'              , 'text'     ],
            ['buildVersion'            , 'text'     ],
            ['comments'                , 'text'     ],
            ['resolved'                , 'integer'  ],
            ['bug'                     , 'integer'  ],
        ]
        self.TestTablePrimaryKeyColumns = ['buildVersion', 'name', 'suite', 'assembly']

        self.PassRate = "N/A"
        self.TotalTestCount = 0
        self.TotalPassCount = 0
        self.TotalFailCount = 0

        # WTT Fields
        self.ExtractNewResults = False
        self.QueryFile = ''
        self.LogLocationFile = ''

        RemovePath(self.LocalResultsFolder)
        MakePath(self.LocalResultsFolder)

        if ResetDatabase:
            sql.drop_table(self.TestTable)

    def InitForWTT(self, ExtractNewResults, QueryFile, LogLocationFile):
        Trace(r'[ExtractNewResults] [QueryFile] [LogLocationFile]')
        self.ExtractNewResults = ExtractNewResults
        self.QueryFile = ExpandPath(QueryFile)
        self.LogLocationFile = ExpandPath(LogLocationFile)

    def CreateTestData(self,
                    assembly,
                    suite,
                    name,
                    networkLogFile,
                    localLogFile,
                    comments='',
                    resolved=False,
                    bug=False):
        testData = []
        testData = DictN()
        testData.id                     = GetTestID(name, suite, assembly)
        testData.assembly               = assembly
        testData.suite                  = suite
        testData.name                   = name
        testData.networkLogFile         = networkLogFile
        testData.networkResultsFolder   = os.path.dirname(networkLogFile)
        testData.logFile                = localLogFile
        testData.resultsFolder          = os.path.dirname(localLogFile)
        testData.target                 = self.Target
        testData.branchName             = self.BranchName
        testData.buildVersion           = self.BuildVersion
        testData.comments               = comments
        testData.resolved               = resolved
        testData.bug                    = bug
        testData.repro                  = GetReproCommand(name, suite, assembly)
        return testData

    def GenerateExportFormat(self):
        exportColumns = [
            'id',
            'assembly',
            'suite',
            'name',
            'networkLogFile',
            'networkResultsFolder',
            'logFile',
            'resultsFolder',
            'target',
            'branchName',
            'buildVersion',
            'repro',
        ]

        exportTestData = []

        for testData in self.TestData:
            export = DictN()
            for key in exportColumns:
                export[key] = testData[key]
            exportTestData.append(export)

        return exportTestData

    def FindNetworkLogFilesWTT(self):
        Trace(self.LogLocationFile)

        def IsValidTestLogFile(FilePath):
            TestResultLine = 'TESTCASE RESULT=\"'
            for found in FindInFile(TestResultLine, FilePath):
                return True
            return False

        if self.ExtractNewResults:
            Run(Expand(r'[ResultsFetcherExe] --QueryFile [QueryFile] --OutputFile [LogLocationFile] --Verbose'))

        if not os.path.isfile(self.LogLocationFile):
            Warning(r'Missing file LogLocationFile %s' % (self.LogLocationFile))
            return []

        idx = 0
        logfile = open(self.LogLocationFile)
        for logfolder in logfile:
            logfolder = logfolder.strip()
            if not logfolder:
                continue

            buildData = wtt_build_info(logfolder)
            if not buildData:
                continue

            if buildData.BuildVersion != self.BuildVersion and \
               buildData.BranchName   != self.BranchName and \
               buildData.Target       != self.Target :
                # Skip results for different build
                continue

            Log(buildData.LogFile)

            # Extract results files
            resultsFiles = list(FindFiles(logfolder, r'DeviceOutput.txt'))
            resultsFiles.extend(FindFiles(logfolder, r'results.log'))
            foundValidLogFile = False
            for file in resultsFiles:
                if os.path.exists(file) and IsValidTestLogFile(file):
                    self.NetworkLogFiles.append(file)
                    foundValidLogFile = True
                    break

            if not foundValidLogFile:
                Warning('Did not find valid log file for [logfolder]')
        logfile.close()

        self.PopulateTestResults()
        return self.TestData

    def FindNetworkLogFiles(self, NetworkResultsFolder):
        Trace(NetworkResultsFolder)
        NetworkResultsFolder = ExpandPath(NetworkResultsFolder)

        fileList = list(FindFiles(NetworkResultsFolder, r'*Client.json'))
        if not len(fileList):
            Warning(r'Did not find Client.json file')
            return []

        for file in fileList:
            Log('Processing [file]')
            buildInfo = JSON.load_from_file(file)
            if buildInfo.BranchName     != self.BranchName and \
               buildInfo.Target         != self.Target and \
               buildInfo.BuildVersion   != self.BuildVersion:
                # Skip results for different build
                continue

            LogJSON(buildInfo, Silent=True)

            if not os.path.exists(Path(buildInfo.NetworkTestResultsFolder)):
                Warning('Missing path %s' % Path(buildInfo.NetworkTestResultsFolder))
                return []

            # Get Results files
            self.NetworkLogFiles = FindFiles(buildInfo.NetworkTestResultsFolder, r'results.log')
            self.NetworkLogFiles = list(self.NetworkLogFiles)
            return self.PopulateTestResults()

    def PopulateTestResults(self):
        Trace()

        Log('Found %d tests' % (len(self.NetworkLogFiles)))
        if len(self.NetworkLogFiles) == 0:
            Warning(r'No tests were found for [BuildVersion]')
            return []

        idx = 0
        foundTests = []
        for networkLogFile in self.NetworkLogFiles:
            idx += 1
            Log(r'Test result file: [networkLogFile]', Silent=True)

            test, suite, assembly, passed = TestLogFiles.extract_test_data(networkLogFile)
            test, suite, assembly, passed = TestLogFiles.extract_test_data(networkLogFile)

            id = GetTestID(test, suite, assembly)
            id = lex(r'[BuildVersion]![id]')
            self.AllTestIDs.append(id)
            if passed:
                if id not in list(self.PassedTestData.keys()):
                    self.PassedTestData[id] = True
                continue

            assemblyFolder = TestLogFiles.assembly_folder_name(assembly)

            logFileName = os.path.basename(networkLogFile)
            logFile = ExpandPath(r'[LocalResultsFolder]\[assemblyFolder]\[suite]\[test]\[logFileName]')
            Verbose(r'[idx]: [test] [suite] [assembly] - [logFile]')
            foundTests.append([idx, test, suite, assembly])

            testData = self.CreateTestData(assembly,
                            suite,
                            test,
                            networkLogFile,
                            logFile)
            self.TestData.append(testData)

        Log('Found failed tests:')
        PrettyPrintList(foundTests)

        # Remove tests that actually passed
        toDelete = []
        for testData in self.TestData:
            id = testData.id
            if id in list(self.PassedTestData.keys()):
                toDelete.append(item)

        for testData in toDelete:
            id = testData.id
            Verbose('Removing passed test [id]')
            self.TestData.remove(item)

        # Summarize
        Log('Found %d failed tests' % (len(self.TestData)))

        self.TotalTestCount = len(list(set(self.AllTestIDs)))
        self.TotalPassCount = len(list(set(self.PassedTestData.keys())))
        self.TotalFailCount = len(self.TestData)
        self.PassRate = '{0:.2f}%'.format(100 * float(self.TotalPassCount) / float(self.TotalTestCount))

        Log('TotalTestCount = [TotalTestCount]')
        Log('TotalPassCount = [TotalPassCount]')
        Log('TotalFailCount = [TotalFailCount]')
        Log('PassRate       = [PassRate]')

        PrettyPrintList(self.TestData, Verbose=True)

        self.ExportTestDataSQL()

        return self.TestData

    def UnResolveWebResultsData(self, ClearNonBugComments=False):
        today = datetime.datetime.date(datetime.datetime.now())
        lastRun = History.results(self.Target, self.BranchName, self.BuildVersion)
        if lastRun.BuildVersion == self.BuildVersion and lastRun.RunDate == str(today):
            Log('Results already retrieved for today: [today]')
            return

        Investigations.clear()

    def ProcessFoundResultLogFiles(self):
        Trace()

        if len(self.TestData) == 0:
            Log('No Tests Found')
            return

        resultsHtmlFile = r'[LocalResultsFolder]\html\Results.htm'
        resultsCsvFile = r'[LocalResultsFolder]\Results.csv'

        self.CopyNetworkFiles()
        self.GenerateLocalFiles()
        self.UnResolveWebResultsData()
        self.ExportTestDataJSON()
        self.TestData = Investigations.update_testdata(self.TestData)
        self.GenerateReproFile()
        Investigations.update_comments_from_errors(self.Target, self.BranchName, self.BuildVersion)

        History.update_results(self.Target, self.BranchName, self.BuildVersion)
        History.update_version_list(self.Target, self.BranchName, self.BuildVersion)

        jsonUrl = urllib.request.pathname2url(Globals.ResultsTestDataFile)
        # Done
        Log()
        Log()
        Log(r'Results folder: [LocalResultsFolder]')
        Log(r'Results file:   [resultsHtmlFile]')
        Log(r'JSON file:      [ResultsTestDataFile]')
        Log(r'JSON url:       [jsonUrl]')
        Log(r'Database csv:   [DatabaseCsvFile]')
        Log(r'csv file:       [resultsCsvFile]')
        Log(r'repro file:     [ResultsReproFile]')
        Log()
        #Run(lex(r'start [htmlFileName]'))

    def ExportTestDataJSON(self):
        Trace(Globals.ResultsTestDataFile)

        exportTestData = self.GenerateExportFormat()

        outputTestList = dict()
        for testData in exportTestData:
            outputTestList[testData.id] = testData

        output = dict()
        output['Results'] = outputTestList
        output['Config'] = {}
        output['Config']['Target']          = self.Target
        output['Config']['BranchName']      = self.BranchName
        output['Config']['BuildVersion']    = self.BuildVersion
        output['Config']['buildVersions']   = self.BuildVersion
        output['Config']['totalTestCount']  = self.TotalTestCount
        output['Config']['totalPassCount']  = self.TotalPassCount
        output['Config']['totalFailCount']  = self.TotalFailCount
        output['Config']['passRate']        = self.PassRate

        JSON.save_to_file(Globals.ResultsTestDataFile, output)

        data = r'var g_TestData = %s;' % (json.dumps(output, sort_keys=True, indent=4))
        FileLog(data, FilePath=Globals.ResultsTestDataJavaScriptFile, Silent=True)

    def ExportTestDataSQL(self):
        Trace()

        sqlData = []
        for testData in self.TestData:
            row = []
            for column, type in self.TestTableColumns:
                row.append(testData[column])
            sqlData.append(row)

        # Write new tests into TestTable
        sql.write_to_table(self.TestTable, sqlData, self.TestTableColumns, self.TestTablePrimaryKeyColumns, True)

    def CopyNetworkFiles(self):
        Trace()

        def StripNimbus(FilePath, ResultsFilePath):
            FilePath = ExpandPath(FilePath)
            ResultsFilePath = ExpandPath(ResultsFilePath)
            f = open(FilePath, 'r')
            o = open(ResultsFilePath, 'w')
            for line in f:
                if '[Nimbus]' not in line:
                    o.write(line)
            o.close()
            f.close()

        for testData in self.TestData:
            resultsFolder = Path(testData.resultsFolder)
            logFile = Path(testData.logFile)
            networkResultsFolder = Path(testData.networkResultsFolder)
            networkLogFile = Path(testData.networkLogFile)

            EnsurePath(resultsFolder)
            EnsurePath(os.path.dirname(logFile))

            pngFiles = glob.glob(Path(r'[networkResultsFolder]\*\*.png'))
            pngFiles.extend(glob.glob(Path(r'[networkResultsFolder]\*\*\*.png')))
            for pngFileName in pngFiles:
                pngFileName = Path(pngFileName)
                baseName  = os.path.basename(pngFileName)
                localfile = Path(r'[resultsFolder]\[baseName]')
                Verbose(r'Copy [baseName] to [localfile]')
                CopyFile(pngFileName, localfile)

            fullRunFileName = Path(r'[resultsFolder]\FullRun.log')

            resultsFile = Path(r'[resultsFolder]\results.log')
            Log(r'Copy to [resultsFile]')
            CopyFile(networkLogFile, resultsFile)

            CopyFile(networkLogFile, fullRunFileName)
            Verbose(r'Copy [networkLogFile] to [fullRunFileName]')

            StripNimbus(fullRunFileName, logFile)
            TestLogFiles.make_fail_log(logFile)

    def GenerateLocalFiles(self):
        Trace()

        for testData in self.TestData:
            resultsFolder = testData.resultsFolder

            EnsurePath(resultsFolder)
            # generate repro.ps1
            file = open(ExpandPath(r'[resultsFolder]\repro.ps1'), 'w')
            file.write(testData.repro)
            file.close()

            # generate buildVersion.txt
            file = open(ExpandPath(r'[resultsFolder]\buildVersion.txt'), 'w')
            file.write(testData.buildVersion)
            file.close()

    def GenerateReproFile(self, ExcludeResolved = True):
        Trace(Globals.ResultsReproFile)

        investigations = Investigations.load()

        DeleteFile(Globals.ResultsReproFile)
        reproCommandLines = []
        for testData in self.TestData:
            id = testData.id
            if ExcludeResolved and id in investigations.Results:
                foundItem = investigations.Results[id]
                if foundItem.get('resolved') == True:
                    Verbose('Skipping repro for [id]')
                    continue

            reproCommandLines.append(testData.repro)

        PrettyPrintList(reproCommandLines, FilePath=Globals.ResultsReproFile, Silent=True)

        Verbose(r'Contents of [ResultsReproFile]')
        for line in ListFromFile(Globals.ResultsReproFile):
            Verbose(line)

#-------------------------------------------------------------------------------------
# History class
#-------------------------------------------------------------------------------------
class History():
    @staticmethod
    def load():
        return JSON.load_from_file(Globals.ResultsHistoryFile)

    @staticmethod
    def save(HistoryData):
        Trace(Globals.ResultsHistoryFile)
        JSON.save_to_file(Globals.ResultsHistoryFile, HistoryData)
        _thread.start_new_thread(JSON.save_to_file, (Globals.ResultsHistoryFile2, HistoryData))

    @staticmethod
    def update(HistoryData, NewData):

        loweredData = DictN()
        historyList = NewData.get('History', None)
        if historyList:
            data = DictN()
            for key, value in historyList:
                data[key.lower()] = value


    @staticmethod
    def restore_backup():
        Trace(Globals.ResultsHistoryFile, Globals.ResultsHistoryFile2)
        if Globals.ResultsHistoryFile != Globals.ResultsHistoryFile2:
            if os.path.exists(Globals.ResultsHistoryFile2):
                CopyFile(Globals.ResultsHistoryFile2, Globals.ResultsHistoryFile)

    @staticmethod
    def get_node(HistoryData, Target, BranchName, BuildVersion = None):
        BranchName = BranchName.lower()
        Target = Target.lower()
        if BuildVersion:
            BuildVersion = BuildVersion.lower()
            return HistoryData.getNode(r'History\[BranchName]\[Target]\[BuildVersion]')
        else:
            return HistoryData.getNode(r'History\[BranchName]\[Target]')

    @staticmethod
    def get_results_node(HistoryData, Target, BranchName, BuildVersion = None):
        BranchName = BranchName.lower()
        Target = Target.lower()
        if BuildVersion:
            BuildVersion = BuildVersion.lower()
            return HistoryData.getNode(r'Results\[BranchName]\[Target]\[BuildVersion]')
        else:
            return HistoryData.getNode(r'Results\[BranchName]\[Target]')

    @staticmethod
    def results(Target, BranchName, BuildVersion):
        Trace(r'[BranchName] [Target] [BuildVersion]')
        history = History.load()
        BranchName = BranchName.lower()
        Target = Target.lower()
        return History.get_results_node(history, Target, BranchName, BuildVersion)

    @staticmethod
    def update_results(Target, BranchName, BuildVersion='Latest.tst'):
        Trace(r'[Target] [BranchName] [BuildVersion]')

        today = datetime.datetime.date(datetime.datetime.now())
        yesterday = today - datetime.timedelta(days=1)

        testList = load_testdata(Target, BranchName)
        if len(testList) == 0:
            return

        # Get bug & test list
        bugList = []
        failList = []
        passList = []
        for testData in list(testList.Results.values()):
            #print(testData.name, testData.get('comments', ''))
            if testData.get('comments', '') == Globals.PassedOnRerun:
                Log(r'* Found Passed Test %s' % testData.name)
                passList.append(testData.name)
                passList = list(set(passList))
            else:
                bugList.append(testData.get('comments', ''))
                bugList = list(set(bugList))
                failList.append(testData.name)
                failList = list(set(failList))

        history = History.load()
        DictN.del_key(History.get_results_node(history, Target, BranchName), BuildVersion)
        #PrettyPrint(history)
        node = DictN({
            'Results' : {
                BranchName.lower() : {
                    Target.lower() : {
                        BuildVersion.lower() : {
                            'BuildVersion' : BuildVersion,
                            'Bugs' : bugList,
                            'Failed' : failList,
                            'Passed' : passList,
                        }
                    }
                },
            },
        })
        history.update(node)
        History.save(history)

    @staticmethod
    def update_version_list(Target, BranchName, BuildVersion='Latest.tst'):
        Trace(r'[BranchName] [Target] [BuildVersion]')
        today = datetime.datetime.date(datetime.datetime.now())

        history = History.load()
        versions = History.get_node(history, Target, BranchName)
        versions.RunDate = str(today)
        versions.BuildVersionHistory = versions.get('BuildVersionHistory', [])

        # Add BuildVersion to end of history list
        while BuildVersion in versions.BuildVersionHistory:
            versions.BuildVersionHistory.remove(BuildVersion)
        versions.BuildVersionHistory.append(BuildVersion)

        # Truncate list to max of last 10 items only
        while len(versions.BuildVersionHistory) >= 10:
            removedBuildVersion = versions.BuildVersionHistory.pop(0)
            DictN.del_key(History.get_results_node(history, Target, BranchName), removedBuildVersion)

        History.save(history)

    @staticmethod
    def node(Target, BranchName):
        Trace(r'[BranchName] [Target]')

        history = History.load()
        return History.get_node(history, Target, BranchName)

    @staticmethod
    def version_list(Target, BranchName):
        Trace(r'[BranchName] [Target]')

        history = History.load()
        versions = History.get_node(history, Target, BranchName)
        versions.BuildVersionHistory = versions.get('BuildVersionHistory', [])
        return versions.BuildVersionHistory

#-------------------------------------------------------------------------------------
# BuildVersions class
#-------------------------------------------------------------------------------------
class BuildVersions():
    @staticmethod
    def from_repro_cmd_file(FilePath = r'[SDXROOT]\repro.bat'):
        FilePath = ExpandPath(FilePath)
        Trace(FilePath)
        if not os.path.exists(FilePath):
            return "Missing.Build.Version.From." + FilePath

        buildver = FindInFile(r'set BUILDSTRING=', FilePath)
        if buildver and len(buildver) > 0:
            buildver = buildver[0].split('=')
            if len(buildver) > 1:
                buildver = buildver[1].strip()
                return buildver
        return "Missing.Build.Version.From." + FilePath

    @staticmethod
    def versions(ResultsFolder = r'[NetworkResultsFolder]'):
        Trace(ResultsFolder)
        ResultsFolder = ExpandPath(ResultsFolder)

        fileList = list(FindFiles(ResultsFolder, r'*Client.json'))
        if not len(fileList):
            Warning(r'Did not find Client.json file in [ResultsFolder]')
            return []

        buildDataList = []
        for file in fileList:

            Log('Processing [file]')
            buildInfo = JSON.load_from_file(file)

            buildData = DictN()
            buildData.Target = buildInfo.Target
            buildData.BranchName = buildInfo.BranchName
            buildData.BuildVersion = buildInfo.BuildVersion
            buildData.LogFile = file

            BuildVersions.append_to_build_list(buildDataList, buildData)

        return buildDataList

    @staticmethod
    def latest(Target, BranchName, BuildVersion=''):
        Trace(Target, BranchName, BuildVersion)

        buildVersions = []
        for file in FindFilesByDate(r'[NetworkRootFolder]\[BranchName]', '*.client.json', Desc=False):
            client = JSON.load_from_file(file)
            if client.Target == Target:
                buildVersions.append(client.BuildVersion)

        if is_number(BuildVersion):
            idx = int(BuildVersion)
            try:
                return buildVersions[idx]
            except:
                pass

            if idx < 0 and abs(idx) > len(buildVersions):
                return buildVersions[0]

        if len(buildVersions):
            return buildVersions[-1]

        return r'Latest.tst'

    @staticmethod
    def molive_latest(Target, BranchName, BuildVersion='Latest.tst'):

        if BuildVersion == r'Latest.tst':
            buildFlavor = Target.strip('x86').strip('arm')
            versionFile = Expand(r'\\Edge-svcs\release\WEC\[BranchName]\Latest.tst\[Target]\Bin\build_logs\build[buildFlavor].trc')
            Trace(versionFile)
            prefix = r'BuildNumber='
            if not os.path.exists(versionFile):
                Error(r'Version files does not exist [versionFile]')
            if os.path.exists(versionFile):
                # Use binary mode on version file b/c it has non-ascii characters
                for line in FindInFile(prefix, versionFile, 'rb'):
                    line = line.strip().lstrip("'b").strip()
                    if line.startswith(prefix):
                        line = line.lstrip(prefix).strip()
                        line = line.split('\\')
                        buildNumber = line[0]
                        if buildNumber:
                            return buildNumber.strip()

        # Get BuildVersion from results
        return BuildVersions.latest(Target, BranchName, BuildVersion)

    @staticmethod
    def wp8_lkg_version():
        # Get LKG Version
        outputFile = ExpandPath(r'[Temp]\SyncToLkg.idonly.log')
        Run(r'SyncToLkg.bat -idonly > [outputFile]')
        reproFile = FindInFile("repro.bat", outputFile)
        reproFile = reproFile[0]
        lkgVer = BuildVersions.from_repro_cmd_file(reproFile)

        # Get Build Version
        reproFile = ExpandPath(r'[SDXROOT]\repro.bat')
        buildVer = BuildVersions.from_repro_cmd_file(reproFile)

        versions = DictN()
        versions.LkgVer = lkgVer
        versions.BuildVer = buildVer
        PrettyPrintDict(versions)

        return versions

    @staticmethod
    def latest_wtt(ExtractNewResults = True,
                        QueryFile = r'[PUBLIC_SHARE]\TodaysFailedResults.wtq',
                        LogLocationFile = r'[Temp]\LogLocations.log',
                        LocalResultsFolder = r'[ResultsOutputFolder]',
                        DefaultTarget='UnknownTarget'):
        Trace()
        QueryFile = ExpandPath(QueryFile)
        LogLocationFile = ExpandPath(LogLocationFile)

        if ExtractNewResults:
            Run(Expand(r'[ResultsFetcherExe] --QueryFile [QueryFile] --OutputFile [LogLocationFile] --Verbose'))

        if not os.path.isfile(LogLocationFile):
            Warning(r'missing file %s' % (LogLocationFile))
            return []

        buildDataList = []

        logfile = open(LogLocationFile)
        for logfolder in logfile:
            logfolder = logfolder.strip()
            if not logfolder:
                continue

            Verbose(r'Test log folder:  %s' % logfolder)

            buildData = wtt_build_info(logfolder)
            if buildData:
                BuildVersions.append_to_build_list(buildDataList, buildData)
        logfile.close()

        return buildDataList

    @staticmethod
    def append_to_build_list(BuildDataList, BuildData):
        if not BuildData:
            return
        for previous in BuildDataList:
            if previous.BuildVersion == BuildData.BuildVersion and \
               previous.BranchName   == BuildData.BranchName and   \
               previous.Target       == BuildData.Target:
                return

        BuildDataList.append(BuildData)

#-------------------------------------------------------------------------------------
# Investigations class
#-------------------------------------------------------------------------------------
class Investigations():
    @staticmethod
    def load():
        investigations = JSON.load_from_file(Globals.ResultsWebDataFile)
        investigations.Results = investigations.get('Results', {})
        return investigations

    @staticmethod
    def save(investigations, strip=True):
        if strip:
            # remove blank entries
            toBeRemoved = []
            for key in investigations.Results:
                data = investigations.Results[key]
                if isinstance(data, dict):
                    if (not data.get('resolved', False)) and (not data.get('comments', '')):
                        toBeRemoved.append(key)

            for key in toBeRemoved:
                Verbose('Removing empty result for [key]')
                del investigations.Results[key]

        JSON.save_to_file(Globals.ResultsWebDataFile, investigations)
        _thread.start_new_thread(JSON.save_to_file, (Globals.ResultsWebDataFile2, investigations))

    @staticmethod
    def restore_backup():
        Trace(Globals.ResultsWebDataFile, Globals.ResultsWebDataFile2)
        if Globals.ResultsWebDataFile != Globals.ResultsWebDataFile2:
            if os.path.exists(Globals.ResultsWebDataFile2):
                CopyFile(Globals.ResultsWebDataFile2, Globals.ResultsWebDataFile)

    @staticmethod
    def update_testdata(TestData):
        # Joins Web Results JSON to Test Data list
        investigations = Investigations.load()
        if isinstance(TestData, list):
            for testData in TestData:
                testData.update(investigations.Results.get(testData.id, {}))
        else:
            for testData in list(TestData.values()):
                testData.update(investigations.Results.get(testData.id, {}))

        return TestData

    @staticmethod
    def strip():
        investigations = Investigations.load()
        Investigations.save(investigations, True)

    @staticmethod
    def clear():
        Trace(Globals.ResultsWebDataFile)
        Investigations.strip()

        investigations = Investigations.load()
        for key in investigations.Results:
            investigations.Results[key]['resolved'] = False
            if investigations.Results[key].get('comments', '') == '':
                investigations.Results[key]['bug'] = False
            elif not investigations.Results[key].get('bug', False):
                investigations.Results[key]['comments'] = ''

        Investigations.save(investigations)

    @staticmethod
    def update_from_results(ResultsFolder=r'[Temp]\Results', ClearNonBugComments=False):
        Trace('ClearNonBugComments:[ClearNonBugComments] [ResultsFolder]')
        ResultsFolder = ExpandPath(ResultsFolder)

        Investigations.strip()

        #FailMessage = 'TESTCASE RESULT=\"FAILED\"'
        PassMessage = 'TESTCASE RESULT=\"PASSED\"'

        passedTests = []
        failedTests = []
        for file in FindFiles(ResultsFolder, r'results.log'):
            if len(FindInFile(PassMessage, file)):
                passedTests.append(file)
            else:
                failedTests.append(file)

        PrettyPrintList(passedTests, 'Passed Tests')
        Log()
        PrettyPrintList(failedTests, 'Failed Tests')
        Log()

        #buildVer = BuildVersions.from_repro_cmd_file()
        investigations = Investigations.load()

        defaultResult = DictN({
            'comments'  : '',
            'resolved'  : False,
            'bug'       : False,
        })

        #PrettyPrintDict(investigations)
        for file in passedTests:
            test, suite, assembly, passed = TestLogFiles.extract_test_data(file)
            assemblyFolder = TestLogFiles.assembly_folder_name(assembly)
            id = GetTestID(test, suite, assembly)

            Log('Processing [id]')
            testResult = DictN.get_value(investigations.Results, id, defaultResult)
            investigations.Results[id] = testResult

            comments = testResult.get('comments', '')
            if comments == "" or comments == Globals.PassedOnRerun:
                Log('* Updating [id] to [PassedOnRerun]')
                testResult["bug"] = False
                testResult["comments"] = Globals.PassedOnRerun
                testResult["resolved"] = True

        Investigations.save(investigations)

    @staticmethod
    def update_comments_from_errors(Target, BranchName, BuildVersion, ResultsPath=r'[Temp]\WTTResults\[BranchName]\[BuildVersion]\[Target]'):
        ResultsPath = ExpandPath(ResultsPath)
        Trace(ResultsPath)

        investigations = Investigations.load()

        defaultResult = DictN({
            'comments'  : '',
            'resolved'  : False,
            'bug'       : False,
        })

        for file in FindFiles(ResultsPath, r'fail.log'):
            test, suite, assembly, passed = TestLogFiles.extract_test_data(file.replace('fail.log', 'results.log'))
            id = GetTestID(test, suite, assembly)
            Log('Processing [id]')
            testResult = DictN.get_value(investigations.Results, id, defaultResult)
            if testResult.bug: # or testResult.get('comments', ''):
                Log('skipping   [id] %s - %s' % (testResult.bug, testResult.get('comments', '')), UseExpand=False)
                continue

            fp = open(file, 'r')
            error = ''
            for line in fp:
                line = line.strip()
                if 'Error: Operation failed ' in line:
                    continue
                elif 'Error:' in line and 'failed' in line:
                    Log('Error      %s' % line, UseExpand=False)
                    testResult["comments"] = line
                    investigations.Results[id] = testResult
                    break
                elif 'Error: ' in line:
                    Log('Error      %s' % line, UseExpand=False)
                    testResult["comments"] = line
                    investigations.Results[id] = testResult
            fp.close()

        Investigations.save(investigations)

#-------------------------------------------------------------------------------------
# TestLogFiles class
#-------------------------------------------------------------------------------------
class TestLogFiles():
    @staticmethod
    def exclude_line(Line):
        exclude = [
            r'[1] Warning: Failed to find the process id of gamesux.exe - it may not be running. Exception message from FindProcessIdByName: [Could not find a running process named gamesux.exe]',
            r'Warning: Failed to find the process id of gamesux.exe - it may not be running. Exception message from FindProcessIdByName: [Could not find a running process named gamesux.exe]',
            r'*** Result:         Failed',
            r'<BreakOnFail>False</BreakOnFail>',
            r'*** Failed:          1',
            r'Screen Capture on Exceptions: Enabled',
            '</TESTCASE RESULT=\"FAILED\">',
            '<\/TESTCASE RESULT=\"FAILED\">',
            #'Now Playing Tile game image url is incorrect',
            #'Now Playing Tile media image url was correct. Expected',
            #'[1] Verification = Fail: Now Playing Tile\'s Thumbnail visibilty. Expected: False, Actual: True',
            #'[1] Verification = Fail: Now Playing Tile\'s Static Icon visibilty is correct. Expected: True, Actual: False',
            ]
        excluded = False
        idx=0
        line = Line.strip()
        if line in exclude:
            idx = exclude.index(line)
            excluded = True
        else:
            for ex in exclude:
                if ex in line:
                    excluded = True
                    break
            idx = idx + 1

        return excluded
        if not excluded:
            return Line
        else:
            return 'Excluded: %d' % idx

    @staticmethod
    def make_fail_log(ResultsFile=r'[Temp]\results.log'):
        #Trace(ResultsFile)
        ResultsFile = ExpandPath(ResultsFile)
        failLog = r'%s\fail.log' % os.path.dirname(ResultsFile)
        DeleteFile(failLog)

        extractionLines = [
            r'fail',
            r'error',
            r'exception',
            r'type    = ',
            r'message = ',
            r'Exception in test',
            r'at Microsoft.Phone.Test.',
            ]

        errors=[]
        idx = 0
        for message in extractionLines:
            idx += 1
            for line in FindInFile(message, ResultsFile):
                if not TestLogFiles.exclude_line(line):
                    errors.append(str(idx) + ": " + line.strip())

        if len(errors) == 0:
            errors.append(r'Unknown Error: Failed tested has no error messages')

        errors = list(set(errors))
        errors.sort()
        f = open(failLog, 'w')
        for line in errors:
            f.write(line + '\n')
        f.close()

    def wtt_build_info(FolderPath):
        #Trace(FolderPath)
        FolderPath = ExpandPath(FolderPath)

        for networkLogFile in glob.glob(r'%s\*.JobLogs\JobLog.txt' % (FolderPath)):
            # Get Build Version from line(s):

            imageLine = [
                    r'Information (WTTMobileTaskPlugInFactory) 	: 	ImagePath =',
                    r'ImagePath = ',
            ]
            for pattern in imageLine:
                found = FindInFile(pattern, networkLogFile)
                for item in found:
                    item = item.strip()[item.index(pattern) + len(pattern):].replace('\\\\', '').strip()
                    folders = item.split('\\')
                    if len(folders) >= 6 :
                        buildData = DictN()
                        # 0 = build
                        # 1 = release
                        # 2 = Apollo
                        buildData.BranchName    = folders[3].strip()
                        buildData.BuildVersion  = folders[4].strip()
                        buildData.Target        = folders[5].split(r'.')[-1].lower().strip()
                        buildData.LogFile       = networkLogFile
                        return buildData

            #   Parameter:system_Build = WP8_ESB_DEV_MVMARKETPLACE.8422.9725.20120625-2325
            buildLine = [r'Parameter:system_Build = ']
            for pattern in buildLine:
                found = FindInFile(pattern, networkLogFile)
                for item in found:
                    item = item.strip()[item.index(pattern) + len(pattern):].strip()
                    buildData = DictN()
                    buildData.BranchName = item.split(r'.')[0]
                    buildData.BuildVersion = item
                    buildData.Target = DefaultTarget
                    buildData.LogFile = networkLogFile
                    return buildData

        return None

    @staticmethod
    def extract_test_names_helper(FilePath):

        # Repro: -assembly Microsoft.Phone.Test.MoLIVE.Native.TestCases.dll -suites DefaultUserTestCases -tests GameMessages_MoLIVE_AsyncTextMessageBoundary
        searchText = r'Repro: -assembly '
        found = FindInFile(searchText, FilePath)
        if found and len(found):
            values = found[0]
            values = values.split(' ')
            if len(values) == 7:
                assembly = values[2]
                suite = values[4]
                test = values[6]
                return [test, suite, assembly]

        # assembly = Microsoft.Phone.Test.MoLIVE.Native.TestCases.dll
        # suites =  DefaultUserTestCases
        # tests = GameMessages_MoLIVE_AsyncTextMessageBoundary
        assemblyText = r'assembly = '
        suitesText = r'suites ='
        suiteText = r'suite ='
        testText = r'tests ='

        assembly = ''
        suite = ''
        test = ''

        for found in FindInFile(assemblyText, FilePath):
            assembly = found.strip().replace(assemblyText, r'').strip()

        for found in FindInFile(suitesText, FilePath):
            suite = found.strip().replace(suitesText, r'').strip()

        if not suite:
            for found in FindInFile(suiteText, FilePath):
                suite = found.strip().replace(suiteText, r'').strip()

        for found in FindInFile(testText, FilePath):
            test = found.strip().replace(testText, r'').strip()

        if test and suite and assembly:
            return [test, suite, assembly]

        #*** Test Name:      Microsoft.Phone.Test.AppPlatform.YMTF.TuxNet.TestCases.DefaultUserTestCases.Achievements_MoLIVE_AsyncUnlockAchievementForUserTest
        searchText = r'*** Test Name:      '
        found = FindInFile(searchText, FilePath)
        if found and len(found):
            values = found[0]
            values = values.strip().replace(searchText, r'').strip()
            values = values.split('.')

            test = values[-1]
            values = values[0:-1]

            suite = values[-1]
            values = values[0:-1]

            assembly = r'%s.dll' % ('.'.join(values))
            return [test, suite, assembly]

    @staticmethod
    def extract_test_data(FilePath):
        data = TestLogFiles.extract_test_names_helper(FilePath)

        passed = False
        PassMessage = 'TESTCASE RESULT=\"PASSED\"'
        for found in FindInFile(PassMessage, FilePath):
            passed = True

        data.append(passed)
        return data

    @staticmethod
    def assembly_folder_name(Assembly):
        folder = Assembly
        folder = folder.replace(r'Microsoft.Phone.Test.MediaApps.', r'').strip()
        folder = folder.replace(r'MediaApps.', r'').strip()
        folder = folder.replace(r'Microsoft.Phone.Test.', r'').strip()
        folder = folder.replace(r'.dll', r'').strip()
        folder = folder.replace(r'.Tests', r'').strip()
        folder = folder.replace(r'.Test', r'').strip()
        folder = folder.replace(r'.', '\\').strip()
        return folder

    @staticmethod
    def pretty_print(TestFileList, *args, **kwargs):
        testFunctions = []
        for file in TestFileList:
            test, suite, assembly, passed = TestLogFiles.extract_test_data(file)
            if test and suite and assembly:
                cmdLine = Expand(r'RunTuxNet [test] [suite] [assembly]')
                testFunctions.append(cmdLine.split(' '))

        PrettyPrintList(testFunctions, *args, **kwargs)

#-------------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------------
def GetTestResults(Target,
                   BranchName,
                   BuildVersion,
                   NetworkResultsFolder = r'[Temp]\MoLiveResults',
                   LocalResultsFolder = r'[ResultsOutputFolder]',
                   ResetDatabase=False):
    Trace(NetworkResultsFolder)
    NetworkResultsFolder = ExpandPath(NetworkResultsFolder)

    results = TestResults(LocalResultsFolder, ResetDatabase)
    results.Target = Target
    results.BranchName = BranchName
    results.BuildVersion = BuildVersion

    IncreaseIndent()
    results.FindNetworkLogFiles(NetworkResultsFolder)
    DecreaseIndent()

    results.ProcessFoundResultLogFiles()
    return results.TestData

def GetTestResultsWTT(
                Target,
                BranchName,
                BuildVersion,
                LogLocationFile = r'[Temp]\LogLocations.log',
                LocalResultsFolder = r'[ResultsOutputFolder]',
                ResetDatabase=False):
    Trace(r'[BranchName] [Target] [BuildVersion]')

    results = TestResults(LocalResultsFolder, ResetDatabase)
    results.Target = Target
    results.BranchName = BranchName
    results.BuildVersion = BuildVersion
    results.LogLocationFile = ExpandPath(LogLocationFile)

    IncreaseIndent()
    results.FindNetworkLogFilesWTT()
    DecreaseIndent()

    results.ProcessFoundResultLogFiles()
    return results.TestData

def RunResultsFetcher(QueryFile = r'[PUBLIC_SHARE]\TodaysFailedResults.wtq', ResultsLogFile = r'[Temp]\LogLocations.log', WTTServer=''):
    Trace(r'[QueryFile] [ResultsLogFile] [WTTServer]')
    Run(r'[ResultsFetcherExe] --QueryFile [QueryFile] --OutputFile [ResultsLogFile] --DataStore [WTTServer] --Verbose')

def GetTestID(test, suite, assembly):
    return Expand(r'[assembly]![suite]![test]')

def GetReproCommand(test, suite, assembly):
    return Expand(r'RunTuxNet [test] [suite] [assembly]')

def load_testdata(Target, BranchName):
    return load_testdata_file(Globals.ResultsTestDataFile)

def load_testdata_file(FilePath):
    Trace(FilePath)
    if not os.path.exists(FilePath):
        Warning('Missing [FilePath]')
        return {}
    testList = JSON.load_from_file(FilePath)
    if len(testList) == 0:
        return {}
    testList.Results = Investigations.update_testdata(testList.Results)
    for key in list(testList.Results.keys()):
        testData = testList['Results'][key]
        testData.comments = testData.get('comments', '').strip().replace(',', '-').replace(r'[', r'(').replace(r']', r')')

    return testList

def GetNetworkTestResults(Target, BranchName, BuildVersion, ResetDatabase=False):
    BuildVersion = Expand(BuildVersion)
    Trace(r'[Target] [BranchName] [BuildVersion]')

    if not os.path.exists(ExpandPath(Globals.NetworkResultsFolder)):
        Warning(r'Missing results folder [NetworkResultsFolder]')
        return None

    testlist = GetTestResults(Target, BranchName, BuildVersion, Globals.NetworkResultsFolder)
    if len(testlist) == 0:
        Warning(r'No results found for [BranchName] [BuildVersion] [Target]')
        return None

    reproOutputFolder = r'[Temp]\ReproResults\[BranchName]\[Target]'
    GenNetworkTestResultsRepro(Target, BranchName, BuildVersion, reproOutputFolder)

    return testlist

def GenNetworkTestResultsRepro(Target, BranchName, BuildVersion, OutputFolder, IncludeAllTests = False):
    Trace(r'[Target] [BranchName] [BuildVersion] [OutputFolder]')
    OutputFolder = ExpandPath(OutputFolder)

    testList = load_testdata(Target, BranchName)
    if len(testList) == 0:
        return

    testNames = []
    for item in list(testList.Results.values()):
        if not item.bug and item.get('comments', '') != Globals.PassedOnRerun: # or IncludeAllTests
            testNames.append(item.name)
            Log('   Add Repro test: %s' % item.name)

    # Generate MoLive Repro File
    fp = open(Globals.ResultsReproFile, 'w')
    if len(testNames) == 0:
        Log('No failed non-bug tests')
        fp.write(Expand(r'echo No Failed tests for [BranchName] [BuildVersion] [Target]'))
    else:
        for name in testNames:
            fp.write(Expand(r'ReproTest.cmd -OutputFolder "[OutputFolder]" -BranchName "[BranchName]" -BuildVersion "[BuildVersion]" -Target "[Target]" -Tests "[name]" %*\n'))
    fp.close()

    Log(r'Generated repro file: [ResultsReproFile]')

def GetMoLiveResults(Target='x86chk',
                        BranchName='main_dev_molive_sdk_dev',
                        BuildVersion='Latest.tst',
                        ResetDatabase=False):

    BuildVersion = Expand(BuildVersion)
    if BuildVersion == r'Latest.tst' or is_number(BuildVersion):
        BuildVersion = BuildVersions.molive_latest(Target, BranchName, BuildVersion)

    Trace(r'[Target] [BranchName] [BuildVersion]')

    if not os.path.exists(Globals.NetworkResultsFolder):
        Log(r'Missing results folder [NetworkResultsFolder]')
        return

    testlist = GetTestResults(Target, BranchName, BuildVersion, Globals.NetworkResultsFolder)
    if len(testlist) == 0:
        Log(r'No results found for [BranchName] [BuildVersion] [Target]')
        return

    reproOutputFolder = r'[Temp]\MoLIVE\ReproResults\[BranchName]\[Target]'
    GenMoLiveRepro(Target, BranchName, BuildVersion, reproOutputFolder)

def GenMoLiveRepro(Target, BranchName, BuildVersion, OutputFolder, IncludeAllTests = False):
    Trace(r'[Target] [BranchName] [BuildVersion] [OutputFolder]')
    OutputFolder = ExpandPath(OutputFolder)

    testList = load_testdata(Target, BranchName)
    if len(testList) == 0:
        return

    testNames = []
    for item in list(testList.Results.values()):
        if not item.bug and item.get('comments', '') != Globals.PassedOnRerun: # or IncludeAllTests
            testNames.append(item.name)
            Log('   Add Repro test: %s' % item.name)

    # Generate MoLive Repro File
    fp = open(Globals.ResultsReproFile, 'w')
    if len(testNames) == 0:
        Log('No failed non-bug tests')
        fp.write(Expand(r'echo No Failed tests for [BranchName] [BuildVersion] [Target]'))
    else:
        testNames = ','.join(testNames)
        #MakePath(OutputFolder)
        fp.write(Expand(r'C:\NewDailyTestRun\RunDailyTests.cmd -OutputFolder "[OutputFolder]" -BranchName "[BranchName]" -BuildVersion "[BuildVersion]" -Target "[Target]" -Tests "[testNames]" -SkipRetry -SkipSendEmail %*'))
    fp.close()

    Log(r'Generated repro file: [ResultsReproFile]')

def GenSummaryReportHtml(OutputFile=r'[Temp]\TestReport\Summary.htm', InputFolder=r'[Temp]\WTTResults', Append=False, LatestOnly=True):
    Trace(OutputFile)
    IncreaseIndent()
    OutputFile = ExpandPath(OutputFile)
    InputFolder = ExpandPath(InputFolder)
    EnsurePath(os.path.dirname(OutputFile))

    summaryData = []
    htmlTableEntries = []
    title = r'Test Result Summary - [Date]'

    fpTemplate = open(ExpandPath(r'[ScriptFolder]\Templates\TestResults.htm'), 'r')
    htmlTemplate = fpTemplate.read()
    fpTemplate.close()

    htmlBuildVersionTableEntryTemplate = """
            <tr class='BlankLine'>
                <td colspan="2">&nbsp;</th>
            </tr>
            <tr>
                <th colspan="2"><span>[Target] - [BuildVersion] - [BranchName]</span>&nbsp;</th>
            </tr>
    """
    htmlTableEntryTemplate = """
            <tr>
                <td class='TestResultCell' colspan='2'><span>[name]</span></td>
            </tr>
            <tr>
                <td class='TestResultCommentsCell'><span>-</span></td>
                <td class='TestResultCommentsCell'><span>[comments]</span></td>
            </tr>
    """

    allIssues = []
    allTests = []

    today = datetime.datetime.date(datetime.datetime.now())
    yesterday = today - datetime.timedelta(days=1)

    testDataFiles = list(FindFilesByDate(InputFolder, 'TestData.json'))
    if LatestOnly:
        configs = []
        latest = []
        # Get the files latest files with unique target, branchName combinations
        for file in testDataFiles:
            testList = JSON.load_from_file(file)
            configName = '%s,%s', testList.Config.Target.lower(), testList.Config.BranchName.lower()
            if configName not in configs:
                configs.append(configName)
                latest.append(file)

        testDataFiles = latest

    for file in testDataFiles:
        Log(r'Process [file] [today] [yesterday]')

        testList = load_testdata_file(file)
        Target = testList.Config.Target
        BranchName = testList.Config.BranchName.lower()
        BuildVersion = testList.Config.BuildVersion

        todayHistoryNode = History.results(Target, BranchName, BuildVersion)
        historyList = History.version_list(Target, BranchName)
        yesterdayBuildVersion = BuildVersion
        if len(historyList) >= 2:
            yesterdayBuildVersion = historyList[-2]
        yesterdayHistoryNode = History.results(Target, BranchName, yesterdayBuildVersion)

        diff = list(set(todayHistoryNode.Bugs) - set(yesterdayHistoryNode.Bugs))
        diff.extend(list(set(todayHistoryNode.Tests) - set(yesterdayHistoryNode.Tests)))
        if len(diff) > 0:
            Log('Found %d new test issues' % len(diff))
            Log('-----------------------------------------')
            PrettyPrint(diff)
            Log('-----------------------------------------')

        # Summary of pass rate
        summaryData.append([BranchName, BuildVersion, Target, '%s Pass' % testList.Config.passRate])

        testEntries = []
        for testData in list(testList.Results.values()):
            name = testData.name
            suite = testData.suite
            assembly = testData.assembly
            comments = testData.comments
            testEntries.append([name, suite, assembly, comments])
            if len(comments) and comments != Globals.PassedOnRerun:
                allIssues.append(r'<li>%s</li>' % comments)
                allIssues = list(set(allIssues))
                allTests.append(name)
                allTests = list(set(allTests))

        # Sort data for output
        testEntries = sql.sort_data(testEntries, [3, 2, 2, 1])

        testHtmlEntries = []
        for row in testEntries:
            [ name, suite, assembly, comments] = row
            testHtmlEntries.append(Expand(htmlTableEntryTemplate))

        htmlTableEntries.append(Expand(htmlBuildVersionTableEntryTemplate))
        htmlTableEntries.extend(testHtmlEntries)

    allIssues = sql.sort_data(allIssues, [0])
    issuesTableEntries = ListToHtmlTableRows(allIssues)
    summaryTableEntries = ListToHtmlTableRows(summaryData)

    # Gen Final Html
    htmlTableEntries = '\n'.join(htmlTableEntries)

    htmlFile = open(OutputFile, 'w')
    htmlFile.write(Expand(htmlTemplate))
    htmlFile.close()

    Log('Generated [OutputFile]')
    DecreaseIndent()

def FetchLatestResultsIfNeeded(Target, BranchName, BuildVersion, Type='MoLive'):
    today = datetime.datetime.date(datetime.datetime.now())
    yesterday = today - datetime.timedelta(days=1)

    historyNode = History.node(Target, BranchName)
    previousFetch = History.results(Target, BranchName, BuildVersion)

    if previousFetch.BuildVersion == BuildVersion and historyNode.RunDate == str(today):
        Log(r'Results already fetched for [BranchName] [Target] [BuildVersion] [today]')
        return

    Investigations.clear()

    Log(r'Processing [BranchName] [Target] [BuildVersion] [today]')
    PrettyPrint(previousFetch, 'Previous Run')
    if Type == 'MoLive':
        GetMoLiveResults(Target=Target, BranchName=BranchName, BuildVersion=BuildVersion)

    todayHistoryNode = History.results(Target, BranchName, str(today))
    yesterdayHistoryNode = History.results(Target, BranchName, str(yesterday))

    diff = list(set(todayHistoryNode.Bugs) - set(yesterdayHistoryNode.Bugs))
    diff.extend(list(set(todayHistoryNode.Tests) - set(yesterdayHistoryNode.Tests)))
    if len(diff) > 0:
        Log('Found %d new test issues' % len(diff))
        Log('-----------------------------------------')
        PrettyPrint(diff)
        Log('-----------------------------------------')
        resultsChanged = True
        message = 'Test Differences\n%s\n' % ('\n'.join(diff))
        email.send_email(Subject='SixShot-MoLive:: Test Differences - [Target]- [BranchName] - [BuildVersion] - [Date] - [COMPUTERNAME]', Body=message, Attachments=[Globals.LogFile], Strict=True)
