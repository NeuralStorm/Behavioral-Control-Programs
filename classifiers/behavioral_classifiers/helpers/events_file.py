"""

original format example
{"type": "spike","system_time": 3.5888344, "time": 769.4554, "ignored": null, "relevent": false, "channel": 26, "unit": 1},
{"type": "tilt", "system_time": 3.5888486, "time": 769.450575, "ignored": null, "relevent": true, "tilt_type": 1},

event_type slow left tilt, fast right tilt
event_class enter homezone, start of tilt

"""
from typing import Optional, Any
import time
from contextlib import ExitStack
from array import array
from struct import Struct
from base64 import b85encode
import sys
import logging

logger = logging.getLogger(__name__)

EMPTY = array('d')

class EventsFileWriter:
    def __init__(self, *, callback: Any = None):
        self._stack = ExitStack()
        
        self._callback = callback
        
        self._last_spike_write = time.perf_counter()
        self._ts = {}
        self._events = {}
        
        self._packer = Struct('<d')
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self.flush_ts(force=True)
        self._stack.__exit__(*exc)
    
    def finish(self):
        self._stack.close()
    
    def _get_buf(self, key, *, events=False):
        if events:
            m = self._events
        else:
            m = self._ts
        
        try:
            buf = m[key]
        except KeyError:
            buf = bytearray()
            m[key] = buf
        return buf
    
    def _write_record(self, data):
        if self._callback is not None:
            self._callback(data)
    
    def flush_ts(self, force=False):
        now = time.perf_counter()
        if now - self._last_spike_write < 5 and not force:
            return
        else:
            self._last_spike_write = now
        
        out = {}
        for chan, buf in self._ts.items():
            if not buf:
                continue
            out[chan] = b85encode(buf).decode('ascii')
            buf.clear()
        if not out:
            return
        out = { 'type': 'spikes', 's': out }
        self._write_record(out)
    
    def write_event(self, *, event_type: str, timestamp: float, event_class: Optional[str] = None):
        rec = {
            'type': 'classification_event',
            'ext_t': timestamp,
            'event_type': event_type,
        }
        if event_class is not None:
            rec['event_class'] = event_class
        self._write_record(rec)
    
    def write_spike(self, *, channel: str, timestamp: float):
        buf = self._get_buf(f'{channel}')
        
        buf.extend(self._packer.pack(timestamp))
        
        self.flush_ts()
