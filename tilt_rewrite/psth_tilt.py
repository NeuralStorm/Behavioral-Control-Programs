
import time
from random import randint

import PyDAQmx
from PyDAQmx import Task
from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType, PL_ExtEventType
import numpy as np

from psth import PSTH as Psth

class PsthTiltPlatform:
    def __init__(self):
        begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        
        self.task = Task()
        
        self.task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
        self.task.StartTask()
        self.begin()
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
        
        task_interrupt = Task()
        task_interrupt.CreateDOChan("/Dev4/port1/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
        task_interrupt.StartTask()
        task_interrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
        self.task_interrupt = task_interrupt
        
        client = PyPlexClientTSAPI()
        client.init_client()
        self.plex_client = client
        _nores = client.get_ts() # ?
        
        channel_dict = {
            1: [1], 2: [1,2], 3: [1,2], 4: [1,2],
            6: [1,2], 7: [1,2,3,4], 8: [1,2,3],
            9: [1,2,3], 13: [1,2,3,4], 14: [1,2],
            20: [1,2,3], 25: [1,2], 26: [1], 27: [1], 28: [1],
            31: [1]
        }
        pre_time = 0.200
        post_time = 0.200
        bin_size = 0.020
        baseline_recording = True
        self.baseline_recording = baseline_recording
        psth = Psth(channel_dict, pre_time, post_time, bin_size)
        if not baseline_recording:
            psth.loadtemplate()
        self.psth = psth
    
    def begin(self):
        begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
    
    def close(self):
        self.task.StopTask()
        self.plex_client.close_client()
        
        self.psth.psthtemplate()
        self.psth.savetemplate()
    
    def tilt(self, tilt_type, water=False):
        water_duration = 0.15
        # tilt_duration = 1.75
        
        tilt1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
        tilt3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
        tilt4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
        tilt6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
        begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
        
        punish  = np.array([0,0,1,0,0,0,0,0], dtype=np.uint8)
        reward  = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
        
        if tilt_type == 1:
            data = tilt1
        elif tilt_type == 2:
            data = tilt3
        elif tilt_type == 3:
            data = tilt4
        elif tilt_type == 4:
            data = tilt6
        else:
            raise ValueError("Invalid tilt type {}".format(tilt_type))
        
        # ?Time dependent section. Will include the client and decode here.
        # ?if tiltbool == False:
        res = self.plex_client.get_ts()
        time.sleep(self.psth.pre_time)
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
        time.sleep(self.psth.post_time)
        time.sleep(0.075)
        
        
        found_event = False
        collected_ts = False
        while found_event == False or collected_ts == False:
            res = self.plex_client.get_ts()
            
            for t in res: # 50ms ?
                if t.Type == PL_SingleWFType \
                    and t.Channel in self.psth.total_channel_dict.keys() \
                    and t.Unit in self.psth.total_channel_dict[t.Channel]:
                    
                    self.psth.build_unit(t.Channel, t.Unit, t.TimeStamp)
                    if found_event and t.TimeStamp >= (self.psth.current_ts + self.psth.post_time):
                        if not collected_ts:
                            collected_ts = True
                            print("collected ts")
                    if t.Type == PL_ExtEventType:
                        if t.Channel == 257 and not found_event:
                            print(('Event Ts: {}s Ch: {} Unit: {}').format(t.TimeStamp, t.Channel, t.Unit))
                            print('event')
                            self.psth.event(t.TimeStamp, t.Unit)
                            found_event = True
        
        print('found event and collected ts')
        # ?if calc_psth == False and collected_ts == True:
        self.psth.psth(True, self.baseline_recording)
        if not self.baseline_recording:
            self.psth.psth(False, self.baseline_recording)
        
        # ?if not self.baseline_recording and found_event and collected_ts:
        if not self.baseline_recording:
            decoder_result = self.psth.decode()
            print("decode")
            
            if decoder_result:
                self.task_interrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,reward,None,None)
                self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
                time.sleep(water_duration)
                self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
                self.task_interrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
            else:
                self.task_interrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,punish,None,None)
                time.sleep(water_duration)
                self.task_interrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
                time.sleep(2)
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        print('delay')
        
        delay = ((randint(1,50))/100)+ 1.5
        time.sleep(delay)
        
        if not self.baseline_recording:
            if decoder_result:
                time.sleep(0.5)
