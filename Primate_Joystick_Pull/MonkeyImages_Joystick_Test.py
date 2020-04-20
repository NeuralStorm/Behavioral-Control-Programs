# Helpful Instructions / Parameters / Notes:
# check that self.readyforplexon = True
# self.NumEvents = # of discrim events, self.RewardClass(self.NumEvents, + (2 arguments * NumEvents:center,width))
# TestImages folder should include aBlank, xBlack,yPrepare, and zMonkey2. All images that begin with b or c are related to NumEvents. You need to have at least NumEvents # for b AND c.
# Example: self.NumEvents = 3. We have bOval, bRectangle, and bStar. We have cOval, cRectangel, and cStar. (3 of each)
# If you need to add additional events, we need to add more shapes + shape with red rectangle and name them so that they go after the preexisting shapes, or change the order of the RewardClass arguments.
# RewardClass arguments are paired center/width and are relative to the order of the images in the TestImages folder.

# For keypad controls, search "def KeyPress"

# Defs- DS: Discriminatory Stimuli, GC: Go Cue, Rel: Reltive, 

# TODO: Finish testing bugs



from definitionsRyan import * #Given definitions to Ryan. It might need updates for later. If you use this and some are missing you can uncomment them below
###################### These are all called in line 4 above from definitionsRyan import *. -They are listed here for Nathan's testing
import tkinter as tk
from tkinter import *
import threading as t
from PIL import Image, ImageTk
from csv import reader, writer
import os
import os.path
import time
import random
import winsound
import math
import queue
import statistics
import sys, traceback

