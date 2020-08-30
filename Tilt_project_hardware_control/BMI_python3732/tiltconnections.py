#Tilt Connection test
from definitions import *
from MAPOnlineDecoder import *


print('start')
taskinterrupt = Task()
taskinterrupt.CreateDOChan("/Dev4/port1/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
task = Task()
task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)

begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
test1 = np.array([0,1,0,1,0,0,0,0], dtype=np.uint8) #punish?
test2 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8) #reward?
test3 = np.array([1,1,1,1,0,0,0,0], dtype=np.uint8)


task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
while True:
    try:
        input('press enter for "begin"')
        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
        input('press enter for test1, punish')
        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,test1,None,None)
        input('press enter for test2, reward')
        taskinterrupt.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,test2,None,None)



        
    except KeyboardInterrupt:
        break

print('done')

input('press enter for "begin"')
task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,test3,None,None)
input('press enter for "end"')
task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

task.StopTask()
taskinterrupt.StopTask()
