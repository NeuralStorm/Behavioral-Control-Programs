import tkinter
from tkinter import *
import xlwt

class Application(Frame):
    def begin(self):
        print("hi there, everyone!")
    
    def save(self):
        wb = xlwt.Workbook()
        ws = wb.add_sheet('Sheet 1')
        ws.write(0,0, 1234.56)
        wb.save('example.xls')
        print('Saved')
        
    def one(self):
        if self.var1.get() == 1:
            print("check button 1")

    def two(self):
        if self.var2.get() == 1:
            print("check button 2")

    def createWidgets(self):
        Start = Button(self)
        Start["text"] = "Start",
        Start["command"] = self.begin
        Start.grid(column=0, row=0)
        
        
        QUIT = Button(self)
        QUIT["text"] = "QUIT"
        QUIT["fg"]   = "red"
        QUIT["command"] =  self.quit

        QUIT.grid(column=0, row=4)

        Save = Button(self)
        Save["text"] = "Save"
        Save["command"] = self.save
        Save.grid(column=0, row=3)
        self.var1= IntVar()
                
        CH1 = Checkbutton(self)
        CH1["variable"] = self.var1
        CH1["text"] = "Tilt 1"
        CH1["command"] = self.one

        CH1.grid(column=0, row=1)

        self.var2= IntVar()
        
        CH2 = Checkbutton(self)
        CH2["variable"] = self.var2
        CH2["text"] = "Tilt 2"
        CH2["command"] = self.two

        CH2.grid(column=0, row=2)

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

self = Tk()
self.title("Tilt Platform GUI")
self.geometry('500x350')
app = Application(master=self)
app.mainloop()
self.destroy()
