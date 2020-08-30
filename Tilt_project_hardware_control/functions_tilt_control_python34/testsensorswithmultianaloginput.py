import definitions
from definitions import *
import numpy as np
import xlwt


if __name__ == '__main__':

   
    #Transducer 2 - 26922
    multipleAI = MultiChannelAnalogInput(["Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22", "Dev6/ai23"])

    #Transducer 3 - 19675
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36", "Dev6/ai37"])

    #Transducer 4 - 19676
    #multipleAI = MultiChannelAnalogInput(["Dev6/ai38", "Dev6/ai39", "Dev6/ai48", "Dev6/ai49", "Dev6/ai50", "Dev6/ai51"])

    #Force Sensor Front(ai4), Left Hind Limb (ai5), Right Hind Limb(ai6)
    #multipleAI = MultiChannelAnalogInput(["Dev3/ai4","Dev3/ai5","Dev3/ai6"])
    
    multipleAI.configure()
    test = multipleAI.readAll()
    start_time = time.time()
    a = 0
    while a < 20:
        
        try:
            test = multipleAI.readAll()
            print(test)
##            sortedKeys = sorted(test)
##            for key in test:
##                i = sortedKeys.index(key)
##                channelList[i] = np.append(channelList[i], test[key])
            elapsed_time = time.time() - start_time
            print('Time: %f' %elapsed_time)
            a += 1


        except KeyboardInterrupt:
            print('\nPausing...  (Hit ENTER to continue, type quit to exit.)')
            try:
                response = input()
                if response == 'quit':
                    for index in [0,1,2]:
                        channelList[index] = channelList[index].reshape(len(channelList[index]),1)
                    combinedData = np.append(channelList[0],channelList[1],axis=1)
                    combinedData = np.append(combinedData,channelList[2],axis=1)
                    print(combinedData)
                    ExcelWrite(combinedData)
                    break
                print('Resuming...')
            except KeyboardInterrupt:
                print('Resuming...')
            continue
