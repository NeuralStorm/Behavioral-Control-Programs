##### VERY IMPORTANT: Possibly have Pedal1 and Pedal3 switched for testing using Francois Setup.Approx Lines: ~500~ Check these if problems occur.
#Also check around line ~20~ that self.readyforplexon = True
### FOR RYAN: Use Line 4, it contains all the definitions listed just below (lines 6-33)
#from definitionsRyan import * #Given definitions to Ryan. It might need updates for later. If you use this and some are missing you can uncomment them below
###################### These are all called in line 4 above from definitionsRyan import *. -They are listed here for Nathan's testing
import tkinter as tk
from tkinter import *
import threading as t
from PIL import Image, ImageTk
import os
import time
import random
import winsound
import math
import queue
##############################################################################################
###Monkey Images Class set up for Tkinter GUI
class MonkeyImages(tk.Frame,):
    def __init__(self, parent, *args, **kwargs):
        self.readyforplexon = False ### Nathan's Switch for testing while not connected to plexon omni. I will change to true / get rid of it when not needed.
                                    ### Also changed the server set up so that it won't error out and exit if the server is not on, but it will say Client isn't connected.

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

        ############# Specific for pedal Press Tasks
        self.Pedal = 0 #Initialize Pedal/Press
        self.PullThreshold = 4.5 #(Voltage)Amount that Monkey has to pull to. Will be 0 or 5, because digital signal from pedal. (Connected to Analog input in plexon?)
        self.DiscrimStimDuration = round((random.randint(60,180)/60),2) # (seconds)How long is the Discriminative Stimulus displayed for. Currently 1 to 3 seconds.
        self.TimeBeforeSound = 1 #(seconds)
        self.MaxTimeAfterSound = 5 #(seconds) Maximum time Monkey has to pull. I think we want this, not sure. ???
        self.RewardDelay = 0.5 #(seconds)Length of Delay before Reward is given.
        self.Pedal1 = 0 #Push / Forward
        self.Pedal2 = 0 #Right
        self.Pedal3 = 0 #Pull / Backwards
        self.Pedal4 = 0 #Left
        self.list_images = [] # Image list for Discriminative Stimuli
        src = "./TestImages/" #Name of folder in which you keep your images to be displayed
        for images in os.listdir(src):
            self.list_images.append(images)

        self.NumEvents = 3
        # RangeIntervals = RewardClass(0.5,0.05,1,0.25,2,0.45)  #Sample RangeIntervals for Monkey Test
        self.DurationList()                                 #Creates dict of lists to encapsulate press durations. Will be used for Adaptive Reward Control
        self.AdaptiveValue = 0.05                           # Probably going to use this in the form of a value that represents a percent. (EX: 0.05 = 5%)
        self.AdaptiveAlgorithm = 1                          # 1: Percentage based change 2: mean, std, calculated shift of distribution (Don't move center?) 3: TBD Move center as well?
        self.AdaptiveFrequency = 50                         # Number of trials inbetween calling AdaptiveRewardThreshold()


        self.RewardClass(self.NumEvents,1,0.5,2,0.75,3,1)   #Hi Ryan, I added this range for your testing for now, because I changed where the reward is given so that it has to fit into an interval now.
        self.counter = 0
        self.current_counter = 0
        self.excluded_events = [] #Might want this for excluded events
        self.ImageRatio = 75 # EX: ImageRatio = 75 => 75% Image Reward, 25% Water Reward , Currently does not handle the both choice for water and image.
        ############# Omniplex / Map Channels
        self.RewardDO_chan = 1
        self.Area1_right = 5
        self.Area2_right = 6
        self.Area1_left = 7
        self.Area2_left = 8

        #############
        # Queue
        self.queue = queue.Queue()

        ############# Rewards
        self.RewardSound = 'Exclamation'
        self.Bloop       = 'Question'
        self.MaxReward = 0.18 #(seconds, maximum time to give water)
        self.WaterReward = self.WaterRewardThread(self.queue)
        ##############

        # Parameters (Parameters built into GUI Class functions):
        self.MonkeyLoop = False
        self.StartTrialBool = False
        self.CurrentPress = False
        self.RewardReady = False
        self.PictureBool = False
        self.ReadyForSound = False
        self.PunishLockout = False
        self.ReadyForPull = False
        self.RewardReady = False
        #Rename Area1 and Area2
        self.Area1 = False
        self.Area2 = True #???????????? Will have to test how cineplex acts to determine starting bool for Area 1 and 2 ?????????
        self.ImageReward = False
        self.PictureCueTimeInterval = 5 #(seconds) Duration between animal in start position (Area 2) and displaying an image cue.

        self.StartTime = time.time()
        self.RelStartTime = time.time() - self.StartTime
        self.CueTime = time.time()
        self.RelCueTime = time.time() - self.CueTime
        self.DiscrimStimTime = time.time()
        self.RelDiscrimStimTime = time.time() - self.DiscrimStimTime
        self.SoundTime = time.time()
        self.RelSoundTime = time.time() - self.SoundTime
        self.PressTime = time.time()
        self.RelPressTime = time.time() - self.PressTime

        print('mainloop')
        print("ready for plexon:" , self.readyforplexon)
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.root.wm_title("MonkeyImages")

        ###Adjust width and height to fit monitor### bd is for if you want a border
        self.frame1 = tk.Frame(self.root, width = 1600, height = 1000, bd = 0)
        self.frame1.pack(side = BOTTOM)
        self.cv1 = tk.Canvas(self.frame1, width = 1600, height = 800, background = "white", bd = 1, relief = tk.RAISED)
        self.cv1.pack(side = BOTTOM)

        startbutton = tk.Button(self.root, text = "Start", height = 5, width = 5, command = self.Start)
        startbutton.pack(side = LEFT)

        endbutton = tk.Button(self.root, text = "Stop", height = 5, width = 5, command = self.End)
        endbutton.pack(side = LEFT)

        testbutton = tk.Button(self.root, text = "Test", height = 5, width = 5, command = self.Test)
        testbutton.pack(side = LEFT)

        # Likely Don't Need these buttons, Image reward will always be an option, and will be controlled by %
        ImageRewardOn = tk.Button(self.root, text = "ImageReward\nOn", height = 5, width = 10, command = self.HighLevelRewardOn)
        ImageRewardOn.pack(side = LEFT)
        ImageRewardOff = tk.Button(self.root, text = "ImageReward\nOff", height = 5, width = 10, command = self.HighLevelRewardOff)
        ImageRewardOff.pack(side = LEFT)

        self.root.bind('<Key>', lambda a : self.KeyPress(a))


