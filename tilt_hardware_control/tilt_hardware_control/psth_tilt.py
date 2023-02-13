
from typing import Union, List, Tuple, Dict, Any, Optional, Callable
import time
import random
from contextlib import ExitStack, AbstractContextManager
from pathlib import Path
import json

from classifier import Classifier
from motor_control import MotorControl, SerialMotorOutputWrapper
from util_nidaq import line_wait
from event_source import Event, SpikeEvent, TiltEvent, StimEvent, UnknownEvent
from event_source import Source, MockSource, OpxSource, PyPlexSource
from grf_data import RecordState
from stimulation import TiltStimulation

WAIT_TIMEOUT = 8

class TiltWaitTimeout(Exception):
    pass

class PsthTiltPlatform(AbstractContextManager):
    def __init__(self, *, 
            baseline_recording: bool,
            channel_dict,
            mock: bool = False,
            pyopx: bool = True,
            after_tilt_delay: float,
            collect_events: bool,
            reward_enabled: bool,
            water_duration: float,
            post_time: int,
            delay_range: Tuple[float, float],
            classifier: Optional[Classifier],
            tilt_duration: Optional[float] = None,
            record_state: RecordState,
            stim_handler: Optional[TiltStimulation] = None,
        ):
        """
            Args:
                collect_events: if true events will be collected from plexon
                tilt_duration: if not None assumes the tilt lasts the specified duration
                    instead of waiting for the tilt end signal
            """
        
        self.record_state = record_state
        self.mock = mock
        self.reward_enabled = reward_enabled
        self.after_tilt_delay = after_tilt_delay
        self.collect_events = collect_events
        self.water_duration: float = water_duration
        self.tilt_duration: Optional[float] = tilt_duration
        
        if mock:
            self.motor = MotorControl(mock = mock)
        else:
            self.motor = SerialMotorOutputWrapper()
        
        if not mock and reward_enabled:
            assert not isinstance(self.motor, MotorControl)
            
            import nidaqmx
            from nidaqmx.constants import LineGrouping
            
            self.water_task = nidaqmx.Task()
            self.water_task.do_channels.add_do_chan(f"/Dev6/port1/line4", line_grouping = LineGrouping.CHAN_PER_LINE)
            self.water_task.start()
        else:
            self.water_task = None
        
        self.event_source: Source
        if mock or classifier is None:
            self.event_source = MockSource(1, 1)
        elif pyopx:
            self.event_source = OpxSource()
        else:
            self.event_source = PyPlexSource()
        
        # channel_dict = {
        #     1: [1], 2: [1,2], 3: [1,2], 4: [1,2],
        #     6: [1,2], 7: [1,2,3,4], 8: [1,2,3],
        #     9: [1,2,3], 13: [1,2,3,4], 14: [1,2],
        #     20: [1,2,3], 25: [1,2], 26: [1], 27: [1], 28: [1],
        #     31: [1],
        #     55: [1,2,3,4],
        # }
        # { channel => [Unit] }
        self.channel_dict = channel_dict
        self._post_time = post_time
        self._post_time_ms = post_time / 1000
        self.baseline_recording = baseline_recording
        
        self.classifier: Optional[Classifier] = classifier
        self.stim_handler: Optional[TiltStimulation] = stim_handler
        
        self._tilt_record: Optional[Dict[str, Any]] = None
        
        self.closed: bool = False
        self.delay_range: Tuple[float, float] = delay_range
        
        self.event_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    
    def __exit__(self, *exc):
        self.close()
    
    def close(self):
        if self.closed:
            return
        self.closed = True
        
        self.motor.close()
        self.event_source.close()
        
        if self.water_task is not None:
            self.water_task.close()
    
    def _init_record(self):
        self._tilt_record = {
            'system_time': time.perf_counter(),
            'tilt_name': None,
            'events': [],
            'local_events': [],
            'warnings': [],
            'got_response': None,
            'delay': None,
            'decoder_result': None,
            'decoder_result_source': None,
            'predicted_tilt_type': None,
        }
    
    def _add_event_to_record(self, event: Event, *, ignored=None, relevent=None):
        rec = {
            'type': None,
            'system_time': time.perf_counter(),
            'time': event.timestamp,
            'ignored': ignored,
            'relevent': relevent,
            # 'channel': None,
            # 'unit': None,
            # 'tilt_type': None,
        }
        include_in_record = False
        if isinstance(event, SpikeEvent):
            rec['type'] = 'spike'
            rec['channel'] = event.channel
            rec['unit'] = event.unit
        elif isinstance(event, TiltEvent):
            rec['type'] = 'tilt'
            rec['tilt_type'] = event.tilt_type
            include_in_record = True
        elif isinstance(event, StimEvent):
            rec['type'] = 'stim'
        elif isinstance(event, UnknownEvent):
            rec['type'] = 'unknown'
            rec['channel'] = event.channel
            rec['unit'] = event.unit
        else:
            pass
        
        if include_in_record:
            assert self._tilt_record is not None
            self._tilt_record['events'].append(rec)
        
        if self.event_callback is not None:
            self.event_callback(rec)
    
    def _add_local_event(self, event_type, extra = None):
        if extra is None:
            extra = {}
        rec = {
            'system_time': time.perf_counter(),
            'type': event_type,
            **extra,
        }
        self._tilt_record['local_events'].append(rec)
    
    def _collect_events(self,
        tilt_name: str,
        send_tilt_time: float,
    ):
        """collect events 
            """
        assert self._tilt_record is not None
        assert self.classifier is not None
        
        found_event = False
        collected_ts = False
        
        wait_start_time = time.perf_counter()
        while True:
            evt: Optional[Event] = self.event_source.next_event()
            if evt is not None:
                if isinstance(evt, TiltEvent):
                    tilt_time: float = time.perf_counter()
                    self._add_local_event('recieve_tilt_remote')
                    found_event = True
                    self.classifier.event(tilt_name, evt.timestamp)
                    self._add_event_to_record(evt, relevent=True)
                    break
                self._add_event_to_record(evt, relevent=False)
            if time.perf_counter() - wait_start_time > WAIT_TIMEOUT:
                raise TiltWaitTimeout()
        
        while True:
            evt = self.event_source.next_event()
            
            if evt is not None:
                if isinstance(evt, SpikeEvent):
                    is_relevent = evt.unit in self.channel_dict.get(evt.channel, [])
                    if is_relevent:
                        self.classifier.spike(evt.channel, evt.unit, evt.timestamp)
                        collected_ts = True
                elif isinstance(evt, TiltEvent):
                    warn_str = "WARNING: recieved a second tilt event"
                    print(warn_str)
                    self._tilt_record['warnings'].append(warn_str)
                    is_relevent = False
                else:
                    is_relevent = False
                
                self._add_event_to_record(evt, relevent=is_relevent)
            
            if time.perf_counter() - tilt_time >= self._post_time_ms:
                break
        
        print('found event and collected ts')
        if tilt_time is not None:
            post_tilt_wait_time = time.perf_counter() - tilt_time
        else:
            post_tilt_wait_time = None
        print('post tilt wait time', post_tilt_wait_time, 'send', time.perf_counter() - send_tilt_time)
        # print('post send tilt time', time.time() - send_tilt_time)
        
        got_response = found_event and collected_ts
        self._tilt_record['got_response'] = got_response
        
        return {
            'got_response': got_response,
        }
    
    def tilt(self, *, tilt_name, yoked_prediction=None, delay=None):
        self._init_record()
        tilt_record = self._tilt_record
        add_event_to_record = self._add_event_to_record
        
        def flush_events():
            if self.collect_events:
                res = self.event_source.clear()
                for event in res:
                    add_event_to_record(event, ignored=True)
        
        self._tilt_record['tilt_name'] = tilt_name
        
        if self.classifier is not None:
            self.classifier.clear()
        
        flush_events()
        
        self.motor.tilt(tilt_name)
        send_tilt_time = time.perf_counter()
        self._add_local_event('send_tilt')
        
        if self.collect_events and self.classifier is not None:
            collect_result = self._collect_events(tilt_name, send_tilt_time)
            got_response = collect_result['got_response']
        else:
            if self.tilt_duration is None:
                if not isinstance(self.motor, SerialMotorOutputWrapper):
                    self.record_state.digital_lines['tilt_active'].wait_true(timeout=WAIT_TIMEOUT)
            got_response = False
        
        if not self.baseline_recording:
            if yoked_prediction is not None:
                d_source = 'yoked'
                predicted_tilt_type: str = yoked_prediction
                decoder_result = yoked_prediction == tilt_name
            elif got_response:
                assert self.classifier is not None
                d_source = 'psth'
                predicted_tilt_type = self.classifier.classify()
                decoder_result = predicted_tilt_type == tilt_name
            else:
                assert self.classifier is not None
                print("skipping decode due to no spikes")
                decoder_result = True
                d_source = 'no_spikes'
                predicted_tilt_type = None
            
            if self.stim_handler is not None and predicted_tilt_type is not None:
                self.stim_handler.prediction_made(predicted_tilt_type, tilt_name)
            
            tilt_record['decoder_result_source'] = d_source
            tilt_record['decoder_result'] = decoder_result
            tilt_record['predicted_tilt_type'] = predicted_tilt_type
            
            print(f"decode {decoder_result}")
            
            # if classified correctly stop tilt
            # otherwise switch to punish tilt
            if decoder_result:
                self.motor.tilt_return()
                self._add_local_event('tilt_interrupt_reward')
            else:
                self.motor.tilt_punish()
                self._add_local_event('tilt_interrupt_punish')
        else:
            decoder_result = True
        
        # wait for tilt to finish
        if self.tilt_duration is None:
            if isinstance(self.motor, SerialMotorOutputWrapper):
                tilt_res = self.motor.wait_for_tilt_finish()
                # from pprint import pprint
                # pprint(tilt_res)
            elif not self.mock:
                # line_wait("Dev4/port2/line3", False)
                self.record_state.digital_lines['tilt_active'].wait_false(timeout=WAIT_TIMEOUT)
            self._add_local_event('tilt_finish')
        else:
            # calculate additional time to sleep
            dur_remaining = self.tilt_duration - (time.perf_counter() - send_tilt_time)
            if dur_remaining > 0:
                time.sleep(dur_remaining)
            self._add_local_event('tilt_finish', {
                'fixed_duration': self.tilt_duration,
                'remaining_time': dur_remaining,
            })
        
        time.sleep(self.after_tilt_delay)
        
        if self.reward_enabled and decoder_result:
            # self.motor.water(self.water_duration)
            if self.water_task is not None:
                try:
                    self.water_task.write([True])
                    time.sleep(self.water_duration)
                    self.water_task.write([False])
                finally:
                    self.water_task.write([False])
        
        if delay is None:
            delay = random.uniform(*self.delay_range)
        tilt_record['delay'] = delay
        
        self.motor.tilt('stop')
        # print(f'delay {delay:.2f}')
        
        time.sleep(delay)
        
        flush_events()
        
        self._tilt_record = None
        return tilt_record
