import definitions
from definitions import *
import numpy as np
import xlwt
import csv


class ContinuousMultiChannelAnalogInput():
    """Class to create a multi-channel analog input
    
    Usage: AI = MultiChannelInput(physicalChannel)
        physicalChannel: a string or a list of strings
    optional parameter: limit: tuple or list of tuples, the AI limit values
                        reset: Boolean
    Methods:
        read(name), return the value of the input name
        readAll(), return a dictionary name:value
    """
    def __init__(self,physicalChannel, limit = None, reset = False):
        if type(physicalChannel) == type(""):
            self.physicalChannel = [physicalChannel]
        else:
            self.physicalChannel  =physicalChannel
        self.numberOfChannel = physicalChannel.__len__()
        if limit is None:
            self.limit = dict([(name, (-10.0,10.0)) for name in self.physicalChannel])
        elif type(limit) == tuple:
            self.limit = dict([(name, limit) for name in self.physicalChannel])
        else:
            self.limit = dict([(name, limit[i]) for  i,name in enumerate(self.physicalChannel)])           
        if reset:
            DAQmxResetDevice(physicalChannel[0].split('/')[0] )

            
    def configure(self):
        # Create one task handle per Channel
        taskHandles = dict([(name,TaskHandle(0)) for name in self.physicalChannel])
        for name in self.physicalChannel:
            DAQmxCreateTask("",byref(taskHandles[name]))
            DAQmxCreateAIVoltageChan(taskHandles[name],name,"",DAQmx_Val_RSE,
                                     self.limit[name][0],self.limit[name][1],
                                     DAQmx_Val_Volts,None)
            DAQmxCfgSampClkTiming(taskHandles[name],"",1000.0,DAQmx_Val_Rising,DAQmx_Val_ContSamps,10000)
        self.taskHandles = taskHandles
    def readAll(self):
        return dict([(name,self.read(name)) for name in self.physicalChannel])
    def read(self,name = None):
        if name is None:
            name = self.physicalChannel[0]
        taskHandle = self.taskHandles[name]             
        DAQmxStartTask(taskHandle)
        data = numpy.zeros((1,), dtype=numpy.float64)
        #data = AI_data_type()
        read = int32()
        DAQmxReadAnalogF64(taskHandle,1000,10.0,DAQmx_Val_GroupByChannel,data,1000,byref(read),None)
        #DAQmxStopTask(taskHandle)
        print("Acquired %d points"%read.value)
        print(data)
        return data
    def stopAll(self):
        dict([(name,self.stop(name)) for name in self.physicalChannel])
    def stop(self,name = None):
        if name is None:
            name = self.physicalChannel[0]
        taskHandle = self.taskHandles[name] 
        DAQmxStopTask(taskHandle)
if __name__ == '__main__':
    #Transducer Analog Output order: Fx, Tx, Fy, Ty, Fz, Tz
    #Transducer 2 - 26922
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23"])
    #Transducer 3 - 19675
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37"])
    #Transducer 4 - 19676
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"])
    #numSensor = 6
    #All Transducer
    #ChnList = ["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"]
    #multipleAI = MultiChannelAnalogInput(ChnList)
    #numSensor = 18
    
    ChnList = ["Dev6/ai18"]
    TestContAI = ContinuousMultiChannelAnalogInput(ChnList)

    TestContAI.configure()
    tic = time.time()
    TestContAI.readAll()
    toc = time.time() - tic
    print(toc)
    TestContAI.stopAll()
    
    analog_input = Task()
    read = int32()
    data = np.zeros((1000,), dtype =np.float64)

    analog_input.CreateAIVoltageChan("Dev6/ai18","",DAQmx_Val_Cfg_Default, -10.0,10.0,DAQmx_Val_Volts,None)
    analog_input.CfgSampClkTiming("",1000.0,DAQmx_Val_Rising,DAQmx_Val_ContSamps,10000)

    analog_input.StartTask()
    tic = time.time()
    analog_input.ReadAnalogF64(1000,10.0,DAQmx_Val_GroupByChannel,data,1000,byref(read),None)
    toc = time.time() - tic
    print(toc)
    print("Acquired %d points"%read.value)
    print(data)
    print(len(data))


##    print(sensors)
##    names = (sensors)
##    print(names)
##    sensors1 = multipleAI.readAll()
##    names1 = (sensors1)
##    print(sensors1)
##    for line in names1:
##        if names1 in names:
##            sensors[names1].append(sensors1[names1])
##    print(sensors)

##def ExcelWrite(sensorReadings):
##    wb = xlwt.Workbook()
##    dataSheet = wb.add_sheet('Test Trial')

##    style = xlwt.easyxf('font: name Arial, color-index black, bold off')
##    numTrials = np.size(sensorReadings,0)

##    for sensor in [0,1,2]:
##        for reading in range(0,numTrials):
##            data = sensorReadings[reading,sensor]
##            dataSheet.write(reading,sensor,data.item(),style)

##    wb.save('Test Write' + '.xls')

def WriteCSV(sensorReadings,sensorLabels,name):
    with open(name + '.csv','a',newline='') as f:
        writer = csv.writer(f)
        writer.writerow(sensorLabels)
        writer.writerows(sensorReadings)



##channelList = [[] for i in range(numSensor)]
##count = 0
##while True:
##        
##        try:
##            tic = time.time()
##            test = multipleAI.readAll()
##            print(test)
####            count = count + 1
####            #print(test)
####            sortedKeys = sorted(test)
####            for key in test:
####                i = sortedKeys.index(key)
####                channelList[i] = np.append(channelList[i], test[key])
####            for index in range(numSensor):
####                channelList[index] = channelList[index].reshape(len(channelList[index]),1)
####            combinedData = channelList[0]
####            for num in range(1,numSensor):
####                combinedData = np.append(combinedData,channelList[num],axis=1)
####            sheetName = 'TiltLoadCell'
####            #WriteCSV(combinedData,sortedKeys,sheetName)
####            with open(sheetName + '.csv','w+',newline='') as f:
####                writer = csv.writer(f)
####                writer.writerow(sortedKeys)
####                writer.writerows(combinedData)
####                f.close()
##            toc = time.time() - tic
##            print(toc)
##            
##            
##
##        except KeyboardInterrupt:
##            print(count)
##            print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
##            try:
##                response = input()
##                if response == 'quit':
##                    for index in range(numSensor):
##                        channelList[index] = channelList[index].reshape(len(channelList[index]),1)
##                    combinedData = channelList[0]
##                    for num in range(1,numSensor):
##                        combinedData = np.append(combinedData,channelList[num],axis=1)
##                    print(combinedData)
##                    sheetName = input('Enter a name for the sheet: ')
##                    WriteCSV(combinedData,sortedKeys,sheetName)
##                    break
##                print('Resuming...')
##            except KeyboardInterrupt:
##                print('Resuming...')
##            continue
