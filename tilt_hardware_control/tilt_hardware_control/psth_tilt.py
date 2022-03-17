
import time
from random import randint
import random
from contextlib import ExitStack, AbstractContextManager
from pathlib import Path

import numpy as np

from psth import PSTH as Psth
from motor_control import MotorControl

class SpikeWaitTimeout(Exception):
    def __init__(self, tilt_rec):
        super().__init__()
        
        self.tilt_rec = tilt_rec
    
    # def __str__(self):
    #     return super().__repr__() + str(self.tilt_rec)

class OpxEvent:
    Channel: int
    Unit: int
    Type: int
    TimeStamp: float

class PsthTiltPlatform(AbstractContextManager):
    def __init__(self, *, 
            baseline_recording: bool,
            save_template: bool = True,
            template_output_path,
            template_in_path,
            channel_dict,
            mock: bool = False,
            pyopx: bool = True,
            reward_enabled: bool,
            ):
        
        self.mock = mock
        self.save_template = save_template
        self.template_output_path = template_output_path
        self.template_in_path = template_in_path
        self.reward_enabled = reward_enabled
        if save_template:
            assert self.template_output_path is not None
        
        self.motor = MotorControl(mock = mock)
        self.motor.tilt('stop')
        
        self.motor_interrupt = MotorControl(port = 1, mock = mock)
        self.motor_interrupt.tilt('stop')
        
        self.pyopx = pyopx
        if mock:
            self.PL_SingleWFType = 0
            self.PL_ExtEventType = 1
            self.plex_client = None
        elif self.pyopx:
            from pyopxclient import PyOPXClientAPI, OPX_ERROR_NOERROR, SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, OTHER_TYPE
            dll_path = Path(__file__).parent / 'bin'
            self.opx_client = PyOPXClientAPI(opxclient_dll_path=dll_path)
            self.opx_client.connect()
            if not self.opx_client.connected:
                msg = "Client isn't connected. Error code: {}".format(self.opx_client.last_result)
                raise RuntimeError(msg)
            
            def _get_opx_config():
                client = self.opx_client
                
                spike_source_nums = set()
                event_source_nums = set()
                
                global_parameters = client.get_global_parameters()
                for src_num in global_parameters.source_ids:
                    src_info = client.get_source_info(src_num)
                    source_name, source_type, num_chans, linear_start_chan = src_info
                    
                    if source_type == SPIKE_TYPE:
                        spike_source_nums.add(src_num)
                    elif source_type == EVENT_TYPE:
                        event_source_nums.add(src_num)
                
                return {
                    'spike_source_nums': spike_source_nums,
                    'event_source_nums': event_source_nums,
                }
            
            self.opx_config = _get_opx_config()
            self.PL_SingleWFType = 0
            self.PL_ExtEventType = 1
        else:
            from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType, PL_ExtEventType
            dll_path = Path(__file__).parent / 'bin'
            client = PyPlexClientTSAPI(plexclient_dll_path=dll_path)
            client.init_client()
            self.PL_SingleWFType = PL_SingleWFType
            self.PL_ExtEventType = PL_ExtEventType
            self.plex_client = client
        
        # channel_dict = {
        #     1: [1], 2: [1,2], 3: [1,2], 4: [1,2],
        #     6: [1,2], 7: [1,2,3,4], 8: [1,2,3],
        #     9: [1,2,3], 13: [1,2,3,4], 14: [1,2],
        #     20: [1,2,3], 25: [1,2], 26: [1], 27: [1], 28: [1],
        #     31: [1],
        #     55: [1,2,3,4],
        # }
        pre_time = 0.0
        post_time = 0.200
        self._post_time = post_time
        bin_size = 0.020
        self.baseline_recording = baseline_recording
        event_num_mapping = {
            1: 1, 2: 2, 3: 3, 4: 4,
            9: 1, 11: 2, 12: 3, 14: 4,
        }
        psth = Psth(channel_dict, pre_time, post_time, bin_size, event_num_mapping=event_num_mapping)
        if not baseline_recording:
            assert template_in_path is not None
        if template_in_path is not None:
            psth.loadtemplate(template_in_path)
        self.psth = psth
        
        self._mock_state = {
            '_get_ts': {
                's': 'pending',
                't': time.perf_counter(),
            }
        }
        
        self.no_spike_wait = False
        # time to wait after tilt event is recieved from plexon
        self.fixed_spike_wait_time = None
        # program fails after this amount of time if tilt isn't recieved from plexon
        self.fixed_spike_wait_timeout = None
        self.closed = False
        self.delay_range = (1.5, 2)
    
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
            if self.pyopx:
                self.opx_client.disconnect()
            else:
                self.plex_client.close_client()
        
        if save_template:
            self.psth.psthtemplate()
            self.psth.savetemplate(self.template_output_path)
    
    def _get_ts(self):
        if self.mock:
            for k, v in self.psth.channel_dict.items():
                if v:
                    channel = k
                    unit = v[0]
                    break
            
            class MockEvent:
                Channel: int
                Unit: int
                Type: int
                TimeStamp: float
            
            time.sleep(0.050) # wait 50ms to maybe mimick plexon
            s = self._mock_state['_get_ts']
            if s['s'] == 'pending':
                e = MockEvent()
                e.Type = self.PL_ExtEventType
                e.Channel = 257
                e.Unit = unit
                e.TimeStamp = time.perf_counter()
                s['s'] = 'tilting'
                return [e]
            elif s['s'] == 'tilting':
                e = MockEvent()
                e.Type = self.PL_SingleWFType
                e.Channel = channel
                e.Unit = unit
                e.TimeStamp = time.perf_counter()
                s['s'] = 'pending'
                return [e]
            else:
                assert False
        elif self.pyopx:
            self.opx_client.opx_wait(50)
            new_data = self.opx_client.get_new_data()
            
            out = []
            for i, num in enumerate(new_data.source_num_or_type):
                if num in self.opx_config['spike_source_nums']:
                    e = OpxEvent()
                    e.Type = self.PL_SingleWFType
                    e.Channel = new_data.channel[i]
                    e.Unit = new_data.unit[i]
                    e.TimeStamp = new_data.timestamp[i]
                    out.append(e)
                elif num in self.opx_config['event_source_nums']:
                    e = OpxEvent()
                    e.Type = self.PL_ExtEventType
                    e.Channel = new_data.channel[i]
                    e.Unit = new_data.unit[i]
                    e.TimeStamp = new_data.timestamp[i]
                    out.append(e)
            
            return out
        else:
            res = self.plex_client.get_ts()
            return res
    
    def tilt(self, tilt_type, water=False, *, sham_result=None, delay=None):
        tilt_record = {
            'system_time': time.perf_counter(),
            'tilt_type': tilt_type,
            'events': [],
            'warnings': [],
            'got_response': None,
            'delay': None,
            'decoder_result': None,
            'decoder_result_source': None,
            'predicted_tilt_type': None,
        }
        def add_event_to_record(event, *, ignored=None, relevent=None):
            rec = {
                'system_time': time.perf_counter(),
                'type': None,
                'ignored': ignored,
                'relevent': relevent,
                'time': event.TimeStamp,
                'channel': event.Channel,
                'unit': event.Unit,
            }
            if event.Type == self.PL_SingleWFType:
                rec['type'] = 'spike'
            elif event.Type == self.PL_ExtEventType:
                rec['type'] = 'tilt'
            else:
                rec['type'] = event.Type
            
            tilt_record['events'].append(rec)
        
        water_duration = 0.15
        punish_duration = 2
        
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
        
        res = self._get_ts()
        for event in res:
            add_event_to_record(event, ignored=True)
        
        self.motor.tilt(tilt_name)
        send_tilt_time = time.time()
        
        
        found_event = False # track if a tilt has started yet
        collected_ts = False
        packets_since_tilt = 0
        tilt_time = None
        tilt_plexon_time = None
        while (found_event == False or collected_ts == False) or self.fixed_spike_wait_time is not None:
            res = self._get_ts()
            if found_event:
                packets_since_tilt += 1
            
            for t in res: # 50ms ?
                is_relevent = None
                if t.Type == self.PL_SingleWFType:
                    is_relevent = self.psth.build_unit(t.Channel, t.Unit, t.TimeStamp)
                    
                    if is_relevent:
                        if self.fixed_spike_wait_time or self.no_spike_wait:
                            collected_ts = True
                        elif tilt_plexon_time is not None and \
                                t.TimeStamp >= tilt_plexon_time + self._post_time:
                            collected_ts = True
                elif t.Type == self.PL_ExtEventType:
                    if t.Channel == 257 and found_event:
                        warn_str = "WARNING: recieved a second tilt event"
                        print(warn_str)
                        tilt_record['warnings'].append(warn_str)
                        is_relevent = False
                    
                    # tilt started
                    if t.Channel == 257 and not found_event:
                        print(('Event Ts: {}s Ch: {} Unit: {}').format(t.TimeStamp, t.Channel, t.Unit))
                        # print('event')
                        self.psth.event(t.TimeStamp, t.Unit)
                        found_event = True
                        is_relevent = True
                        tilt_time = time.time()
                        tilt_plexon_time = t.TimeStamp
                
                add_event_to_record(t, relevent=is_relevent)
            
            if self.no_spike_wait or \
                    (
                        self.fixed_spike_wait_time is not None and
                        tilt_time is not None and
                        time.time() - tilt_time > self.fixed_spike_wait_time
                    ):
                # don't wait for a spike
                if not found_event or not collected_ts:
                    warn_str = "WARNING: no spike events found for trial. THIS SHOULD NOT HAPPEN. TELL DR MOXON"
                    print(warn_str)
                    tilt_record['warnings'].append(warn_str)
                break
            
            if self.fixed_spike_wait_timeout is not None and \
                    (time.time() - send_tilt_time > self.fixed_spike_wait_timeout):
                raise SpikeWaitTimeout(tilt_record)
        
        print('found event and collected ts')
        if tilt_time is not None:
            post_tilt_wait_time = time.time() - tilt_time
        else:
            post_tilt_wait_time = None
        print('post tilt wait time', post_tilt_wait_time, 'send', time.time() - send_tilt_time)
        # print('post send tilt time', time.time() - send_tilt_time)
        
        got_response = found_event and collected_ts
        tilt_record['got_response'] = got_response
        
        if got_response:
            self.psth.psth(True, self.baseline_recording)
            if not self.baseline_recording:
                self.psth.psth(False, self.baseline_recording)
        
        # ?if not self.baseline_recording and found_event and collected_ts:
        if not self.baseline_recording:
            if sham_result is not None:
                decoder_result = sham_result
                d_source = 'sham'
                predicted_tilt_type = None
            elif got_response:
                decoder_result = self.psth.decode()
                d_source = 'psth'
                predicted_tilt_type = self.psth.decoder_list[-1]
            else:
                print("skipping decode due to no spikes")
                decoder_result = True
                d_source = 'no_spikes'
                predicted_tilt_type = None
            
            tilt_record['decoder_result_source'] = d_source
            tilt_record['decoder_result'] = decoder_result
            tilt_record['predicted_tilt_type'] = predicted_tilt_type
            
            print(f"decode {decoder_result}")
            
            if decoder_result:
                if self.reward_enabled:
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
        
        if delay is None:
            delay = random.uniform(*self.delay_range)
        tilt_record['delay'] = delay
        
        self.motor.tilt('stop')
        print(f'delay {delay:.2f}')
        
        time.sleep(delay)
        
        return tilt_record
