#testing threading + tkinter
import tkinter
from tkinter import *
import threading
from threading import *


class TkinterThread(threading.Thread):
    def __init__(self):
        self.root = Tk()
        self.root.geometry("250x250")
        self.lab = Label(self.root, text = "Not Recording")
        self.lab.pack()
        mainloop()
    def updatetext(self):
        self.lab = Label(self.root, text = "Recording")



if __name__ == "__main__":
    test = TkinterThread()

    print('not recording')
    i = 0
    while i < 10:
        i = i + 1

    test.updatetext()
    print('done')
    
        
