import datetime
import glob
import json
import os
import platform
import re
import sys
import _thread
import time

import Utility.Utility
from   Utility.Utility import *
import Utility.Sql as sql
import Utility.SqlServer as sqlserver
import Utility.Email as email
import Utility.XmlToDict as xml

class ReportGenerator():

    DefaultHtmlTemplate = """
    <html>
        <head>
        </head>
        <body>
            <!-- Insert Table Here -->
        </body>
    </html>
    """;

    TableTemplate = """
            <table style='clear:both;'>
                [table_html]
            </table>
            <!-- Insert Table Here -->
    """

    HeaderTemplate = """
            <h2>[header_html]</h2>
            <!-- Insert Table Here -->
    """

    def __init__(self, ConfigFile, UseResultsFile = False):
        ConfigFile = ExpandPath(ConfigFile)
        ConfigFolder = os.path.dirname(ConfigFile)
        self.Config = JSON.load_from_file(ConfigFile)
        self.UseResultsFile = UseResultsFile

        self.SqlFilePath = ExpandPath(self.Config.SqlFilePath)
        self.OutputFile = ExpandPath(self.Config.OutputFile)
        self.TemplateFile = ExpandPath(self.Config.TemplateFile)
        self.CssFile = ExpandPath(self.Config.CssFile)
        self.Subject = ExpandPath(self.Config.Subject)
        self.ResultsFile = ExpandPath(self.Config.ResultsFile)

        Trace(self.SqlFilePath, self.OutputFile, self.TemplateFile, self.CssFile, self.Subject, self.ResultsFile)

        if not self.OutputFile:
            basename,ext = os.path.splitext(os.path.split(self.SqlFilePath)[1])
            self.OutputFile = ExpandPath(r'[Temp]\[basename].htm')
        EnsurePath(os.path.dirname(self.OutputFile))

        if self.CssFile and os.path.exists(self.CssFile):
            fp = open(self.CssFile, 'r', encoding="utf-8")
            self.CssFile = fp.read()
            self.CssFile = self.CssFile.encode('ascii', 'ignore').decode(encoding='utf-8')
            fp.close()

        self.HtmlTemplate = ReportGenerator.DefaultHtmlTemplate
        if self.TemplateFile:
            fp = open(self.TemplateFile, 'r', encoding="utf-8")
            self.HtmlTemplate = fp.read()
            fp.close()
        self.HtmlTemplate = Expand(self.HtmlTemplate)

        self.PreviousResults = None
        if UseResultsFile:
            if os.path.exists(self.ResultsFile):
                savedData = JSON.load_from_file(self.ResultsFile)
                if len(savedData.results):
                    self.PreviousResults = savedData.results

    def queryFromXml(self, FilePath):
        Trace(FilePath)
        FilePath = ExpandPath(FilePath)
        if os.path.exists(FilePath):
            DeleteFile(FilePath)
        outputFolder = os.path.dirname(FilePath)
        RemovePath(outputFolder)
        EnsurePath(r'[outputFolder]\Raw') # TODO: Pass in

        if not self.UseResultsFile or not os.path.exists(FilePath):
            folder = os.path.dirname(self.Config.SqlFilePath)
            Run(r'sqlcmd.exe -S [Server] -d [Database] -E -i "%s" -v report_path="[folder]" -v output_folder="[outputFolder]"' % (self.Config.SqlFilePath))
            self.UseResultsFile = True

        rows = []
        xmlDict = xml.ConvertXmlToDict(FilePath)

        baseName = os.path.basename(FilePath)
        columns = self.Config.xml[FilePath]["columns"]
        rows.append(columns)

        for event in xmlDict["Table"]["Event"]:
            row = []
            for column in columns:
                row.append(event[column])
            rows.append(row)

        return rows

    def queryResults(self):
        Trace(self.Config.OutputFolder)
        outputFolder = ExpandPath(self.Config.OutputFolder)

        if not self.UseResultsFile:
            RemovePath(outputFolder)
            EnsurePath(r'[outputFolder]\Raw') # TODO: Pass in

            folder = os.path.dirname(self.Config.SqlFilePath)
            Run(r'sqlcmd.exe -S [Server] -d [Database] -E -i "%s" -v report_path="[folder]" -v output_folder="[outputFolder]"' % (self.Config.SqlFilePath))
            self.UseResultsFile = True

    def extractXml(self, FilePath):
        Trace(FilePath)
        FilePath = ExpandPath(FilePath)
        outputFolder = os.path.dirname(FilePath)
        if not os.path.exists(FilePath):
            Error(r'Missing [FilePath]')

        rows = []
        xmlDict = xml.ConvertXmlToDict(FilePath)
        if not xmlDict["Table"]["Event"] or not len(xmlDict["Table"]["Event"]):
            Error(r'Incorrect XML Schema for [FilePath]')
            return []

        columns = xmlDict["Table"]["Event"][0].keys()
        baseName = os.path.basename(FilePath)

        print(columns)
        for event in xmlDict["Table"]["Event"]:
            row = []
            for item in event.keys():
                print(item)
            for item in event.values():
                print(item)
            Exit()
            for column in columns:
                row.append(event[column])
            rows.append(row)

        return rows

    def createReportFromXml(self):
        Trace()
        reportHtml = self.HtmlTemplate
        self.queryResults()

        outputFolder = ExpandPath(self.Config.OutputFolder)
        xmlFiles = GlobByDate(ExpandPath(r'[outputFolder]\*.xml'))
        if not len(xmlFiles):
            Error(r'Missing XML files: [outputFolder]\*.xml')
            return Expand(r'<H1>Error Missing XML files: [outputFolder]\*.xml</H1>')

        for filePath in xmlFiles:
            print(filePath)
            table = os.path.splitext(os.path.basename(filePath))[0]
            headerHtml = ReportGenerator.HeaderTemplate.replace('[header_html]', table)
            reportHtml = reportHtml.replace('<!-- Insert Table Here -->', headerHtml)

            rows = self.extractXml(filePath)
            table = ListToHtmlTableRows(rows)
            tableHtml = ReportGenerator.TableTemplate.replace('[table_html]', table)
            reportHtml = reportHtml.replace(r'<!-- Insert Table Here -->', tableHtml)
        return reportHtml

    def generateFromXml(self):
        Trace()
        self.ReportHtml = self.createReportFromXml()
        self.emit()
        self.send_email()

    def query(self):
        if self.PreviousResults:
            return self.PreviousResults

        return sqlserver.execute_file(self.SqlFilePath)

    def createReport(self):
        reportHtml = self.HtmlTemplate

        for idx, rows in enumerate(self.Results):

            # Exclude columns from report
            if self.Config.excludeTableColumns and idx < len(self.Config.excludeTableColumns):
                filtered = []
                for row in rows:
                    newRow = []
                    for col, value in enumerate(row, 1):
                        if col not in self.Config.excludeTableColumns[idx]:
                            newRow.append(value)
                    filtered.append(newRow)
                rows = filtered

            tableMetaData = ReportGenerator.getTableMetaData(rows)
            if tableMetaData:
                headerHtml = ReportGenerator.HeaderTemplate.replace('[header_html]', tableMetaData.name)
                reportHtml = reportHtml.replace('<!-- Insert Table Here -->', headerHtml)
            else:
                table = ListToHtmlTableRows(rows)
                tableHtml = ReportGenerator.TableTemplate.replace('[table_html]', table)
                reportHtml = reportHtml.replace(r'<!-- Insert Table Here -->', tableHtml)

        return reportHtml

    def emit(self):
        EnsurePath(os.path.dirname(self.OutputFile))
        fp = open(self.OutputFile, 'w', encoding="utf-8")
        fp.write(self.ReportHtml)
        fp.close()

        if self.ResultsFile:
            EnsurePath(os.path.dirname(self.ResultsFile))
            resultsJson = {
                "Date": Globals.Date,
                "Time": Globals.Time,
                "Report" : self.OutputFile,
                #"results": self.Results,
            }
            JSON.save_to_file(self.ResultsFile, resultsJson)

    def generate(self):
        self.Results = self.query()
        self.ReportHtml = self.createReport()
        self.emit()
        self.send_email()

    def send_email(self):
        email.SendEmailViaPowerShell(
                         To=self.Config.email.To,
                         CC=self.Config.email.CC,
                         Subject=self.Subject,
                         BodyFile = self.OutputFile,
                         BodyAsHtml = True,
                         From=self.Config.email.From,
                         TestMode = False)


    @staticmethod
    def getTableMetaData(rowset):
        if len(rowset) != 2 or len(rowset[0]) == 0 or len(rowset[1]) == 0 or rowset[0][0].lower() != 'table':
            return None

        columns = rowset[0]
        values = rowset[1]

        data = DictN()
        data.name = values[0]

        return data
