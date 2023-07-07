
import time
import statistics
import logging

logger = logging.getLogger(__name__)
debug = logger.debug

class PhotoDiode:
    def __init__(self):
        self.calibrating: bool = True
        self._cal_buffer = []
        self.last_value = None
        self._last_time = 0
        self.changed = False
        
        # using high % change since plexon seems to see oscillations in the signal
        # self._cal_perc = 0.25
        
        self._change_threshold: float = 0.0
    
    def set_range(self, min_val: float, max_val: float):
        assert self.calibrating
        threshold = abs(max_val - min_val) / 2 + min_val
        self._change_threshold = threshold
        self.calibrating = False
    
    def run_calibration(self, set_marker_level):
        assert self.calibrating
        def wait(t):
            s = time.perf_counter()
            while time.perf_counter() - s < t:
                yield
        
        wait_t = 1
        
        # set_marker_level(1)
        # yield from wait(wait_t)
        # max_val = self.last_value
        set_marker_level(0.5)
        yield from wait(wait_t)
        mid_val = self.last_value
        # print(self.last_value)
        set_marker_level(0)
        # yield from wait(wait_t)
        # min_val = self.last_value
        # time.sleep(20)
        
        # print(max_val, min_val)
        # assert max_val is not None
        # assert min_val is not None
        # assert max_val > min_val
        # threshold = abs(max_val - min_val) * self._cal_perc
        # self._change_threshold = threshold
        self.calibrating = False
        
        return {
            # 'min': min_val,
            'mid': mid_val,
            # 'max': max_val,
        }
    
    def _cal_value(self, val: float):
        print(val)
        self._cal_buffer.append(val)
        if len(self._cal_buffer) >= 500:
            # cmin = min(self._cal_buffer)
            # cmax = max(self._cal_buffer)
            
            avg = statistics.mean(self._cal_buffer)
            abs_threshold = avg * 0.001
            
            diffs = []
            for i in range(1, len(self._cal_buffer)):
                diffs.append(abs(self._cal_buffer[i] - self._cal_buffer[i-1]))
            stdev = statistics.stdev(diffs)
            print(diffs)
            print(stdev)
            diffs = [x for x in diffs if x <= stdev*3]
            assert diffs, "no non outlier photodiode samples"
            d_threshold = statistics.mean(diffs)
            d_threshold *= 10
            
            threshold = max(abs_threshold, d_threshold)
            self._change_threshold = threshold
            
            debug("photodiode change threshold set: %s", threshold)
            
            self.calibrating = False
            self._cal_buffer.clear()
    
    def handle_value(self, val: float, ts: float):
        if self.calibrating:
            # self._cal_value(val)
            self.last_value = val
            return
        if self.last_value is None:
            self.last_value = val
            self._last_time = ts
            return
        
        # require at least 0.5 ms between events
        if ts - self._last_time < 0.0005:
            self.changed = False
            return
        
        # if abs(self.last_value - val) > self._change_threshold:
        #     self.changed = True
            
        #     self.last_value = val
        #     self._last_time = ts
        # else:
        #     self.changed = False
        
        ct = self._change_threshold
        rising = self.last_value < ct and val >= ct
        falling = self.last_value >= ct and val < ct
        if rising or falling:
            self.changed = True
            self.last_value = val
            self._last_time = ts
        else:
            self.changed = False