##########################################################################################################################################
    def LOOP(self): #LOOP will be different for each experiment
        #try: #For Later when we want a try block to catch exceptions.
            if self.MonkeyLoop == True:
                if self.readyforplexon == True:
                    #Gather new data
                    self.gathering_data_omni()

                # Flashing box for trial start cue + low freq sound.
                if self.StartTrialBool == True:
                    self.StartTrialCue()

                if self.PictureBool == False and self.RelStartTime >=  self.PictureCueTimeInterval: #This will be changed to # if self.PictureBool == False and self.Area1 == True:
                    print('Random pic')
                    self.StartTrialBool = False
                    self.PictureBool = True# This will be on for the duration of the trial
################################################################################################################################################################################################
                    #while self.counter not in self.excluded_events: #Don't use excluded events
                    #Need to work on this logic to choose a counter value that is not in self.excluded_events
################################################################################################################################################################################################
                    self.counter = random.randint(1,self.NumEvents) #Randomly chooses next image -Current,will change the range depending on which images are to be shown here.
                    self.current_counter = self.counter
                    self.CueTime = time.time()
                    self.RelCueTime = time.time() - self.CueTime
                    self.next_image()

                # TODO: Discriminatory Stimulus here
                elif self.PictureBool == True and self.RelCueTime >= self.DiscrimStimDuration and self.ReadyForPull == False:
                    self.ReadyForPull = True
                    self.counter = self.counter + self.NumEvents
                    self.next_image()
                    self.DiscrimStimTime = time.time()
                    self.RelDiscrimStimTime = time.time() - self.DiscrimStimTime

                ### Needs to play a sound cue for animal.
                # elif self.ReadyForSound == True and self.RelDiscrimStimTime >= self.TimeBeforeSound and self.ReadyForPull == False:
                #     print('Sound')
                #     self.ReadyForPull = True
                #     self.SoundTime = time.time()
                #     self.RelSoundTime = time.time() - self.SoundTime
                #     winsound.PlaySound(winsound.Beep(750,1000), winsound.SND_ALIAS | winsound.SND_ASYNC) #750 Hz, 1000 ms
                
                # If Lever is PUlled On and ready for Pull
                elif self.ReadyForPull == True and self.Pedal3 >= self.PullThreshold:
                    if self.CurrentPress == False:
                        print('Pull')
                        self.CurrentPress = True
                        self.PressTime = time.time()
                    else:
                        while self.Pedal3 >= self.PullThreshold:                    ### While loop in place to continuously and quickly update the Press Time for the Duration that
                            self.gathering_data_omni()
                            self.RelPressTime = time.time() - self.PressTime        ### The Monkey is Pulling it for. This will reduce latency issues with running through the whole
                        print('Pull for: {} seconds'.format(self.RelPressTime))     ### Loop.
                        self.AddDuration(self.RelPressTime)
                        self.RewardTime = self.ChooseReward(self.RelPressTime)
                        if self.RewardTime > 0:                                     ### Reward will Only be Given if the Pull Duration Falls in one of the intervals.
                            self.RewardReady = True
                elif self.RewardReady == True:                                      ### Reward will be Water or Image or Both
                    Reward = self.ChooseOne(self.ImageRatio)
                    if self.ImageReward == True and Reward == 1:
                        print('Image Reward coming soon to a Pedal Press Project near you!')
                    else:
                        winsound.PlaySound(winsound.Beep(550,500), winsound.SND_ALIAS | winsound.SND_ASYNC)
                        print('Press Duration: {}'.format(self.RelPressTime))
                        print('Reward Duration: {}'.format(self.RewardTime))
                        winsound.PlaySound(self.RewardSound, winsound.SND_ALIAS | winsound.SND_ASYNC)
                        self.WaterReward.run()
                        self.CurrentPress = False
                        self.RewardReady = False
                        self.PictureBool = False
                        self.ReadyForSound = False
                        self.PunishLockout = False
                        self.ReadyForPull = False
                        self.RewardTime = 0
                        self.RewardReady = False
                        self.DiscrimStimDuration = round((random.randint(60,180)/60),2)
                        self.StartTime = time.time() #Update start time for next cue.
                        self.RelStartTime = time.time() - self.StartTime

                # Reset
                elif self.RelDiscrimStimTime >= self.MaxTimeAfterSound and self.ReadyForPull == True:
                    print('Time Elapsed, wait for Cue again.')
                    self.counter = 0
                    self.CurrentPress = False
                    self.StartTrialBool = True
                    self.RewardReady = False
                    self.PictureBool = False
                    self.ReadyForSound = False
                    self.PunishLockout = False
                    self.ReadyForSound = False
                    self.ReadyForPull = False
                    self.DiscrimStimDuration = round((random.randint(60,180)/60),2)
                    self.StartTime = time.time() #Update start time for next cue.
                    self.RelStartTime = time.time() - self.StartTime

                #End of Loop, track times