# from definitions import *
##############################################################################################
###M onkey Images Class set up for Tkinter GUI
class MonkeyImages(tk.Frame,):
    def __init__(self, parent, *args, **kwargs):
        self.readyforplexon = True  ### Nathan's Switch for testing while not connected to plexon omni. I will change to true / get rid of it when not needed.
                                    ### Also changed the server set up so that it won't error out and exit if the server is not on, but it will say Client isn't connected.

        if self.readyforplexon == True:
            ## Setup Plexon Server
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
                if source_name == 'Single-bit events':
                    self.event_source = source_id
                if source_name == 'Other events':
                    self.other_event_source = source_id
                    print ("Other event source is {}".format(self.other_event_source))
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
            ## Setup for Plexon DO
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
            ## End Setup for Plexon DO
        self.begin   = numpy.array([0,0,0,0,0,0,0,0], dtype=numpy.uint8) # Connector Currently on Port A, When switched to port B, Events = Event + 16
        self.event0  = numpy.array([1,0,0,0,0,0,0,0], dtype=numpy.uint8) #task: EV30    #task2: NC
        self.event1  = numpy.array([0,1,0,0,0,0,0,0], dtype=numpy.uint8) #task: EV29    #task2: NC
        self.event2  = numpy.array([0,0,1,0,0,0,0,0], dtype=numpy.uint8) #task: EV28    #task2: EV31
        self.event3  = numpy.array([0,0,0,1,0,0,0,0], dtype=numpy.uint8) #task: EV27    #task2: EV32
        self.event4  = numpy.array([0,0,0,0,1,0,0,0], dtype=numpy.uint8) #task: EV26    #task2: NC
        self.event5  = numpy.array([0,0,0,0,0,1,0,0], dtype=numpy.uint8) #task: EV25    #task2: EV21
        self.event6  = numpy.array([0,0,0,0,0,0,1,0], dtype=numpy.uint8) #task: EV24    #task2: EV20
        self.event7  = numpy.array([0,0,0,0,0,0,0,1], dtype=numpy.uint8) #task: EV23    #task2: EV19
        
        # Connector Currently on Port B
        # EV19: Ready (Beginning of Trial) / Currently Computer Gen / Temporary while making the connector
        # EV20: Correct Count (Time of Correct Tone)
        # EV21: Incorrect Count (Time of Blooper Tone)
        # EV23: Reward Count (Time of Reward)
        # EV24: End of Trial
        # EV25: DS 1
        # EV26: GC 1
        # EV27: DS 2
        # EV28: GC 2
        # EV29: DS 3
        # EV30: GC 3
        # EV31: DS 4 (Not Currently Used)
        # EV32: GC 4 (Not Currently Used)



        # self.word0  = numpy.array([1,0,0,0,0,0,0,1], dtype=numpy.uint8)
        # self.word1  = numpy.array([0,1,0,0,0,0,0,1], dtype=numpy.uint8)
        # self.word2  = numpy.array([0,0,1,0,0,0,0,1], dtype=numpy.uint8)
        # self.word3  = numpy.array([0,0,0,1,0,0,0,1], dtype=numpy.uint8)
        # self.word4  = numpy.array([0,0,0,0,1,0,0,1], dtype=numpy.uint8)
        # self.word5  = numpy.array([0,0,0,0,0,1,0,1], dtype=numpy.uint8)
        # self.word6  = numpy.array([0,0,0,0,0,0,1,1], dtype=numpy.uint8)
        # self.word7  = numpy.array([0,0,0,0,0,0,0,1], dtype=numpy.uint8)
        
        
        if self.readyforplexon == True:
            self.task = Task()
            self.task.CreateDOChan("/Dev2/port2/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
            self.task.StartTask()
            self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            self.task2 = Task()
            self.task2.CreateDOChan("/Dev2/port1/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
            self.task2.StartTask()
            self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        else: # For testing without plexon, initialize vars here
            self.RecordingStartTimestamp = 0
        
        #self.task3 = Task()
        #self.task3.CreateDOChan("/Dev2/port0/line0","",PyDAQmx.DAQmx_Val_ChanForAllLines)
        #self.task3.StartTask()
        #self.task3.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        
        ############# Specific for pedal Press Tasks
        self.Pedal = 0 # Initialize Pedal/Press
        self.PullThreshold = 4 # (Voltage)Amount that Monkey has to pull to. Will be 0 or 5, because digital signal from pedal. (Connected to Analog input in plexon)
        #self.TimeBeforeSound = 0.2 # (seconds) Not Currently Used
        self.Pedal1 = 0 # Push / Forward
        self.Pedal2 = 0 # Right
        self.Pedal3 = 0 # Pull / Backwards
        self.Pedal4 = 0 # Left
        self.list_images = [] # Image list for Discriminative Stimuli
        source = "./TestImages/" # Name of folder in which you keep your images to be displayed
        for images in os.listdir(source):
            self.list_images.append(images)
        
        root = Tk()
        root.filename =  filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("jpeg files","*.jpg")))
        print (root.filename)
        csvreaderdict = {}
        with open(root.filename, newline='') as csvfile:
            spamreader = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
            for row in spamreader:
                data = list(spamreader)

        for row in range(0,len(data)):
            for entry in range(0,len(data[row])):
                if entry == 0:
                    csvreaderdict[data[row][0]] = []
                else:
                    csvreaderdict[data[row][0]].append(data[row][entry])

        # PARAMETERS META DATA
        self.StudyID = csvreaderdict['Study ID'][0]                              # 3 letter study code
        self.SessionID = csvreaderdict['Session ID'][0]                              # Type of Session
        self.AnimalID = csvreaderdict['Animal ID'][0]                               # 3 digit number
        self.Date = [time.strftime('%Y%m%d')]               # Today's Date
        # PARAMETERS
        # self.filename = 'test'
        self.filename = self.StudyID[0] + '_' + self.AnimalID[0] + '_' + self.Date[0] + '_Joystick'
        self.fullfilename = self.filename + '.csv'
        self.DiscrimStimMin = float(csvreaderdict['Pre Discriminatory Stimulus Min delta t1'][0])                           # (seconds) Minimum seconds to display Discrim Stim for before Go Cue
        self.DiscrimStimMax = float(csvreaderdict['Pre Discriminatory Stimulus Max delta t1'][0])                             # (seconds) Maxiumum seconds to display Discrim Stim for before Go Cue
        self.DiscrimStimDuration = self.RandomDuration(self.DiscrimStimMin,self.DiscrimStimMax) # (seconds) How long is the Discriminative Stimulus displayed for.
        self.GoCueMin = float(csvreaderdict['Pre Go Cue Min delta t2'][0])#0.25                           # (seconds) Minimum seconds to display Discrim Stim for before Go Cue
        self.GoCueMax = float(csvreaderdict['Pre Go Cue Max delta t2'][0])#0.5                             # (seconds) Maxiumum seconds to display Discrim Stim for before Go Cue
        self.GoCueDuration = self.RandomDuration(self.GoCueMin,self.GoCueMax) # (seconds) How long is the Discriminative Stimulus displayed for.
        self.MaxTimeAfterSound = 20                         # (seconds) Maximum time Monkey has to pull. However, it is currently set so that it will not reset if the Pedal is being Pulled
        self.NumEvents = int(csvreaderdict['Number of Events'][0])
        self.InterTrialTime = float(csvreaderdict['Inter Trial Time'][0])                             # (seconds) Time between Trials / Reward Time
        self.AdaptiveValue = int(csvreaderdict['Adaptive Value'][0])                           # Probably going to use this in the form of a value
        self.AdaptiveAlgorithm = int(csvreaderdict['Adaptive Algorithm'][0])                          # 1: Percentage based change 2: mean, std, calculated shift of distribution (Don't move center?) 3: TBD Move center as well?
        self.AdaptiveFrequency = int(csvreaderdict['Adaptive Frequency'][0])                         # Number of trials inbetween calling AdaptiveRewardThreshold()
        self.EarlyPullTimeOut = bool(csvreaderdict['Enable Early Pull Time Out'][0])                       # This Boolean sets if you want to have a timeout for a pull before the Go Red Rectangle.
        self.RewardDelayMin = float(csvreaderdict['Pre Reward Delay Min delta t3'][0])#0.010                         # (seconds) Min Length of Delay before Reward (Juice) is given.
        self.RewardDelayMax = float(csvreaderdict['Pre Reward Delay Max delta t3'][0])#0.010                         # (seconds) Max Length of Delay before Reward (Juice) is given.
        self.RewardDelay = self.RandomDuration(self.RewardDelayMin, self.RewardDelayMax) # (seconds) Length of Delay before Reward (Juice) is given.
        self.UseMaximumRewardTime = bool(csvreaderdict['Use Maximum Reward Time'][0])                   # This Boolean sets if you want to use the Maximum Reward Time for each Reward or to use scaled Reward Time relative to Pull Duration.
        self.RewardTime = float(csvreaderdict['Maximum Reward Time'][0])                              #
        self.MaxReward = float(csvreaderdict['Maximum Reward Time'][0])                               # (seconds) maximum time to give water
        self.EnableTimeOut = bool(csvreaderdict['Enable Time Out'][0])                          # Toggle this to True if you want to include 'punishment' timeouts (black screen for self.TimeOut duration), or False for no TimeOuts.
        self.TimeOut = float(csvreaderdict['Time Out'][0]) # (seconds) Time for black time out screen
        self.EnableBlooperNoise = bool(csvreaderdict['Enable Blooper Noise'][0])                     # Toggle this to True if you want to include the blooper noise when an incorrect pull is detected (Either too long or too short / No Reward Given)
        self.RewardClassArgs = []
        for i in range(0,len(csvreaderdict['Ranges'])):
            self.RewardClassArgs.append(float(csvreaderdict['Ranges'][i]))
        self.RewardClass(self.RewardClassArgs)   #Hi Ryan, I added this range for your testing for now, because I changed where the reward is given so that it has to fit into an interval now.
        self.ImageRatio = 100 # EX: ImageRatio = 75 => 75% Image Reward, 25% Water Reward , Currently does not handle the both choice for water and image.
        self.WaterReward = self.WaterRewardThread()
        self.ActiveJoystickChans = []                  # This can be used if you only want him to pull in certain directions as commented above as self.Pedal#_chan.
        for k in range(0,len(csvreaderdict['Active Joysick Channels'])):
            self.ActiveJoystickChans.append(int(csvreaderdict['Active Joysick Channels'][k]))
        ############# Initializing vars
        self.DurationList()                                 # Creates dict of lists to encapsulate press durations. Will be used for Adaptive Reward Control
        self.counter = 0 # Counter Values: Alphabetic from TestImages folder
        # Blank(white screen), disc stim 1, disc stim 2, disc stim 3, disc stim go 1, disc stim go 2, disc stim go 3, black(timeout), Prepare(to put hand in position), Monkey image
        self.current_counter = 0 
        self.excluded_events = [] #Might want this for excluded events
        
        ############# Omniplex / Map Channels
        self.RewardDO_chan = 1 # DO Channel
        # Continuous AI channels
        self.Pedal1_chan = 1 # Push / Forward channel
        self.Pedal2_chan = 2 # Right channel
        self.Pedal3_chan = 3 # Pull / Backwards channel
        self.Pedal4_chan = 4 # Left channel
        self.Area1_right = 5 # Home Area (Area 1)
        self.Area2_right = 6 # Joystick Area (Area 2)
        self.Area1_left = 7 # Home Area (Area 1)
        self.Area2_left = 8 # Joystick Area (Area 2)
        self.StartTimestamp = 0
        self.RewardTime = 0
        #############
        # Queue 
        self.queue = queue.Queue()

        ############# Confusion Matrix initiation #TODO: Change to using scikit-learn
        self.pnan = 0 # Predicted: No, Actual: No
        self.pyan = 0 # Predicted: Yes, Actual: No
        self.pnay = 0 # Predicted: No, Actual: Yes
        self.pyay = 0 # Predicted: Yes, Actual: Yes
        ############# Rewards
        self.RewardSound = 'Exclamation'
        self.Bloop       = 'Question'
        ##############
        
        # Booleans (built into GUI Class functions):
        self.MonkeyLoop = False         # Overall for when the program is looping
        self.StartTrialBool = False     # Gives the flashing diamond signal before discrim stimulus
        self.TrainingStart = False
        self.CurrentPress = False       # Changes to True to show that a Press has happened / recorded into plexon and on server.
        self.JoystickPulled = False     # Should RENAME this one. Is True when animal pull is within range of the wanted pull duration.
        self.PictureBool = False
        self.ReadyForSound = False
        self.PunishLockout = False
        self.ReadyForPull = False
        self.OutofHomeZoneOn = False    # Used for StartTrialCue to turn on and off the dinging sound before DS / GC
        self.HandInBool = False         # Used for EV09 / EV14 (EV10) for the unlikely case that monkey leaves hand in Home Zone for the full duration and doesn't pull.
        self.HandInJoystickBool = False # Used for EV11 / EV12 Joystick Area Boolean?
        self.T1FailBool = False         # True if last trial was T1 Failure
        self.T2FailBool = False         # True if last trial was T2 Failure
        
        self.StartButtonBool = False
        self.PauseButtonBool = False
        #Rename Area1 and Area2
        self.Area1_right_pres = False   # Home Area
        self.Area2_right_pres = False   # Joystick Area
        self.Area1_left_pres = False    # Home Area
        self.Area2_left_pres = False    # Joystick Area
        self.ImageReward = False        # Default Image Reward set to True
        
        
        #Error Handling while fixing connector
        self.HandInTime = float(0)
        self.HandOutTime = float(0)
        self.HandOutGCTime = float(0)
        self.HandDurationTime = float(0)
        self.HandDurationGCTime = float(0)
        
        
        self.StartTime = time.time()
        self.RelStartTime = time.time() - self.StartTime
        self.TrainingStartTime = time.time()
        self.RelTrainingStartTime = time.time() - self.TrainingStartTime
        self.CueTime = time.time()
        self.RelCueTime = time.time() - self.CueTime
        self.DiscrimStimTime = time.time()
        self.RelDiscrimStimTime = time.time() - self.DiscrimStimTime
        self.SoundTime = time.time()
        self.RelSoundTime = time.time() - self.SoundTime
        self.PunishLockTime = time.time()
        self.RelPunishLockTime = time.time() - self.PunishLockTime

        print("ready for plexon:" , self.readyforplexon)
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.root.wm_title("MonkeyImages")

        ###Adjust width and height to fit monitor### bd is for if you want a border
        self.frame1 = tk.Frame(self.root, width = 1600, height = 1000, bd = 0)
        self.frame1.pack(side = BOTTOM)
        self.cv1 = tk.Canvas(self.frame1, width = 1600, height = 800, background = "white", bd = 1, relief = tk.RAISED)
        self.cv1.pack(side = BOTTOM)

        startbutton = tk.Button(self.root, text = "Start-'a'", height = 5, width = 6, command = self.Start)
        startbutton.pack(side = LEFT)

        pausebutton = tk.Button(self.root, text = "Pause-'s'", height = 5, width = 6, command = self.Pause)
        pausebutton.pack(side = LEFT)

        unpausebutton = tk.Button(self.root, text = "Unpause-'d'", height = 5, width = 8, command = self.Unpause)
        unpausebutton.pack(side = LEFT)

        stopbutton = tk.Button(self.root, text = "Stop-'f'", height = 5, width = 6, command = self.Stop)
        stopbutton.pack(side = LEFT)
        
        trialbutton = tk.Button(self.root, text = "Print Trials", height = 5, width = 12, command = self.TotalTrials)
        trialbutton.pack(side = LEFT)

        durationbutton = tk.Button(self.root, text = "Print Durations", height = 5, width = 12, command = self.Durationbutton)
        durationbutton.pack(side = LEFT)

        metabutton = tk.Button(self.root, text = "Print Meta Data", height = 5, width = 12, command = self.Metabutton)
        metabutton.pack(side = LEFT)

        rangesbutton = tk.Button(self.root, text = " Print Ranges", height = 5, width = 10, command = self.Rangesbutton)
        rangesbutton.pack(side = LEFT)

        # Likely Don't Need these buttons, Image reward will always be an option, and will be controlled by %
        ImageRewardOn = tk.Button(self.root, text = "ImageReward\nOn", height = 5, width = 10, command = self.HighLevelRewardOn)
        ImageRewardOn.pack(side = LEFT)
        ImageRewardOff = tk.Button(self.root, text = "ImageReward\nOff", height = 5, width = 10, command = self.HighLevelRewardOff)
        ImageRewardOff.pack(side = LEFT)

        testbutton = tk.Button(self.root, text = "Water Reward-'z'", height = 5, width = 12, command = self.WaterButton)
        testbutton.pack(side = LEFT)

        updatebutton = tk.Button(self.root, text = "Test", height = 5, width = 5, command = self.Test)
        updatebutton.pack(side = LEFT)

        savebutton = tk.Button(self.root, text = "Save CSV", height = 5, width = 10, command = self.FormatDurations)
        savebutton.pack(side = LEFT)

        self.root.bind('<Key>', lambda a : self.KeyPress(a))
        
        if self.readyforplexon == True:
            WaitForStart = True
            print('Start Plexon Recording now')
            while WaitForStart == True:
                #self.client.opx_wait(1)
                new_data = self.client.get_new_data()
                if new_data.num_data_blocks < max_block_output:
                    num_blocks_to_output = new_data.num_data_blocks
                else:
                    num_blocks_to_output = max_block_output
                for i in range(new_data.num_data_blocks):
                    if new_data.source_num_or_type[i] == self.other_event_source and new_data.channel[i] == 2: # Start event timestamp is channel 2 in 'Other Events' source
                        print ("Recording start detected. All timestamps will be relative to a start time of {} seconds.".format(new_data.timestamp[i]))
                        WaitForStart = False
                        self.RecordingStartTimestamp = new_data.timestamp[i]


