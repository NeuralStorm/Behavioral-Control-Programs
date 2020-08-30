#Test_StrobedPulse_Trigger
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
        strobepulse = self.taskstop.read(number_of_samples_per_channel = 1000)
        for i in strobepulse:
            if strobepulse[i] == True:
                print('True')
    def end(self):
        self.taskstrobe.stop()

class StopThread(threading.Thread):
    def __init__(self):
        self.taskstop = nidaqmx.Task()
        self.taskstop.di_channels.add_di_chan("/Dev4/port2/line6", line_grouping = LineGrouping.CHAN_PER_LINE)
        self.taskstop.start()
    def run(self):
        stop_time = time.time()
        stoppulse = self.taskstop.read(number_of_samples_per_channel = 1)
        return stoppulse
    def end(self):
        self.taskstop.stop()

def LoadCellThread():
    Chan_list = ["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51",'Timestamp']
    with nidaqmx.Task() as task, nidaqmx.Task() as taskstart:
        #######################################################
        sheetName = 'triggertest'
        #######################################################

        with open(sheetName + '.csv','w+',newline='') as f:
            ###Initialize Channels and Variables
            task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
            ### timing to 1000 Hz
            task.timing.cfg_samp_clk_timing(1000,source =  "", sample_mode= AcquisitionType.CONTINUOUS)
            print(task.timing.samp_clk_src)
            ###Start Pulse task
            # task.triggers.start_trigger.cfg_dig_edge_start_trig("Dev4/port2/line5",trigger_edge=Edge.RISING)
            
            
            # taskstart.di_channels.add_di_chan("Dev4/port2/line5", line_grouping = LineGrouping.CHAN_PER_LINE )
            # taskstart.triggers.start_trigger.cfg_anlg_edge_start_trig("Dev4/PFI13",trigger_slope=Slope.RISING, trigger_level = 1) 
            taskstart.di_channels.add_di_chan("Dev4/port2/line4", line_grouping = LineGrouping.CHAN_PER_LINE)
            
            taskstart.timing.ai_conv_timebase_src("Dev4/port2/line6")
            
            taskstart.triggers.start_trigger.cfg_dig_edge_start_trig("Dev4/port2/line5", trigger_edge = Edge.RISING) # port2.5 / PFI 13
            
            taskstart.read(number_of_samples_per_channel=1)
            taskstart.export_signals.export_signal(12491,'/Dev6/ao/StartTrigger') # Export signal?
            # Or try using nidaqmx.system.connect_terms(sourceterminal, destinationterminal)


            task.start()
            ###Initiate Variables
            samples = 1000
            channels = len(Chan_list) - 1
            counter = 0
            ###Collects data and time
            data = [[0 for i in range(samples)] for i in range(channels)]
            tic = round(time.time(),3)
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
            writer = csv.writer(f)
            # wait_start = True

            ###Wait for Start Pulse

            # while wait_start == True:
            #     ex = taskstart.read(number_of_samples_per_channel=1)
            #     if ex == True or ex == [True]:
            endtiming = 0
            # taskstart.stop()
            # wait_start = False
            csvrunlogging = True
            print('start stop thread')
            taskstopthread = StopThread()
            print('open csv')





            ##############Read and Record Continuous Loop
            writer = csv.writer(f)
            writer.writerow(Chan_list)
            print('start')
            while running == True:
                data = task.read(samples)
                if counter ==0:
                    tic = round(time.time(),3)
                    counter = counter + 1
                else:
                    tic = tic + 1.001
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
                    running = False
            print('done')
            task.stop()
            taskstopthread.end()
            #############End of LoadCells


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
    print('Sensors started, waiting for Start pulse from Plexon.')
    LoadCellThread()
##    tiltstart.terminate()
    
    
    
    

##    sensors = Process(target = LoadCellThread, args = '')
##    sensors.start()
##    tic,clk,starttic,start,starttime,running,stoprunning,startpulse,endtime,counter = initialize()
##    loop = traverseSG()
##    endgame = loop.run()
##    print('Sensors started, waiting for Start pulse from Plexon.')
##    while endgame < 2:
##        endgame = loop.run()




    task.StopTask()
##    sensors.terminate()
    print('Done')