#########################################################################################################
                # TODO: Adaptive Thresholding to check lengths of duration lists here
#########################################################################################################
                try:
                    if len(self.durationdict[self.current_counter])%self.AdaptiveFrequency == 0:
                        self.AdaptiveRewardThreshold(self.AdaptiveValue,self.AdaptiveAlgorithm)
                except KeyError:
                    pass
                # self.update_idletasks
                self.RelStartTime = time.time() - self.StartTime
                self.RelCueTime = time.time() - self.CueTime
                self.RelDiscrimStimTime = time.time() - self.DiscrimStimTime
                self.RelSoundTime = time.time() - self.SoundTime###This Timing is used for if animal surpasses max time to do task, needs to update every loop
                self.after(1,func=self.LOOP)
        #except: #For Later when we want a try block to deal with errors, will help to properly stop water in case of emergency.
        #    print('Error')
        #    if self.readyforplexon == True:
        #        self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
    

##########################################################################################################################################
    def ChooseOne(self,Ratio):
        rand = random.randint(1,100)
        if rand <= Ratio: 
            output = 1
        else:
            output = 2
        return output
######################
    def RewardClass(self, num_of_events, *args): #Duration is the input of how long the animal will press
        rewcounter = 0
        index = 0
        self.Ranges = {}
        for i in range(num_of_events):
            self.Ranges[(i+1)] = []
        if len(args)%2 == 1:
            input("Odd number of args. This might cause errors. Press Enter to continue")
        if len(args)/2 != num_of_events:
            input("Range Arguments given, does not match number of expected events. Press Enter to continue")
        for arg in args:
            rewcounter = rewcounter + 1
            peak = math.trunc((rewcounter + 1) / 2)
            if rewcounter%2 == 1:
                print('This arg is for peak {} center: {}'.format(peak,arg))
                arg_center = arg
            else:
                index += 1
                print('This arg is for peak {} width: {}'.format(peak,arg))
                arg_width = arg
                low = arg_center - arg_width
                high = arg_center + arg_width
                print('The range for interval {} is {} to {}'.format(peak,low,high))
                self.Ranges[index].append(low)
                self.Ranges[index].append(arg_center)
                self.Ranges[index].append(high)
        print(self.Ranges)
