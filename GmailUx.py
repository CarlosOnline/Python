import imaplib
import email
import email.utils
import threading
import tkinter
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

from   Utility.Utility import *
import Utility.HomeUtility as Home
import Utility.Sql as sql
import Utility.GMail as GMail
import Utility.TKFramework as TKFramework
import Utility.tkCalendar as tkCalendar

class GmailUx(TKFramework.TKFramework):

    def __init__(self, gmail_file=r'[Temp]\GMail.json'):
        self.json_file = ExpandPath(r'[Temp]\GmailUx.json')
        Trace(gmail_file, self.json_file)
        self.root = Tk()
        self.imap = None
        self.gmail_file = gmail_file
        self.gmail = JSON.load_from_file(self.gmail_file)
        self.curSender = -1
        self.sender = ''
        self.select_all_emails = True
        self.ux = JSON.load_from_file(self.json_file)

        # *******
        # header
        # *******
        self.header = Frame(self.root, bg='grey')
        self.header.grid(row=0, column=0, sticky='WE')
        lbl = Label(self.header, text="User ID", anchor=W, justify=LEFT)
        lbl.grid(row=1, column=0)

        self.user_id = StringVar()
        self.user_id.set(self.ux.getNode('Login').user_id)
        self.UserID = Entry(self.header, textvariable=self.user_id)
        self.UserID.bind("<Key>", self.on_entry_change)
        self.UserID.grid(row=1, column=1, sticky=W)

        lbl = Label(self.header, text="Password", anchor=W, justify=LEFT)
        lbl.grid(row=1, column=2)

        self.pwd = StringVar()
        if self.user_id.get():
            self.pwd.set(Password.decode(self.user_id.get(), SilentError=True))
        self.Password = Entry(self.header, textvariable=self.pwd, show="*")
        self.Password.grid(row=1, column=3, sticky=W)

        self.btnConnect = Button(self.header, text="Login", command=self.login_gmail, state=NORMAL)
        self.btnConnect.grid(row=1, column=5, sticky=W)

        self.btnRefresh = Button(self.header, text="Refresh", command=self.refresh_gmail, state=NORMAL)
        self.btnRefresh.grid(row=1, column=6, sticky=W)

        self.btnTest = Button(self.header, text="Test", command=self.test, state=NORMAL)
        self.btnTest.grid(row=1, column=7, sticky=W)

        self.progressbar = ttk.Progressbar(self.header, orient=HORIZONTAL, length=200, mode="determinate")
        self.progressbar.grid(row=2, column=0, columnspan=6, sticky='EW')

        # *******
        # BODY
        # *******
        #self.body = Frame(self.root, bg='grey')
        #self.body.grid(row=1, column=0, sticky='WE')
        self.body = self.root

        self.Senders = self.create_listbox('Senders', self.body, 2, 0, self.on_sender_select)
        self.Emails = self.create_listbox('Emails', self.body, 4, 0, self.on_email_select, selectMode=MULTIPLE)

        self.email_select = self.ux.get('email_select', None)
        if not self.email_select:
            self.email_select = dictn()
            self.email_select.year = time.localtime()[0]
            self.email_select.month = time.localtime()[1]
            self.email_select.day = time.localtime()[2]
            self.email_select.date = (str(self.email_select.year) + "/" + tkCalendar.dictmonths[str(self.email_select.month)] + "/" + str(self.email_select.day))
            dt = datetime.datetime(self.email_select.year, self.email_select.month, self.email_select.day)
            self.email_select.dt = dt.strftime('%Y-%m-%d %H:%M:%S')
        self.ux['email_select'] = self.email_select

        # *******
        # Footer
        # *******
        self.footer = Frame(self.root)
        self.footer.grid(row=5, column=0, sticky='EW')
        self.buttonFrame = Frame(self.footer)
        self.buttonFrame.grid(row=0, column=0, sticky='W')
        self.btnDelete = Button(self.buttonFrame, text="Delete", command=self.delete_gmail, state=NORMAL)
        self.btnDelete.grid(row=0, column=0, sticky=W)
        self.btnDate = Button(self.buttonFrame, text="Change Date", command=self.select_date, state=NORMAL)
        self.btnDate.grid(row=1, column=0, sticky=W)
        self.root.bind("<Control-d>", self.delete_gmail)

        self.email_selection_mode = StringVar()
        self.email_selection_mode.set(self.ux.get('email_selection_mode', 'all'))
        self.email_before_select = StringVar()
        self.email_before_select.set('Before %s' % (self.email_select.date))
        select_options = ['All', 'None', self.email_before_select]
        select_ids = ['all', 'none', 'before_date']

        self.email_selection_radio = self.create_radiobuttons('email_selection_radio',
                self.footer,
                0, 1,
                select_options,
                select_ids,
                'Selection Mode:',
                self.email_selection_mode,
                self.on_email_selection_mode_select)

        self.root.grid_rowconfigure(2, weight=1)
        self.root.grid_rowconfigure(4, weight=1)

        self.statusBar = TKFramework.StatusBar(self.root, 99, 0)
        self.statusBar.set('Loading')
        self.add_senders()

    def run(self):
        if platform.system() == 'Darwin':
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

        self.root.id = 'root'
        self.root.columnconfigure(0, weight=1)
        self.root.grid_propagate(False)
        config = self.ux.get('root', {'geometry' : '800x500+0+0'})
        self.root.geometry(config['geometry'])
        self.root.bind('<Configure>', self.on_root_configure)

        #self.root.focus_force()
        self.root.lift()
        self.root.mainloop()

    def clear(self, Duplicates=True, Originals=True, Folders=False):
        self.Senders.delete(0, END)
        self.Emails.delete(0, END)
        self.curSender = -1
        self.sender = ''

    def on_root_configure(self, evt):
        #Trace(evt, evt.type)
        if evt.type == '22':
            config = self.ux.get('root', {'geometry' : '800x500+0+0'})
            new = self.root.geometry()
            old = config['geometry']
            if new == old:
                return
            config['geometry'] = new
            self.ux['root'] = config
            JSON.save_to_file(self.json_file, self.ux)

    def on_sender_select(self, evt):
        try:
            if len(self.gmail.senders) == 0:
                return
            w = evt.widget
            cur_selection = w.curselection()
            if not cur_selection or cur_selection == 0:
                return
            idx = int(cur_selection[0])
            self.Senders.see(idx)
            if self.curSender == idx:
                return
            self.curSender = idx
            self.sender = self.gmail.senders[idx]
            self.add_emails()
        except:
            self.Exception()

    def on_email_select(self, evt):
        try:
            if len(self.gmail.senders) == 0:
                return
            w = evt.widget
            items = map(int, w.curselection())
            for idx in items:
                self.Emails.see(idx)
        except:
            self.Exception()

    def on_entry_change(self, evt):
        try:
            login = {
                "user_id" : self.user_id.get(),
                }
            self.ux['Login'] = login
            JSON.save_to_file(self.json_file, self.ux)
        except:
            self.Exception()

    def on_email_selection_mode_select(self, *args):
        try:
            self.ux['email_selection_mode'] = self.email_selection_mode.get()
            JSON.save_to_file(self.json_file, self.ux)
            self.select_emails()
        except:
            self.Exception()

    def login_gmail(self):
        try:
            self.statusBar.set('Logging In')
            if not self.pwd.get():
                self.Error('Password not specified. Please enter password')
                return

            try:
                self.imap = GMail.GMail(self.user_id.get(), self.pwd.get())
            except:
                self.Error('Failed to login to GMail.  Please re-enter your credentials')
                return
            self.statusBar.set('Login Successful')
        except:
            self.Exception()

    def refresh_gmail(self):
        try:
            Trace()
            self.clear()
            if self.imap == None:
                self.login_gmail()
            if self.imap == None:
                self.Error("Not connected to GMail.  Please login")
                return
            self.statusBar.set('Fetching emails from server.  Slow ...')
            #self.progressbar.start()
            thd = threading.Thread(target=self.imap.save, args=(self.gmail_file, self.progressbar, self.on_refresh_complete))
            thd.start()
        except:
            self.Exception()

    def on_refresh_complete(self):
        try:
            self.progressbar.stop()
            self.gmail = JSON.load_from_file(self.gmail_file)
            self.add_senders()
            self.statusBar.set('Completed fetch of emails')
        except:
            self.Exception()

    def delete_gmail(self, *args):
        try:
            self.statusBar.set('Deleting emails from server')
            if self.imap == None:
                self.login_gmail()
            if self.imap == None:
                self.Error("Not connected to GMail.  Please login")
                return
            if self.curSender == -1 or not self.sender_emails or len(self.sender_emails) == 0:
                self.Error('No messages to delete')
                return

            uidList = []
            items = list(map(int, self.Emails.curselection()))
            if len(items) == 0:
                return
            items.sort()
            items.reverse()
            for idx in items:
                uidList.append(self.sender_emails[idx])
            PrettyPrint(uidList, 'delete')
            self.imap.delete_email(uidList)
            print('completed', items)
            for idx in items:
                self.Emails.delete(idx)
                del self.sender_emails[idx]

            if len(self.sender_emails) == 0:
                self.Senders.delete(self.curSender)
                del self.gmail.senders[self.curSender]
                self.select_sender(min(self.curSender, len(self.gmail.senders)))
            self.statusBar.set('Deleted emails from server')
        except:
            self.Exception()

    def add_senders(self):
        if len(self.gmail.senders) == 0:
            return

        for row in self.gmail.senders:
            self.Senders.insert(END, row)

        if len(self.gmail.senders):
            self.select_sender(0)

        self.statusBar.set('Ready')

    def select_sender(self, idx):
        Trace(idx)
        self.curSender = -1
        self.sender = ''
        self.Senders.selection_set(idx)
        self.Senders.activate(idx)
        self.on_sender_select(dictn({ 'widget' : self.Senders }))

    def add_emails(self):
        self.Emails.delete(0, END)
        if self.sender not in self.gmail.sender_emails:
            self.Error('Missing emails for sender: %s' % self.sender)
            self.curSender = -1
            self.sender = None
            return

        self.sender_emails = self.gmail.sender_emails[self.sender]

        for uid in self.sender_emails:
            email = self.gmail.emails[uid]
            self.Emails.insert(END, "#%s %s %s" % (uid, email['Date'], email['Subject']))

        self.select_emails()

    def select_emails(self):
        mode = self.email_selection_mode.get()
        if mode == 'all':
            self.Emails.selection_set(0, END)
            self.Emails.activate(0)
        elif mode == 'none':
            self.Emails.selection_clear(0, END)
        elif mode == 'before_date':
            cur_dt = datetime.datetime.strptime(self.email_select.dt, '%Y-%m-%d %H:%M:%S')
            for idx, uid in enumerate(self.sender_emails):
                msg = self.gmail.emails[uid]
                tt = email.utils.parsedate_tz(msg['Date'])
                dt = datetime.datetime(tt[0], tt[1], tt[2])
                if dt < cur_dt:
                    self.Emails.selection_set(idx)
        self.on_email_select(dictn({ 'widget' : self.Emails }))

    def select_date(self):
        date_var1 = StringVar(self.root)
        date_var1.set(self.email_select.date)
        date_var1.trace("w", lambda nm, idx, mode, var=date_var1: self.on_date_selected(var.get()))
        tkCalendar.tkCalendar(self.root, self.email_select.year, self.email_select.month, self.email_select.day, date_var1)

    def on_date_selected(self, new_date):
        Trace(new_date)
        self.email_select.date = new_date
        self.email_select.year, self.email_select.month, self.email_select.day = new_date.split('/')
        month = 0
        for key, value in tkCalendar.dictmonths.items():
            if value == self.email_select.month:
                self.email_select.month = int(key)
        dt = datetime.datetime(int(self.email_select.year), int(self.email_select.month), int(self.email_select.day))
        self.email_select.dt = dt.strftime('%Y-%m-%d %H:%M:%S')
        self.email_before_select.set('Before %s' % (new_date))
        self.ux.email_select = self.email_select
        JSON.save_to_file(self.json_file, self.ux)

    def Error(self, Message):
        self.statusBar.set('Error: ' + Message)
        messagebox.showinfo("Error", Message)

    def Exception(self):
        ReportException()
        exception_info = sys.exc_info()
        exType, message, tbObject = exception_info
        message = str(message)
        self.Error('Exception: ' + message)

    def test(self, *args):
        try:
            if self.imap == None:
                self.login_gmail()
            if self.imap == None:
                self.Error("Not connected to GMail.  Please login")
                return
            uidList = []
            items = list(map(int, self.Emails.curselection()))
            if len(items) == 0:
                return
            items.sort()
            items.reverse()
            for idx in items:
                uidList.append(self.sender_emails[idx])
            labels = self.imap.get_labels(uidList)
            for item in labels:
                print(item[2])
        except:
            self.Exception()