##########################################################################################################################################
    def LOOP(self): #LOOP will be different for each experiment
        #try: #For Later when we want a try block to catch exceptions.
            if self.MonkeyLoop == True:
                tic = time.time()
                if self.readyforplexon == True:
                    #Gather new data
                    self.gathering_data_omni()

                # Flashing box for trial start cue + low freq sound.
                if self.StartTrialBool == True and self.PunishLockout == False and self.RelStartTime >= self.InterTrialTime and self.Area1_right_pres == False and self.Area1_left_pres == False:
                    if self.Area1_right_pres == False and self.Area1_left_pres == False:
                        # starttrialtic = time.time()
                        self.StartTrialCue()
                        # starttrialtoc = time.time() - starttrialtic
                        # print('starttrialtoc: ', starttrialtoc)
                #################################################################################################################
                elif (self.Area1_right_pres == True or self.Area1_left_pres == True) and self.TrainingStart == False: # Start of Hand in Home Zone
                    winsound.PlaySound(winsound.Beep(100,0), winsound.SND_PURGE) #Purge looping sounds
                    if self.counter != 0:
                        self.counter = 0
                        self.next_image()
                    # EV19 Ready # TODO: Take this out when finish the connector since new start of trial comes from hand in home zone
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event7,None,None)
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    print('hand in area, stop sound.')
                    self.csvdict['Total Trials'][0] += 1
                    self.TrainingStartTime = time.time()
                    self.RelTrainingStartTime = time.time() - self.TrainingStartTime
                    self.StartTrialBool = False
                    self.TrainingStart = True
                    self.OutofHomeZoneOn = False
                    self.T1FailBool = False
                    self.T2FailBool = False
                    
                    
                    
                #################################################################################################################

                    
                elif self.TrainingStart == True and self.PictureBool == False and (self.Area1_right_pres == True or self.Area1_left_pres == True) and self.PunishLockout == False and self.RelTrainingStartTime >= self.DiscrimStimDuration:
                    print('RelTrainingStartTime: ', self.RelTrainingStartTime)
                    print('Discriminatory Stimulus')
                    self.PictureBool = True # This will be on for the duration of the trial
################################################################################################################################################################################################
                    #while self.counter not in self.excluded_events: #Don't use excluded events
                    #Need to work on this logic to choose a counter value that is not in self.excluded_events
