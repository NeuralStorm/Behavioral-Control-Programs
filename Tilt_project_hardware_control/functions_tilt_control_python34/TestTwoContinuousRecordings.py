import definitions
from definitions import *
import threading
from threading import Thread
#import numpy as np

class StopThread(threading.Thread):
    def __init__(self):
        self.taskstop = nidaqmx.Task()
        self.taskstop.di_channels.add_di_chan("Dev4/port2/line6", line_grouping = LineGrouping.CHAN_PER_LINE)
        self.taskstop.start()
    def run(self):
        stoppulse = self.taskstop.read(number_of_samples_per_channel = 1)
        return stoppulse
    def end(self):
        self.taskstop.stop()

Chan_list = ["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51",'Timestamp']
with nidaqmx.Task() as task, nidaqmx.Task() as taskstart:
    sheetName = 'TiltLoadCell'
    with open(sheetName + '.csv','w+',newline='') as f:
        ###Initialize Channels and Variables
        task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
        ### timing to 1000 Hz
        task.timing.cfg_samp_clk_timing(1000, sample_mode= AcquisitionType.CONTINUOUS)
        ###
        taskstart.di_channels.add_di_chan("Dev4/port2/line5", line_grouping = LineGrouping.CHAN_PER_LINE )
        taskstart.read(number_of_samples_per_channel=1)
        ###
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
        wait_start = True
        writer = csv.writer(f)
        print('start')
        while wait_start == True:
            ex = taskstart.read(number_of_samples_per_channel=1)
            print(ex)
            if ex == True or ex == [True]:
                endtiming = 0
                wait_start = False
                csvrunlogging = True
                print('start stop thread')
                taskstopthread = StopThread()
                print('open csv')

        writer.writerow(Chan_list)
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
##
    
