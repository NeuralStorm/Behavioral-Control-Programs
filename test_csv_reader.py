# test csv reader
import csv
from tkinter import filedialog
from tkinter import *
def createvar(self,name, value):
    self.name = value


root = Tk()
root.filename =  filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("jpeg files","*.jpg")))
print (root.filename)


csvreaderdict = {}
with open(root.filename, newline='') as csvfile:
    spamreader = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
    for row in spamreader:
        # print(row)
        # print(row[0])
        # print(row[1])
        csvreaderdict[row[0]] = row[1]
        
csvcheck =['Study ID', 'Session ID', 'Animal ID', 'Number of Events', 'Pre Discriminatory Stimulus Min delta t1',
    'Pre Discriminatory Stimulus Max delta t1', 'Pre Go Cue Min delta t2', 'Pre Go Cue Max delta t2',
    'Pre Reward Delay Min delta t3', 'Pre Reward Delay Max delta t3', 'Use Maximum Reward Time', 'Maximum Reward Time',
    'Enable Time Out', 'Time Out', 'Ranges', 'Max Time After Sound', 'Inter Trial Time',
    'Adaptive Value', 'Adaptive Algorithm', 'Adaptive Frequency', 'Enable Early Pull Time Out',
    'Enable Blooper Noise', 'Active Joystick Channels']
print('output')
print(csvreaderdict)
for label in csvcheck:
    print(label)
    print(csvreaderdict[label])
    
