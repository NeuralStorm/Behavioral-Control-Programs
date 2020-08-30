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

import MAPOnlineDecoder 
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

def LoadCellThread():
    Chan_list = ["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51",'Timestamp']
    with nidaqmx.Task() as task, nidaqmx.Task() as taskstart:
        #######################################################
        sheetName = 'CSM001_TILT_SYNCEDLOCAL_72219_LOADCELL'
        #######################################################
        with open(sheetName + '.csv','w+',newline='') as f:
            ###Initialize Channels and Variables
            task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
            ### timing to 1000 Hz
            task.timing.cfg_samp_clk_timing(1000, sample_mode= AcquisitionType.CONTINUOUS)
            ###Start Pulse task
            taskstart.di_channels.add_di_chan("Dev4/port2/line5", line_grouping = LineGrouping.CHAN_PER_LINE )
            taskstart.read(number_of_samples_per_channel=1)
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
            wait_start = True
            ###Wait for Start Pulse
            while wait_start == True:
                ex = taskstart.read(number_of_samples_per_channel=1)
                print(ex)
                if ex == True or ex == [True]:
                    endtiming = 0
                    taskstart.stop()
                    wait_start = False
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


#####################################################################################################################################################################################################################
                                                        #Tilt class beings here
class tiltclass():
    def __init__(self):  
        self.WaterDuration = 0.15
        self.punish  = np.array([0,1,0,0,0,0,0,0], dtype=np.uint8)
        self.reward  = np.array([0,1,1,0,0,0,0,0], dtype=np.uint8)
        self.start1  = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
        self.start3  = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
        self.start4  = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
        self.start6  = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
        self.tilt1   = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
        self.tilt3   = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
        self.tilt4   = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
        self.tilt6   = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
        self.begin   = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        self.wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
        
        #task = Task()
        #task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
        #task.StartTask()
        #task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
        #test  = np.array([0,0,0,0,1,1,1,1], dtype=np.uint8)
        #testall  = np.array([1,1,1,1,1,1,1,1], dtype=np.uint8)
        #pseudo-random generator 1,2,3,4
        #Task is from PyDAQmx

    
    def tilt(self,i,task,taskinterrupt,tilts,psthclass,client,baseline_recording):  
        delay = ((randint(1,100))/100)+1.5      
        #Needs x = choose() as shown below
        if int(tilts[i]) == 1:
            data = self.tilt1
            data2 = self.start1
        elif int(tilts[i]) == 2:
            data = self.tilt3
            data2 = self.start3
        elif int(tilts[i]) == 3:
            data = self.tilt4
            data2 = self.start4
        elif int(tilts[i]) == 4:
            data = self.tilt6
            data2 = self.start6

        #Reduce the timestamps in buffer and wait for pretime to add to buffer.
        res = client.get_ts()
        time.sleep(psthclass.pre_time)
        

    ################################################################################################################################################################################################################        
                                            #Time dependent section. Will include the client and decode here.
        tiltbegintime = time.time()
        tiltwaittime = time.time() - tiltbegintime
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data2,None,None)
        time.sleep(psthclass.post_time)

        # Get accumulated timestamps
        res = client.get_ts()
        # Print information on the data returned
        for t in res: #50ms
            # Print information on spike channel 1
            if t.Type == PL_SingleWFType and t.Channel in psthclass.channel_dict.keys() and t.Unit in psthclass.channel_dict[t.Channel]:
                psthclass.build_unit(t.Channel,t.Unit,t.TimeStamp)
            # Print information on events
            if t.Type == PL_ExtEventType:
                #print(('Event Ts: {}s Ch: {} Type: {}').format(t.TimeStamp, t.Channel, t.Type))
                if t.Channel == 257: #Channel for Strobed Events.
                    psthclass.event(t.TimeStamp, t.Unit)

        psthclass.psth()
        if baseline_recording == False:
            decoderesult = psthclass.decode()
            ####
            if decoderesult == True: #Change statement later for if the decoder is correct.
                taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.reward,None,None)
                task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.wateron,None,None)
                time.sleep(self.WaterDuration)##### water duration --- can keep this
                task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            else: ###This will be if decoder is false, have to deal with punishment tilt.
                taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.punish,None,None) 
                time.sleep(self.WaterDuration)
                taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        print('delay')
        time.sleep(delay) ############################################# delay--- can keep this


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
    # Create instance of API class
    channel_dict = {8: [2], 9: [1,2], 20: [2], 22: [2,3]} #New Format to compare Channel and Unit. 0 is unsorted. Channels are Dict Keys, Units are in each list.
    pre_time = 0.200 #seconds (This value is negative or whatever you put, ex: put 0.200 for -200 ms)
    post_time = 0.200 #seconds
    bin_size = 0.05 #seconds
    baseline_recording = True
    psthclass = PSTH(channel_dict, pre_time, post_time, bin_size)
    tilter = tiltclass()
    if baseline_recording == False:
        psthclass.loadtemplate()
    
    ##Setup for Plexon DO ########### Maybe will use this later?
    # compatible_devices = ['PXI-6224', 'PXI-6259']
    # plexdo = PyPlexDO()
    # doinfo = plexdo.get_digital_output_info()
    # device_number = None
    # for i in range(doinfo.num_devices):
    #     if plexdo.get_device_string(doinfo.device_numbers[i]) in compatible_devices:
    #         device_number = doinfo.device_numbers[i]
    # if device_number == None:
    #     print("No compatible devices found. Exiting.")
    #     sys.exit(1)
    # else:
    #     print("{} found as device {}".format(plexdo.get_device_string(device_number), device_number))
    # res = plexdo.init_device(device_number)
    # if res != 0:
    #     print("Couldn't initialize device. Exiting.")
    #     sys.exit(1)
    # plexdo.clear_all_bits(device_number)
    ##End Setup for Plexon DO
    
    client = PyPlexClientTSAPI()

    # Connect to OmniPlex Server
    client.init_client()

    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    task = Task()
    taskinterrupt = Task()
    data = begin
    task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    taskinterrupt.CreateDOChan("/Dev4/port1/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    taskinterrupt.StartTask()
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
        
##    For Testing
##    tiltstart = Process(target = tilttest, args = '')
##    tiltstart.start()
##    tiltstart.join()
##    LoadCellThread()
##    tiltstart.terminate()
    
    
    
    

    # sensors = Process(target = LoadCellThread, args = '')
    # sensors.start()
    # tic,clk,starttic,start,starttime,running,stoprunning,startpulse,endtime,counter = initialize()
    # loop = traverseSG()
    # endgame = loop.run()
    # print('Sensors started, waiting for Start pulse from Plexon,\n press Enter to begin Tilts after starting Plexon Recording.')
    # while endgame < 2:
    #     endgame = loop.run()


    input('Start Pulse Acquired, Press Enter to begin Tilts')
    
    
    tilts = choose()
    ####################################################################################################################################################
                                                                    #Tilt called here.
    for i in range(0,400):
        try:
            tilter.tilt(i,task,taskinterrupt,tilts,psthclass,client,baseline_recording)
            if endgame < 3:
                endgame = loop.run()
        except KeyboardInterrupt:
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
            print('\nPausing... (Hit ENTER to contrinue, type quit to exit.)')
            try:
                response = input()
                if response == 'quit':
                    # endgame = 3
                    break
                print('Resuming...')
            except:
                pass
            continue
        except TypeError:
            continue
    ######################################################################################################################################################

    # endgame = 3
    # try:
    #     print('Stop Plexon Recording.')
    #     while  endgame < 4:
    #         endgame = loop.waitforend()
            

    # except KeyboardInterrupt:
    #     sensors.terminate()
    #     pass

    task.StopTask()
    taskinterrupt.StopTask()
    sensors.terminate()
    print('Done')


