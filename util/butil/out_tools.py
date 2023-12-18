
import sys
import time
from array import array
from base64 import b85encode
from collections.abc import Callable
from struct import Struct

from .out_file import EventFile

FlushCallback = Callable[[str], None]

class NumChunker:
    def __init__(self, flush_callback: FlushCallback, *, array_type='d'):
        self._empty = array(array_type)
        self._flush_callback = flush_callback
        
        self._last_flush = time.perf_counter()
        self._flush_period = 5
        
        self._buf = bytearray()
        self._packer = Struct('<d')
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self.flush(force=True)
    
    def flush(self, force=False):
        now = time.perf_counter()
        if now - self._last_flush < self._flush_period and not force:
            return
        self._last_flush = now
        
        if not self._buf:
            return
        
        encoded = b85encode(self._buf).decode('ascii')
        self._buf.clear()
        
        self._flush_callback(encoded)
    
    def append(self, x):
        self._buf.extend(self._packer.pack(x))
        self.flush()

class AnalogOut:
    def __init__(self, channel: str, event_file: EventFile):
        self._ts: float | None = None
        def flush(data: str):
            event_file.write_record({
                'type': 'analog',
                'ts': self._ts,
                'channel': channel,
                'samples': data,
            })
            self._ts = None
        self._chunker = NumChunker(flush)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self._chunker.__exit__(*exc)
    
    def append(self, x: float, *, ts: float | None = None):
        if self._ts is None:
            self._ts = ts
        self._chunker.append(x)
