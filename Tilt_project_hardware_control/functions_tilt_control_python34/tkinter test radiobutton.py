from tkinter import *
import tkinter

top = Tk()

lb = Listbox(top)
lb.insert(1, "Python")
lb.insert(2, "Perl")
lb.insert(3, "C")

lb.pack()
top.mainloop()