################################################################################################################################################################################################
                    self.counter = random.randint(1,self.NumEvents) #Randomly chooses next image -Current,will change the range depending on which images are to be shown here.
                    self.current_counter = self.counter
                    self.CueTime = time.time()
                    self.RelCueTime = time.time() - self.CueTime
                    # EV25 , EV27, EV29, EV31
                    if self.current_counter == 1: # EV25
                        self.csvdict['Trial DS Type'].append(1)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event5,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    elif self.current_counter == 2: # EV27
                        self.csvdict['Trial DS Type'].append(2)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event3,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    elif self.current_counter == 3: # EV29
                        self.csvdict['Trial DS Type'].append(3)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event1,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    elif self.current_counter == 4: # EV31
                        self.csvdict['Trial DS Type'].append(4)
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event2,None,None)
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    self.next_image()
            

                elif self.PictureBool == True and self.RelCueTime >= self.GoCueDuration and (self.Area1_right_pres == True or self.Area1_left_pres == True) and self.ReadyForPull == False:
                    print('RelCueTime: ', self.RelCueTime)
                    print('Go Cue')
                    self.ReadyForPull = True
                    self.counter = self.counter + self.NumEvents
                    # EV26, EV28, EV30 EV32
                    if self.current_counter == 1: # EV026
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event4,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    elif self.current_counter == 2: # EV28
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event2,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    elif self.current_counter == 3: # EV30
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event0,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    elif self.current_counter == 4: # EV32
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event3,None,None)
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    self.next_image()
                    self.DiscrimStimTime = time.time()
                    self.RelDiscrimStimTime = time.time() - self.DiscrimStimTime



                ##################################################################################################### Unused Currently.
                # TEST: For Pull before ReadyForPull. Go to Black Screen and lockout
                # elif self.PictureBool == True and self.ReadyForPull == False and self.CurrentPress == True and self.EarlyPullTimeOut == True and self.PunishLockout == False:
                #         self.PunishLockout = True
                #         if self.EnableBlooperNoise == True:
                #             winsound.PlaySound('WrongHoldDuration.wav', winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT) # Might have this sound or another or None
                #         self.PunishLockTime = time.time()
                #         self.RelPunishLockTime = time.time() - self.PunishLockTime
                #         self.counter = -3
                #         self.next_image()
                
                        
                        
                        
                ### Needs to play a sound cue for animal.
                # elif self.ReadyForSound == True and self.RelDiscrimStimTime >= self.TimeBeforeSound and self.ReadyForPull == False:
                #     print('Sound')
                #     self.ReadyForPull = True
                #     self.SoundTime = time.time()
                #     self.RelSoundTime = time.time() - self.SoundTime
                #     winsound.PlaySound('750Hz_1s_test.wav', winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT) #750 Hz, 1000 ms
                #####################################################################################################

                # If Lever is Pulled On and ready for Pull
                elif self.ReadyForPull == True and self.CurrentPress == True and self.PunishLockout == False:
                    print('Pull')
                    #winsound.PlaySound('550Hz_1s_test.wav', winsound.SND_ASYNC + winsound.SND_LOOP + winsound.SND_NOWAIT)
                    while self.Pedal3 >= self.PullThreshold:                     ### While loop in place to continuously and quickly update the Press Time for the Duration that
                        #self.client.opx_wait(100)                               ### The Monkey is Pulling it for. This will reduce latency issues with running through the whole
                        self.gathering_data_omni()                               ### Loop.
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    
                    if self.UseMaximumRewardTime == False:
                        self.RewardTime = self.ChooseReward(self.DurationTimestamp)
                    elif self.UseMaximumRewardTime == True:
                        self.RewardTime = self.MaxReward
                        
                    if self.RewardTime > 0:                                      ### Reward will Only be Given if the Pull Duration Falls in one of the intervals.
                        self.JoystickPulled = True
                        self.AddCorrectStimCount(self.current_counter)
                        self.AddCorrectDuration(self.DurationTimestamp, self.RewardTime)
                        self.AddCorrectStartPress(self.StartTimestamp)
                        self.AddCorrectEndPress(self.StopTimestamp)
                    elif self.RewardTime == 0:
                        print('pull fail')
                        self.csvdict['Total pull failures'][0] += 1
                        self.csvdict['Trial Outcome'].append('Pull Fail')
                        self.csvdict[('Post t1 failure pull counter')].append(0)
                        self.csvdict[('Post t2 failure pull counter')].append(0)
                        self.csvdict['Discriminant Stimuli On'].insert(-1, '---------->')
                        self.csvdict['Go Cue On'].insert(-1, '---------->')
                        self.csvdict['Duration in Home Zone'].append('---------->')
                        self.csvdict['Trial DS Type'].insert(-1, '---------->')
                        self.AddIncorrectDuration(self.DurationTimestamp)
                        self.AddIncorrectStartPress(self.StartTimestamp)
                        self.AddIncorrectEndPress(self.StopTimestamp)
                        self.csvdict[('Incorrect Stim Count ' + str(self.current_counter))][0] += 1
                        self.csvdict[('Trial End')].append('---------->')
                        self.AddPawInHome('---------->')
                        self.AddPawOutHome('---------->')
                        # EV21 Pull failure
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event5,None,None)
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                        if self.EnableBlooperNoise == True:
                            winsound.PlaySound('WrongHoldDuration.wav', winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                        if self.EnableTimeOut == True:
                            self.RelPunishLockTime = time.time() - self.PunishLockTime
                            self.PunishLockout = True
                            self.counter = -3
                            self.next_image()
                    self.CurrentPress = False
                    
                    #Moved  Success into this loop 3/16/2020 Testing Now.
                    if self.JoystickPulled == True and self.ReadyForPull == True:                                   ### Reward will be Water or Image or Both (Need to add Both Option)
                        Reward = self.ChooseOne(self.ImageRatio)
                        if self.ImageReward == True and Reward == 1:
                            self.counter = -1
                            self.next_image()
                        print('Press Duration: {}'.format(self.DurationTimestamp))
                        print('Reward Duration: {}'.format(self.RewardTime))
                        #EV20
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
                        self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                        winsound.PlaySound('550Hz_0.5s_test.wav', winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                        #winsound.PlaySound(self.RewardSound, winsound.SND_ALIAS + winsound.SND_ASYNC)
                        try:
                            if self.csvdict['Discriminatory Stimulus Trial Count ' + str(self.current_counter)][0]%self.AdaptiveFrequency == 0 and self.csvdict['Discriminatory Stimulus Trial Count ' + str(self.current_counter)][0] > 0:
                                self.AdaptiveRewardThreshold(self.AdaptiveValue,self.AdaptiveAlgorithm)
                        except KeyError:
                            pass
                        self.WaterReward.run()
                        self.counter = 0
                        self.next_image()
                        self.CurrentPress = False
                        self.JoystickPulled = False
                        self.PictureBool = False
                        self.ReadyForSound = False
                        self.ReadyForPull = False
                        self.RewardTime = 0
                        self.DiscrimStimDuration = self.RandomDuration(self.DiscrimStimMin,self.DiscrimStimMax)
                        self.GoCueDuration = self.RandomDuration(self.GoCueMin,self.GoCueMax)
                        # EV24
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
                        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                        print('success')
                        self.csvdict['Total successes'][0] += 1
                        self.csvdict['Trial Outcome'].append('Success')
                        self.csvdict[('Post t1 failure pull counter')].append(0)
                        self.csvdict[('Post t2 failure pull counter')].append(0)
                        self.csvdict['Duration in Home Zone'].append(self.HandDurationGCTime)
                        self.AddPawOutHome(self.HandOutGCTime)
                        self.AddPawInHome(self.HandInTime)
                        self.StartTrialBool = True
                        self.TrainingStart = False
                        self.OutofHomeZoneOn = False
                        self.StartTime = time.time() #Update start time for next cue.
                        self.RelStartTime = time.time() - self.StartTime
                        self.PunishLockTime = time.time()
                        self.RelPunishLockTime = time.time() - self.PunishLockTime
                    

                # Reset after Max Time
                elif (self.RelDiscrimStimTime >= self.MaxTimeAfterSound and self.ReadyForPull == True and 
                         self.Pedal1 < self.PullThreshold and self.Pedal2 < self.PullThreshold and
                         self.Pedal3 < self.PullThreshold and self.Pedal4 < self.PullThreshold):
                    print('Time Elapsed, wait for Cue again.')
                    self.csvdict['No Pull'][0] += 1
                    self.csvdict['Trial Outcome'].append('No Pull')
                    self.csvdict[('Post t1 failure pull counter')].append(0)
                    self.csvdict[('Post t2 failure pull counter')].append(0)
                    if self.HandInBool == True:
                        self.csvdict['Duration in Home Zone'].append('No exit')
                        self.AddPawOutHome('No exit')
                        pass # placeholder
                    else:
                        self.csvdict['Duration in Home Zone'].append(self.HandDurationGCTime)
                        self.AddPawOutHome(self.HandOutGCTime)
                    self.AddPawInHome(self.HandInTime)
                    self.counter = -3
                    self.next_image()
                    self.counter = 0
                    self.CurrentPress = False
                    self.StartTrialBool = True
                    self.TrainingStart = False
                    self.JoystickPulled = False
                    self.PictureBool = False
                    self.ReadyForSound = False
                    if self.EnableTimeOut == True:
                        self.PunishLockout = True
                        self.PunishLockTime = time.time()
                        self.RelPunishLockTime = time.time() - self.PunishLockTime
                    self.ReadyForSound = False
                    self.ReadyForPull = False
                    self.DiscrimStimDuration = self.RandomDuration(self.DiscrimStimMin,self.DiscrimStimMax)
                    self.GoCueDuration = self.RandomDuration(self.GoCueMin,self.GoCueMax)
                    self.OutofHomeZoneOn = False
                    # EV24
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    self.StartTime = time.time() #Update start time for next cue.
                    self.RelStartTime = time.time() - self.StartTime


                if self.PunishLockout == True and self.RelPunishLockTime <= self.TimeOut:
                    self.PunishLockout = False
                    # EV24
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                    self.StartTrialBool = True
                    self.TrainingStart = False
                    self.StartTime = time.time()
                    self.CueTime = time.time()
                    self.DiscrimStimTime = time.time()
                    self.SoundTime = time.time()
                    self.RelPunishLockTime = time.time() - self.PunishLockTime
                    self.OutofHomeZoneOn = False
                    self.after(0,func=self.LOOP)
                else:
                    if self.counter == -3:
                        self.counter = 0
                        self.next_image()
                    self.update_idletasks() # Check speeds with this / without it
                    self.RelStartTime = time.time() - self.StartTime
                    self.RelCueTime = time.time() - self.CueTime
                    self.RelDiscrimStimTime = time.time() - self.DiscrimStimTime
                    self.RelSoundTime = time.time() - self.SoundTime###This Timing is used for if animal surpasses max time to do task, needs to update every loop
                    self.RelTrainingStartTime = time.time() - self.TrainingStartTime
                    # toc = time.time() - tic
                    # print('loop end toc: ', toc)
                    self.after(0,func=self.LOOP)
                
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
    def RandomDuration(self, Min, Max):
        output = round(random.uniform(Min,Max),2)
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
                print('This arg is for Range: {} center: {}'.format(peak,arg))
                arg_center = arg
            else:
                index += 1
                print('This arg is for Range: {} width: {}'.format(peak,arg))
                arg_width = arg
                low = arg_center - arg_width
                high = arg_center + arg_width
                print('The range for interval {} is {} to {}'.format(peak,low,high))
                self.Ranges[index].append(low)
                self.Ranges[index].append(arg_center)
                self.Ranges[index].append(high)
        print("Ranges: {}".format(self.Ranges))
############################################################################################################################################
            #TODO: Need to add event to the choose reward inputs. This will come from the event cue that is shown ( Can Use self.current_counter )
############################################################################################################################################
    def ChooseReward(self,Duration): #New (8/23/2019): Ranges = {X: [low, center, high],..., X:[low, center, high]}
        #currently counter can be 1,2,3 for the 3 images. 8/23/2019
        counter = self.current_counter
        RewardDuration = 0
        if Duration >= self.Ranges[counter][0] and Duration <= self.Ranges[counter][2]: #Checks that duration is within the range of the current counter (event) 
            Value = abs((self.Ranges[counter][1] - Duration)/(self.Ranges[counter][1]-self.Ranges[counter][0]))
            RewardDuration = self.MaxReward - (Value * self.MaxReward)
        return RewardDuration
############################################################################################################################################
    def DurationList(self):
        self.metadict = {'Joystick': [], 'Meta Data:': [], 'Study ID': self.StudyID, 'Session ID': self.SessionID, 'Animal ID': self.AnimalID, 'Date': self.Date, 'Session Start': [], 'Session Stop': [], 'Session Time': []}
        self.metadict[('Number of Events')] = [self.NumEvents]
        self.metadict['Pre Discrimanatory Stimulus Min delta t1'] = [self.DiscrimStimMin]
        self.metadict['Pre Discrimanatory Stimulus Max delta t1'] = [self.DiscrimStimMax]
        self.metadict['Pre Go Cue Min delta t2'] = [self.GoCueMin]
        self.metadict['Pre Go Cue Max delta t2'] = [self.GoCueMax]
        self.metadict['Pre Reward Delay Min delta t3'] = [self.RewardDelayMin]
        self.metadict['Pre Reward Delay Max delta t3'] = [self.RewardDelayMax]
        self.metadict['Use Maximum Reward Time'] = [self.UseMaximumRewardTime]
        self.metadict['Maximum Reward Time'] = [self.MaxReward]
        self.metadict['Enable Time Out'] = [self.EnableTimeOut]
        self.metadict['Time Out'] = [self.TimeOut]
        self.metadict['Ranges'] = [self.Ranges]
        self.metadict['End Ranges'] = []
        self.metadict['Max Time After Sound'] = [self.MaxTimeAfterSound]
        self.metadict['Inter Trial Time'] = [self.InterTrialTime]
        self.metadict['Adaptive Value'] = [self.AdaptiveValue]
        self.metadict['Adaptive Algorithm'] = [self.AdaptiveAlgorithm]
        self.metadict['Adaptive Frequency'] = [self.AdaptiveFrequency]
        self.metadict['Enable Early Pull Time Out'] = [self.EarlyPullTimeOut]
        self.metadict['Enable Blooper Noise'] = [self.EnableBlooperNoise]
        self.metadict['Active Joystick Channels'] = [self.ActiveJoystickChans]
        self.csvdict = {'': []}
        self.csvdict['Data:'] = []
        self.csvdict['Total Trials'] = [0]
        self.csvdict['Total t1 failures'] = [0]
        self.csvdict['Total t2 failures'] = [0]
        self.csvdict['Total pull failures'] = [0]
        self.csvdict['No Pull'] = [0]
        self.csvdict['Total successes'] = [0]
        self.csvdict['Check Trials'] = []
        self.csvdict['Paw into Home Box: Start'] = []
        self.csvdict['Paw out of Home Box: End'] = []
        # self.csvdict['Paw into Joystick Box'] = []
        # self.csvdict['Paw out of Joystick Box'] = []
        self.csvdict['Discriminant Stimuli On'] = [] # Need to add these times from Plexon Events # EV25 27 29 31
        # self.csvdict['Discriminant Stimuli Off'] = [] # Need to create an event for this. and Ask about it.
        self.csvdict['Go Cue On'] = [] # Need to add these times from Plexon Events # EV26 28 30 32
        # self.csvdict['Go Cue Off'] = [] # Need to ask about this.
        self.csvdict['Trial DS Type'] = []
        self.csvdict['Duration in Home Zone'] = []
        self.csvdict['Trial Outcome'] = []
        self.csvdict['Trial End'] = [] # EV24 Use for Resets
        self.csvdict[('Post t1 failure pull counter')] = [0]
        self.csvdict[('Post t2 failure pull counter')] = [0]
        
        for i in range(self.NumEvents):
            blankspace = ['_']
            for j in range(i):
                blankspace.append('_')
            blankspaceconcat = "".join(blankspace)
            self.csvdict[blankspaceconcat] = []
            self.csvdict[('Discriminatory Stimulus Trial Count ' + str(i+1))] = [0]
            self.csvdict[('Correct Stim Count ' + str(i+1))] = [0]
            self.csvdict[('Incorrect Stim Count ' + str(i+1))] = [0]
            self.csvdict[('Correct Average ' + str(i+1))] = [0]
            self.csvdict[('Correct St Dev ' + str(i+1))] = [0]
            
        self.csvdict[(' _ ')] = []
        self.tsdict = {'Timestamps:': []}
        for i in range(self.NumEvents):
            blankspace = ['.']
            for j in range(i):
                blankspace.append('.')
            blankspaceconcat = "".join(blankspace)
            self.tsdict[('Discriminatory Stimulus ' + str(i+1))] = []
            self.tsdict[('Go Cue ' + str(i+1))] = []
            self.tsdict[('Correct Start Press ' + str(i+1))] = []
            self.tsdict[('Correct End Press ' + str(i+1))] = []
            self.tsdict[('Correct Duration ' + str(i+1))] = []
            self.tsdict[('Reward Duration ' + str(i+1))] = []
            self.tsdict[('Incorrect Start Press ' + str(i+1))] = []
            self.tsdict[('Incorrect End Press ' + str(i+1))] = []
            self.tsdict[('Incorrect Duration ' + str(i+1))] = []
            self.tsdict[blankspaceconcat] = []
        
        self.tsdict[('Errors:')] = []
        # self.csvdict[('Testing Area:')] = []
        # print('Duration Dictionary: {}'.format(self.csvdict))

    def AddCorrectDuration(self, Duration, Reward): 
        self.tsdict[('Correct Duration ' + str(self.current_counter))].append(Duration)
        self.tsdict[('Reward Duration ' + str(self.current_counter))].append(Reward)
    
    def AddIncorrectDuration(self, Duration):
        self.tsdict[('Incorrect Duration ' + str(self.current_counter))].append(Duration)
    
    def AddCorrectStimCount(self, event):
        self.csvdict['Correct Stim Count ' + str(event)][0] += 1
    
    def AddCorrectStartPress(self, Startts):
        self.tsdict[('Correct Start Press ' + str(self.current_counter))].append(Startts)
    
    def AddCorrectEndPress(self, End):
        self.tsdict[('Correct End Press ' + str(self.current_counter))].append(End)

    def AddIncorrectStartPress(self, Startts):
        self.tsdict[('Incorrect Start Press ' + str(self.current_counter))].append(Startts)
    
    def AddIncorrectEndPress(self, End):
        self.tsdict[('Incorrect End Press ' + str(self.current_counter))].append(End)
    
    def AddDiscriminatoryStimulus(self, Timestamp):
        self.tsdict[('Discriminatory Stimulus ' + str(self.current_counter))].append(Timestamp)
        
    def AddGoCue(self, Timestamp):
        self.tsdict[('Go Cue ' + str(self.current_counter))].append(Timestamp)
        
    def AddPawInHome(self, Timestamp):
        self.csvdict[('Paw into Home Box: Start')].append(Timestamp)
        
    def AddPawOutHome(self, Timestamp):
        self.csvdict[('Paw out of Home Box: End')].append(Timestamp)
        
    # def AddPawInJoystick(self, Timestamp):
    #     self.csvdict[('Paw into Joystick Box')].append(Timestamp)
        
    # def AddPawOutJoystick(self, Timestamp):
    #     self.csvdict[('Paw out of Joystick Box')].append(Timestamp)

    def CheckTrialFunc(self):
        try:
            self.checklengthlist = ['Paw into Home Box: Start', 'Paw out of Home Box: End',
                'Discriminant Stimuli On', 'Go Cue On', ' Trial DS Type', 'Duration in Home Zone', 'Trial Outcome']
            truelen = (self.csvdict['Total Trials'][0] + self.csvdict['Total pull failures'][0])
            for i in self.checklengthlist:
                keylen = len(self.csvdict[i][0])
                if keylen > truelen:
                    self.csvdict[i][0].pop()
            if self.csvdict['Total Trials'][0] == (self.csvdict['Total t1 failures'][0] + self.csvdict['Total t2 failures'][0] + self.csvdict['No Pull'][0] + self.csvdict['Total successes'][0]):
                self.csvdict['Check Trials'].append('True, Fixed')
            else:
                self.csvdict['Check Trials'].append('False, Error')
        except:
            errormsg = traceback.format_exc()
            self.csvdict['Errors:'].append(errormsg)
            print('CheckTrialFunc error, continuing')

    
    def FormatDurations(self):
        self.metadict['End Ranges'].append(self.Ranges)
        self.metadict['Session Stop'].append(self.SessionStopTime)
        self.metadict['Session Time'].append(self.SessionDuration)
        
        for i in range(self.NumEvents):
            try:
                self.csvdict[('Correct Average ' + str(i+1))][0] = statistics.mean(self.tsdict[('Correct Duration ' + str(i+1))])
                self.csvdict[('Correct St Dev ' + str(i+1))][0] = statistics.stdev(self.tsdict[('Correct Duration ' + str(i+1))])
            except:
                pass
        if self.csvdict['Total Trials'][0] == (self.csvdict['Total t1 failures'][0] + self.csvdict['Total t2 failures'][0] + self.csvdict['No Pull'][0] + self.csvdict['Total successes'][0]):
            self.csvdict['Check Trials'].append('True')
        else:
            self.CheckTrialFunc()
        try:
            csvtest = True
            while csvtest == True:
                check = os.path.isfile(self.fullfilename)
                while check == True:
                    print('File name already exists')
                    self.filename = input('Enter File name: ')
                    self.fullfilename = self.filename + '.csv'
                    check = os.path.isfile(self.fullfilename)
                print('File name not currently used, saving.')
    
                with open(self.filename + '.csv', 'w', newline = '') as csvfile:
                    csv_writer = writer(csvfile, delimiter = ',')
                    for key in self.metadict.keys():
                        csv_writer.writerow([key]+self.metadict[key])
                    for key in self.csvdict.keys():
                        csv_writer.writerow([key]+self.csvdict[key])
                    for key in self.tsdict.keys():
                        csv_writer.writerow([key]+self.tsdict[key])
                csvtest = False
                    # with open(name + '.csv', newline = '') as csv_read, open(data +'.csv', 'w', newline = '') as csv_write:
                    #     writer(csv_write, delimiter= ',').writerows(zip(*reader(csv_read, delimiter=',')))
            print(self.fullfilename)
            print('saved')
        except RuntimeError:
            print('Error with File name')
            self.filename = self.StudyID[0] + '_' + self.AnimalID[0] + '_' + self.Date[0] + '_Joystick'
            self.fullfilename = self.filename + '.csv'
            errormsg = traceback.format_exc()
            self.tsdict['Errors:'].append(errormsg)
        except OSError:
            print('Invalid File Name, Please select save CSV again.')
            self.filename = self.StudyID[0] + '_' + self.AnimalID[0] + '_' + self.Date[0] + '_Joystick'
            self.fullfilename = self.filename + '.csv'
            errormsg = traceback.format_exc()
            self.tsdict['Errors:'].append(errormsg)

############################################################################################################################################
    def AdaptiveRewardThreshold(self, AdaptiveValue, AdaptiveAlgorithm):
        #Take each self.csvdict and analyze duration times. (Average, sliding average?, etc)
        #Modify the self.Ranges to reduce the range to increase performance close to the center. Ranges[self.current_counter][1]
        if AdaptiveAlgorithm == 1: # 1: Percentage based change
            self.Ranges[self.current_counter][0] = round((self.Ranges[self.current_counter][0] + self.AdaptiveValue),2)
            self.Ranges[self.current_counter][2] = round((self.Ranges[self.current_counter][2] - self.AdaptiveValue),2)
        elif AdaptiveAlgorithm == 2: #2: mean, std, calculated shift of distribution
            self.Ranges[self.current_counter][0] = round((self.Ranges[self.current_counter][0] + self.AdaptiveValue),2)
        elif AdaptiveAlgorithm == 3:#3: ???
            pass
        #Print statement about new range? for X event, etc
    def AdaptiveValueChange(self, AdaptiveVariable, AdaptiveAlgorithm):
        if AdaptiveAlgorithm == 1:
            pass
        if AdaptiveAlgorithm == 2:
            pass
        if AdaptiveAlgorithm == 3:
            pass
############################################################################################################################################
    def Start(self):
        # TODO: Include a dump of Plexon data so that any initial pulls are not included here?
        if self.StartButtonBool == False:
            print('Start')
            self.StartButtonBool = True
            self.MonkeyLoop = True
            self.StartTrialBool = True
            self.TrainingStart = False
            self.StartTime = time.time()
            self.SessionStart = time.time()
            self.RelStartTime = time.time() - self.StartTime
            self.SessionStartTime = [time.strftime('%R:%S')]
            self.metadict['Session Start'].append(self.SessionStartTime)
            self.after(0,func=self.LOOP) #Polls for other inputs
        else:
            print('Already Started')
    def Pause(self):
        if self.StartButtonBool == True and self.PauseButtonBool == False:
            print('pause')
            self.PauseButtonBool = True
            if self.StartTrialBool == True:
                self.OutofHomeZoneOn = False
            winsound.PlaySound(None, winsound.SND_PURGE)
            if self.readyforplexon == True:
                self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
            self.MonkeyLoop = False
            self.Pause_RelStartTime = self.RelStartTime
            self.Pause_RelCueTime = self.RelCueTime
            self.Pause_RelDiscrimStimTime = self.RelDiscrimStimTime
            self.Pause_RelSoundTime = self.RelSoundTime
            self.Pause_RelPunishLockTime = self.RelPunishLockTime
        else:
            if self.StartButtonBool == False:
                print('Not Started')
            elif self.PauseButtonBool == True:
                print('Already Paused')

    def Unpause(self):
        if self.StartButtonBool == True and self.PauseButtonBool == True:
            try:
                print('unpause')
                self.PauseButtonBool = False
                self.MonkeyLoop = True
                self.StartTime = time.time() - self.Pause_RelStartTime
                self.CueTime = time.time() - self.Pause_RelCueTime
                self.DiscrimStimTime = time.time() - self.Pause_RelDiscrimStimTime
                self.SoundTime = time.time() - self.Pause_RelSoundTime
                self.PunishLockTime = time.time() - self.Pause_RelPunishLockTime
                self.after(0,func=self.LOOP)
            except AttributeError:
                print('Need to start and pause before unpause / try loop')
                pass
        else:
            print('Need to start and pause before unpause')

    def Stop(self): ###IMPORTANT###Need to make sure this End cleans up any loose ends, such as Water Reward being open. Anything Else?
        if self.StartButtonBool == True:
            self.SessionStop = time.time()
            self.SessionStopTime = [time.strftime('%R:%S')]
            try:
                hours, rem = divmod(self.SessionStop - self.SessionStart, 3600)
                minutes, seconds = divmod(rem, 60)
                self.SessionDuration = ["{:0>2}:{:0>2}:{:05.2f}".format(int(hours),int(minutes),seconds)]
            except:
                print("Didn't start session")
            winsound.PlaySound(None, winsound.SND_PURGE)
            if self.readyforplexon == True:
                self.plexdo.clear_bit(self.device_number, self.RewardDO_chan)
            print('Stop')
            self.StartButtonBool = False
            self.MonkeyLoop = False
            self.StartTrialBool = False
            self.PictureBool = False
            self.CurrentPress = False
            self.JoystickPulled = False
            self.ReadyForSound = False
            self.PunishLockout = False
            self.ReadyForPull = False
            self.OutofHomeZoneOn = False
            self.counter = 0
            self.next_image()
            self.after(0,func=None)
        else:
            print('Start First')
        
    def TotalTrials(self):
            print('Total Trials: %i' %self.csvdict['Total Trials'][0])
            print('Total t1 fails: %i' %self.csvdict['Total t1 failures'][0])
            print('Total t2 fails: %i' %self.csvdict['Total t2 failures'][0])
            print('Total pull fails: %i' %self.csvdict['Total pull failures'][0])
            print('Total no pulls: %i' %self.csvdict['No Pull'][0])
            print('Total successes: %i' %self.csvdict['Total successes'][0])
            
    def Test(self):
        print('test')
        # print('self.MonkeyLoop',self.MonkeyLoop)
        # print('self.StartTrialBool',self.StartTrialBool)
        # print('self.CurrentPress',self.CurrentPress)
        # print('self.JoystickPulled',self.JoystickPulled)
        # print('self.PictureBool',self.PictureBool)
        # print('self.ReadyForSound',self.ReadyForSound)
        # print('self.PunishLockout',self.PunishLockout)
        # print('self.ReadyForPull',self.ReadyForPull)
        # print('self.OutofHomeZoneOn',self.OutofHomeZoneOn)
        # print('self.Area1_right_pres',self.Area1_right_pres)
        # print('self.Area2_right_pres',self.Area2_right_pres)
        # print('self.Area1_left_pres',self.Area1_left_pres)
        # print('self.Area2_left_pres',self.Area2_left_pres)
        # print('self.ImageReward',self.ImageReward)
        
        

        
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event0,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event1,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event2,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event3,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event4,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event5,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event7,None,None)
        # self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event2,None,None)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event3,None,None)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event5,None,None)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event7,None,None)
        # self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
        # time.sleep(0.1)
        
    def StartTrialCue(self):
        if self.counter == 0:
            self.counter = -2
            self.next_image()
        elif self.counter == -2:
            self.counter = 0
            self.next_image()
        if self.OutofHomeZoneOn == False:
            winsound.PlaySound('OutOfHomeZone.wav', winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT + winsound.SND_LOOP) #Need to change the tone
            self.OutofHomeZoneOn = True

    def EndTrialCue(self):
        self.counter = 0
        self.next_image()
    
    def Metabutton(self):
        print(self.metadict)

    def Durationbutton(self):
        print(self.csvdict)

    def Rangesbutton(self):
        print(self.Ranges)

    def KeyPress(self, event):
        key = event.char
        if key == 'a':
            self.Start()
        elif key == 's':
            self.Pause()
        elif key == 'd':
            self.Unpause()
        elif key == 'f':
            self.Stop()
        elif key == 'z':
            self.RewardTime = self.MaxReward # Gives MaxReward for the water
            self.WaterReward.run()
        elif key == 'x':
            self.TotalTrials()
        elif key == 'c':
            self.FormatDurations()

    def WaterButton(self):
        self.WaterReward.run()

    def ConfusionMatrix(self): # This will only be called once at the beginning
        self.confmat = tk.Toplevel(self)
        self.confmat.wm_title("Confusion Matrix")
        pn = tk.Label(self.confmat, text="Predicted: No")
        py = tk.Label(self.confmat, text="Predicted: Yes")
        an = tk.Label(self.confmat, text="Actual: No")
        ay = tk.Label(self.confmat, text="Actual: Yes")

        pnan = tk.Label(self.confmat, text="%s" % self.pnan)
        pyan = tk.Label(self.confmat, text="%s" % self.pyan)
        pnay = tk.Label(self.confmat, text="%s" % self.pnay)
        pyay = tk.Label(self.confmat, text="%s" % self.pyay)

        pn.grid(row = 0, column = 1)
        py.grid(row = 0, column = 2)
        an.grid(row = 1, column = 0)
        ay.grid(row = 2, column = 0)

        pnan.grid(row = 1, column = 1)
        pyan.grid(row = 1, column = 2)
        pnay.grid(row = 2, column = 1)
        pyay.grid(row = 2, column = 2)


    def ConfusionMatrixUpdate(self):
        self.pnan = (self.pnan + 1) # Predicted: No, Actual: No
        self.pyan = (self.pyan + 1) # Predicted: Yes, Actual: No
        self.pnay = (self.pnay + 1) # Predicted: No, Actual: Yes
        self.pyay = (self.pyay + 1) # Predicted: Yes, Actual: Yes
    
    ### These attach to buttons that will select if Monkey has access to the highly coveted monkey image reward
    def HighLevelRewardOn(self):
        print('Image Reward On')
        self.ImageReward = True

    def HighLevelRewardOff(self):
        print('Image Reward Off')
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
        self.client.opx_wait(1000)
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
                if source_numbers_types[new_data.source_num_or_type[i]] == CONTINUOUS_TYPE and (new_data.channel[i] in self.ActiveJoystickChans
                     or new_data.channel[i] == self.Area1_right or new_data.channel[i] == self.Area2_right or new_data.channel[i] == self.Area1_left
                     or new_data.channel[i] == self.Area2_left):
                    # Output info
                    tmp_source_number = new_data.source_num_or_type[i]
                    tmp_channel = new_data.channel[i]
                    tmp_source_name = source_numbers_names[tmp_source_number]
                    tmp_voltage_scaler = source_numbers_voltage_scalers[tmp_source_number]
                    tmp_timestamp = new_data.timestamp[i]
                    tmp_unit = new_data.unit[i]
                    #tmp_rate = source_numbers_rates[tmp_source_number]
    
                    # Convert the samples from AD units to voltage using the voltage scaler, use tmp_samples[0] because it could be a list.
                    tmp_samples = new_data.waveform[i][:max_samples_output]
                    tmp_samples = [s * tmp_voltage_scaler for s in tmp_samples]
                    if new_data.channel[i] == 1:
                        if self.Pedal1 < self.PullThreshold and tmp_samples[0] >= self.PullThreshold:
                            # print('start press')
                            self.StartTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            if self.CurrentPress == False and self.ReadyForPull == True:
                                self.CurrentPress = True
                        elif self.Pedal1 >= self.PullThreshold and tmp_samples[0] < self.PullThreshold:
                            # print('stop press')
                            self.StopTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            self.DurationTimestamp = self.StopTimestamp - self.StartTimestamp
                            #
    
                        self.Pedal1 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal1)
                    elif new_data.channel[i] == 2:
    
                        if self.Pedal2 < self.PullThreshold and tmp_samples[0] >= self.PullThreshold:
                            # print('start press')
                            self.StartTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            if self.CurrentPress == False and self.ReadyForPull == True:
                                self.CurrentPress = True
                        elif self.Pedal2 >= self.PullThreshold and tmp_samples[0] < self.PullThreshold:
                            # print('stop press')
                            self.StopTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            self.DurationTimestamp = self.StopTimestamp - self.StartTimestamp
                            #
                            
    
                        self.Pedal2 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal2)
                    if new_data.channel[i] == 3: # Change to elif if using other channels 1,2 and 4.
    
                        if self.Pedal3 < self.PullThreshold and tmp_samples[0] >= self.PullThreshold:
                            # print('start press')
                            self.StartTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            if self.CurrentPress == False and self.ReadyForPull == True:
                                self.CurrentPress = True
                        elif self.Pedal3 >= self.PullThreshold and tmp_samples[0] < self.PullThreshold:
                            # print('stop press')
                            self.StopTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            self.DurationTimestamp = self.StopTimestamp - self.StartTimestamp
                            #
                            if self.T1FailBool == True:
                                self.csvdict[('Post t1 failure pull counter')][(len(self.csvdict['Trial Outcome'])-1)] += 1 # [0] Needs to be Trial number
                            if self.T2FailBool == True:
                                self.csvdict[('Post t2 failure pull counter')][(len(self.csvdict['Trial Outcome'])-1)] += 1 # [0] Needs to be Trial number
                                
                        self.Pedal3 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal3)
                    elif new_data.channel[i] == 4:
    
                        if self.Pedal4 < self.PullThreshold and tmp_samples[0] >= self.PullThreshold:
                            # print('start press')
                            self.StartTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            if self.CurrentPress == False and self.ReadyForPull == True:
                                self.CurrentPress = True
                        elif self.Pedal4 >= self.PullThreshold and tmp_samples[0] < self.PullThreshold:
                            # print('stop press')
                            self.StopTimestamp = tmp_timestamp - self.RecordingStartTimestamp
                            self.DurationTimestamp = self.StopTimestamp - self.StartTimestamp
                            #
    
                        self.Pedal4 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal4)
    
                    ################################################################ #TEMPFIX
                    # elif new_data.channel[i] == (self.Area1_right):
                    #     if tmp_samples[0] >= 1:
                    #         if self.Area1_right_pres == False and tmp_samples[0] >= 1: #Paw Into Home
                    #             print('Area1_right_pres set to True')
                    #             # #self.AddPawInHome(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area1_right_pres = True
                    #     else:
                    #         if self.Area1_right_pres == True and tmp_samples[0] <= 1: #Paw Out of Home
                    #             print('Area1_right_pres set to False')
                    #             # #self.AddPawOutHome(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area1_right_pres = False
                    #         ####### Connector Unplugged - Reset #TEMPFIX
                    #         if self.ReadyForPull == False and self.TrainingStart == True:
                    #             self.StartTrialBool = True
                    #             self.TrainingStart = False
                    #             self.PictureBool = False
                    #             self.counter = 0
                    #             self.next_image()
                    #         #######
                            
                            
                    # elif new_data.channel[i] == (self.Area1_left):
                    #     if tmp_samples[0] >= 1:
                    #         if self.Area1_left_pres == False and tmp_samples[0] >= 1: #Paw Into Home
                    #             print('Area1_left_pres set to True')
                    #             # #self.AddPawInHome(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area1_left_pres = True
                    #     else:
                    #         if self.Area1_left_pres == True and tmp_samples[0] <= 1: #Paw Out of Home
                    #             print('Area1_left_pres set to False')
                    #             # #self.AddPawOutHome(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area1_left_pres = False
    
                    # elif new_data.channel[i] == (self.Area2_right): 
                    #     if tmp_samples[0] >= 1:
                    #         if self.Area2_right_pres == False and tmp_samples[0] >= 1: #Paw Into Joystick
                    #             print('Area2_right_pres set to True')
                    #             # ####self.AddPawInJoystick(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area2_right_pres = True
                    #     else:
                    #         if self.Area2_right_pres == True and tmp_samples[0] <= 1: #Paw Out of Joystick
                    #             print('Area2_right_pres set to False')
                    #             # #self.AddPawOutJoystick(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area2_right_pres = False
                    # elif new_data.channel[i] == (self.Area2_left):
                    #     if tmp_samples[0] >= 1:
                    #         if self.Area2_left_pres == False and tmp_samples[0] >= 1: #Paw Into Joystick
                    #             print('Area2_left_pres set to True')
                    #             # ####self.AddPawInJoystick(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area2_left_pres = True
                    #     else:
                    #         if self.Area2_left_pres == True and tmp_samples[0] <= 1: #Paw Out of Joystick
                    #             print('Area2_left_pres set to False')
                    #             # #self.AddPawOutJoystick(tmp_timestamp - self.RecordingStartTimestamp)
                    #         self.Area2_left_pres = False
                    # # ##print values that we want from AI
                
                # This is for 2 events that come from Cineplex, might have to change channels depending on physical connections.
                # Waiting for Ryan to see if these should be event type or continuous
                elif new_data.source_num_or_type[i] == self.event_source: # Single-bit events EV01 - EV32
                    tmp_source_number = new_data.source_num_or_type[i]
                    tmp_channel = new_data.channel[i]
                    #tmp_source_name = source_numbers_names[tmp_source_number]
                    tmp_timestamp = new_data.timestamp[i]
                    #tmp_unit = new_data.unit[i]
                    
                    if tmp_channel == 9:
                        print('Area1_right_pres set to True')
                        self.Area1_right_pres = True
                        if self.TrainingStart == False:
                            self.HandInTime = tmp_timestamp - self.RecordingStartTimestamp
                            self.HandInBool = True
                    elif tmp_channel == 14:  # TEMPFIX 10 --> 14 because of hardware issue
                        print('Area1_right_pres set to False')
                        self.Area1_right_pres = False
                        self.HandOutTime = tmp_timestamp - self.RecordingStartTimestamp
                        self.HandDurationTime = self.HandOutTime - self.HandInTime
                        if self.ReadyForPull == True:
                            self.HandInBool = False
                            self.HandOutGCTime = tmp_timestamp - self.RecordingStartTimestamp
                            self.HandDurationGCTime = self.HandOutTime - self.HandInTime
                        if self.StartTrialBool == False:
                            if self.PictureBool == False:
                                self.csvdict['Total t1 failures'][0] += 1
                                self.csvdict['Trial Outcome'].append('t1 Fail')
                                self.csvdict[('Post t1 failure pull counter')].append(0)
                                self.csvdict[('Post t2 failure pull counter')].append(0)
                                self.csvdict['Trial DS Type'].append(0)
                                self.csvdict['Discriminant Stimuli On'].append('X')
                                self.csvdict['Go Cue On'].append('X')
                                self.AddPawInHome(self.HandInTime)
                                self.AddPawOutHome(self.HandOutTime)
                                self.csvdict['Duration in Home Zone'].append(self.HandDurationTime)
                                self.T1FailBool = True
                                self.StartTrialBool = True
                                self.TrainingStart = False
                                self.PictureBool = False
                                self.counter = 0
                                # EV24
                                self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
                                self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                                self.next_image()
                            elif self.PictureBool == True and self.ReadyForPull == False:
                                self.csvdict['Total t2 failures'][0] += 1
                                self.csvdict['Trial Outcome'].append('t2 Fail')
                                self.csvdict[('Post t1 failure pull counter')].append(0)
                                self.csvdict[('Post t2 failure pull counter')].append(0)
                                self.csvdict['Go Cue On'].append('X')
                                self.AddPawInHome(self.HandInTime)
                                self.AddPawOutHome(self.HandOutTime)
                                self.csvdict['Duration in Home Zone'].append(self.HandDurationTime)
                                self.T2FailBool = True
                                self.StartTrialBool = True
                                self.TrainingStart = False
                                self.PictureBool = False
                                self.counter = 0
                                self.next_image()
                                # EV24
                                self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event6,None,None)
                                self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                            # elif self.PictureBool == True and self.ReadyForPull == True:
                            #     self.csvdict['Total successes'][0] += 1
                            #     self.csvdict['Trial Outcome'].append('Success')
                            #     self.AddPawInHome(self.HandInTime)
                            #     self.AddPawOutHome(self.HandOutTime)
                            #     self.csvdict['Duration in Home Zone'].append(self.HandDurationTime)
                            self.DiscrimStimDuration = self.RandomDuration(self.DiscrimStimMin,self.DiscrimStimMax)
                            self.GoCueDuration = self.RandomDuration(self.GoCueMin,self.GoCueMax)
                            
                    
                    elif tmp_channel == 11:
                        pass
                        # self.HandInJoystickTime = tmp_timestamp - self.RecordingStartTimestamp
                        # self.HandInJoystickBool = True
                    elif tmp_channel == 12:
                        pass
                        # self.HandOutJoystickTime = tmp_timestamp - self.RecordingStartTimestamp
                        # self.HandOutJoystickBool = True

                        
                        
                    elif tmp_channel == 19: 
                        pass
                    elif tmp_channel == 20:
                        pass
                    elif tmp_channel == 21:
                        pass
                    elif tmp_channel == 23:
                        pass
                    elif tmp_channel == 24:
                        self.csvdict[('Trial End')].append(tmp_timestamp - self.RecordingStartTimestamp)
                        pass
                    elif tmp_channel == 25 or tmp_channel == 27 or tmp_channel == 29 or tmp_channel == 31:
                        self.AddDiscriminatoryStimulus(tmp_timestamp - self.RecordingStartTimestamp)
                        self.csvdict['Discriminant Stimuli On'].append(tmp_timestamp - self.RecordingStartTimestamp)
                    elif tmp_channel == 26:
                        self.AddGoCue(tmp_timestamp - self.RecordingStartTimestamp)
                        self.csvdict[('Discriminatory Stimulus Trial Count 1')][0] += 1
                        self.csvdict['Go Cue On'].append(tmp_timestamp - self.RecordingStartTimestamp)
                    elif tmp_channel == 28:
                        self.AddGoCue(tmp_timestamp - self.RecordingStartTimestamp)
                        self.csvdict[('Discriminatory Stimulus Trial Count 2')][0] += 1
                        self.csvdict['Go Cue On'].append(tmp_timestamp - self.RecordingStartTimestamp)
                    elif tmp_channel == 30:
                        self.AddGoCue(tmp_timestamp - self.RecordingStartTimestamp)
                        self.csvdict[('Discriminatory Stimulus Trial Count 3')][0] += 1
                        self.csvdict['Go Cue On'].append(tmp_timestamp - self.RecordingStartTimestamp)
                    elif tmp_channel == 32:
                        self.AddGoCue(tmp_timestamp - self.RecordingStartTimestamp)
                        self.csvdict[('Discriminatory Stimulus Trial Count 4')][0] += 1
                        self.csvdict['Go Cue On'].append(tmp_timestamp - self.RecordingStartTimestamp)
                    
    
                        
            except KeyError:
                pass
    #end of gathering data

########################################
##########TODO: Need to Queue water reward similar to online example to use time.sleep() / use after or some other method
########################################

    class WaterRewardThread(t.Thread,):
        def __init__(self):
            t.Thread.__init__(self)
        
        def run(self):
            print('start')
            time.sleep(MonkeyTest.RewardDelay)
            if MonkeyTest.ImageReward == True:
                MonkeyTest.counter = -1
                MonkeyTest.next_image()
            print("Water On")
            if MonkeyTest.readyforplexon == True:
                #EV23
                MonkeyTest.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,MonkeyTest.event7,None,None)
                MonkeyTest.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,MonkeyTest.begin,None,None)
                MonkeyTest.plexdo.set_bit(MonkeyTest.device_number, MonkeyTest.RewardDO_chan)
                time.sleep(MonkeyTest.RewardTime)
                MonkeyTest.plexdo.clear_bit(MonkeyTest.device_number, MonkeyTest.RewardDO_chan)
            print("Water Off")


if __name__ == "__main__":
    root = tk.Tk()
    
    MonkeyTest = MonkeyImages(root)

    tk.mainloop()