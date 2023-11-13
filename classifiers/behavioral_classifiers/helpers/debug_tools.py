
import time
from threading import Thread
import random

from . import Helper

class DebugSpikeSource:
    def __init__(self, helper: Helper):
        self.stopping = False
        
        def gen_dbg_spikes():
            while not self.stopping:
                now = time.perf_counter()
                helper.spike(
                    channel = random.choice([1, 2, 3]),
                    unit = random.choice([1, 2]),
                    timestamp = now,
                )
                helper.any_event(now)
                time.sleep(random.random() * 0.004)
        self.thread = Thread(target=gen_dbg_spikes)
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *exc):
        self.stopping = True
        self.thread.join(timeout=2)
    
    def start(self):
        self.thread.start()
