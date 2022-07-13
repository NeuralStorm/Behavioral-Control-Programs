
from typing import List, Optional, Any
from multiprocessing import Value, Array, Event
from ctypes import c_bool, c_double, c_size_t
import atexit
from multiprocessing import Process, RLock, Lock
import traceback

def _print_exc(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except:
        print(f"process failed {func.__name__}")
        traceback.print_exc()
        raise

def spawn_process(func, *args, **kwargs) -> Process:
    proc = Process(target=_print_exc, args=[func, *args], kwargs=kwargs)
    atexit.register(proc.terminate)
    proc.start()
    return proc

class Timeout(Exception):
    def __init__(self):
        Exception.__init__(self)

class DigitalLine:
    def __init__(self):
        # self.value = Value(c_bool)
        self._true_event = Event()
        self._false_event = Event()
        self._false_event.set()
    
    def set_true(self):
        self._false_event.clear()
        self._true_event.set()
    
    def set_false(self):
        self._true_event.clear()
        self._false_event.set()
    
    def wait_true(self, timeout=None):
        res = self._true_event.wait(timeout=timeout)
        if res is not True:
            raise Timeout()
    
    def wait_false(self, timeout=None):
        res = self._false_event.wait(timeout=timeout)
        if res is not True:
            raise Timeout()

class AnalogChannel:
    def __init__(self, *, max_len: int, lock: Optional[Lock] = None):
        self._max_len = max_len
        
        if lock is None:
            lock = Lock()
        self._lock = lock
        
        self._buffer = Array(c_double, self._max_len, lock=False)
        self._write_index = Value(c_size_t, lock=False)
        self._full = Value(c_bool, lock=False)
    
    def _write_sample(self, val: float):
        if self._write_index.value == self._max_len:
            self._full.value = True
            self._write_index.value = 0
        self._buffer[self._write_index.value] = val
        self._write_index.value += 1
    
    def write_sample(self, val: float):
        with self._lock:
            self._write_sample(val)
    
    def write_samples(self, vals: List[float]):
        with self._lock:
            for val in vals:
                self._write_sample(val)
    
    def read(self) -> List[float]:
        with self._lock:
            full = self._full.value
            idx = self._write_index.value
            buffer = self._buffer
            # indexing creates a copy of the data as a list
            if full:
                return buffer[idx:] + buffer[:idx]
            return buffer[:idx]
