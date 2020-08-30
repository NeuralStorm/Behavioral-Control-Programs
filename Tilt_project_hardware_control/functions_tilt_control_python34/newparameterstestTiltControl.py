""" Simple example of digital output

    This example outputs the values of data on line 0 to 7
"""
import definitions
from definitions import *
##Parameters:
#Tilt Types: (1, 3)


#make sure that NI-DAQ are not using the lines at the same time, i.e. test panel
#data array for Dev3/port0/line0:7 corresponds to channels going to Si Programmer
#            lines([0,1,2,3,4,5,6,7])
#tilt = np.array([IN3,IN4,IN5/cwjog,IN6/ccwjog(Go_5V),Wait_5V,?,?,?])
# Tilts have been edited to work with Si Tilt Program
#BMITiltProgram6b- from Nate B's work
def tilt(i):
    tilt1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
    tilt3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
    tilt4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
    tilt6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    test  = np.array([0,0,0,0,1,1,1,1], dtype=np.uint8)
    testall  = np.array([1,1,1,1,1,1,1,1], dtype=np.uint8)
    #pseudo-random generator 1,2,3,4
    #Task is from PyDAQmx
    task = Task()
    data = begin
    task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    
    if int(x[i]) == 1:
        data = tilt1
    elif int(x[i]) == 2:
        data = tilt3
    elif int(x[i]) == 3:
        data = tilt4
    elif int(x[i]) == 4:
        data = tilt6
    if (int(x[i])<=6):
        print(data)
        print(x[i])
        print(i)
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    time.sleep(0.5)
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
    delay = ((randint(1,100))/100)+3
    time.sleep(delay)
    
    task.StopTask()
def choose():
    #No event 2 and 4 for early training
    #because they are the fast tilts and animals take longer to get used to them
    
    a = [1]*200
    #a.extend([2]*100)
    a.extend([3]*200)
    #a.extend([4]*100)
    np.random.shuffle(a)
    return a

x = choose()
input('Press enter when ready to begin')

for i in range(1,400):
    try:
        t = tilt(i)

    except KeyboardInterrupt:
        print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
        try:
            response = input()
            if response == 'quit':
                break
            print('Resuming...')
        except:
            pass
        continue