############################################################################################################################################
            #TODO: Need to add event to the choose reward inputs. This will come from the event cue that is shown ( Can Use self.current_counter )
############################################################################################################################################
    def ChooseReward(self,Duration): #New (8/23/2019): Ranges = {X: [low, center, high],..., X:[low, center, high]}
        #currently counter can be 1,2,3 for the 3 images. 8/23/2019
        counter = self.current_counter
        if Duration >= self.Ranges[counter][0] and Duration <= self.Ranges[counter][2]: #Checks that duration is within the range of the current counter (event) 
            Value = abs((self.Ranges[counter][1] - Duration)/(self.Ranges[counter][1]-self.Ranges[counter][0]))
            RewardDuration = self.MaxReward - (Value * self.MaxReward)
        return RewardDuration
############################################################################################################################################
    def DurationList(self):
        self.durationdict = {}
        for i in range(self.NumEvents):
            self.durationdict[(i+1)] = []
        print(self.durationdict)

    def AddDuration(self, Duration): 
        self.durationdict[self.current_counter].append(Duration)

    def FormatDurations(self):
        # name = 'dummydelete'
        data = input('What would you like to save the Duration File as: ')
        # if name == data:
        #     input('Please choose a different name to save the Duration File: ')
        with open(data + '.csv', 'w', newline = '') as csvfile:
            csv_writer = writer(csvfile, delimiter = ',')
            for key in self.durationdict.keys():
                csv_writer.writerow([key]+self.durationdict[key])

        # with open(name + '.csv', newline = '') as csv_read, open(data +'.csv', 'w', newline = '') as csv_write:
        #     writer(csv_write, delimiter= ',').writerows(zip(*reader(csv_read, delimiter=',')))
############################################################################################################################################
    def AdaptiveRewardThreshold(self, AdaptiveValue, AdaptiveAlgorithm):
        #Take each self.durationdict and analyze duration times. (Average, sliding average?, etc)
        #Modify the self.Ranges to reduce the range to increase performance close to the center. Ranges[self.current_counter][1]
        if AdaptiveAlgorithm == 1: # 1: Percentage based change
            self.Ranges[self.current_counter][0] = round((self.Ranges[self.current_counter][0] + self.AdaptiveValue),2)
            self.Ranges[self.current_counter][2] = round((self.Ranges[self.current_counter][2] - self.AdaptiveValue),2)
        elif AdaptiveAlgorithm == 2: #2: mean, std, calculated shift of distribution

            pass
        elif AdaptiveAlgorithm == 3:#3: ???
            pass
        #Print statement about new range? for X event, etc
