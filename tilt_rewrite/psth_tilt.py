
import time
from random import randint
from contextlib import ExitStack, AbstractContextManager

import numpy as np

from psth import PSTH as Psth
from motor_control import MotorControl

class PsthTiltPlatform(AbstractContextManager):
    def __init__(self, *, 
            baseline_recording: bool,
            save_template: bool = True,
            template_output_path,
            template_in_path,
            mock: bool = False,
            ):
        
        self.mock = mock
        self.save_template = save_template
        self.template_output_path = template_output_path
        self.template_in_path = template_in_path
        if save_template:
            assert self.template_output_path is not None
        
        self.motor = MotorControl(mock = mock)
        self.motor.tilt('stop')
        
        self.motor_interrupt = MotorControl(port = 1, mock = mock)
        self.motor_interrupt.tilt('stop')
        
        if mock:
            self.PL_SingleWFType = 0
            self.PL_ExtEventType = 0
            self.plex_client = None
        else:
            from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType, PL_ExtEventType
            client = PyPlexClientTSAPI()
            client.init_client()
            self.PL_SingleWFType = PL_SingleWFType
            self.PL_ExtEventType = PL_ExtEventType
            self.plex_client = client
        _nores = self._get_ts() # ?
        
        channel_dict = {
            1: [1], 2: [1,2], 3: [1,2], 4: [1,2],
            6: [1,2], 7: [1,2,3,4], 8: [1,2,3],
            9: [1,2,3], 13: [1,2,3,4], 14: [1,2],
            20: [1,2,3], 25: [1,2], 26: [1], 27: [1], 28: [1],
            31: [1],
            55: [1,2,3,4],
        }
        pre_time = 0.0
        post_time = 0.200
        bin_size = 0.020
        self.baseline_recording = baseline_recording
        psth = Psth(channel_dict, pre_time, post_time, bin_size)
        if not baseline_recording:
            assert template_in_path is not None
        if template_in_path is not None:
            psth.loadtemplate(template_in_path)
        self.psth = psth
        
        if mock:
            # self.psth.event(10, 1)
            # for v in channel_dict.values():
            #     for c in v:
            #         for i in range(0, 1000, 10):
            #             self.psth.event(i, c)
            
            for t in range(10, 21, 10):
                self.psth.event(t, 1)
                for chan, units in channel_dict.items():
                    # chan, units = next(iter(channel_dict.items()))
                    # chan = 55
                    # units = [1]
                    # self.psth.build_unit(chan, units[0], t-2)
                    # self.psth.event(t, units[0])
                    # self.psth.event(t+2, units[0])
                    self.psth.build_unit(chan, units[0], t+2)
                    self.psth.build_unit(chan, units[0], t+6)
                    
                    self.psth.psth(True, self.baseline_recording)
                    if not self.baseline_recording:
                        self.psth.psth(False, self.baseline_recording)
                        
                        self.psth.decode()
                    for unit in units:
                        # self.psth.event(t, unit)
                        # self.psth.build_unit(chan, unit, t)
                        pass
        
        self.no_spike_wait = False
        self.closed = False
    
    def __exit__(self, *exc):
        self.close()
    
    def close(self, *, save_template=None):
        if self.closed == True:
            return
        self.closed = True
        
        if save_template is None:
            save_template = self.save_template
        self.motor.close()
        self.motor_interrupt.close()
        if not self.mock:
            self.plex_client.close_client()
        
        if save_template:
            self.psth.psthtemplate()
            self.psth.savetemplate(self.template_output_path)
    
    def _get_ts(self):
        if self.mock:
            return []
        else:
            res = self.plex_client.get_ts()
            return res
    
    def tilt(self, tilt_type, water=False, *, sham_result=None):
        water_duration = 0.15
        punish_duration = 2
        # tilt_duration = 1.75
        
        if tilt_type == 1:
            # data = tilt1
            tilt_name = 'a'
        elif tilt_type == 2:
            # data = tilt3
            tilt_name = 'b'
        elif tilt_type == 3:
            # data = tilt4
            tilt_name = 'c'
        elif tilt_type == 4:
            # data = tilt6
            tilt_name = 'd'
        else:
            raise ValueError("Invalid tilt type {}".format(tilt_type))
        
        # ?Time dependent section. Will include the client and decode here.
        # ?if tiltbool == False:
        res = self._get_ts()
        time.sleep(self.psth.pre_time)
        self.motor.tilt(tilt_name)
        time.sleep(self.psth.post_time)
        # time.sleep(0.075)
        
        
        found_event = False
        collected_ts = False
        while found_event == False or collected_ts == False:
            res = self._get_ts()
            
            for t in res: # 50ms ?
                if t.Type == self.PL_SingleWFType: #\
                    # and t.Channel in self.psth.total_channel_dict.keys() \
                    # and t.Unit in self.psth.total_channel_dict[t.Channel]:
                    
                    is_relevent_channel = self.psth.build_unit(t.Channel, t.Unit, t.TimeStamp)
                    if is_relevent_channel:
                        collected_ts = True
                        print("collected ts")
                        # if found_event and t.TimeStamp >= (self.psth.current_ts + self.psth.post_time):
                        #     if not collected_ts:
                        #         collected_ts = True
                        #         print("collected ts")
                if t.Type == self.PL_ExtEventType:
                    if t.Channel == 257 and not found_event:
                        print(('Event Ts: {}s Ch: {} Unit: {}').format(t.TimeStamp, t.Channel, t.Unit))
                        print('event')
                        self.psth.event(t.TimeStamp, t.Unit)
                        found_event = True
            
            if self.no_spike_wait:
                # don't wait for a spike
                if not found_event or not collected_ts:
                    print("WARNING: no spike events found for trial. THIS SHOULD NOT HAPPEN. TELL DR MOXON")
                break
        
        print('found event and collected ts')
        # ?if calc_psth == False and collected_ts == True:
        if collected_ts == True:
            self.psth.psth(True, self.baseline_recording)
            if not self.baseline_recording:
                self.psth.psth(False, self.baseline_recording)
        
        # ?if not self.baseline_recording and found_event and collected_ts:
        if not self.baseline_recording:
            if sham_result is not None:
                decoder_result = sham_result
            else:
                decoder_result = self.psth.decode()
            print("decode")
            
            if decoder_result:
                self.motor_interrupt.tilt('reward')
                self.motor.tilt('wateron')
                time.sleep(water_duration)
                self.motor.tilt('stop')
                self.motor_interrupt.tilt('stop')
            else:
                self.motor_interrupt.tilt('punish')
                time.sleep(punish_duration)
                self.motor_interrupt.tilt('stop')
                # time.sleep(2)
        
        delay = ((randint(1,50))/100)+ 1.5
        
        # if sham_result is not None:
        #     self.motor.tilt('stop')
        #     print('delay (sham)')
        #     time.sleep(delay)
        # if not self.baseline_recording and sham_result is True:
        #     time.sleep(0.5)
        
        self.motor.tilt('stop')
        print('delay')
        
        time.sleep(delay)
        
        # if not self.baseline_recording:
        #     if decoder_result:
        #         time.sleep(0.5)
