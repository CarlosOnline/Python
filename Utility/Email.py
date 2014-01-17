import argparse
import collections
import datetime
import email
import mimetypes
import os
import platform
import re
import smtplib
import sys
import threading
import time

import email
from   email import encoders
from   email.message import Message
from   email.mime.audio import MIMEAudio
from   email.mime.base import MIMEBase
from   email.mime.image import MIMEImage
from   email.mime.multipart import MIMEMultipart
from   email.mime.text import MIMEText

import Utility
from   Utility.Utility import *
if platform.system() == 'Windows':
    import Utility.Win32 as Plat
    import Utility.Win32.Win32Utility as PlatUtility
    import Utility.Win32.ActionService
else:
    import Utility.OSX as Plat
    import Utility.OSX.OSXUtility as PlatUtility
    import Utility.OSX.ActionService

def SendEmailEx(To=[r'[USERNAME]@microsoft.com'], CC=[], Subject='', Body=r'', BodyFile=r'[LogFile]', Attachments=[], MimeType="", Verbose='', Strict=False):
    if not os.path.exists(Globals.SendMailExe):
        Log("Missing [SendMailExe]")

    Body = Body.strip()

    if Verbose:
        Verbose = r'--Verbose'
    if MimeType:
        MimeType = Expand(r'--MimeType "[MimeType]"')

    if not Strict:
        Subject = r'[ProgramName] [Action] %s ([COMPUTERNAME] [SDXROOT])' % (Subject)

    cmdLine = Expand(r'[SendMailExe] --To "%s" --CC "%s" --Subject "[Subject]" --Body "[Body]" --BodyFile="[BodyFile]" --Attachments "%s" [MimeType] [Verbose]' % (','.join(To), ','.join(CC), ','.join(Attachments)))
    Log(cmdLine, Silent=True)
    RunUIApp(cmdLine, '')

