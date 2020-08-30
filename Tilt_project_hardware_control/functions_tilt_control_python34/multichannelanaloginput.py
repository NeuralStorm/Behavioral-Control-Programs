import definitions
from definitions import *
import numpy as np
import xlwt
import csv


if __name__ == '__main__':

    #Transducer Analog Output order: Fx, Tx, Fy, Ty, Fz, Tz

    #Transducer 2 - 26922
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23"])

    #Transducer 3 - 19675
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37"])

    #Transducer 4 - 19676
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"])
 
    
    #All Transducer
    multipleAI = MultiChannelAnalogInput(["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23","Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37","Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"])
    numSensor = 18
    
    multipleAI.configure()
    test = multipleAI.readAll()
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



channelList = [[] for i in range(numSensor)]
 
while True:
        
        try:
            test = multipleAI.readAll()
            print(test)
            sortedKeys = sorted(test)
            for key in test:
                i = sortedKeys.index(key)
                channelList[i] = np.append(channelList[i], test[key])
            

        except KeyboardInterrupt:
            print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
            try:
                response = input()
                if response == 'quit':
                    for index in range(numSensor):
                        channelList[index] = channelList[index].reshape(len(channelList[index]),1)
                    combinedData = channelList[0]
                    for num in range(1,numSensor):
                        combinedData = np.append(combinedData,channelList[num],axis=1)
                    print(combinedData)
                    sheetName = input('Enter a name for the sheet: ')
                    WriteCSV(combinedData,sortedKeys,sheetName)
                    break
                print('Resuming...')
            except KeyboardInterrupt:
                print('Resuming...')
            continue
