
from typing import Optional
import time
import statistics
import logging
from collections import deque

logger = logging.getLogger(__name__)
debug = logger.debug

class Edge:
    rising = False
    falling = False
    ts: Optional[float] = None
    
    @property
    def changed(self):
        return self.rising or self.falling

class Photodiode:
    def __init__(self):
        self.calibrating: bool = True
        self._cal_buffer = deque(maxlen=500)
        self._last_value = None
        self._last_time = 0
        # self.changed = False
        
        # using high % change since plexon seems to see oscillations in the signal
        # self._cal_perc = 0.25
        
        # self._change_threshold: float = 0.0
        self._falling_threshold: float = 0.0
        self._rising_threshold: float = 0.0
        
        # counter for the number of samples the signal has been past the threshold
        self._edge_samples = 0
        # the number of samples that the signal must remain over the threshold
        self._edge_width = 1
        # fixed offset applied to edge ts
        self._edge_offset = 0.0
        
        self._edge_start_ts = 0
        
        self._is_high = False
    
    # def set_range(self, min_val: float, max_val: float):
    #     assert self.calibrating
    #     # threshold = abs(max_val - min_val) / 2 + min_val
    #     # self._change_threshold = threshold
    #     self._falling_threshold = min_val
    #     self._rising_threshold = max_val
    #     self.calibrating = False
    
    def set_params(self, *,
        falling_threshold: float,
        rising_threshold: float,
        min_pulse_width: int = 4,
        edge_offset: float = 0.0,
    ):
        self._falling_threshold = falling_threshold
        self._rising_threshold = rising_threshold
        self._edge_width = min_pulse_width
        self._edge_offset = edge_offset
    
    # def measure_level(self):
    #     self._cal_buffer.clear()
    #     while len(self._cal_buffer) < 500:
    #         # print('cal', len(self._cal_buffer))
    #         yield
        
    #     out = {
    #         'avg': statistics.mean(self._cal_buffer),
    #         'min': min(self._cal_buffer),
    #         'max': max(self._cal_buffer),
    #     }
        
    #     return out
    
    # def run_calibration(self, set_marker_level):
    #     assert self.calibrating
    #     def wait(t):
    #         s = time.perf_counter()
    #         while time.perf_counter() - s < t:
    #             yield
        
    #     wait_t = 1
        
    #     # buffer = deque(maxlen=500)
        
    #     set_marker_level(1)
    #     yield from wait(wait_t)
    #     high_levels = yield from self.measure_level()
        
    #     # print("\n".join(str(x) for x in self._cal_buffer))
        
    #     set_marker_level(0)
    #     yield from wait(wait_t)
    #     low_levels = yield from self.measure_level()
        
    #     high_t = (high_levels['max'] + high_levels['min']) / 2
    #     low_t = (low_levels['max'] + low_levels['min']) / 2
        
    #     # assert high_t > low_levels['max']
    #     # assert low_t < high_levels['min']
        
    #     # self._falling_threshold = low_t
    #     # self._rising_threshold = high_t
    #     self._falling_threshold = low_levels['max']
    #     self._rising_threshold = high_levels['min']
        
    #     # print("\n".join(str(x) for x in self._cal_buffer))
        
    #     debug((low_levels, high_levels))
        
    #     assert high_levels['min'] > low_levels['max']
    #     # assert low_levels['max'] < high_levels['min']
        
    #     # set_marker_level(0.5)
    #     # yield from wait(wait_t)
    #     # mid_val = self.last_value
    #     # # print(self.last_value)
    #     # set_marker_level(0)
    #     # yield from wait(wait_t)
    #     # min_val = self.last_value
    #     # time.sleep(20)
        
    #     # print(max_val, min_val)
    #     # assert max_val is not None
    #     # assert min_val is not None
    #     # assert max_val > min_val
    #     # threshold = abs(max_val - min_val) * self._cal_perc
    #     # self._change_threshold = threshold
    #     self.calibrating = False
    #     self._cal_buffer.clear()
        
    #     out = {
    #         # 'min': min_val,
    #         # 'mid': mid_val,
    #         # 'max': max_val,
    #         'low': low_levels,
    #         'high': high_levels,
    #         'thresholds': [self._falling_threshold, self._rising_threshold],
    #     }
        
    #     debug(out)
        
    #     return out
    
    # def _cal_value(self, val: float):
    #     print(val)
    #     self._cal_buffer.append(val)
    #     if len(self._cal_buffer) >= 500:
    #         # cmin = min(self._cal_buffer)
    #         # cmax = max(self._cal_buffer)
            
    #         avg = statistics.mean(self._cal_buffer)
    #         abs_threshold = avg * 0.001
            
    #         diffs = []
    #         for i in range(1, len(self._cal_buffer)):
    #             diffs.append(abs(self._cal_buffer[i] - self._cal_buffer[i-1]))
    #         stdev = statistics.stdev(diffs)
    #         print(diffs)
    #         print(stdev)
    #         diffs = [x for x in diffs if x <= stdev*3]
    #         assert diffs, "no non outlier photodiode samples"
    #         d_threshold = statistics.mean(diffs)
    #         d_threshold *= 10
            
    #         threshold = max(abs_threshold, d_threshold)
    #         self._change_threshold = threshold
            
    #         debug("photodiode change threshold set: %s", threshold)
            
    #         self.calibrating = False
    #         self._cal_buffer.clear()
    
    def handle_value(self, val: float, ts: float):
        # if self.calibrating:
        #     # self._cal_value(val)
        #     self._cal_buffer.append(val)
        #     self._last_value = val
        #     return NO_EDGE
        # if self._last_value is None:
        #     self._last_value = val
        #     self._last_time = ts
        #     return NO_EDGE
        
        # require at least 10 ms between events
        # at 60hz events should be separated by at least 16ms
        # if ts - self._last_time < 0.010:
        #     print('a')
        #     # self.changed = False
        #     return NO_EDGE
        
        # if val > self._rising_threshold:
        #     print(val)
        
        # if abs(self.last_value - val) > self._change_threshold:
        #     self.changed = True
            
        #     self.last_value = val
        #     self._last_time = ts
        # else:
        #     self.changed = False
        edge = Edge()
        if self._is_high:
            if val < self._falling_threshold:
                edge.falling = True
                # self.changed = True
                self._is_high = False
                # print('falling')
        else:
            if val > self._rising_threshold:
                if self._edge_samples == 0:
                    self._edge_start_ts = ts
                self._edge_samples += 1
                if self._edge_samples < self._edge_width:
                    pass
                else:
                    edge.rising = True
                    edge.ts = self._edge_start_ts + self._edge_offset
                    self._is_high = True
                    self._edge_samples = 0
                # print('rising')
            else:
                self._edge_samples = 0
        
        return edge
        
        # ct = self._change_threshold
        # rising = self.last_value < ct and val >= ct
        # falling = self.last_value >= ct and val < ct
        # if rising or falling:
        #     self.changed = True
        #     self.last_value = val
        #     self._last_time = ts
        # else:
        #     self.changed = False
