import definitions
from definitions import *
from nidaqmx import stream_readers as sr
#import numpy as np
with nidaqmx.Task() as task:
    sheetName = 'TiltLoadCell'
    with open(sheetName + '.csv','w+',newline='') as f:
        ###Initialize Channels and Variables
        task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
        samples = 1000

        sr.AnalogMultiChannelReader   
