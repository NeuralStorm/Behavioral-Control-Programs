# Testing strobed pulses
import definitions
from definitions import *
import threading
from threading import Thread
from multiprocessing import *
import numpy as np
import xlwt
import csv
import TestRunwLoadCells
from TestRunwLoadCells import *

class StrobeThread(threading.Thread):
    def __init__(self):
        self.taskstrobe = nidaqmx.Task()
        self.taskstrobe.di_channels.add_di_chan("Dev4/port2/line7", line_grouping = LineGrouping.CHAN_PER_LINE)
        self.taskstrobe.start()
    def run(self):
        strobepulse = self.taskstrobe.read(number_of_samples_per_channel = 1000)
        print('strobe block')
        for i in range(0,len(strobepulse)):
            if strobepulse[i] == True:
                print('True')
        
    def end(self):
        self.taskstrobe.stop()


if __name__ == "__main__":
    strobe = StrobeThread()
    count = 0
    while True:
        strobe.run()
