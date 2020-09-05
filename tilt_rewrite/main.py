
import time
from random import randint
from contextlib import ExitStack
import csv
from itertools import count
from threading import Thread

import PyDAQmx
from PyDAQmx import Task
import nidaqmx
from nidaqmx.constants import LineGrouping, Edge, AcquisitionType
import numpy as np

# start Dev4/port2/line1 True
# stop  Dev4/port2/line2 False
def line_wait(line: str, value):
    waiter = LineWait(line)
    waiter.wait(value)
    waiter.end()

class LineWait:
    def __init__(self, line: str):
        self.task = nidaqmx.Task()
        self.task.di_channels.add_di_chan(line, line_grouping = LineGrouping.CHAN_PER_LINE)
        self.task.start()
    
    def wait(self, value):
        while True:
            data = self.task.read(number_of_samples_per_channel = 1)
            if data == [value]:
                return
    
    def end(self):
        self.task.end()

# record stop line "Dev4/port2/line6"
class LineReader:
    def __init__(self, line: str):
        task = nidaqmx.Task()
        task.di_channels.add_di_chan(line, line_grouping=LineGrouping.CHAN_PER_LINE)
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

class TiltPlatform:
    def __init__(self):
        self.task = Task()
        
        self.task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
        self.task.StartTask()
        self.begin()
    
    def begin(self):
        begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
    
    def close(self):
        self.task.StopTask()
    
    def tilt(self, tilt_type, water=False):
        water_duration = 0.15
        tilt_duration = 1.75
        
        tilt1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
        tilt3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
        tilt4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
        tilt6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
        begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
        
        if tilt_type == 1:
            data = tilt1
        elif tilt_type == 2:
            data = tilt3
        elif tilt_type == 3:
            data = tilt4
        elif tilt_type == 4:
            data = tilt6
        else:
            raise ValueError("Invalid tilt type {}".format(tilt_type))
        
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
        time.sleep(1) # should this be tilt duration?
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
        time.sleep(tilt_duration)
        
        if water:
            self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
            time.sleep(water_duration)
            self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
        
        delay = ((randint(1,100))/100)+1.5
        time.sleep(delay)

def generate_tilt_sequence():
    #No event 2 and 4 for early training
    #because they are the fast tilts and animals take longer to get used to them
    
    a = [1]*100
    a.extend([2]*100)
    a.extend([3]*100)
    a.extend([4]*100)
    np.random.shuffle(a)
    return a

def record_data():
    # samples per second
    SAMPLE_RATE = 1250
    SAMPLE_BATCH_SIZE = SAMPLE_RATE
    
    csv_headers = [
        "Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22","Dev6/ai23",
        "Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36","Dev6/ai37","Dev6/ai38", "Dev6/ai39",
        "Dev6/ai48", "Dev6/ai49", "Dev6/ai50","Dev6/ai51",
        "Strobe", "Start", "Inclinometer", 'Timestamp',
    ]
    csv_path = './loadcell_tilt.csv'
    # clock sourcs Dev6/PFI6
    with ExitStack() as stack:
        task = stack.enter_context(nidaqmx.Task())
        
        task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
        task.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
        # task.timing.cfg_samp_clk_timing(1000, source = "", sample_mode= AcquisitionType.CONTINUOUS, samps_per_chan = 1000)
        # set sample rate slightly higher than actual sample rate, not sure if that's needed
        task.timing.cfg_samp_clk_timing(SAMPLE_RATE+5, source="Dev6/PFI6", sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=SAMPLE_BATCH_SIZE)
        task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev6/PFI8", trigger_edge = Edge.RISING)
        
        csv_file = stack.enter_context(open(csv_path, 'w+', newline=''))
        writer = csv.writer(csv_file)
        writer.writerow(csv_headers)
        
        stop_reader = LineReader("Dev4/port2/line6")
        stack.enter_context(stop_reader)
        
        task.start()
        
        for row_i in count(0):
            if row_i == 0:
                # no timeout on first read to wait for start trigger
                read_timeout = -1
            else:
                read_timeout = 10 # default in nidaq
            
            data = task.read(SAMPLE_BATCH_SIZE, read_timeout)
            
            for i in range(SAMPLE_BATCH_SIZE):
                def gen_row():
                    for chan in data:
                        yield chan[i]
                    yield row_i / SAMPLE_RATE
                
                writer.writerow(gen_row())
                
                row_i += 1
            
            if stop_reader.read_bool() == False:
                break

def spawn_thread(func, *args, **kwargs) -> Thread:
    thread = Thread(target=func, args=args, kwargs=kwargs)
    thread.start()
    return thread

def main():
    line_wait("Dev4/port2/line1", True)
    
    platform = TiltPlatform()
    
    # line_wait("Dev4/port2/line2", False)
    waiter = LineWait("Dev4/port2/line2")
    
    tilt_sequence = generate_tilt_sequence()
    
    spawn_thread(record_data)
    
    first_run = True
    i = 0
    while False:
        try:
            while True:
                # check at start of loop in case of keyboard interrupt
                if i >= 400:
                    break
                
                platform.tilt(tilt_sequence[i])
                if first_run:
                    first_run = False
                    waiter.wait(False)
                
                i += 1
        except KeyboardInterrupt:
            platform.begin()
            i += 1
            input("\nPausing... (Hit ENTER to continue, ctrl-c again to quit.)")
            continue
    
    waiter.wait(False)
    waiter.end()
