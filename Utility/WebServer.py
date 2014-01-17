import cgi
import glob
import json
import mimetypes
import os
import string
import sys
import _thread
import time
import urllib.error
import urllib.request
import urllib.parse
from   urllib.parse import parse_qs
from   http.server import BaseHTTPRequestHandler, HTTPServer

from   Utility.Utility import *
if platform.system() == 'Windows':
    import Utility.Win32.Service as Service
else:
    import Utility.OSX.Service as Service
import Utility.Email as email

ExtraMimeTypes = {}
ExtraMimeTypes['json'] = r'application/json'

#-------------------------------------------------------------------------------------
# MyWebServer
#-------------------------------------------------------------------------------------
class MyWebServer(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        try:
            mimetypes.init()
            self.DebugMode = False

            BaseHTTPRequestHandler.__init__(self, request, client_address, server)

        except:
            ReportException()

    def log_message(self, format, *args):
        Log(format % args, UseExpand=False)

    def log_error(self, format, *args):
        Log('Error: ' + format % args, UseExpand=False)

    def do_GET(self):
        self.Debug('GET')
        self.handle_common_actions()

    def do_POST(self):
        self.Debug('POST')
        self.handle_common_actions()

    def do_OPTIONS(self):
        self.Debug('OPTIONS')

        try:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-Type")
            self.send_response(200, "ok")
            self.end_headers()
            # --allow-file-access-from-files

        except Exception as ExObj:
            self.log_error('ERROR OPTIONS failed for %s', self.path)
            self.HandleResponseError("OPTIONS", ExObj)

    def Debug(self, *args, **kwargs):
        if self.DebugMode:
            Log(*args, **kwargs)

    def MapUrlToDataPath(self, Url, Params):

        if 'fileUrl' in Params:
            fileUrl = Params['fileUrl'][0]
            Url = urllib.request.url2pathname(fileUrl)
            return Url

        folder = Url
        folder = folder.strip(r'/')
        folder = folder.strip(r'\\')
        folder = folder.replace(r'/', '.')
        folder = folder.replace(r'\\', '.')
        return ExpandPath(r'[WebDataFileStore]\[folder].json')

    def GetMimeType(self, Url):
        idx = Url.find(r'?')
        if (idx != -1):
            Url = Url[0: idx-1]

        types = mimetypes.guess_type(Url)
        if types and types[0]:
            return types[0]

        ext = "json"
        names = os.path.basename(Url).split(r'.')
        if len(names) > 1:
            ext = names[1]

        if ext in ExtraMimeTypes:
            return ExtraMimeTypes[ext]
        else:
            return "text/plain"

    def handle_common_actions(self):
        try:
            self.url = self.getUrl(self.path)
            self.params = self.getParams(self.path)
            self.dataFilePath = self.MapUrlToDataPath(self.url, self.params)
            self.Debug(r'dataFilePath: [dataFilePath]')

            if os.path.exists(self.url):
                self.LoadFile(self.url)
            elif 'LoadFile' in self.params:
                self.LoadFile(self.dataFilePath)
            elif 'SaveFile' in self.params:
                self.SaveFile(self.dataFilePath)
            elif 'UpdateData' in self.params:
                self.UpdateData(self.dataFilePath)
            elif 'LoadDataFromFiles' in self.params:
                self.LoadDataFromFiles(self.dataFilePath)
            elif 'LoadData' in self.params:
                self.LoadData(self.dataFilePath)
            elif 'SendEmail' in self.params:
                self.SendEmail()
            else:
                self.log_error('ERROR Unhandled url %s', self.path)

                # Send Response
                self.send_header('Content-type',ExtraMimeTypes['json'])
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_response(200)
                self.end_headers()
                self.wfile.write(bytes('{ "Errors" : "Occured" }', 'utf-8'))
        except Exception as ExObj:
            self.HandleResponseError("POST", ExObj)

    def getUrl(self, Url):
        idx = Url.find(r'?')
        if (idx != -1):
            Url = Url[0 : idx - 1]
        if len(Url) > 4 and Url[0] == '/' and Url[2] == ':':
            Url = Url[1:]
        return Url

    def getParams(self, Url):
        params = {}
        idx = self.path.find(r'?')
        if (idx != -1):
            paramsUrl = self.path[idx + 1:]
            params = parse_qs(paramsUrl)

        return params

    def getParam(self, key, default=''):
        value = self.params.get(key, None)
        if value != None:
            return value[0]

        key = key.lower()
        for item in self.params.keys():
            if item.lower() == key:
                return self.params[key][0]
        else:
            return default

    def LoadFile(self, FilePath):
        FilePath = ExpandPath(FilePath)
        body = b''
        if os.path.exists(FilePath):
            file = open(FilePath, 'rb')
            body = file.read()
            file.close()

            self.Debug(r'LoadFile succeeded for: [FilePath]')

        # Send Response
        mimeType = self.GetMimeType(FilePath)
        self.send_header('Content-type', mimeType)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def SaveFile(self, FilePath):
        FilePath = ExpandPath(FilePath)
        DeleteFile(FilePath)

        contentLength = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(contentLength)

        file = open(FilePath, 'wb')
        file.write(body)
        file.close()
        self.Debug(r'SaveFile succeeded for: [FilePath]')

        # Send Response
        self.send_header('Content-type','text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def UpdateData(self, FilePath):
        FilePath = ExpandPath(FilePath)
        args = {}

        # Update data with new values
        # Some servers return multiple Content-Length headers :(
        contentLength = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(contentLength)
        args = json.loads(body.decode('utf-8'))

        data = JSON.update_file(FilePath, args)
        dataString = json.dumps(data, sort_keys=True, indent=4)

        # Send Response
        self.send_header('Content-type',ExtraMimeTypes['json'])
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_response(200)
        self.end_headers()
        if False:
            self.wfile.write(bytes(dataString, 'utf-8'))
        else:
            self.wfile.write(b'OK')

        #backup file
        if Globals.WebDataFileStore2 != Globals.WebDataFileStore:
            filename = os.path.basename(FilePath)
            _thread.start_new_thread(JSON.update_file, (ExpandPath(r'[WebDataFileStore2]\[filename]'), args))

    def LoadData(self, FilePath):
        FilePath = ExpandPath(FilePath)

        data = JSON.load_from_file(FilePath)
        dataString = json.dumps(data, sort_keys=True, indent=4)

        # Send Response
        self.send_header('Content-type',ExtraMimeTypes['json'])
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_response(200)
        self.end_headers()

        self.wfile.write(bytes(dataString, 'utf8'))

    def LoadDataFromFiles(self, Folder):
        Trace(Folder, self.params)
        Folder = ExpandPath(Folder)
        Mask = self.getParam('Mask', '*')

        data = DictN()
        for filePath in FindFilesByDate(Folder, Mask):
            fp = open(filePath, 'r')
            data[filePath] = json.load(fp)
            fp.close()

        dataString = json.dumps(data, sort_keys=False, indent=4)

        # Send Response
        self.send_header('Content-type',ExtraMimeTypes['json'])
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_response(200)
        self.end_headers()

        self.wfile.write(bytes(dataString, 'utf8'))

    def SendEmail(self):

        # Get Send Email data
        contentLength = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(contentLength)
        data = json.loads(body)

        sendEmailFile = Expand(r'[Temp]\WebServer.SendEmail.body.htm')
        self.log_message('SendEmail %s', sendEmailFile)

        file = open(sendEmailFile, 'w')
        file.write(data["body"])
        file.close()

        email.send_email(To=[data["to"]], Subject=data["subject"], Body=data["body"], BodyFile="", Silent=False, Strict=True)

        # Send Response
        self.send_header('Content-type', 'text/plain')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')


    def HandleResponseError(self, Method, ExceptionObj):

        self.log_error('%s Exception : %s', Method, ExceptionObj)
        ReportException()
        return
        try:
            self.send_error(404, lex(r'GET Exception: [path]'))
        except Exception as X:
            self.log_error('%s nested exception in send_error(404): %s', Method, X)

#-------------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------------
def RunWebServer():
    Trace(Globals.WebDataFileStore)
    if not Globals.RunningAsService:
        EnsurePath(Globals.WebDataFileStore)

    try:
        if not Globals.RunningAsService:
            Service.StopService()

        server = HTTPServer(('127.0.0.1', 3000), MyWebServer)
        Log('Listening on port %s for [WebDataFileStore]' % server.server_port)
        server.serve_forever()

    except:
        ReportException()
        if not Globals.RunningAsService:
            print('^C received, shutting down server')
        server.socket.close()
