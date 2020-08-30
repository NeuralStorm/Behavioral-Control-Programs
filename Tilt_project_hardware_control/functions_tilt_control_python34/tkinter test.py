import tkinter
from tkinter import *

class Application(Frame):
    def begin(self):
        print("hi there, everyone!")

    def end(self):
        print("check button")

    def createWidgets(self):
        self.Start = Button(self)
        self.Start["text"] = "Start",
        self.Start["command"] = self.begin

        self.Start.pack()
        
        self.QUIT = Button(self)
        self.QUIT["text"] = "QUIT"
        self.QUIT["fg"]   = "red"
        self.QUIT["command"] =  self.quit

        self.QUIT.pack()

        self.Tilt = Checkbutton(self)
        self.Tilt["text"] = "Tilt"
        self.Tilt["command"] = self.end

        self.Tilt.pack()
        

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

root = Tk()
app = Application(master=root)
app.mainloop()
root.destroy()
