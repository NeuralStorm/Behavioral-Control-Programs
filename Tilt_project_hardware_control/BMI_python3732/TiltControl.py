import definitions
from definitions import *
##Parameters:
#Tilt Types: (1, 3)

#make sure that NI-DAQ are not using the lines at the same time, i.e. test panel
#data array for Dev3/port0/line0:7 corresponds to channels going to Si Programmer
#            lines([0,1,2,3,4,5,6,7])
#tilt = np.array([IN3,IN4,IN5/cwjog,IN6/ccwjog(Go_5V),Wait_5V,?,?,?])
# Tilts have been edited to work with Si Tilt Program
#BMITiltProgram6b- from Nate B's work (renamed a copy to TiltControl)

def tilt(x):
    try:
###
        count = 0
        for i in x:
            AutoWaterReward = False #Change this to false if you don't want automatic water rewards
            TTLon = False
            TiltWait = False
            WaterFrequency = 1 #Gives water every # tilts
            WaterDuration = 0.15
            start1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
            start3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
            start4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
            start6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
            tilt1 = np.array([1,0,0,0,0,0,0,0], dtype=np.uint8)
            tilt3 = np.array([1,1,0,0,0,0,0,0], dtype=np.uint8)
            tilt4 = np.array([0,0,1,0,0,0,0,0], dtype=np.uint8)
            tilt6 = np.array([0,1,1,0,0,0,0,0], dtype=np.uint8)
            begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
            wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
            TiltDuration = 1.75
            #test  = np.array([0,0,0,0,1,1,1,1], dtype=np.uint8)
            #testall  = np.array([1,1,1,1,1,1,1,1], dtype=np.uint8)
            #pseudo-random generator 1,2,3,4
            #Task is from PyDAQmx
            task = Task()
            data = begin
            task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
            task.StartTask()
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
            #Needs x = choose() as shown below
            if int(x[i]) == 1:
                data = start1
                data2 = tilt1
            elif int(x[i]) == 2:
                data = start3
                data2 = tilt3
            elif int(x[i]) == 3:
                data = start4
                data2 = tilt4
            elif int(x[i]) == 4:
                data = start6
                data2 = tilt6
            if (int(x[i])<=6):
                count += 1
                print(data)
                print(i)
                print(count)
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data2,None,None)
            time.sleep(0.5) #Replaced by decoder stuff for online
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
            delay = ((randint(1,100))/100)+1.5
            time.sleep(TiltDuration)
            if i%WaterFrequency == 0 and AutoWaterReward == True:
                print('Water')
                task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
                time.sleep(WaterDuration)
                task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

            time.sleep(delay)

            task.StopTask()

###
            
    except KeyboardInterrupt:
        try:
            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
            print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
            response = input()
            if response == 'quit':
                exit()  
            print('Resuming...')
        except:
            pass

def choose():
    #No event 2 and 4 for early training
    #because they are the fast tilts and animals take longer to get used to them
    
    a = [1]*100
    a.extend([2]*100)
    a.extend([3]*100)
    a.extend([4]*100)
    np.random.shuffle(a)
    return a

if __name__ == "__main__":
    x = choose()
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    task = Task()
    data = begin
    task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    task.StopTask()
    input('Press enter when ready to begin')


    t = tilt(x)
            

    


