# CSV Writer
import sys, traceback
import os
import os.path
from csv import reader, writer
# class testclass():


metadict = {'Study ID': ['TIP']}
metadict['Session ID'] = ['1']
metadict['Animal ID'] = ['001']
metadict['Number of Events'] = [3]
metadict['Pre Discriminatory Stimulus Min delta t1'] = [0.15]
metadict['Pre Discriminatory Stimulus Max delta t1'] = [0.25]
metadict['Pre Go Cue Min delta t2'] = [0.35]
metadict['Pre Go Cue Max delta t2'] = [0.75]
metadict['Pre Reward Delay Min delta t3'] = [0.020]
metadict['Pre Reward Delay Max delta t3'] = [0.020]
metadict['Use Maximum Reward Time'] = [False]
metadict['Maximum Reward Time'] = [0.18]
metadict['Enable Time Out'] = [False]
metadict['Time Out'] = [0.5]
metadict['Ranges'] = [3,0.5,0.25,0.75,0.5,1,0.75]
metadict['Max Time After Sound'] = [0]
metadict['Inter Trial Time'] = [0]
metadict['Adaptive Value'] = [0.05]
metadict['Adaptive Algorithm'] = [1]
metadict['Adaptive Frequency'] = [50]
metadict['Enable Early Pull Time Out'] = [False]
metadict['Enable Blooper Noise'] = [False]
metadict['Active Joystick Channels'] = [3]


filename = 'csvconfig'
fullfilename = filename + '.csv'
csvtest = True
while csvtest == True:
   check = os.path.isfile(fullfilename)
   while check == True:
       print('File name already exists')
       filename = input('Enter File name: ')
       fullfilename = filename + '.csv'
       check = os.path.isfile(fullfilename)
       csvtest = False
   print('File name not currently used, saving.')
   with open(filename + '.csv', 'w', newline = '') as csvfile:
        csv_writer = writer(csvfile, delimiter = ',')
        # for key in csvdict.keys():
        #     csv_writer.writerow([key]+csvdict[key])
        for key in metadict.keys():
            csv_writer.writerow([key]+metadict[key])
   csvtest = False

