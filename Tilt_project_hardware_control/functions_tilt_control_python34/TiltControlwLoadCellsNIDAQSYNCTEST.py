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
### TO TEST: HOW PAUSE WORKS, CHECK PRINT STATEMENTS ARE CORRECT, WHILE LOOP IS WORKING, EACH TIME.SLEEP IS CHANGED TO A DURATION

##Parameters:0
#Tilt Types: (1, 3, 4, 6)

#make sure that NI-DAQ are not using the lines at the same time, i.e. test panel
#data array for Dev3/port0/line0:7 corresponds to channels going to SI Programmer
#            lines([0,1,2,3,4,5,6,7])
#tilt = np.array([IN3,IN4,IN5/cwjog,IN6/ccwjog(Go_5V),Wait_5V,?,?,?])
# Tilts have been edited to work with Si Tilt Program
#BMITiltProgram6b- from Nate B's work (renamed a copy to TiltControl)

##Load Cells
##Transducer 2 (26922)

class StopThread(threading.Thread):
    def __init__(self):
        self.taskstop = nidaqmx.Task()
        self.taskstop.di_channels.add_di_chan("Dev4/port2/line6", line_grouping = LineGrouping.CHAN_PER_LINE)
        self.taskstop.start()
    def run(self):
        stop_time = time.time()
        stoppulse = self.taskstop.read(number_of_samples_per_channel = 1)
        return stoppulse
    def end(self):
        self.taskstop.stop()

