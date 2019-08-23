##### VERY IMPORTANT: Possibly have Pedal1 and Pedal3 switched for testing using Francois Setup.Approx Lines: 182-197 Check these if problems occur.
#Also check around line 41 that self.readyforplexon = True
### FOR RYAN: Use Line 4, it contains all the definitions listed just below (lines 6-33)
#from definitionsRyan import * #Given definitions to Ryan. It might need updates for later
###################### These are all called in line 4 above from definitionsRyan import *. -They are listed here for Nathan's testing
import tkinter as tk
from tkinter import *
from PIL import Image, ImageTk
import os
import time
import random
import winsound
import math
##############################################################################################
#TODO:Commented out code in first def is for changing to dictionary that's paired with events
##############################################################################################
def RewardClass(num_of_events, *args): #Duration is the input of how long the animal will press
    counter = 0
    index = 0
    Ranges = []
    # Ranges = {}
    # for i in range(num_of_events):
    #     Ranges[(i+1)] = []
    if len(args)%2 == 1:
        input("Odd number of args. This might cause errors. Press Enter to continue")
    elif len(args)/2 != num_of_events:
        input("Range Arguments given, does not match number of expected events. Press Enter to continue")
    for arg in args:
        counter = counter + 1
        peak = math.trunc((counter + 1) / 2)
        if counter%2 == 1:
            print('This arg is for peak {} center: {}'.format(peak,arg))
            arg_center = arg
        else:
            index += 1
            print('This arg is for peak {} width: {}'.format(peak,arg))
            arg_width = arg
            low = arg_center - arg_width
            high = arg_center + arg_width
            print('The range for interval {} is {} to {}'.format(peak,low,high))
            # Ranges[index].append(low)
            # Ranges[index].append(arg_center)
            # Ranges[index].append(high)
            Ranges.append(low)
            Ranges.append(arg_center)
            Ranges.append(high)
    print(Ranges)
    return Ranges
######################


