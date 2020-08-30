import definitions
from definitions import *


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
            #DAQmxWaitForValidTimestamp(taskHandles[name],DAQmx_Val_StartTrigger,-1)
        self.taskHandles = taskHandles
    def readAll(self):
        return dict([(name,self.read(name)) for name in self.physicalChannel])
    def read(self,name = None):
        global startcounter
        if name is None:
            name = self.physicalChannel[0]
        taskHandle = self.taskHandles[name]
        data = numpy.zeros((1000,), dtype=numpy.float64)
        #data = AI_data_type()
        read = int32()
        startcounter = 0
        if startcounter == 0:
            #DAQmxStartTask(taskHandle)
            DAQmxReadAnalogF64(taskHandle,1000,10.0,DAQmx_Val_GroupByChannel,data,1000,byref(read),None)
            startcounter = 1

        
        DAQmxStopTask(taskHandle)
        #print("Acquired %d points"%read.value)
        #print(data)
        return data
    def stopAll(self):
        dict([(name,self.stop(name)) for name in self.physicalChannel])
    def stop(self,name = None):
        if name is None:
            name = self.physicalChannel[0]
        taskHandle = self.taskHandles[name]
        DAQmxStopTask(taskHandle)



if __name__ == '__main__':
##    ChnList = ["Dev6/ai18"]
##    TestContAI = ContinuousMultiChannelAnalogInput(ChnList)
##    TestContAI.configure()
##    TestContAI.readAll()
##    TestContAI.stopAll()
    try:
        with nidaqmx.Task() as taskstart, nidaqmx.Task() as taskstop:
            #print('Thread start')
            multipleAI = ContinuousMultiChannelAnalogInput(["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"])
            numSensor = 18
            multipleAI.configure()
            
            #channelList = [[] for i in range(numSensor)]
            channelList = []
            counter = 0
            sheetName = 'TiltLoadCell'
            
            taskstop.di_channels.add_di_chan("Dev4/port2/line6", line_grouping = LineGrouping.CHAN_PER_LINE)
            #taskstop.timing.cfg_samp_clk_timing( 1000, sample_mode = AcquisitionType.CONTINUOUS)
            
            taskstart.di_channels.add_di_chan("Dev4/port2/line5", line_grouping = LineGrouping.CHAN_PER_LINE )
            taskstart.read(number_of_samples_per_channel=1)
            wait_start = True
            print('start rec')
            while wait_start:
                ex = taskstart.read(number_of_samples_per_channel=1)
                print(ex)
                if ex == True or ex == [True]:
                    wait_start = False
            with open(sheetName + '.csv','w+',newline='') as f:
                while True:
                    test = multipleAI.readAll()
                    sortedKeys = sorted(test)
                    for key in sortedKeys:
                        #i = sortedKeys.index(key)
                        channelList.append(test[key])
                    #if counter == 1:
                        #counter = 0
                    #for index in range(numSensor):
                        #channelList[index] = channelList[index].reshape(len(channelList[index]),1)
                    #combinedData = channelList[0]
            ##        for num in range(1,numSensor):
            ##            combinedData = np.append(combinedData,channelList[num],axis=1)
                    
                    
                    #print('data')
                    
                    #print(channelList)
                    #WriteCSV(combinedData,sortedKeys,sheetName)
                    if counter == 0:
                        writer = csv.writer(f)
                        writer.writerow(sortedKeys)
                        writer.writerow(channelList)
                    else:
                       #with open(sheetName + '.csv','a',newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow(channelList)
                    counter = counter + 1
                    channelList=[]
                    print('loop')
    except KeyboardInterrupt:
        pass
