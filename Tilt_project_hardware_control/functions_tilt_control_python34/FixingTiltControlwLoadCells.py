import definitions
from definitions import *
from multiprocessing import *
import numpy as np
import xlwt
import csv
### TO TEST: HOW PAUSE WORKS, CHECK PRINT STATEMENTS ARE CORRECT, WHILE LOOP IS WORKING, EACH TIME.SLEEP IS CHANGED TO A DURATION

##Parameters:
#Tilt Types: (1, 3, 4, 6)

#make sure that NI-DAQ are not using the lines at the same time, i.e. test panel
#data array for Dev3/port0/line0:7 corresponds to channels going to SI Programmer
#            lines([0,1,2,3,4,5,6,7])
#tilt = np.array([IN3,IN4,IN5/cwjog,IN6/ccwjog(Go_5V),Wait_5V,?,?,?])
# Tilts have been edited to work with Si Tilt Program
#BMITiltProgram6b- from Nate B's work (renamed a copy to TiltControl)

##Load Cells
##Transducer 2 (26922)


def LoadCellThread():
    
    #print('Thread start')
    
    multipleAI = MultiChannelAnalogInput(["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"])
    numSensor = 18
    multipleAI.configure()
    test = multipleAI.readAll()
    channelList = [[] for i in range(numSensor)]
    #counter = 0
    while True:
        #counter = counter + 1
        tic = time.time()
        test = multipleAI.readAll()
        #print(test)
        sortedKeys = sorted(test)
        for key in test:
            i = sortedKeys.index(key)
            channelList[i] = np.append(channelList[i], test[key])
        #if counter == 1:
            #counter = 0
        for index in range(numSensor):
            channelList[index] = channelList[index].reshape(len(channelList[index]),1)
        combinedData = channelList[0]
        for num in range(1,numSensor):
            combinedData = np.append(combinedData,channelList[num],axis=1)
        sheetName = 'TestTiltLoadCell'
        #WriteCSV(combinedData,sortedKeys,sheetName)
        with open(sheetName + '.csv','w+',newline='') as f:
            writer = csv.writer(f)
            writer.writerow(sortedKeys)
            writer.writerows(combinedData)
            f.close()
        toc = time.time() - tic
        print(toc)


#def WriteCSV(sensorReadings,sensorLabels,name)
def tilt(i,task):
    
###     
    AutoWaterReward = False #Change this to false if you don't want automatic water rewards 
    TTLon = False
    TiltWait = False
    TiltReady = False
    WaterFrequency = 1 #Gives water every # tilts
    WaterDuration = 0.15
    tilt1 = np.array([1,0,0,1,0,0,0,0], dtype=np.uint8)
    tilt3 = np.array([1,1,0,1,0,0,0,0], dtype=np.uint8)
    tilt4 = np.array([0,0,1,1,0,0,0,0], dtype=np.uint8)
    tilt6 = np.array([0,1,1,1,0,0,0,0], dtype=np.uint8)
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    wateron = np.array([0,0,0,0,1,0,0,0], dtype=np.uint8)
    TiltDuration = 1.75
    #task = Task()
    data = begin
    #task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    #task.StartTask()
    #task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    #test  = np.array([0,0,0,0,1,1,1,1], dtype=np.uint8)
    #testall  = np.array([1,1,1,1,1,1,1,1], dtype=np.uint8)
    #pseudo-random generator 1,2,3,4
    #Task is from PyDAQmx

    ###Need While Loop

        
    #Needs x = choose() as shown below
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
        print(i)
        print(x[i])
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    time.sleep(1)
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
    delay = ((randint(1,100))/100)+1.5
    time.sleep(TiltDuration) ########################################################## TiltDuration
    if i%WaterFrequency == 0 and AutoWaterReward == True:
        print('Water')
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,wateron,None,None)
        time.sleep(WaterDuration)
        task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)

    time.sleep(delay) ############################################# delay

    #task.StopTask()

###
            
##    except KeyboardInterrupt:
##        try:
##            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
##            print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
##            response = input()
##            if response == 'quit':
##                exit()
##            print('Resuming...')
##        except:
##            pass ##Need to check how the loop starts again after pausing like this. Might be ok?

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
    
    begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
    task = Task()
    data = begin
    task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
    task.StartTask()
    task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,data,None,None)
    
    input('Press enter when ready to begin')
    
##    tiltstart = Process(target = tilttest, args = '')
##    tiltstart.start()
##    tiltstart.join()
    LoadCellThread()
##    tiltstart.terminate()
    
    #sensors = Process(target = LoadCellThread, args = '')
    #sensors.start()



#############################################   Commented out all below
#############################################   for testing load cells
##    x = choose()
##    
##    for i in range(0,400):
##        try:
##            t = tilt(i,task)
##        except KeyboardInterrupt:
##            print('\nPausing... (Hit ENTER to contrinue, type quit to exit.)')
##            task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
##            try:
##                response = input()
##                if response == 'quit':
##                    break
##                print('Resuming...')
##            except:
##                pass
##            continue
##    
##
##    
##    try:
##        input('Press Enter to quit')
##    except KeyboardInterrupt:
##        #sensors.terminate()
##        pass
##    task.StopTask()
##    #sensors.terminate()

