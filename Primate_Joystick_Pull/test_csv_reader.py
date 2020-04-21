# test csv reader
import csv
from tkinter import filedialog
from tkinter import *


root = Tk()
root.filename =  filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("jpeg files","*.jpg")))
print (root.filename)


csvreaderdict = {}
with open(root.filename, newline='') as csvfile:
    spamreader = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
    for row in spamreader:
        data = list(spamreader)

for row in range(0,len(data)):
    for entry in range(0,len(data[row])):
        if entry == 0:
            csvreaderdict[data[row][0]] = []
        else:
            csvreaderdict[data[row][0]].append(data[row][entry])

print(csvreaderdict)

csvcheck =['Study ID', 'Session ID', 'Animal ID', 'Number of Events', 'Pre Discriminatory Stimulus Min delta t1',
    'Pre Discriminatory Stimulus Max delta t1', 'Pre Go Cue Min delta t2', 'Pre Go Cue Max delta t2',
    'Pre Reward Delay Min delta t3', 'Pre Reward Delay Max delta t3', 'Use Maximum Reward Time', 'Maximum Reward Time',
    'Enable Time Out', 'Time Out', 'Ranges', 'Max Time After Sound', 'Inter Trial Time',
    'Adaptive Value', 'Adaptive Algorithm', 'Adaptive Frequency', 'Enable Early Pull Time Out',
    'Enable Blooper Noise', 'Active Joystick Channels']
# print('output')
# print(csvreaderdict)

# for label in csvcheck:
RewardClassArgs = []
for i in range(0,len(csvreaderdict['Ranges'])):
    RewardClassArgs.append(float(csvreaderdict['Ranges'][i]))

print(RewardClassArgs)

ActiveChans = []
for k in range(0,len(csvreaderdict['Active Joysick Channels'])):
    ActiveChans.append(int(csvreaderdict['Active Joysick Channels'][k]))