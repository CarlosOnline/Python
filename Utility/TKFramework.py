import imaplib
import os
import platform
import sys
import tkinter
from tkinter import *
from tkinter import ttk
from tkinter import messagebox

from   Utility.Utility import *
import Utility.Utility

class TKFramework(dict):

    def __init__(self, *args, **kwargs):
        self.root = Tk()

    def create_label(self, id, parent, row, column, value, Anchor=W):
        self.lbl = Label(parent, text=value, anchor=Anchor, justify=LEFT)
        self.lbl.grid(row=row, column=column)

    def create_textbox(self, id, parent, row, column):
        sb = ttk.Scrollbar(orient="vertical")
        text = Text(self.root, width=40, height=20, yscrollcommand=sb.set)
        sb.config(command=text.yview)
        text.grid(row=row, column=column, sticky=(N, E, S, W))
        sb.grid(row=row, column=column + 1, sticky=(N, S, E))
        return text

    def create_listbox(self, id, parent, row, column, callback=None, configure=None, selectMode=BROWSE):
        lb = Listbox(parent, exportselection=0, selectmode=selectMode)
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

    def create_combobox(self, id, parent, row, column, callback=None, configure=None):
        cb = ttk.Combobox(self.root)
        cb.id = id
        self[id] = cb
        if callback:
            cb.bind('<<ComboboxSelected>>', callback)
        if configure:
            cb.bind('<Configure>', configure)
        cb.grid(row=row, column=column, sticky=(N, E, S, W))
        config = self.ux.get(id, None)
        try:
            if config:
                cb.config(**config)
        except:
            pass
        return cb

    def create_radiobuttons(self, id, parent, row, column, values, ids, title, variable, callback=None):
        frame = Frame(parent)
        frame.grid(row=row, column=column, sticky=W)
        lbl = Label(frame, text=title, anchor=W, justify=LEFT)
        lbl.pack(anchor=W)

        for idx, item in enumerate(values, 0):
            text = item
            var = None
            if isinstance(item, StringVar):
                text = item.get()
                var = item
            radio = Radiobutton(frame, text=text, textvariable=var, variable=variable, value=ids[idx], command=callback)
            radio.pack(anchor=W)

class StatusBar(Frame):
    def __init__(self, master, row, column, sticky='EW'):
        Frame.__init__(self, master)
        self.grid(row=row, column=column, sticky=sticky)
        self.label = Label(self, bd=1, relief=SUNKEN, anchor=W, bg='grey')
        self.label.pack(fill=X)

    def set(self, format, *args):
        self.label.config(text=format % args)
        self.label.update_idletasks()

    def clear(self):
        self.label.config(text="")
        self.label.update_idletasks()
