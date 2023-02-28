
from typing import Union, List, Tuple, Dict, Any, Optional
from abc import ABC, abstractmethod
import time
from pathlib import Path

class Event(ABC):
    @property
    @abstractmethod
    def timestamp(self):
        raise NotImplementedError()

class Source(ABC):
    @abstractmethod
    def next_event(self) -> Optional[Event]:
        raise NotImplementedError()
    
    @abstractmethod
    def clear(self) -> List[Event]:
        raise NotImplementedError()
    
    def close(self):
        raise NotImplementedError()

class SpikeEvent(Event):
    channel: int
    unit: int
    
    def __init__(self, *, channel, unit, timestamp):
        self.channel = channel
        self.unit = unit
        self._timestamp = timestamp
    
    @property
    def timestamp(self) -> float:
        return self._timestamp

class TiltEvent(Event):
    tilt_type: int
    
    def __init__(self, *, tilt_type, timestamp):
        self.tilt_type = tilt_type
        self._timestamp = timestamp
    
    @property
    def timestamp(self) -> float:
        return self._timestamp

class StimEvent(Event):
    def __init__(self, *, timestamp):
        self._timestamp = timestamp
    
    @property
    def timestamp(self) -> float:
        return self._timestamp

class UnknownEvent(Event):
    channel: int
    unit: int
    
    def __init__(self, *, channel, unit, timestamp):
        self.channel = channel
        self.unit = unit
        self._timestamp = timestamp
    
    @property
    def timestamp(self) -> float:
        return self._timestamp

class MockSource(Source):
    def __init__(self, channel: int, unit: int):
        self.PL_SingleWFType = 0
        self.PL_ExtEventType = 1
        
        self.channel = channel
        self.unit = unit
        
        self.step = 'pending'
    
    def next_event(self):
        # note: pyplexclientts waits 50ms, pyopxclient should wait 5ms
        time.sleep(0.005) # wait 5ms to maybe mimick plexon
        if self.step == 'pending':
            evt = TiltEvent(
                tilt_type = self.unit,
                timestamp = time.perf_counter(),
            )
            
            self.step = 'tilting'
            return evt
        elif self.step == 'tilting':
            evt = SpikeEvent(
                channel = self.channel,
                unit = self.unit,
                timestamp = time.perf_counter(),
            )
            
            return evt
        else:
            assert False
    
    def clear(self):
        self.step = 'pending'
        return []
    
    def close(self):
        pass

class OpxSource(Source):
    def __init__(self):
        from pyopxclient import PyOPXClientAPI, OPX_ERROR_NOERROR, SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, OTHER_TYPE
        self.SPIKE_TYPE = SPIKE_TYPE
        self.EVENT_TYPE = EVENT_TYPE
        
        dll_path = Path(__file__).parent / 'bin'
        self._opx_client = PyOPXClientAPI(opxclient_dll_path=str(dll_path))
        self._opx_client.connect()
        if not self._opx_client.connected:
            msg = "Client isn't connected. Error code: {}".format(self._opx_client.last_result)
            raise RuntimeError(msg)
        
        self._opx_config = self._get_opx_config()
        # self.PL_SingleWFType = 0
        # self.PL_ExtEventType = 1
        
        self._event_queue = []
    
    def _get_opx_config(self):
        client = self._opx_client
        
        spike_source_nums = set()
        event_source_nums = set()
        
        global_parameters = client.get_global_parameters()
        for src_num in global_parameters.source_ids:
            src_info = client.get_source_info(src_num)
            source_name, source_type, num_chans, linear_start_chan = src_info
            
            if source_type == self.SPIKE_TYPE:
                spike_source_nums.add(src_num)
            elif source_type == self.EVENT_TYPE:
                event_source_nums.add(src_num)
        
        return {
            'spike_source_nums': spike_source_nums,
            'event_source_nums': event_source_nums,
        }
    
    def _fetch_events(self):
        self._opx_client.opx_wait(5)
        new_data = self._opx_client.get_new_data()
        
        out = []
        for i, num in enumerate(new_data.source_num_or_type):
            if num in self._opx_config['spike_source_nums']:
                evt = SpikeEvent(
                    channel = new_data.channel[i],
                    unit = new_data.unit[i],
                    timestamp = new_data.timestamp[i],
                )
                out.append(evt)
            elif num in self._opx_config['event_source_nums']:
                # print('plx evt', new_data.channel[i], new_data.unit[i])
                # if new_data.channel[i] == 257:
                chan = new_data.channel[i]
                unit = new_data.unit[i]
                ts = new_data.timestamp[i]
                tilt_type = {
                    25: 1,
                    22: 3,
                    24: 2,
                    21: 4,
                }.get(chan)
                if tilt_type is not None:
                    evt = TiltEvent(
                        # tilt_type = new_data.unit[i],
                        tilt_type = tilt_type,
                        timestamp = ts,
                    )
                elif chan == 20:
                    evt = StimEvent(
                        timestamp = ts,
                    )
                else:
                    evt = UnknownEvent(
                        channel = chan,
                        unit = unit,
                        timestamp = ts,
                    )
                
                out.append(evt)
        
        return out
    
    def next_event(self):
        if not self._event_queue:
            # reverse list so pop() will get earlier events first
            self._event_queue = list(reversed(self._fetch_events()))
        
        if not self._event_queue:
            return None
        
        return self._event_queue.pop()
    
    def clear(self):
        self._event_queue.clear()
        out = []
        while True:
            # res = self._opx_client.get_new_data()
            res = self._fetch_events()
            out.extend(res)
            # continue until less than the max number of events is returned
            if len(res) != self._opx_client.opx_client.max_opx_data:
                break
        
        return out
    
    def close(self):
        self._opx_client.disconnect()

class PyPlexSource(Source):
    def __init__(self):
        from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType, PL_ExtEventType
        dll_path = Path(__file__).parent / 'bin'
        client = PyPlexClientTSAPI(plexclient_dll_path=str(dll_path))
        client.init_client()
        self._PL_SingleWFType = PL_SingleWFType
        self._PL_ExtEventType = PL_ExtEventType
        self._plex_client = client
        
        self._event_queue = []
    
    def _fetch_events(self):
        res = self._plex_client.get_ts()
        out = []
        for plx_evt in res:
            if plx_evt.Type == self._PL_SingleWFType:
                evt = SpikeEvent(
                    channel = plx_evt.Channel,
                    unit = plx_evt.Unit,
                    timestamp = plx_evt.TimeStamp,
                )
                out.append(evt)
            elif plx_evt.Type == self._PL_ExtEventType:
                if plx_evt.Channel == 257:
                    evt = TiltEvent(
                        tilt_type = plx_evt.Unit,
                        timestamp = plx_evt.TimeStamp,
                    )
                    out.append(evt)
        
        return out
    
    def next_event(self):
        if not self._event_queue:
            # reverse list so pop() will get earlier events first
            self._event_queue = list(reversed(self._fetch_events()))
        
        if not self._event_queue:
            return None
        
        return self._event_queue.pop()
    
    def clear(self):
        self._event_queue.clear()
        # may not actually clear all events if there are more than the max batch size
        return self._fetch_events()
    
    def close(self):
        self._plex_client.close_client()
