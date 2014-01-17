import tkinter as tk
from tkinter import*
from tkinter import messagebox as tkMessageBox
import sys, string, calendar
import time
#import ttk

fnta = ("Times", 10)
fnt = ("Times", 12)
fntc = ("Times", 12, 'bold')

strtitle = "Calendar"
strdays = "Mon  Tue  Wed  Thu  Fri  Sat Sun"
dictmonths = {'1':'Jan', '2':'Feb', '3':'Mar',
              '4':'Apr', '5':'May', '6':'Jun',
              '7':'Jul', '8':'Aug', '9':'Sep',
              '10':'Oct', '11':'Nov', '12':'Dec'}

year = time.localtime()[0]
month = time.localtime()[1]
day = time.localtime()[2]

class tkCalendar :
  def __init__ (self, master, arg_year, arg_month, arg_day, arg_parent_updatable_var):
    self.update_var = arg_parent_updatable_var
    top = self.top = tk.Toplevel(master)
    try:
        self.intmonth = int(arg_month)
    except:
        self.intmonth = int(1)
    self.canvas = tk.Canvas (top, width=200, height=220, relief=tk.RIDGE, background="white", borderwidth=1)
    self.canvas.create_rectangle(0, 0, 303, 30, fill="#a4cae8", width=0)
    self.canvas.create_text(100, 17, text=strtitle, font=fntc, fill="#2024d6")
    stryear = str(arg_year)

    self.year_var = tk.StringVar()
    self.year_var.set(stryear)
    self.lblYear = tk.Label(top, textvariable=self.year_var, font=fnta, background="white")
    self.lblYear.place(x=85, y=30)

    self.month_var = tk.StringVar()
    strnummonth = str(self.intmonth)
    strmonth = dictmonths[strnummonth]
    self.month_var.set(strmonth)

    self.lblYear = tk.Label(top, textvariable=self.month_var, font=fnta, background="white")
    self.lblYear.place(x=85, y=50)
    #Variable muy usada
    tagBaseButton = "Arrow"
    self.tagBaseNumber = "DayButton"
    #draw year arrows
    x, y = 40, 43
    tagThisButton = "leftyear"
    tagFinalThisButton = tuple((tagBaseButton, tagThisButton))
    self.fnCreateLeftArrow(self.canvas, x, y, tagFinalThisButton)
    x, y = 150, 43
    tagThisButton = "rightyear"
    tagFinalThisButton = tuple((tagBaseButton, tagThisButton))
    self.fnCreateRightArrow(self.canvas, x, y, tagFinalThisButton)
    #draw month arrows
    x, y = 40, 63
    tagThisButton = "leftmonth"
    tagFinalThisButton = tuple((tagBaseButton, tagThisButton))
    self.fnCreateLeftArrow(self.canvas, x, y, tagFinalThisButton)
    x, y = 150, 63
    tagThisButton = "rightmonth"
    tagFinalThisButton = tuple((tagBaseButton, tagThisButton))
    self.fnCreateRightArrow(self.canvas, x, y, tagFinalThisButton)
    #Print days
    self.canvas.create_text(100, 90, text=strdays, font=fnta)
    self.canvas.pack (expand=1, fill=tk.BOTH)
    self.canvas.tag_bind ("Arrow", "<ButtonRelease-1>", self.fnClick)
    self.canvas.tag_bind ("Arrow", "<Enter>", self.fnOnMouseOver)
    self.canvas.tag_bind ("Arrow", "<Leave>", self.fnOnMouseOut)
    self.fnFillCalendar()

  def fnCreateRightArrow(self, canv, x, y, strtagname):
    canv.create_polygon(x, y, [[x + 0, y - 5], [x + 10, y - 5] , [x + 10, y - 10] , [x + 20, y + 0], [x + 10, y + 10] , [x + 10, y + 5] , [x + 0, y + 5]], tags=strtagname , fill="blue", width=0)

  def fnCreateLeftArrow(self, canv, x, y, strtagname):
    canv.create_polygon(x, y, [[x + 10, y - 10], [x + 10, y - 5] , [x + 20, y - 5] , [x + 20, y + 5], [x + 10, y + 5] , [x + 10, y + 10] ], tags=strtagname , fill="blue", width=0)

  def fnClick(self, event):
    owntags = self.canvas.gettags(tk.CURRENT)
    if "rightyear" in owntags:
        intyear = int(self.year_var.get())
        intyear += 1
        stryear = str(intyear)
        self.year_var.set(stryear)
    if "leftyear" in owntags:
        intyear = int(self.year_var.get())
        intyear -= 1
        stryear = str(intyear)
        self.year_var.set(stryear)
    if "rightmonth" in owntags:
        if self.intmonth < 12 :
            self.intmonth += 1
            strnummonth = str(self.intmonth)
            strmonth = dictmonths[strnummonth]
            self.month_var.set(strmonth)
        else :
            self.intmonth = 1
            strnummonth = str(self.intmonth)
            strmonth = dictmonths[strnummonth]
            self.month_var.set(strmonth)
            intyear = int(self.year_var.get())
            intyear += 1
            stryear = str(intyear)
            self.year_var.set(stryear)
    if "leftmonth" in owntags:
        if self.intmonth > 1 :
            self.intmonth -= 1
            strnummonth = str(self.intmonth)
            strmonth = dictmonths[strnummonth]
            self.month_var.set(strmonth)
        else :
            self.intmonth = 12
            strnummonth = str(self.intmonth)
            strmonth = dictmonths[strnummonth]
            self.month_var.set(strmonth)
            intyear = int(self.year_var.get())
            intyear -= 1
            stryear = str(intyear)
            self.year_var.set(stryear)
    self.fnFillCalendar()

  def fnFillCalendar(self):
    init_x_pos = 20
    arr_y_pos = [110, 130, 150, 170, 190, 210]
    intposarr = 0
    self.canvas.delete("DayButton")
    self.canvas.update()
    intyear = int(self.year_var.get())
    monthcal = calendar.monthcalendar(intyear, self.intmonth)
    for row in monthcal:
        xpos = init_x_pos
        ypos = arr_y_pos[intposarr]
        for item in row:
            stritem = str(item)
            if stritem == "0":
                xpos += 27
            else :
                tagNumber = tuple((self.tagBaseNumber, stritem))
                self.canvas.create_text(xpos, ypos , text=stritem, font=fnta, tags=tagNumber)
                xpos += 27
        intposarr += 1
    self.canvas.tag_bind ("DayButton", "<ButtonRelease-1>", self.fnClickNumber)
    self.canvas.tag_bind ("DayButton", "<Enter>", self.fnOnMouseOver)
    self.canvas.tag_bind ("DayButton", "<Leave>", self.fnOnMouseOut)

  def fnClickNumber(self, event):
    owntags = self.canvas.gettags(tk.CURRENT)
    for x in owntags:
        if x not in ("current", "DayButton"):
            strdate = (str(self.year_var.get()) + "/" + str(self.month_var.get()) + "/" + str(x))
            self.update_var.set(strdate)
            self.top.withdraw()
            #event.widget.update_idletasks()

  def fnOnMouseOver(self, event):
    self.canvas.move(tk.CURRENT, 1, 1)
    self.canvas.update()

  def fnOnMouseOut(self, event):
    self.canvas.move(tk.CURRENT, -1, -1)
    self.canvas.update()

def dateDis():
    app = Tk()
    app.title('Date Picker')
    app.geometry('400x300+300+400')

    strdate = (str(year) + "/" + dictmonths[str(month)] + "/" + str(day))
    date_var1 = StringVar(app)
    date_var1.set(strdate)

    parent = ()
    tkCalendar(parent, year, month, day, date_var1)

def quitter():
    if tkMessageBox.askokcancel('Verify Exit', 'Are you sure you want to quit?'):
        quit()

def aboutMe():
    tkMessageBox.showinfo('Hello', message='We are the Medical Coding Team!')
    return