############################################################################################################################################
    def Start(self):
        self.MonkeyLoop = True
        self.StartTrialBool = True
        self.StartTime = time.time()
        self.RelStartTime = time.time() - self.StartTime
        self.after(1,func=self.LOOP) #Polls for other inputs

    def End(self): ###IMPORTANT###Need to make sure this End cleans up any loose ends, such as Water Reward being open. Anything Else?
        print('Stop')
        self.MonkeyLoop = False
        self.StartTrialBool = False
        self.PictureBool = False
        self.CurrentPress = False
        self.RewardReady = False
        self.ReadyForSound = False
        self.PunishLockout = False
        self.ReadyForPull = False
        if self.readyforplexon == True:
            self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
        self.counter = 0
        self.next_image()
        self.after(1,func=None)

    def Test(self):
        self.WaterReward.run()

    def StartTrialCue(self):
        if self.counter == 0:
            self.counter = -2
            self.next_image()
        elif self.counter == -2:
            self.counter = 0
            self.next_image()
        winsound.PlaySound(winsound.Beep(650,500), winsound.SND_ALIAS | winsound.SND_ASYNC) #Need to change the tone

    def EndTrialCue(self):
        self.counter = 0
        self.next_image()

    def KeyPress(self, event):
        key = event.char
        if key == 'a':
            print(key, 'is pressed')
        elif key == 's':
            print(key, 'is pressed')
        elif key == 'd':
            print(key, 'is pressed')
        
    
    ### These attach to buttons that will select if Monkey has access to the highly coveted monkey image reward
    def HighLevelRewardOn(self):
        print('Image Reward On')
        print('Image Reward coming soon to a Pedal Press Project near you!')
        self.ImageReward = True

    def HighLevelRewardOff(self):
        print('Image Reward Off')
        print('Image Reward coming soon to a Pedal Press Project near you!')
        self.ImageReward = False

    def next_image(self): #This is the call for nextimage, set counter to 0 and run next_image to get blank. For this to work need a blank image in first position in directory.
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
############################################################################################################################################
    def gathering_data_omni(self):
        new_data = self.client.get_new_data()
        if new_data.num_data_blocks < max_block_output:
            num_blocks_to_output = new_data.num_data_blocks
        else:
            num_blocks_to_output = max_block_output
        # If a keyboard event is in the returned data, perform action
        for i in range(new_data.num_data_blocks):
            try:
                if new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 1: #Alt 1
                    pass
                elif new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 2: #Alt 2
                    pass
                elif new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 8: #Alt 8
                    pass
            #For other new data find the AI channel 1 data for pedal
                if source_numbers_types[new_data.source_num_or_type[i]] == CONTINUOUS_TYPE and (new_data.channel[i] == 1 or new_data.channel[i] == 2 or new_data.channel[i] == 3 or new_data.channel[i] == 4 or new_data.channel[i] == self.Area1_right or new_data.channel[i] == self.Area2_right or new_data.channel[i] == self.Area1_left or new_data.channel[i] == self.Area2_left):
                    # Output info
                    tmp_source_number = new_data.source_num_or_type[i]
                    tmp_channel = new_data.channel[i]
                    tmp_source_name = source_numbers_names[tmp_source_number]
                    tmp_voltage_scaler = source_numbers_voltage_scalers[tmp_source_number]
                    tmp_timestamp = new_data.timestamp[i]
                    tmp_unit = new_data.unit[i]
                    tmp_rate = source_numbers_rates[tmp_source_number]

                    # Convert the samples from AD units to voltage using the voltage scaler, use tmp_samples[0] because it could be a list. Should be fine.
                    tmp_samples = new_data.waveform[i][:max_samples_output]
                    tmp_samples = [s * tmp_voltage_scaler for s in tmp_samples]
                    if new_data.channel[i] == 1:
                        self.Pedal1 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal1)
                    elif new_data.channel[i] == 2:
                        self.Pedal2 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal2)
                    elif new_data.channel[i] == 3:
                        self.Pedal3 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal3)
                    elif new_data.channel[i] == 4:
                        self.Pedal4 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal4)
                    elif new_data.channel[i] == (self.Area1_right or self.Area1_left):
                        if tmp_samples[0] >= 1:
                            self.Area1 = True
                        else:
                            self.Area1 = False
                    elif new_data.channel[i] == (self.Area2_right or self.Area2_left):
                        if tmp_samples[0] >= 1:
                            self.Area2 = True
                        else:
                            self.Area2 = False
                    #print values that we want from AI
                    #if new_data.channel[i] == 1:
                        #print("SRC:{} {} TS:{} CH:{} WF:{}".format(tmp_source_number, tmp_source_name, tmp_timestamp, tmp_channel, tmp_samples_str))
                
                # This is for 2 events that come from Cineplex, might have to change channels depending on physical connections.
                # Waiting for Ryan to see if these should be event type or continuous

                    
            except KeyError:
                continue
    #end of gathering data

########################################
##########TODO: Need to Queue water reward similar to online example to use time.sleep() / use after or some other method
########################################

    class WaterRewardThread(t.Thread,):
        def __init__(self, queue):
            t.Thread.__init__(self)
            self.queue = queue
            
        
        def run(self):
            print('start')
            time.sleep(MonkeyTest.RewardDelay)
            #time.sleep(5) #For Testing
            print("Water On")
            if MonkeyTest.readyforplexon == True:
                MonkeyTest.plexdo.set_bit(MonkeyTest.device_number, MonkeyTest.RewardDO_chan)
                time.sleep(MonkeyTest.RewardTime)
                MonkeyTest.plexdo.clear_bit(MonkeyTest.device_number, MonkeyTest.RewardDO_chan)
            print("Water Off")


if __name__ == "__main__":
    root = tk.Tk()
    
    MonkeyTest = MonkeyImages(root)

    tk.mainloop()