###Monkey Images Class set up for Tkinter GUI
class MonkeyImages(tk.Frame,):
    def __init__(self, parent, *args, **kwargs):
        self.readyforplexon = False ### Nathan's Switch for testing while not connected to plexon omni. I will change to true / get rid of it when not needed.
                                   ### Also changed the server set up so that it won't error out and exit if the server is not on, but it will say Client isn't connected.
        self.MonkeyLoop = False
        self.CurrentPress = False
        self.RewardReady = False
        self.PictureCue = False
        self.ReadyForSound = False
        self.PunishLockout = False
        self.ReadyForSound = False
        self.ReadyForPull = False
        self.RewardReady = False
        self.Area1 = False
        self.Area2 = True #???????????? Will have to test how cineplex acts to determine starting bool for Area 1 and 2 ?????????
        self.ImageReward = False
        self.PictureCueTimeInterval = 5 #(seconds) Duration between animal in start position (Area 2) and displaying an image cue.
        self.StartTime = time.time()
        self.RelStartTime = time.time() - self.StartTime
        self.CueTime = time.time()
        self.RelCueTime = time.time() - self.CueTime
        self.CueEndTime = time.time()
        self.RelCueEndTime = time.time() - self.CueEndTime
        self.SoundTime = time.time()
        self.RelSoundTime = time.time() - self.SoundTime
        self.PressTime = time.time()
        self.RelPressTime = time.time() - self.PressTime
        self.Pedal = 0 #Initialize Pedal/Press
        self.PullThreshold = 4.5 #(Voltage)Amount that Monkey has to pull to. Will be 0 or 5???\
        self.PullDuration = 0.5 #(seconds)Duration that animal has to pull lever for.
        self.PictureDuration = 3 #(seconds)How long is the picture displayed for.
        self.TimeBeforeSound = 1 #(seconds)
        self.MaxTimeAfterSound = 5 #(seconds) Maximum time Monkey has to pull. I think we want this, not sure. ???
        self.RewardDelay = 0.5 #(seconds)Length of Delay before Reward is given.
        self.Pedal1 = 0 #Push / Forward
        self.Pedal2 = 0 #Right
        self.Pedal3 = 0 #Pull / Backwards
        self.Pedal4 = 0 #Left
        self.RewardDO_chan = 1
        self.RewardSound = 'Exclamation'
        self.MaxReward = 0.18 #(seconds, maximum time to give water)
        #RangeIntervals = RewardClass(0.5,0.05,1,0.25,2,0.45)  #Sample RangeIntervals for Monkey Test

        ########################
        num_of_evts = 1 #Testing
        ########################
        
        RangeIntervals = RewardClass(num_of_evts,2,1.5) #Hi Ryan, I added this range for your testing for now, because I changed where the reward is given so that it has to fit into an interval now.
        self.Ranges = RangeIntervals#Sets up Intervals, Odd args are peaks, Even args are width.
        self.ImageRatio = 75 # EX: ImageRatio = 75 => 75% Image Reward, 25% Water Reward , Currently does not handle the both choice for water and image.
        
        print('mainloop')
        print("ready for plexon:" , self.readyforplexon)
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.root.wm_title("MonkeyImages")
        src = "./TestImages/" #Name of folder in which you keep your images to be displayed
        
        if self.readyforplexon == True:
            ##Setup Plexon Server
            # Initialize the API class
            self.client = PyOPXClientAPI()
            # Connect to OmniPlex Server, check for success
            self.client.connect()
            if not self.client.connected:
                print("Client isn't connected, exiting.\n")
                print("Error code: {}\n".format(self.client.last_result))
                self.readyforplexon = False
                
            print("Connected to OmniPlex Server\n")
            # Get global parameters
            global_parameters = self.client.get_global_parameters()
            # For this example, we'll treat DO channel 8 as if it's connected
            # to the OmniPlex strobe input
            strobe_channel = 9
            for source_id in global_parameters.source_ids:
                source_name, _, _, _ = self.client.get_source_info(source_id)
                if source_name == 'KBD':
                    self.keyboard_event_source = source_id
                if source_name == 'AI':
                    self.ai_source = source_id
            # Print information on each source

            ##### Need to include information here about getting Digital signals ############


            for index in range(global_parameters.num_sources):
                # Get general information on the source
                source_name, source_type, num_chans, linear_start_chan = self.client.get_source_info(global_parameters.source_ids[index])
                # Store information about the source types and names for later use.
                source_numbers_types[global_parameters.source_ids[index]] = source_type
                source_numbers_names[global_parameters.source_ids[index]] = source_name
                if source_name == 'AI':
                    print("----- Source {} -----".format(global_parameters.source_ids[index]))
                    print("Name: {}, Type: {}, Channels: {}, Linear Start Channel: {}".format(source_name,
                                                                                    source_types[source_type],
                                                                                    num_chans,
                                                                                    linear_start_chan))
                if source_type == CONTINUOUS_TYPE and source_name == 'AI':
                    # Get information specific to a continuous source
                    _, rate, voltage_scaler = self.client.get_cont_source_info(source_name)     
                    # Store information about the source rate and voltage scaler for later use.
                    source_numbers_rates[global_parameters.source_ids[index]] = rate
                    source_numbers_voltage_scalers[global_parameters.source_ids[index]] = voltage_scaler
                    print("Digitization Rate: {}, Voltage Scaler: {}".format(rate, voltage_scaler))   
            ##Setup for Plexon DO
            compatible_devices = ['PXI-6224', 'PXI-6259']
            self.plexdo = PyPlexDO()
            doinfo = self.plexdo.get_digital_output_info()
            self.device_number = 1
            for k in range(doinfo.num_devices):
                if self.plexdo.get_device_string(doinfo.device_numbers[k]) in compatible_devices:
                    device_number = doinfo.device_numbers[k]
            if device_number == None:
                print("No compatible devices found. Exiting.")
                sys.exit(1)
            else:
                print("{} found as device {}".format(self.plexdo.get_device_string(device_number), device_number))
            res = self.plexdo.init_device(device_number)
            if res != 0:
                print("Couldn't initialize device. Exiting.")
                sys.exit(1)
            self.plexdo.clear_all_bits(device_number)
            ##End Setup for Plexon DO




        self.list_images = []
        for images in os.listdir(src):
            self.list_images.append(images)

        ###Adjust width and height to fit monitor### bd is for if you want a border
        self.frame1 = tk.Frame(self.root, width = 1600, height = 1000, bd = 0)
        self.frame1.pack(side = BOTTOM)
        self.cv1 = tk.Canvas(self.frame1, width = 1600, height = 800, background = "white", bd = 1, relief = tk.RAISED)
        self.cv1.pack(side = BOTTOM)

        startbutton = tk.Button(self.root, text = "Start", height = 5, width = 5, command = self.START)
        startbutton.pack(side = LEFT)

        endbutton = tk.Button(self.root, text = "Stop", height = 5, width = 5, command = self.END)
        endbutton.pack(side = LEFT)

        ImageRewardOn = tk.Button(self.root, text = "ImageReward\nOn", height = 5, width = 10, command = self.HighLevelRewardOn)
        ImageRewardOn.pack(side = LEFT)
        ImageRewardOff = tk.Button(self.root, text = "ImageReward\nOff", height = 5, width = 10, command = self.HighLevelRewardOff)
        ImageRewardOff.pack(side = LEFT)

        self.counter = 0
        self.max_count = len(self.list_images) - 1


