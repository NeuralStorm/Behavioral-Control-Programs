"""

original format example
{"type": "spike","system_time": 3.5888344, "time": 769.4554, "ignored": null, "relevent": false, "channel": 26, "unit": 1},
{"type": "tilt", "system_time": 3.5888486, "time": 769.450575, "ignored": null, "relevent": true, "tilt_type": 1},

event_type slow left tilt, fast right tilt
event_class enter homezone, start of tilt

"""
from typing import Optional
import json
from pathlib import Path
import time
from contextlib import ExitStack
import gzip
import bz2

class EventsFileWriter:
    def __init__(self, *, file_obj=None, path: Optional[Path]):
        self._stack = ExitStack()
        if path is not None:
            assert file_obj is None
            if path.name.endswith('.gz'):
                self._f = self._stack.enter_context(gzip.open(path, 'at', encoding='utf8', newline='\n'))
            elif path.name.endswith('.bz2'):
                self._f = self._stack.enter_context(bz2.open(path, 'at', encoding='utf8', newline='\n'))
            else:
                self._f = self._stack.enter_context(open(path, 'a', encoding='utf8', newline='\n'))
            # self._f.seek(0, 2) # seek to end of file (append while having in readable mode)
            self._managing_file = True
        elif file_obj is not None:
            self._f = file_obj
            self._managing_file = False
        else:
            raise ValueError()
        
        self._first_event = True
        
        self._f.write('[\n')
    
    def finish(self):
        self._f.write('\n]\n')
        # if self._managing_file:
        #     self._f.close()
        self._stack.close()
    
    def _write_record(self, data):
        if self._first_event:
            self._first_event = False
        else:
            self._f.write(',\n')
        
        json.dump(data, self._f)
    
    def write_raw(self, rec):
        assert 'type' in rec
        assert 'ext_t' in rec
        if 'sys_t' not in rec:
            rec['sys_t'] = time.perf_counter()
        
        if rec['type'] == 'event':
            assert 'event_type' in rec
        if rec['type'] == 'spike':
            assert 'channel' in rec
            assert 'unit' in rec
        
        self._write_record(rec)
    
    def write_event(self, *, event_type: str, timestamp: float, event_class: Optional[str] = None):
        rec = {
            'type': 'event',
            'ext_t': timestamp,
            'event_type': event_type,
        }
        if event_class is not None:
            rec['event_class'] = event_class
        self.write_raw(rec)
    
    def write_spike(self, *, channel: int, unit: int, timestamp: float):
        rec = {
            'type': 'spike',
            'ext_t': timestamp,
            'channel': channel,
            'unit': unit,
        }
        self.write_raw(rec)
