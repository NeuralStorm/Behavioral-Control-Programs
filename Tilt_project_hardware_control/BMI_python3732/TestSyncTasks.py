# Test individual tasks
import definitions
from definitions import *
import threading
from threading import Thread
from multiprocessing import *
import numpy as np
import xlwt
import csv
import TestRunwLoadCells
from TestRunwLoadCells import *

def callbackloop(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
    data = task_handle.read(number_of_samples_per_channel=1000,timeout = -1)
    return 0


if __name__ == "__main__":
    # Test System
    print('program begin')
    sensortask = nidaqmx.Task()
    sensortask.stop()
    # sensortask Channels: Load Cells(ai18:23,32:39,48:51), Clock(PFI7), Trigger(PFI8)
    # sensortask AI Channels for load cells
    sensortask.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
    sensortask.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
    # sensortask.ai_channels.add_ai_voltage_chan("Dev6/ai18")
    # sensortask Configure Timing
    sensortask.timing.cfg_samp_clk_timing(1000, source = "/Dev6/PFI7", sample_mode = AcquisitionType.CONTINUOUS, samps_per_chan = 1000) #source = '/Dev6/PFI7'

    sensortask.in_stream.auto_start = False
    print(sensortask.timing.samp_clk_rate)
    print(sensortask.timing.samp_clk_src)
    print(sensortask.timing.samp_clk_term)
    data = []
    sensortask.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev6/PFI8", trigger_edge = Edge.RISING) #ai/StartTrigger or di/StartTrigger?
    print('DI go')
    sensortask.start()
    print('task started')
    data = sensortask.register_every_n_samples_acquired_into_buffer_event(1000, callbackloop(task_handle = sensortask ,every_n_samples_event_type = list, number_of_samples = 1000, callback_data = data))
    print('register callback')
    #sensortask.start()
    print('read w/ timeout / start plexon')
    #data = sensortask.read(1000, timeout = -1)
##    print(data)
##    print(len(data))
##    print(len(data[0]))
##    tic = time.time()
##    for i in range(0,5):
##        tic2 = time.time()
        #data = sensortask.register_every_n_samples_acquired_into_buffer_event(1000, callbackloop)
##        toc2 = time.time() - tic2
##        print(data)
##        print(len(data[0]))
##        print(toc2)
##        print(len(data))
##        print(len(data[0]))
##    toc = time.time() - tic
##    print(toc)

    
##    master.stop()
    # print stuff
##    print(sensortask.timing.ai_conv_max_rate)
##    print(sensortask.timing.ai_conv_timebase_div)
##    sensortask.wait_until_done()
    print('stop')