##########################################################################################################################################
    def LOOP(self):
        #try: #For Later when we want a try block to catch exceptions.
            if self.MonkeyLoop == True:
                if self.readyforplexon == True:
                    #Gather new data
                    new_data = self.client.get_new_data()
                    if new_data.num_data_blocks < max_block_output:
                        num_blocks_to_output = new_data.num_data_blocks
                    else:
                        num_blocks_to_output = max_block_output
                    # If a keyboard event is in the returned data, perform action
                    for i in range(new_data.num_data_blocks):
                        if new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 1: #Alt 1
                            pass
                        elif new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 2: #Alt 2
                            pass
                        elif new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 8: #Alt 8 - Manual Stop Code
                            MonkeyLoop = False
                    #For other new data find the AI channel 1 data for pedal
                    for i in range(new_data.num_data_blocks):
                        try:
                            if source_numbers_types[new_data.source_num_or_type[i]] == CONTINUOUS_TYPE and (new_data.channel[i] == 1 or new_data.channel[i] == 2 or new_data.channel[i] == 3 or new_data.channel[i] == 4):
                                # Output info
                                tmp_source_number = new_data.source_num_or_type[i]
                                tmp_channel = new_data.channel[i]
                                tmp_source_name = source_numbers_names[tmp_source_number]
                                tmp_voltage_scaler = source_numbers_voltage_scalers[tmp_source_number]
                                tmp_timestamp = new_data.timestamp[i]
                                tmp_unit = new_data.unit[i]
                                tmp_rate = source_numbers_rates[tmp_source_number]

                                # Convert the samples from AD units to voltage using the voltage scaler
                                tmp_samples = new_data.waveform[i][:max_samples_output]
                                tmp_samples = [s * tmp_voltage_scaler for s in tmp_samples]
                                if new_data.channel[i] == 1:
                                    self.Pedal1 = tmp_samples[0] # Assign Pedal from AI continuous
                                    # Construct a string with the samples for convenience
                                    tmp_samples_str = str(self.Pedal1)
                                elif new_data.channel[i] == 2:
                                    self.Pedal2 = tmp_samples[0] # Assign Pedal from AI continuous
                                    # Construct a string with the samples for convenience
                                    tmp_samples_str = str(self.Pedal2)
                                elif new_data.channel[i] == 3:
                                    self.Pedal3 = tmp_samples[0] # Assign Pedal from AI continuous
                                    # Construct a string with the samples for convenience
                                    tmp_samples_str = str(self.Pedal3)
                                elif new_data.channel[i] == 4:
                                    self.Pedal4 = tmp_samples[0] # Assign Pedal from AI continuous
                                    # Construct a string with the samples for convenience
                                    tmp_samples_str = str(self.Pedal4)

                                #print values that we want from AI
                                #if new_data.channel[i] == 1:
                                    #print("SRC:{} {} TS:{} CH:{} WF:{}".format(tmp_source_number, tmp_source_name, tmp_timestamp, tmp_channel, tmp_samples_str))
                        except KeyError:
                            continue
                    #end of gathering data    
                
                if self.PictureCue == False and self.RelStartTime >=  self.PictureCueTimeInterval: 
                    print('Random pic')
                    self.PictureCue = True# This will be on for the duration of the trial
                    self.counter = random.randint(1,len(self.list_images)-1) #Randomly chooses next image -Current,will change the range depending on which images are to be shown here.
                    self.CueTime = time.time()
                    self.RelCueTime = time.time() - self.CueTime
                    self.next_image()

                elif self.PictureCue == True and self.RelCueTime >= self.PictureDuration and self.ReadyForSound == False:
                    print('Blank')
                    self.ReadyForSound = True
                    self.counter = 0
                    self.next_image()
                    self.CueEndTime = time.time()
                    self.RelCueEndTime = time.time() - self.CueEndTime
                    
                
                ### Needs to play a sound cue for animal.
                elif self.ReadyForSound == True and self.RelCueEndTime >= self.TimeBeforeSound and self.ReadyForPull == False:
                    print('Sound')
                    self.ReadyForPull = True
                    self.SoundTime = time.time()
                    self.RelSoundTime = time.time() - self.SoundTime
                    winsound.PlaySound(winsound.Beep(750,1000), winsound.SND_ALIAS | winsound.SND_ASYNC) #750 Hz, 1000 ms
                
                elif self.ReadyForPull == True and self.Pedal3 >= self.PullThreshold: #If Lever is Pulled On and ready for pull
                    if self.CurrentPress == False:
                        print('Pull')
                        self.CurrentPress = True
                        self.PressTime = time.time()
                    else:


