# pylint: disable=import-outside-toplevel

# port 2 changing to port 0

# tilt finish Dev6/port0/line3
# gos high while tilt is active
# output 2 on motor controller

# tilt midpoint Dev6/port0/line4
# gos high when the tilt reaches it's maximum inclination
# stim output Dev6/port0/line5


def line_wait(line: str, value=True):
    waiter = LineWait(line)
    waiter.wait(value)
    waiter.end()

class LineWait:
    def __init__(self, line: str):
        import nidaqmx # pylint: disable=import-error
        from nidaqmx.constants import LineGrouping, SampleTimingType # pylint: disable=import-error
        
        self.task = nidaqmx.Task()
        self.task.di_channels.add_di_chan(line, line_grouping = LineGrouping.CHAN_PER_LINE)
        self.task.timing.samp_timing_type = SampleTimingType.ON_DEMAND
        # self.task.timing.samp_timing_type = SampleTimingType.CHANGE_DETECTION
        self.task.start()
    
    def wait(self, value):
        while True:
            data = self.task.read(number_of_samples_per_channel = 1)
            if data == [value]:
                return
    
    def end(self):
        self.task.stop()
    
    def __enter__(self):
        self.task.__enter__()
        return self
    
    def __exit__(self, *exc):
        self.end()
        return self.task.__exit__(*exc)

class LineReader:
    def __init__(self, line: str):
        import nidaqmx # pylint: disable=import-error
        from nidaqmx.constants import LineGrouping, SampleTimingType # pylint: disable=import-error
        
        task = nidaqmx.Task()
        task.di_channels.add_di_chan(line, line_grouping=LineGrouping.CHAN_PER_LINE)
        task.timing.samp_timing_type = SampleTimingType.ON_DEMAND
        task.start()
        self.task = task
    
    def read_bool(self) -> bool:
        value = self.task.read(number_of_samples_per_channel=1)
        return bool(value[0])
    
    def __enter__(self):
        self.task.__enter__()
        return self
    
    def __exit__(self, *exc):
        return self.task.__exit__(*exc)
