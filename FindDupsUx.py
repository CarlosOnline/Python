from   Utility.Utility import *
import FindDups as DupUtil
import Utility.HomeUtility as Home
import Utility.Sql as sql
from tkinter import *
from tkinter import ttk

class DuplicateUx(dict):

    def __init__(self):
        self.root = Tk()
        self.folder = ''
        self.folders = []
        self.origs = []
        self.dups = []
        self.idxOriginal = -1
        self.idxDup = -1
        self.json_file = ExpandPath(r'[Temp]\FindDupsUx.json')
        self.ux = JSON.load_from_file(self.json_file)

        self.cbFolders = ttk.Combobox(self.root)
        self.cbFolders.grid(row=0, column=0, sticky='W')
        self.cbFolders.bind('<<ComboboxSelected>>', self.on_folder_cb_select)
        self.cbFolders.state(['readonly'])

        #self.cbFolders = self.create_listbox('lb_folders', self.root, 0, 0, self.on_folder_select)
        self.lbOrig = self.create_listbox('lb_orig', self.root, 1, 0, self.on_original_select)
        self.lbDups = self.create_listbox('lb_dups', self.root, 4, 0, self.on_duplicate_select)
        self.lbDups.bind("<Double-Button-1>", self.on_duplicate_dbl_click)

        # label
        self.lblContents = StringVar()
        self.lbl = Label(self.root, text="Original Path", textvariable=self.lblContents, anchor=W, justify=LEFT, bg='grey')
        self.lbl.grid(row=2, column=0, sticky=(E, W))

        self.btnMakePrimary = Button(self.root, text="Make Primary", command=self.make_primary, state=DISABLED)
        self.btnMakePrimary.grid(row=5, column=0, sticky=W)

        self.root.id = 'root'
        self.root.columnconfigure(0, weight=1)
        self.root.grid_propagate(False)
        config = self.ux.get('root', {'geometry' : '800x500+0+0'})
        self.root.geometry(config['geometry'])
        self.root.bind('<Configure>', self.on_root_configure)

    def run(self):
        if platform.system() == 'Darwin':
            os.system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')

        #self.root.focus_force()
        self.root.lift()
        self.root.mainloop()

    def create_listbox(self, id, parent, row, column, callback=None, configure=None):
        lb = Listbox(parent, exportselection=0)
        lb.id = id
        self[id] = lb
        sb = Scrollbar(parent, orient=VERTICAL)
        lb.configure(yscrollcommand=sb.set)
        sb.configure(command=lb.yview)
        if callback:
            lb.bind('<<ListboxSelect>>', callback)
        if configure:
            lb.bind('<Configure>', configure)
        lb.grid(row=row, column=column, sticky=(N, E, S, W))
        sb.grid(row=row, column=column + 1, sticky=(N, S, E))
        config = self.ux.get(id, None)
        try:
            if config:
                lb.config(**config)
        except:
            pass
        return lb

    def clear(self, Duplicates=True, Originals=True, Folders=False):
        if Folders:
            self.folder = ''
            self.folders = []
            self.cbFolders['values'] = ''
            self.cbFolders.set('No Folders')

        if Originals:
            self.original = []
            self.origs = []
            self.idxOriginal = -1
            self.lbOrig.delete(0, END)
            self.lblContents.set('')

        if Duplicates:
            self.dups = []
            self.idxDup = -1
            self.lbDups.delete(0, END)
            self.btnMakePrimary.config(state=DISABLED)

    def add_folders(self, data):
        self.folders = data
        self.cbFolders['values'] = data
        if len(data):
            self.cbFolders.set(data[0])
            self.on_folder_cb_select()

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

    def on_configure(self, evt):
        Trace(evt, evt.width, evt.height, evt.widget.id)
        config = self.ux.get(evt.widget.id, {})
        config['width'] = evt.width
        config['height'] = evt.height
        self.ux[evt.widget.id] = config
        JSON.save_to_file(self.json_file, self.ux)

    def on_folder_cb_select(self, *args):
        if self.folder == self.cbFolders.get():
            return

        self.clear(Folders=False, Originals=True, Duplicates=True)
        self.folder = self.cbFolders.get()
        self.finder = DupUtil.FindDups(self.folder)

        self.origs = self.finder.GetOriginals(self.folder)
        for row in self.origs:
            self.lbOrig.insert(END, row[1])

        if len(self.origs):
            self.lbOrig.selection_set(0)
            self.lbOrig.activate(0)
            self.on_original_select(dictn({ 'widget' : self.lbOrig }))

    def on_original_select(self, evt):
        w = evt.widget
        idx = int(w.curselection()[0])
        self.lbOrig.see(idx)
        if idx == self.idxOriginal:
            return
        #Trace(idx)

        self.clear(Folders=False, Originals=False, Duplicates=True)
        self.idxOriginal = idx
        self.original = self.origs[idx]
        self.lblContents.set(self.original[1])
        self.dups = self.finder.GetDuplicates(self.original[0])
        for row in self.dups:
            self.lbDups.insert(END, row[1])

        if len(self.dups):
            self.lbDups.selection_set(0)
            self.lbDups.activate(0)
            self.on_duplicate_select(dictn({ 'widget' : self.lbDups }))

    def on_duplicate_select(self, evt):
        self.btnMakePrimary.config(state=NORMAL)

    def on_duplicate_dbl_click(self, evt):
        self.make_primary()

    def make_primary(self):
        idx = int(self.lbDups.curselection()[0])
        #Trace(idx)
        data = self.dups[idx]

        self.finder.ChangeOriginal(self.original[0], data[0])

        # Update listbox
        self.original = data
        self.origs[self.idxOriginal] = self.original
        self.lbOrig.delete(self.idxOriginal)
        self.lbOrig.insert(self.idxOriginal, self.original[1])
        self.lbOrig.selection_set(min(self.idxOriginal + 1, len(self.origs) - 1))
        self.lbOrig.focus_set()

        self.on_original_select(dictn({ 'widget' : self.lbOrig }))
