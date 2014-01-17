import email
import email.utils
import imaplib
import os
import platform
import sys
import tkinter as tkinter

from   Utility.Utility import *
import Utility.Utility

class GMail():
    def __init__(self, userid, pwd='', Prompt=False):
        if not pwd:
            pwd = Password.decode(userid, Prompt=Prompt)
        self.imap = imaplib.IMAP4_SSL('imap.gmail.com')
        self.imap.login(userid, pwd)
        self.inbox = self.imap.select("inbox")  # connect to inbox.
        result, data = self.imap.uid('search', None, "ALL")
        if result != 'OK':
            Error('Failed to connect to gmail [userid] account')

    def get_email(self, uid):
        if not isinstance(uid, str):
            uid = str(uid, 'utf-8')
        result, fetched = self.imap.uid('fetch', uid, '(RFC822)')
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

    def delete_email(self, uid):
        if isinstance(uid, list):
            uid = ','.join(uid)
        Trace(uid)
        self.imap.uid('STORE', uid , '+FLAGS', '(\Deleted)')
        self.imap.expunge()

    def save(self, FilePath=r'[Temp]\Senders.json', ProgressBar=None, callback=None):
        Trace(FilePath, ProgressBar)
        gmail_log_file = ExpandPath(FilePath)

        progress = tkinter.IntVar()

        gmail = dictn()
        gmail.senders = []
        gmail.emails = dictn()
        result, data = self.imap.uid('search', None, "ALL")
        if result != "OK":
            Error('Failed to search')
        uid_list = data[0].split()
        if ProgressBar:
            ProgressBar['maximum'] = len(uid_list)
            ProgressBar['variable'] = progress
        Log('found %d emails' % (len(uid_list)))
        for idx, msg in enumerate(uid_list):
            dbg_print('fetching', idx)
            uid = msg.split()[-1]
            uid = str(uid, 'utf-8')
            if ProgressBar:
                progress.set(idx)
            email_data = self.get_email(uid)
            if len(email_data.keys()) == 0:
                continue

            gmail.emails[uid] = email_data
            sender = email_data.From.strip()
            if sender and sender not in gmail.senders:
                gmail.senders.append(sender)

        uid_len = len(uid_list)
        if ProgressBar:
            ProgressBar['maximum'] = uid_len + len(gmail.senders)
        gmail.sender_emails = dictn()
        for idx, sender in enumerate(gmail.senders):
            dbg_print('processing', idx)
            sender_emails = []
            if ProgressBar:
                progress.set(idx + uid_len)
            for uid, email in gmail.emails.items():
                if email.From == sender:
                    sender_emails.append(email.uid)
            if len(sender_emails):
                gmail.sender_emails[sender] = sender_emails

        JSON.save_to_file(gmail_log_file, gmail)
        Log(r'Log File: [gmail_log_file]')
        if callback:
            callback()
        return gmail

    # '188 (X-GM-LABELS (work "\\\\Important" "\\\\Sent") UID 44662)'
    pattern_uid = re.compile('\d+ \(UID (?P<uid>\d+)\)')
    pattern_label = re.compile('\d+ \(X-GM-LABELS ([\w\\ "]+) (?P<uid>\d+)\)')

    def parse_label(self, data):
        match = GMail.pattern_uid.match(data)
        return match.group('uid')

    def get_labels(self, uid):
        if isinstance(uid, list):
            uid = ','.join(uid)
        Trace(uid)
        result, labels = self.imap.uid('FETCH', uid, '(X-GM-LABELS)')
        if result == 'OK':
            labels = [str(line, 'utf-8') for line in labels]
            return labels

    @staticmethod
    def save_gmail_to_file(user_id, pwd, FilePath, ProgressBar=None):
        Trace()
        gmail = GMail(user_id, pwd)
        return gmail.save(FilePath, ProgressBar)

