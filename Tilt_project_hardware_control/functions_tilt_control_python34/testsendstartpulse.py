#Test sending a start pulse to 6225
import definitions
from definitions import *
import nidaqmx
import numpy as np

begin   = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
punish  = np.array([0,0,1,0,0,0,0,0], dtype=np.uint8)
reward  = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
tilt1   = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
tilt3   = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
tilt4   = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
tilt6   = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
task = Task()
tasktilts = Task()

task.CreateDOChan("/Dev4/port1/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
tasktilts.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)

task.StartTask()
tasktilts.StartTask()

task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

print('punish')
task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,punish,None,None)
time.sleep(0.15)
task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

time.sleep(1)
print('reward')
task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,reward,None,None)
time.sleep(0.15)
task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

print('done')


