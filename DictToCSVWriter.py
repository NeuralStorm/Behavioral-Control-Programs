from pyplexdo import PyPlexDO, DODigitalOutputInfo
import sys
import time
import os
from csv import reader, writer
def FormatDurations():
    try:
        filename = input('What would you like to save the Duration File as: ')
        fullfilename = filename + '.csv'
        csvtest = True
        while csvtest == True:
            check = os.path.isfile(fullfilename)
            while check == True:
                print('File name already exists')
                filename = input('Enter File name')
                fullfilename = filename + '.csv'
                check = os.path.isfile(fullfilename)
            print('File name not currently used, saving.')

            with open(filename + '.csv', 'w', newline = '') as csvfile:
                csv_writer = writer(csvfile, delimiter = ',')
                for key in csvdict.keys():
                    csv_writer.writerow([key]+ csvdict[key])
            csvtest = False
            # with open(name + '.csv', newline = '') as csv_read, open(data +'.csv', 'w', newline = '') as csv_write:
            #     writer(csv_write, delimiter= ',').writerows(zip(*reader(csv_read, delimiter=',')))
            print('fullfilename: ', fullfilename)
    except RuntimeError:
        print('Error with File name')
        filename = None
if __name__ == '__main__':
    # These are the two NI boards with DO support commonly shipped
    # with OmniPlex systems.
    # compatible_devices = ['PXI-6224', 'PXI-6259']

    # # Create instance of PyPlexDO
    # plexdo = PyPlexDO()

    # # Get information on all compatible boards
    # doinfo = plexdo.get_digital_output_info()

    # # Placeholder for the device number of the board we'll later initialize
    # device_number = None

    # # Loop through each device detected. If it's part of our compatible device list,
    # # store the device number. Since it doesn't break when it finds a compatible device,
    # # the last compatible device found is used.
    # for i in range(doinfo.num_devices):
    #     if plexdo.get_device_string(doinfo.device_numbers[i]) in compatible_devices:
    #         device_number = doinfo.device_numbers[i]
    
    # if device_number == None:
    #     print("No compatible devices found. Exiting.")
    #     sys.exit(1)
    # else:
    #     print("{} found as device {}".format(plexdo.get_device_string(device_number), device_number))

    # # Initialize the device, check for success
    # res = plexdo.init_device(device_number)
    # if res != 0:
    #     print("Couldn't initialize device. Exiting.")
    #     sys.exit(1)

    # # Clear all bits
    # plexdo.clear_all_bits(device_number)

    # # Set bit 1
    # plexdo.set_bit(device_number, 1)

    # # Wait for one second
    # plexdo.sleep(100)

    # # Clear bit 1
    # plexdo.clear_bit(device_number, 1)

    # # Wait for one second
    # plexdo.sleep(1000)
    
    # # Pulse bit 1 for 5 milliseconds
    # plexdo.pulse_bit(device_number, 1, 5)
    # print('test')
    # start = time.time()
    # time.sleep(5)
    # end = time.time()
    # hours, rem = divmod(end-start, 3600)
    # minutes, seconds = divmod(rem, 60)
    # test = ["{:0>2}:{:0>2}:{:05.2f}".format(int(hours),int(minutes),seconds)]
    csvdict = {'Hand in Home Zone': [], 'Study ID': ['TIP'], 'Session ID': ['1'], 'Animal ID':['001'],'Date': ['20200309'], 'Session Time': [['00:15:20.13'], ['00:18:42.63'], ['00:00:01.89']], 'Pre Discrimanatory Stimulus Min delta t1': [0.1], 'Pre Discrimanatory Stimulus Max delta t1': [0.25], 'Pre Go Cue Min delta t2': [0.25], 'Pre Go Cue Max delta t2': [0.5], 'Pre Reward Delay Min delta t3': [0.5], 'Pre Reward Delay Max delta t3': [0.5], 'Use Maximum Reward Time': [True], 'Maximum Reward Time': [0.18], 'Enable Time Out': [False], 'Time Out': [0.5], 'Total Trials': [77], 'Total t1 failures': [19], 'Total t2 failures': [16], 'Total successes': [41], 'Check Trials': ['False', 'False', 'False'], 'Paw into Home Box: Start':[572.5994250000001, 594.0994250000001, 596.2994250000002, 598.449425, 614.169425, 617.8184250000002, 621.298425, 621.688425, 622.538425, 624.5684250000002, 638.9184250000001, 652.1294250000001, 665.1684250000001, 666.4184250000001, 669.219425, 682.938425, 687.449425, 688.8684250000001, 689.3484250000001, 695.1684250000001, 697.3784250000001, 699.3184250000002, 702.3984250000001, 709.768425, 711.248425, 711.9184250000001, 713.188425, 719.5784250000002, 726.8884250000001, 818.317425, 820.238425, 824.5684250000002, 826.998425, 830.547425, 831.5974250000002, 843.3184250000002, 865.9474250000001, 867.7074250000001, 891.9374250000001, 897.0984250000001, 898.307425, 900.8674250000001, 905.9574250000001, 920.1174250000001, 940.8474250000002, 942.8674250000001, 944.817425, 949.307425, 952.576425, 965.247425, 982.017425, 990.6864250000001, 992.027425, 993.057425, 1000.6674250000001, 1002.6364250000001, 1004.016425, 1005.066425, 1035.3674250000001, 1047.486425, 1059.526425, 1061.6664250000001, 1067.676425, 1070.427425, 1104.456425, 1109.8964250000001, 1110.6564250000001, 1111.1564250000001, 1114.276425, 1118.706425, 1144.716425, 1244.946425, 1260.026425, 1267.455425, 1274.475425, 1452.1454250000002], 'Paw out of Home Box: End': [593.8494250000001, 594.659425, 597.0994250000001, 613.279425, 615.499425, 620.8484250000001, 621.498425, 622.228425, 623.948425, 636.6484250000001, 650.6194250000001, 664.8984250000001, 665.768425, 668.719425, 675.8484250000001, 686.0984250000001, 688.748425, 689.268425, 694.8684250000001, 697.1184250000001, 697.8884250000001, 701.198425, 709.5684250000002, 711.038425, 711.6184250000001, 712.778425, 716.238425, 726.688425, 738.298425, 819.9474250000001, 824.1184250000001, 826.3384250000001, 828.287425, 831.3974250000001, 843.0884250000001, 859.3484250000001, 867.1974250000001, 869.9474250000001, 892.267425, 897.7074250000001, 899.807425, 905.767425, 914.3874250000001, 921.757425, 941.9574250000001, 943.4374250000001, 945.6574250000001, 950.4364250000001, 962.757425, 981.817425, 985.8864250000001, 991.3864250000001, 992.8574250000001, 1000.4174250000001, 1002.4564250000001, 1003.756425, 1004.756425, 1020.326425, 1047.286425, 1049.837425, 1061.3864250000001, 1067.226425, 1069.937425, 1073.956425, 1105.306425, 1110.456425, 1110.926425, 1112.026425, 1114.4064250000001,1131.266425, 1155.8764250000002, 1259.736425, 1266.715425, 1273.315425, 1286.3954250000002, 1489.685425], 'Paw into Joystick Box': [], 'Paw out of Joystick Box': [], 'Discriminant Stimuli On': [574.1719, 'X', 599.680775, 615.7476000000001,619.182875, 'X', 'X', 624.2347500000001, 626.2796000000001, 640.5143, 653.7151000000001, 'X', 667.883525, 670.8028000000002, 684.595, 689.0345, 696.64155, 'X',700.484825, 703.7967000000001, 711.3215500000001, 714.906, 720.9727500000001, 728.415925, 819.8016750000002, 826.1132, 828.5628000000002, 'X', 832.9339750000001, 867.248175, 869.2856000000002, 'X', 'X', 900.0221750000001, 902.4758750000001,907.5231000000001, 921.737975, 'X', 'X', 'X', 950.7121750000001, 954.17605, 966.8475000000001, 'X', 'X', 994.4594500000001, 1002.2634500000001, 'X', 1006.85645, 1037.0786500000002, 1060.933, 1063.3160500000001, 1069.1562000000001, 1071.9173250000001, 'X', 'X', 'X', 'X', 'X', 1120.136725, 1146.3127, 1246.571625, 1268.742475, 1275.758775, 1453.699125, 1491.665425], 'Discriminant Stimuli Off': [], 'Go Cue On': [575.1007500000001, 600.5840250000001, 620.0917, 627.1803, 641.4206750000001, 654.6170999999999, 668.7882750000001, 671.7047, 685.494475, 690.1594750000002, 701.3822500000001, 704.7056500000001, 712.4586750000001, 715.8101750000001, 721.87835, 729.3286500000002, 820.820275, 833.8110750000001, 870.203375, 903.3950750000001, 908.439075, 955.0883000000001, 967.716375, 995.3630500000002, 1003.2804000000001, 1007.767425, 1037.99505, 1064.22255, 1070.0715, 1072.82805, 1121.027, 1147.221925, 1247.48205, 1269.6542, 1276.6668750000001, 1454.605425, 1492.579175], 'Go Cue Off': [], 'Trial DS Type': [1, 0, 1, 3, 1, 0, 0, 1, 3, 2, 3, 0, 1, 2, 2, 3, 3, 0, 3, 2, 3, 1, 2, 3, 1, 2, 1, 0, 2, 1, 2, 0, 0, 1, 3, 3, 3, 0, 0, 0, 2, 3, 2, 0, 0, 3, 2, 0, 2, 2, 2, 2, 3, 3, 0, 0, 0, 0, 0, 3, 2, 2, 1, 3,2, 2], 'Duration in Home Zone': [21.25, 0.5599999999999454, 0.7999999999999545,14.829999999999927, 1.3299999999999272, 3.0299999999999727, 0.20000000000004547, 0.5399999999999636, 1.4100000000000819, 12.079999999999927, 11.701000000000022, 12.769000000000005, 0.599999999999909, 2.300999999999931, 6.629000000000133, 3.160000000000082, 1.2989999999999782, 0.3999999999998636, 5.519999999999982, 1.9500000000000455, 0.5099999999999909, 1.8799999999998818, 7.170000000000073, 1.2699999999999818, 0.37000000000011823, 0.8599999999999, 3.0499999999999545, 7.1099999999999, 11.409999999999854, 1.6300000000001091, 3.880000000000109, 1.7699999999999818, 1.2889999999999873, 0.8500000000001364, 11.490999999999985, 16.029999999999973, 1.25, 2.240000000000009, 0.32999999999992724, 0.6089999999999236, 1.5,4.899999999999864, 8.430000000000064, 1.6399999999998727, 1.1099999999999, 0.5699999999999363, 0.8400000000001455, 1.1290000000001328, 10.18100000000004, 16.569999999999936, 3.869000000000142, 0.7000000000000455, 0.8300000000001546, 7.360000000000127, 1.7889999999999873, 1.1199999999998909, 0.7400000000000091, 15.259999999999991, 11.918999999999869, 2.3509999999998854, 1.8600000000001273, 5.559999999999945, 2.2609999999999673, 3.5289999999999964, 0.849999999999909, 0.5599999999999454, 0.2699999999999818, 0.8699999999998909, 0.13000000000010914, 12.559999999999945, 11.160000000000082, 14.789999999999964, 6.689000000000078, 5.8599999999999, 11.920000000000073, 37.539999999999736], 'Trial Outcome': ['Success', 'Success', 't1 Fail', 'Success', 't2 Fail', 'Success', 't1 Fail', 't1 Fail', 't2 Fail', 'Success', 'Success', 'Success', 't1 Fail', 'Success', 'Success', 'Success', 't2 Fail', 't2 Fail', 'Success', 't2 Fail', 't1 Fail', 'Success', 'Success', 't2 Fail', 't2 Fail', 'Success', 'Success', 'Success', 'Success', 't2 Fail', 'Success', 't2 Fail', 't2 Fail', 't1 Fail', 'Success', 'Success', 't2 Fail', 'Success', 't1 Fail', 't1 Fail', 't2 Fail', 'Success', 'Success', 't2 Fail', 't1 Fail', 't1 Fail', 't1 Fail', 't2 Fail', 'Success', 'Success', 'Success', 't1 Fail', 't1 Fail', 'Success', 't2 Fail', 'Success', 't1 Fail', 'Success', 'Success', 'Success', 't2 Fail', 'Success', 'Success', 'Success', 't1 Fail', 't1 Fail', 't1 Fail', 't1 Fail', 't1 Fail', 'Success', 'Success', 'Success', 'Success', 'Success','Success', 'Success'], 'Ranges': [{1: [0.04999999999999999, 0.5, 0.95], 2: [0.06999999999999995, 0.75, 1.4300000000000002], 3: [0.09999999999999998, 1, 1.9]}],'Inter Trial Time': [0.5], 'Adaptive Value': [0.05], 'Adaptive Algorithm': [1],'Adaptive Frequency': [50], 'Enable Early Pull Time Out': [False], 'Correct Start Press 1': [], 'Correct End Press 1': [], 'Correct Duration 1': [], 'Correct Stim Count 1': [0], 'Incorrect Start Press 1': [], 'Incorrect End Press 1': [], 'Incorrect Duration 1': [], 'Discriminatory Stimulus 1': [574.1719, 599.680775, 619.182875, 624.2347500000001, 667.883525, 714.906, 819.8016750000002, 828.5628000000002, 867.248175, 900.0221750000001, 1268.742475], 'Go Cue 1': [575.1007500000001, 600.5840250000001, 620.0917, 668.7882750000001, 715.8101750000001, 820.820275, 1269.6542], 'Correct Start Press 2': [], 'Correct End Press 2': [], 'Correct Duration 2': [], 'Correct Stim Count 2': [0], 'Incorrect Start Press 2': [], 'Incorrect End Press 2': [], 'Incorrect Duration 2': [], 'Discriminatory Stimulus2': [640.5143, 670.8028000000002, 684.595, 703.7967000000001, 720.9727500000001, 826.1132, 832.9339750000001, 869.2856000000002, 950.7121750000001, 966.8475000000001, 1002.2634500000001, 1006.85645, 1037.0786500000002, 1060.933, 1063.3160500000001, 1146.3127, 1246.571625, 1453.699125, 1491.665425], 'Go Cue 2': [641.4206750000001, 671.7047, 685.494475, 704.7056500000001, 721.87835, 833.8110750000001, 870.203375, 967.716375, 1003.2804000000001, 1007.767425, 1037.99505, 1064.22255, 1147.221925, 1247.48205, 1454.605425, 1492.579175], 'Correct Start Press 3': [], 'Correct End Press 3': [], 'Correct Duration 3': [], 'Correct Stim Count 3': [0], 'Incorrect Start Press 3': [], 'Incorrect End Press 3': [], 'Incorrect Duration 3': [], 'Discriminatory Stimulus 3': [615.7476000000001, 626.2796000000001, 653.7151000000001, 689.0345, 696.64155, 700.484825, 711.3215500000001, 728.415925, 902.4758750000001, 907.5231000000001, 921.737975, 954.17605, 994.4594500000001, 1069.1562000000001, 1071.9173250000001, 1120.136725, 1275.758775], 'Go Cue 3': [627.1803, 654.6170999999999, 690.1594750000002, 701.3822500000001, 712.4586750000001, 729.3286500000002, 903.3950750000001, 908.439075, 955.0883000000001, 995.3630500000002, 1070.0715, 1072.82805, 1121.027, 1276.6668750000001]}

    FormatDurations()
    
