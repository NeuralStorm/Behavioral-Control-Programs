#Test for Tilt Interrupt

import definitions
from definitions import *
import numpy as np
import time
import MAPOnlineDecoder
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
    delay = ((randint(1,100))/100)+1.5 ### 1.5 should be given as a delay time variable
    time.sleep(TiltDuration) ########################################################## TiltDuration
    if i%WaterFrequency == 0 and AutoWaterReward == True:
        print('Water')
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
        time.sleep(WaterDuration)
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

    time.sleep(delay) ############################################# delay

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
    # pre_total_bins = 200 #bins
    # post_total_bins = 200 #bins
    wait_for_timestamps = False
    calculate_PSTH = False
    baseline_recording = False
    psthclass = PSTH(channel_dict, pre_time, post_time, bin_size)
    
    if baseline_recording == False:
        psthclass.loadtemplate()

    
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    tilt1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
    tilt3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
    tilt4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
    tilt6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
    punish = np.array([0,1,0,0,0,0,0,0], dtype=np.uint8) #interrupt
    reward = np.array([0,1,1,0,0,0,0,0], dtype=np.uint8) #interrupt then branch
    task = Task()
    testtask = Task()
    testtask.CreateDOChan("/Dev4/port1/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    data = begin
    task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    testtask.StartTask()
    testtask.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    input('press enter to start')
    print('punish')
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)

    client = PyPlexClientTSAPI()

    # Connect to OmniPlex Server
    client.init_client()

    running = True
    print('running')
    running = True
    timer_list = []
    try:
        while running:
            # Wait half a second for data to accumulate
            if wait_for_timestamps:
                time.sleep(post_time)
                calculate_PSTH = True

            else:
                time.sleep(.5)
            # Get accumulated timestamps
            res = client.get_ts()

            # Print information on the data returned
            
            for t in res:
                # Print information on spike channel 1
                if t.Type == PL_SingleWFType and t.Channel in psthclass.channel_dict.keys() and t.Unit in psthclass.channel_dict[t.Channel]:
                    psthclass.build_unit(t.Channel,t.Unit,t.TimeStamp)
                # Print information on events
                if t.Type == PL_ExtEventType:
                    print(('Event Ts: {}s Ch: {} Type: {}').format(t.TimeStamp, t.Channel, t.Type))
                    if t.Channel == 257: #Channel for Strobed Events.
                        if wait_for_timestamps == False:
                            wait_for_timestamps = psthclass.event(t.TimeStamp, t.Unit)
                        else:
                            psthclass.event(t.TimeStamp,t.Unit)

            if calculate_PSTH == True:
                psthclass.psth()
                if baseline_recording == False:
                    decoderesult = psthclass.decode()

                    if psthclass.current_event == 1:
                        data = tilt1
                    elif psthclass.current_event == 3:
                        data = tilt3
                    elif psthclass.current_event == 4:
                        data = tilt4
                    elif psthclass.current_event == 6:
                        data = tilt6

                    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
                    time.sleep(0.5)
                    if decoderesult == True: #Change statement later for if the decoder is correct.
                        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,reward,None,None)
                        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
                        time.sleep(0.1)##### water duration --- can keep this
                        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
                        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
                    else: ###This will be if decoder is false, have to deal with punishment tilt.
                        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,punish,None,None) 
                        time.sleep(0.1)
                        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
                        time.sleep(2)



                wait_for_timestamps = False
                calculate_PSTH = False



                       

    except KeyboardInterrupt:
        running = False
        
    print('close')
    psthclass.psthtemplate()
    client.close_client()
    psthclass.savetemplate()
    x , y = psthclass.Test(baseline_recording)
    data = begin
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    testtask.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    print('done')
    task.StopTask()
    testtask.StopTask()