def callbackloop(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
    data = task.read(number_of_samples_per_channel=1000)
    return data

##    task.register_every_n_samples_acquired_into_buffer_event(
##        1000, callbackloop)
    
def LoadCellThread():
    Chan_list = ["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51", "Strobe", "Start", "Inclinometer", 'Timestamp']
    with nidaqmx.Task() as task:
        #######################################################
        sheetName = 'csm015_02162020_sciweek10_loadcell_tilt' #csm015_112019_baseline_tilt_nohaptic_loadcell #'csm015_122419_week4sci_hindlimbtilt_nohaptic_loadcell2'
        #######################################################
        with open(sheetName + '.csv','w+',newline='') as f:
            ###Initialize AI Voltage Channels to record from
            task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
            task.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
            ### Task Sample Clock Timing #/Dev6/PFI7
            task.timing.cfg_samp_clk_timing(1000, source = "", sample_mode= AcquisitionType.CONTINUOUS, samps_per_chan = 1000)
            ### Task DI Start Trigger #/Dev6/PFI8
            task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev6/PFI8", trigger_edge = Edge.RISING)
            ###Initiate Variables
            samples = 1000
            channels = len(Chan_list) - 1
            counter = 0
            ###Collects data and time
            data = [[0 for i in range(samples)] for i in range(channels)]
            tic = round(0,3)
            #toc = round((time.time()-tic),3)
            ###Process time
            ticsamps = np.linspace(tic,(tic+1),samples)
            #ticsamps = np.linspace(toc,(toc+1),samples)
            ticsamps = ticsamps.tolist()
            data.append(ticsamps)
            ###
            total = samples*len(data)
            channelList = np.zeros(total).reshape(len(data),samples)
            running = True
            taskstopthread = StopThread()

            ##############Read and Record Continuous Loop
            writer = csv.writer(f)
            writer.writerow(Chan_list)
            print('Start sort client')
            task.start()
            while running == True:
##                try:
                if counter == 0:
                    data = task.read(samples, -1)
                    tic = round(0,3)
                    counter = counter + 1
                else:
                    print('loop')
                    data = task.read(samples)
##                    data = task.register_every_n_samples_acquired_into_buffer_event(1000, callbackloop)
                    tic = tic + 1.001
                    counter = counter + 1
                ticsamps = np.linspace(tic,(tic+1),samples)
                ticsamps = ticsamps.tolist()
                data.append(ticsamps)
                for key in range(len(data)):
                    for i in range(samples):
                        channelList[key][i] = data[key][i]
                for i in range(samples):
                    row = [item[i] for item in channelList]
                    writer.writerow(row)
                stahp = taskstopthread.run()
                if stahp ==[False]:
                    task.stop()
                    print('writing final samples')
##                except:
##                    print('break')
##                    break
            print('done')
            taskstopthread.end()
            #############End of LoadCells


#def WriteCSV(sensorReadings,sensorLabels,name)
def tilt(i,task,x):
    
###     
    AutoWaterReward = False #Change this to false if you don't want automatic water rewards 
    TTLon = False
    TiltWait = False
    TiltReady = False
    WaterFrequency = 1 #Gives water every # tilts
    WaterDuration = 0.15
    tilt1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
    tilt3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
    tilt4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
    tilt6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
    TiltDuration = 1.75
    #task = Task()
    data = begin
    #task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    #task.StartTask()
    #task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    #test  = np.array([0,0,0,0,1,1,1,1], dtype=np.uint8)
    #testall  = np.array([1,1,1,1,1,1,1,1], dtype=np.uint8)
    #pseudo-random generator 1,2,3,4
    #Task is from PyDAQmx

    ###Need While Loop

        
    #Needs x = choose() as shown below
    if int(x[i]) == 1:
        data = tilt1
    elif int(x[i]) == 2:
        data = tilt3
    elif int(x[i]) == 3:
        data = tilt4
    elif int(x[i]) == 4:
        data = tilt6
    if (int(x[i])<=6):
        print(data)
        print(i)
        print(x[i])
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    time.sleep(1)
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
    delay = ((randint(1,100))/100)+1.5
    time.sleep(TiltDuration) ########################################################## TiltDuration
    if i%WaterFrequency == 0 and AutoWaterReward == True:
        print('Water')
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
        time.sleep(WaterDuration)
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

    time.sleep(delay) ############################################# delay

    #task.StopTask()

###
            
##    except KeyboardInterrupt:
##        try:
##            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
##            print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
##            response = input()
##            if response == 'quit':
##                exit()
##            print('Resuming...')
##        except:
##            pass ##Need to check how the loop starts again after pausing like this. Might be ok?

def choose():
    #No event 2 and 4 for early training
    #because they are the fast tilts and animals take longer to get used to them
    
    a = [1]*100
    a.extend([2]*100)
    a.extend([3]*100)
    a.extend([4]*100)
    np.random.shuffle(a)
    return a

if __name__ == "__main__":
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    task = Task()
    data = begin
    task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    #task.StopTask()
        
    
##    tiltstart = Process(target = tilttest, args = '')
##    tiltstart.start()
##    tiltstart.join()
##    LoadCellThread()
##    tiltstart.terminate()
    
    
    
    

##    sensors = Process(target = LoadCellThread, args = '')
##    sensors.start()
    tic,clk,starttic,start,starttime,running,stoprunning,startpulse,endtime,counter = initialize()
    loop = traverseSG()
    endgame = loop.run()
    print('Sensors started, wait about 5 seconds\n waiting for Start pulse from Plexon,\n press Enter to begin Tilts after starting Plexon Recording.')
    while endgame < 2:
        endgame = loop.run()
    start_time = time.time()
    input('Start Pulse Acquired, Press Enter to begin Tilts')
    
    
    x = choose()
    
    for i in range(0,400):
        try:
            t = tilt(i,task,x)
            if endgame < 3:
                endgame = loop.run()
        except KeyboardInterrupt:
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
            print('\nPausing... (Hit ENTER to contrinue, type quit to exit.)')
            try:
                response = input()
                if response == 'quit':
                    endgame = 3
                    break
                print('Resuming...')
            except:
                pass
            continue
        except TypeError:
            continue
    

    endgame = 3
    try:
        print('Stop Plexon Recording.')
        while  endgame < 4:
            endgame = loop.waitforend()
        stop_time = time.time()
            

    except KeyboardInterrupt:
##        sensors.terminate()
        pass

    task.StopTask()
##    sensors.terminate()
    print('Done')





