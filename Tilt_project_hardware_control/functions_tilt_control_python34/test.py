import definitions
from definitions import *


task = Task()
read = int32()
print('1')
data = np.zeros(10, dtype=np.uint32)
task.CreateDIChan("/Dev6/PFI0","",DAQmx_Val_ChanForAllLines)
task.StartTask()
print('2')

task.ReadDigitalU32(-1, 1, DAQmx_Val_GroupByChannel, data, 1000, byref(read), None)

print('end')