def send_email(To=[r'[USERNAME]@microsoft.com'],
                CC=[],
                Subject='',
                Body=r'',
                BodyFile=r'[LogFile]',
                Attachments=[],
                MimeType='text/html',
                From=r'[USERNAME]@microsoft.com',
                Silent=True,
                Strict=False,
                UseService=True,
                TestMode=False):
    Trace(r'[To] [CC] "[Subject]" [BodyFile] [MimeType] [Attachments] UseService=[UseService] TestMode=[TestMode]')

    To = to_list(To)
    CC = to_list(CC)
    Attachments = to_list(Attachments)

    From = Expand(From)
    if not Strict:
        Subject = r'[ProgramName] [Action] %s ([COMPUTERNAME] [SDXROOT])' % (Subject)
    Subject = Expand(Subject)
    Body = Expand(Body)
    BodyFile = ExpandPath(BodyFile)
    To = Expand(email.utils.COMMASPACE.join(To))
    CC = Expand(email.utils.COMMASPACE.join(CC))

    def GetMIME(File, Prefix=''):
        File = ExpandPath(File)
        # Guess the content type based on the file's extension.  Encoding
        # will be ignored, although we should check for simple things like
        # gzip'd or compressed files.
        ctype, encoding = mimetypes.guess_type(File)
        filename, ext = os.path.splitext(File)
        if ext == r'.log':
            ctype = r'text/plain'
        if ctype is None or encoding is not None:
            # No guess could be made, or the file is encoded (compressed), so
            # use a generic bag-of-bits type.
            ctype = 'application/octet-stream'
        maintype, subtype = ctype.split('/', 1)
        Verbose('   MimeType [ctype] for [File]')
        if maintype == 'text':
            fp = open(File)
            # Note: we should handle calculating the charset
            msg = MIMEText(Prefix + fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'image':
            fp = open(File, 'rb')
            msg = MIMEImage(Prefix + fp.read(), _subtype=subtype)
            fp.close()
        elif maintype == 'audio':
            fp = open(File, 'rb')
            msg = MIMEAudio(Prefix + fp.read(), _subtype=subtype)
            fp.close()
        else:
            fp = open(File, 'rb')
            msg = MIMEBase(maintype, subtype)
            msg.set_payload(Prefix + fp.read())
            fp.close()
            # Encode the payload using Base64
            encoders.encode_base64(msg)
        return msg

    msg = MIMEMultipart()
    msg['From'] = From
    msg['To'] = To
    msg['CC'] = CC
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Subject'] = Subject

    if Body and BodyFile:
        maintype, subtype = MimeType.split('/', 1)
        part = MIMEBase(maintype, subtype)
        contents = Body
        if BodyFile:
            if subtype == 'html':
                contents += r'<br/><br/><br/>---------------------------------------------------------<br/><br/><br/>'
            else:
                contents += r'\n\n\n---------------------------------------------------------\n\n\n'
            file = open(BodyFile, 'r')
            bodyFileContents = file.read()
            if subtype == 'html':
                bodyFileContents = bodyFileContents.replace('\r\n', r'<br/>')
                bodyFileContents = bodyFileContents.replace('\n', r'<br/>')
            contents += bodyFileContents
            file.close()
        part.set_payload(contents)
        msg.attach(part)
    elif BodyFile:
        part = GetMIME(BodyFile, Body)
        msg.attach(part)
    elif Body:
        msg.attach(MIMEText(Body))

    for file in Attachments:
        file = ExpandPath(file)
        Verbose('   Attaching [file]')
        if not os.path.exists(file):
            Log('Attachment [file] does not exist')
            continue

        part = GetMIME(file)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
        msg.attach(part)

    PrettyPrintList(list(msg.items()), Verbose=True)
    Verbose("   ('Server', '[SMTPServer]')")
    Log("   " + msg.as_string(), UseExpand=False, Verbose=True)

    if TestMode:
        Log(r'TestMode: skipping send')
        return True

    if UseService and PlatUtility.OpenActionEvent('EmailService', False):
        EnsurePath(Globals.SendMailFolder)
        fp = open(Expand(r'[SendMailFolder]\SendEmail.msg'), r'w')
        fp.write(msg.as_string())
        fp.close()
        msgFile = CopyToUniqueFile(r'[SendMailFolder]\SendEmail.msg', r'[SendMailFolder]')

        msgName = os.path.basename(msgFile)

        emailData = JSON.load_from_file(Globals.SendMailJSON)
        emailData[msgName] = {
            'sender'        : From,
            'recipients'    : To,
            'contents'      : msgFile,
        }
        JSON.save_to_file(Globals.SendMailJSON, emailData)
        Verbose('Email saved for service')
        PrettyPrintDict(emailData[msgName], Verbose=True)
        if PlatUtility.SignalActionEvent('EmailService'):
            return True
        else:
            JSON.delete_key_from_file(Globals.SendMailJSON, msgName)

    Log('Sending email')
    try:
        smtp = smtplib.SMTP(Globals.SMTPServer)
        if Globals.SMTPUserID:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(Globals.SMTPUserID, Password.decode(Globals.SMTPUserID, True))
        smtp.sendmail(From, To, msg.as_string())
        smtp.close()
        Log('Email was sent')
        return True
    except:
        ReportException()
        return False

def SendServiceEmail(EmailData, ID):
    filePath = EmailData['contents']

    if not os.path.exists(filePath):
        Log('Missing contents file [filePath]')
        return

    file = open(filePath)
    contents = file.read()
    file.close()

    Verbose(r'[ID]: Sending email from [filePath]')
    smtp = smtplib.SMTP(Globals.SMTPServer)
    smtp.sendmail(EmailData['sender'], EmailData['recipients'], contents)
    smtp.close()
    Verbose(r'[ID]: Email has been sent')

def SendEmailViaPowerShell(To=[r'[USERNAME]@microsoft.com'],
                CC=[],
                Subject='',
                Body=r'',
                BodyFile=r'',
                Attachments=[],
                From=r'[USERNAME]@microsoft.com',
                BodyAsHtml=True,
                TestMode=False):

    # Send-MailMessage 
    #    [-To] <string[]> 
    #    [-Subject] <string> 
    #    -From <string> 
    #    [[-Body] <string>] 
    #    [[-SmtpServer] <string>] 
    #    [-Attachments <string[]>] 
    #    [-Bcc <string[]>] 
    #    [-BodyAsHtml] 
    #    [-Cc <string[]>] 
    #    [-Credential <PSCredential>] 
    #    [-DeliveryNotificationOption {None | O nSuccess | OnFailure | Delay | Never}] 
    #    [-Encoding <Encoding>] 
    #    [-Priority {Normal | Low | High}] 
    #    [-UseSsl] 
    #    [<CommonParameters>]

    if not isinstance(To, list):
        To = list(To)
    if not isinstance(CC, list):
        CC = list(CC)
    if not isinstance(Attachments, list):
        Attachments = list(Attachments)

    args = [
        Expand('-To """%s"""' % Expand(','.join(To))),
        Expand('-Subject """[Subject]"""'),
        Expand('-From """[From]"""'),
        Expand('-SmtpServer [SMTPServer]'),
    ]

    if Body:
        args.append(Expand('-Body """[body]"""'))

    bodyCmdLine = ''
    if BodyFile:
        bodyCmdLine = '[string] $body = get-content -encoding Unicode """%s""";' % (BodyFile)
        args.append('-Body $body')

    if CC and len(CC):
        args.append(Expand('-Cc """%s"""' % Expand(','.join(CC))))

    if Attachments and len(Attachments):
        args.append(r'-Attachments """%s"""' % ExpandPath(','.join(Attachments)))

    if BodyAsHtml:
        args.append('-BodyAsHtml')

    cmdLine = bodyCmdLine + r' send-mailmessage %s' % ' '.join(args)
    Run(r'powershell.exe -inputformat none -noprofile -noninteractive -ExecutionPolicy ByPass -Command  %s' % cmdLine, UseExpand=False)
    