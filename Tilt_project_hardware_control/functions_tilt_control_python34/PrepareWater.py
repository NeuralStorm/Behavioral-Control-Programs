import definitions
from definitions import *
###Prepare water for animals
Watering = True
task = Task()
begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
WaterDuration = 0.15
data = begin
task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
task.StartTask()
while Watering == True:
    go = input("press Enter for Water, or type 'quit' to exit")
    if go == 'quit':
        Watering = False
    else:
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
        time.sleep(WaterDuration)
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)



task.StopTask()