##############################################################################################################################################################################
# TODO: Pretty sure that Pedal3 has to be updated in this loop.
##############################################################################################################################################################################


                        while self.Pedal3 >= self.PullThreshold:                    ### While loop in place to continuously and quickly update the Press Time for the Duration that
                            self.RelPressTime = time.time() - self.PressTime        ### The Monkey is Pulling it for. This will reduce latency issues with running through the whole
                        print('Pull for: {} seconds'.format(self.RelPressTime))     ### Loop.
                        self.RewardTime = self.ChooseReward(self.RelPressTime,self.Ranges,self.MaxReward)
                        if self.RewardTime > 0:                                     ### Reward will Only be Given if the Pull Duration Falls in one of the intervals.
                            self.RewardReady = True
                elif self.RewardReady == True:
                    Reward = self.ChooseOne(self.ImageRatio)
                    if self.ImageReward == True and Reward == 1:
                        print('Image Reward coming soon to a Pedal Press Project near you!')
                    else:
                        winsound.PlaySound(winsound.Beep(550,500), winsound.SND_ALIAS | winsound.SND_ASYNC)
                        print('Press Duration: {}'.format(self.RelPressTime))
                        print('Reward Duration: {}'.format(self.RewardTime))
                        winsound.PlaySound(self.RewardSound, winsound.SND_ALIAS | winsound.SND_ASYNC)
                        time.sleep(self.RewardDelay)
                        print("Water On")
                        self.plexdo.set_bit(self.device_number, self.RewardDO_chan)
                        time.sleep(self.RewardTime)
                        self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
                        print("Water Off")
                        self.CurrentPress = False
                        self.RewardReady = False
                        self.PictureCue = False
                        self.ReadyForSound = False
                        self.PunishLockout = False
                        self.ReadyForSound = False
                        self.ReadyForPull = False
                        self.RewardTime = 0
                        self.RewardReady = False
                        self.StartTime = time.time() #Update start time for next cue.
                        self.RelStartTime = time.time() - self.StartTime

                elif self.RelSoundTime >= self.MaxTimeAfterSound and self.ReadyForPull == True:
                    print('Time Elapsed, wait for Cue again.')
                    self.CurrentPress = False
                    self.RewardReady = False
                    self.PictureCue = False
                    self.ReadyForSound = False
                    self.PunishLockout = False
                    self.ReadyForSound = False
                    self.ReadyForPull = False
                    self.StartTime = time.time() #Update start time for next cue.
                    self.RelStartTime = time.time() - self.StartTime

                #End of Loop, track times
                self.RelStartTime = time.time() - self.StartTime
                self.RelCueTime = time.time() - self.CueTime 
                self.RelCueEndTime = time.time() - self.RelCueEndTime
                self.RelSoundTime = time.time() - self.SoundTime ###This Timing is used for if animal surpasses max time to do task, needs to update every loop
                self.after(1,func=self.LOOP)
        #except: #For Later when we want a try block to deal with errors, will help to properly stop water in case of emergency.
        #    print('Error')
        #    if self.readyforplexon == True:
        #        self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
    

