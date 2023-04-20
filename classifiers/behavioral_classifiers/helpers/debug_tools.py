
import time
from threading import Thread
import random

from . import Helper

class DebugSpikeSource:
    def __init__(self, helper: Helper):
        self.stopping = False
        
        def gen_dbg_spikes():
            while not self.stopping:
                helper.spike(
                    channel = random.choice([1, 2, 3]),
                    unit = random.choice([1, 2]),
                    timestamp = time.perf_counter(),
                )
                helper.any_event(time.perf_counter())
                time.sleep(random.choice([0.001, 0.004, 0.008]))
        self.thread = Thread(target=gen_dbg_spikes)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *exc):
        self.stopping = True
        self.thread.join(timeout=2)
    
    def start(self):
        self.thread.start()
