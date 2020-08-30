# Import H3D specific functions.
#from H3DInterface import *
import nidaqmx
from nidaqmx.constants import *
import time
import threading
from threading import Thread



### Counter class for use later
class Counter(threading.Thread):
    def __init__(self):
        self.taskCO = nidaqmx.Task()
        self.taskCO.co_channels.add_co_pulse_chan_freq("Dev4/ctr0",idle_state = Level.LOW, freq = 1000)
        self.taskCO.start()

    def run(self):
        pass
###

class Clock(threading.Thread):
    #Using  var = Clock()
    #       var.run()
    def __init__(self):
        self.taskclock = nidaqmx.Task()
        self.taskclock.ci_channels.add_ci_count_edges_chan("Dev4/ctr0")
        self.taskclock.start()     
    def run(self):
        clocktime = self.taskclock.read()
        return clocktime
    def end(self):
        self.taskclock.stop()
        

class StartPulse(threading.Thread):
    def __init__(self):
        self.taskstart = nidaqmx.Task()
        self.taskstart.di_channels.add_di_chan("Dev4/port2/line1", line_grouping = LineGrouping.CHAN_PER_LINE)
        self.taskstart.start() 
    def run(self):
        global running
        while running == True:
            starttime = time.time()
            start_pulse = self.taskstart.read(number_of_samples_per_channel = 1)
            if start_pulse == [True]:
                return starttime
    def end(self):
        self.taskstart.stop()

class StopPulse(threading.Thread):
    def __init__(self):
        self.taskstop = nidaqmx.Task()
        self.taskstop.di_channels.add_di_chan("Dev4/port2/line2", line_grouping = LineGrouping.CHAN_PER_LINE)
        self.taskstop.start()

    def run(self):
        global stoprunning
        if stoprunning == True:
            stop_time = time.time()
            stoppulse = self.taskstop.read(number_of_samples_per_channel = 1)
            if stoppulse == [False]:
                stoprunning = False
                return stop_time
        return 0
    def loop(self):
        global stoprunning
        while stoprunning == True:
            stop_time = time.time()
            stoppulse = self.taskstop.read(number_of_samples_per_channel = 1)
            if stoppulse == [False]:
                stoprunning = False
                return stop_time

    def end(self):
        self.taskstop.stop()


def initialize():
    global tic, clk, starttic, start, starttime, running, stoprunning, startpulse, endtime, counter
    #print('Start')
    starttic = time.time()
    start = StartPulse()
    tic = time.time()
    clk = 1
    #clk = Clock()
    #starttimestamp = clk.run()
    starttime = 0
    startpulse = 0
    endtime = 0
    counter = 0
    running = True
    stoprunning = True
    #counter = Counter()

    toc = time.time() - tic
    starttoc = time.time() - starttic
    timedifference = tic - starttic
    #print('Difference', timedifference)
    #print('init toc',toc)
    #print('init starttoc',starttoc)
    return tic,clk,starttic,start,starttime,running,stoprunning,startpulse,endtime,counter

class traverseSG(threading.Thread):
    def __init__(self):
        pass
    def run(self):
        global running, stoprunning, starttic, startpulse,endtime, counter, tic, toc, stop
        if counter < 4:
            if counter == 0:
                #toc = time.time() - tic
                starttoc = time.time() - starttic
                #print('init to traverse 0 toc',toc)
                #print('init to traverse 0 starttoc',starttoc)
                counter = 1
                #print('counter',counter)
                return counter
            elif counter == 1:
                toc = time.time() - tic
                starttoc = time.time() - starttic
                startpulse = start.run()
                #print('traverse 0 to traverse 1 toc',toc)
                #print('traverse 0 to traverse 1 starttoc',starttoc)
                toc = time.time() - tic
                starttoc = time.time() - starttic
                counter = 2
                #print('counter',counter)
                return counter
                
            if running == True:
                if startpulse > 0:
                    #print('traverse 0 to startpulse toc',toc)
                    #print('traverse 0 to startpulse starttoc',starttoc)
                    #print('startpulse time',startpulse)
                    running = False
                    stoprunning = True
                    start.end()
                    #print('timer for start: {}'.format(startpulse))
                    return counter
            if counter ==2 and running ==False:
                stop = StopPulse()
                endtime = stop.run()
                stoprunning = True
                counter =3
                #print('counter',counter)
                #print('stop pulse start')
                return counter 
            elif counter ==3:
                   
                if endtime > 0:
                    #print('timer for start: {}'.format(startpulse))
                    #print('timer for stop: {}'.format(endtime))
                    print('done')
                    stoprunning = False
                    stop.end()
                    counter = 4
                    #print('counter',counter)
                    return counter
                counter = 3
                return counter
                    
    def waitforend(self):
        global endtime, counter, stop
        endtime = stop.loop()
        if endtime > 0:
            #print('timer for start: {}'.format(startpulse))
            #print('timer for stop: {}'.format(endtime))
            #print('done')
            stoprunning = False
            stop.end()
            counter = 4
            #print('counter',counter)
            return counter
            
        

    
    
#For Testing in python, need to comment out from H3DInterface import *
if __name__ == "__main__":
    tic,clk,starttic,start,starttime,running,stoprunning,startpulse,endtime,counter = initialize()
    try:
        loop = traverseSG()
        endgame = loop.run()
        while endgame < 2:
            endgame = loop.run()
        print('started')
        while endgame ==None or endgame <4:
            endgame = loop.run()
    except KeyboardInterrupt:
         pass
    