##########################################################################################################################################
    def ChooseOne(self,RewardRatio): #Repurposed code to choose between image and water randomly given a percentage MonkeyTest.ImageRatio in the main
        rand = random.randint(0,100)
        if rand <= RewardRatio: 
            output = 1  #Image Reward
        else:
            output = 2  #Water Reward
        return output

############################################################################################################################################
            #TODO: Need to add event to the choose reward inputs. This will come from the event cue that is shown ( Can Use self.counter )
############################################################################################################################################
    def ChooseReward(self,Duration,Ranges,MaxReward): #Ranges[i] ~ low, Ranges[i+1] ~ center, Ranges[i+2] ~ high
        #currently counter can be 1,2,3 for the 3 images. 8/23/2019

        # counter = self.counter

        # if Duration >= Ranges[counter][0] and Duration <= Ranges[counter][2]: #Checks that duration is within the range. 
        #     Value = abs(Ranges[i+1] - Duration)/(Ranges[i+1]-Ranges[i])
        #     RewardDuration = MaxReward - (Value * MaxReward)
        # return RewardDuration



        for i in range(len(Ranges)):
            if i%3 == 0  and Duration >= Ranges[i] and Duration <= Ranges[i+2]: #Checks that duration is within the range. 
                Value = abs(Ranges[i+1] - Duration)/(Ranges[i+1]-Ranges[i])
                #print('Value {}'.format(Value))
                RewardDuration = MaxReward - (Value * MaxReward)
        return RewardDuration
############################################################################################################################################


    def START(self):
        self.MonkeyLoop = True
        self.StartTime = time.time()
        self.RelStartTime = time.time() - self.StartTime
        root.after(1,func=self.LOOP) #Polls for other inputs

    def END(self): ###IMPORTANT###Need to make sure this END cleans up any lose ends, such as WaterReward being open. Anything Else?
        print('Stop')
        self.MonkeyLoop = False
        self.PictureCue = False
        self.CurrentPress = False
        self.RewardReady = False
        self.ReadyForSound = False
        self.PunishLockout = False
        self.ReadyForSound = False
        self.ReadyForPull = False
        if self.readyforplexon == True:
            self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
        self.counter = 0
        self.next_image()
        root.after(1,func=None)
    
    ### These attach to buttons that will select if Monkey has access to the highly coveted monkey image reward
    def HighLevelRewardOn(self):
        print('Image Reward On')
        print('Image Reward coming soon to a Pedal Press Project near you!')
        self.ImageReward = True

    def HighLevelRewardOff(self):
        print('Image Reward Off')
        print('Image Reward coming soon to a Pedal Press Project near you!')
        self.ImageReward = False
    ###
    def next_image(self): #This is the call for nextimage, set counter to 0 and run next_image to get blank. For this to work need a blank image in first position in directory.
        if self.counter > self.max_count:
            print("No more images")
        else:
            im = Image.open("{}{}".format("./TestImages/", self.list_images[self.counter]))
            if (490-im.size[0])<(390-im.size[1]):
                width = 1600
                height = width*im.size[1]/im.size[0]
                self.next_step(height, width)
            else:
                height = 800
                width = height*im.size[0]/im.size[1]
                self.next_step(height, width)

    def next_step(self, height, width):
        self.im = Image.open("{}{}".format("./TestImages/", self.list_images[self.counter]))
        self.im.thumbnail((width, height), Image.ANTIALIAS)
        self.root.photo = ImageTk.PhotoImage(self.im)
        self.photo = ImageTk.PhotoImage(self.im)

        if self.counter == 0:
            self.cv1.create_image(0, 0, anchor = 'nw', image = self.photo)

        else:
            self.im.thumbnail((width, height), Image.ANTIALIAS)
            self.cv1.delete("all")
            self.cv1.create_image(0, 0, anchor = 'nw', image = self.photo)

        

if __name__ == "__main__":
    root = tk.Tk()
    
    #Parameters (Parameters set as objects that can be handled through GUI Class functions):
    MonkeyTest = MonkeyImages(root)

    tk.mainloop()
