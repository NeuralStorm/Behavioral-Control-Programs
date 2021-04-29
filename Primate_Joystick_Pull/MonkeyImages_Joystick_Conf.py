
# For keypad controls, search "def KeyPress"

# Defs- DS: Discriminatory Stimuli, GC: Go Cue, 

# VERSION INCORPORATES CONFIG FILE IMPORT!!!

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

try:
    from pyopxclient import PyOPXClientAPI, CONTINUOUS_TYPE
    from pyplexdo import PyPlexDO, DODigitalOutputInfo
    import PyDAQmx
except ImportError:
    plexon_import_failed = True
else:
    plexon_import_failed = False

import tkinter as tk
from tkinter import *
from tkinter import filedialog
from PIL import Image, ImageTk
import csv
from csv import reader, writer
import os
import os.path
from pathlib import Path
import time
import random
import sys
try:
    import winsound
except ImportError:
    winsound = None
import math
import statistics
import sys, traceback
from pprint import pprint
import numpy

# readyforplexon = False

# from definitionsRyan.py
# This will be filled in later. Better to store these once rather than have to call the functions
# to get this information on every returned data block
source_numbers_types = {}
source_numbers_names = {}
source_numbers_rates = {}
source_numbers_voltage_scalers = {}

# from definitionsRyan.py
# To avoid overwhelming the console output, set the maximum number of data
# blocks to print information about
max_block_output = 1

# from definitionsRyan.py
# To avoid overwhelming the console output, set the maximum number of continuous
# samples or waveform samples to output
max_samples_output = 1

##############################################################################################
###M onkey Images Class set up for Tkinter GUI
class MonkeyImages(tk.Frame,):
    def __init__(self, parent):
        test_config = 'test' in sys.argv
        use_hardware = 'test' not in sys.argv and 'nohw' not in sys.argv
        
        self.readyforplexon = use_hardware  ### Nathan's Switch for testing while not connected to plexon omni. I will change to true / get rid of it when not needed.
                                    ### Also changed the server set up so that it won't error out and exit if the server is not on, but it will say Client isn't connected.
        self.nidaq = self.readyforplexon
        self.plexon = self.readyforplexon
        
        if self.readyforplexon:
            assert not plexon_import_failed
        
        # delay for how often state is updated, only used for new loop
        self.cb_delay_ms: int = 1
        
        self.joystick_pulled = False
        self.joystick_pull_remote_ts = None
        self.joystick_release_remote_ts = None
        
        # used in gathering_data_omni_new to track changes in joystick position
        self.joystick_last_state = None
        
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
        
        self.joystick_pull_threshold = 4
        
        root = Tk()
        if test_config:
            self.ConfigFilename = 'csvconfig_EXAMPLE_Joystick.csv'
        else:
            self.ConfigFilename =  filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("csv files","*.csv")))
        
        root.withdraw()
        print (self.ConfigFilename)
        csvreaderdict = {}
        data = []
        with open(self.ConfigFilename, newline='') as csvfile:
            spamreader = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
            for row in spamreader:
                #data = list(spamreader)
                data.append(row)
        csvfile.close()
        
        for row in range(0,len(data)):
            for entry in range(0,len(data[row])):
                if entry == 0:
                    csvreaderdict[data[row][0]] = []
                else:
                    csvreaderdict[data[row][0]].append(data[row][entry])
        
        config_dict = csvreaderdict
        # PARAMETERS META DATA
        self.StudyID = csvreaderdict['Study ID']                            # 3 letter study code
        self.SessionID = csvreaderdict['Session ID']                        # Type of Session
        self.AnimalID = csvreaderdict['Animal ID']                          # 3 digit number
        self.Date = [time.strftime('%Y%m%d')]                               # Today's Date
        #self.TaskType = 'Joystick'
        #self.TaskType = 'HomezoneExit'                                     # Added for Homezone exit version.  String should be 'HomezoneExit'  Leave blank for original Joystick version.
        self.TaskType = csvreaderdict['Task Type'][0]                       # Added additional rows into the config file to reduce
        self.source = Path(csvreaderdict['Path To Graphics Dir'][0])              # required in-code edits to change task versions. R.E. 7-29-2020
        
        if 'images' in config_dict:
            config_images = config_dict['images']
            self.list_images = [
                'aBlank.png',
                *(f'{x.strip()}.png' for x in config_images),
                *(f"{x.strip().replace('b', 'c').replace('d', 'e')}.png" for x in config_images),
                'xBlack.png',
                'yPrepare.png',
                'zMonkey2.png',
            ]
            def build_image_entry(i, x):
                x = x.strip()
                return x, {
                    'path': f"{x}.png",
                    'boxed_path': f"{x.replace('b', 'c').replace('d', 'e')}.png",
                    'list_images_index': i+1,
                }
            
            images = dict(
                build_image_entry(i, x)
                for i, x in enumerate(config_images)
            )
            self.images = images
            self.num_task_images = len(config_dict['images'])
        else:
            self.num_task_images = config_dict.get('num_task_images', 3)
            assert False, "config images is now required"
        
        def parse_threshold(s):
            s = s.strip()
            s = s.split('\'')
            s = [x.split('=') for x in s]
            rwd = {k: v for k, v in s}
            
            if 'cue' in rwd:
                assert rwd['cue'] in self.images
            else:
                rwd['cue'] = None
            
            for x in ['low', 'mid', 'high']:
                if x in rwd:
                    rwd[x] = float(rwd[x])
            
            if 'mid' not in rwd:
                rwd['mid'] = rwd['low'] + (rwd['high'] - rwd['low']) / 2
            elif 'low' not in rwd:
                rwd['low'] = rwd['mid'] - (rwd['high'] - rwd['mid'])
            elif 'high' not in rwd:
                rwd['high'] = rwd['mid'] + (rwd['mid'] - rwd['low'])
            
            assert rwd['low'] < rwd['mid'] < rwd['high']
            
            if rwd['type'] == 'linear':
                for x in ['reward_max', 'reward_min']:
                    rwd[x] = float(rwd[x])
            elif rwd['type'] == 'flat':
                rwd['reward_duration'] = float(rwd['reward_duration'])
            else:
                raise ValueError(f"invalid reward type {rwd['type']}")
            
            return rwd
        
        rw_thr = config_dict['reward_thresholds']
        rw_thr = [parse_threshold(x) for x in rw_thr]
        # pprint(rw_thr)
        
        self.reward_thresholds = rw_thr
        
        # PARAMETERS
        # self.filename = 'test'
        #self.savepath = os.path.join('D:', os.sep, 'IntervalTimingTaskData')            # Path to outside target directory for saving csv file
        self.savepath = Path(csvreaderdict['Task Data Save Dir'][0])
        self.filename = self.StudyID[0] + '_' + self.AnimalID[0] + '_' + self.Date[0] + '_' + self.TaskType # Consolidate metadata into filename
        self.fullfilename = self.filename + '.csv'                                                          # Append filename extension to indicate type
        self.DiscrimStimMin = float(csvreaderdict['Pre Discriminatory Stimulus Min delta t1'][0])           # (seconds) Minimum seconds to display Discrim Stim for before Go Cue
        self.DiscrimStimMax = float(csvreaderdict['Pre Discriminatory Stimulus Max delta t1'][0])           # (seconds) Maxiumum seconds to display Discrim Stim for before Go Cue
        self.DiscrimStimDuration = self.random_duration(self.DiscrimStimMin, self.DiscrimStimMax)             # (seconds) How long is the Discriminative Stimulus displayed for.
        self.GoCueMin = float(csvreaderdict['Pre Go Cue Min delta t2'][0])#0.25                             # (seconds) Minimum seconds to display Discrim Stim for before Go Cue
        self.GoCueMax = float(csvreaderdict['Pre Go Cue Max delta t2'][0])#0.5                              # (seconds) Maxiumum seconds to display Discrim Stim for before Go Cue
        self.GoCueDuration = self.random_duration(self.GoCueMin, self.GoCueMax)                               # (seconds) How long is the Discriminative Stimulus displayed for.
        self.MaxTimeAfterSound = int(csvreaderdict['Maximum Time After Sound'][0])                          # (seconds) Maximum time Monkey has to pull. However, it is currently set so that it will not reset if the Pedal is being Pulled
        self.NumEvents = int(csvreaderdict['Number of Events'][0])                                          # Number of different (desired) interval durations for the animal to produce,
                                                                                                            # corresponds to the number of unique discriminative stimuli.
        
        if self.NumEvents == 0:
            self.NumEvents = 1
            self.task_type = 'homezone_exit'
        else:
            self.task_type = 'joystick_pull'
        
        self.InterTrialTime = float(csvreaderdict['Inter Trial Time'][0])                                   # (seconds) Time between Trials / Reward Time
        self.EarlyPullTimeOut = (csvreaderdict['Enable Early Pull Time Out'][0] == 'TRUE')                  # This Boolean sets if you want to have a timeout for a pull before the Go Red Rectangle.
        self.RewardDelayMin = float(csvreaderdict['Pre Reward Delay Min delta t3'][0])#0.010                # (seconds) Min Length of Delay before Reward (Juice) is given.
        self.RewardDelayMax = float(csvreaderdict['Pre Reward Delay Max delta t3'][0])#0.010                # (seconds) Max Length of Delay before Reward (Juice) is given.
        self.RewardDelay = self.random_duration(self.RewardDelayMin, self.RewardDelayMax)                    # (seconds) Length of Delay before Reward (Juice) is given.
        
        self.manual_reward_time = float(csvreaderdict['manual_reward_time'][0])
        self.EnableTimeOut = (csvreaderdict['Enable Time Out'][0] == 'TRUE')                                # Toggle this to True if you want to include 'punishment' timeouts (black screen for self.TimeOut duration), or False for no TimeOuts.
        self.TimeOut = float(csvreaderdict['Time Out'][0])                                                  # (seconds) Time for black time out screen
        self.EnableBlooperNoise = (csvreaderdict['Enable Blooper Noise'][0] == 'TRUE')                      # Toggle this to True if you want to include the blooper noise when an incorrect pull is detected (Either too long or too short / No Reward Given)
        
        ############# Task sounds 
        self.RewardSound = 'Exclamation'
        #self.Bloop       = 'Question'
        #self.Bloop = '.\\TaskSounds\\WrongHoldDuration.wav'
        self.Bloop = str(Path('./TaskSounds/WrongHoldDuration.wav'))
        #self.OutOfHomeZoneSound = '.\\TaskSounds\\OutOfHomeZone.wav'
        self.OutOfHomeZoneSound = str(Path('./TaskSounds/OutOfHomeZone.wav'))
        ##############

        ############# Initializing vars
        # self.DurationList()                                 # Creates dict of lists to encapsulate press durations. Will be used for Adaptive Reward Control
        self.counter = 0 # Counter Values: Alphabetic from TestImages folder
        # Blank(white screen), disc stim 1, disc stim 2, disc stim 3, disc stim go 1, disc stim go 2, disc stim go 3, black(timeout), Prepare(to put hand in position), Monkey image
        self.current_counter = 0 
        self.excluded_events = [] #Might want this for excluded events
        
        self.reward_nidaq_bit = 1 # DO Channel
        
        self.Area1_right_pres = False   # Home Area
        self.Area2_right_pres = False   # Joystick Area
        self.Area1_left_pres = False    # Home Area
        self.Area2_left_pres = False    # Joystick Area
        self.ImageReward = False        # Default Image Reward set to True
        
        print("ready for plexon:" , self.readyforplexon)
        tk.Frame.__init__(self, parent)
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
        
        # Likely Don't Need these buttons, Image reward will always be an option, and will be controlled by %
        ImageRewardOn = tk.Button(self.root, text = "ImageReward\nOn", height = 5, width = 10, command = self.HighLevelRewardOn)
        ImageRewardOn.pack(side = LEFT)
        ImageRewardOff = tk.Button(self.root, text = "ImageReward\nOff", height = 5, width = 10, command = self.HighLevelRewardOff)
        ImageRewardOff.pack(side = LEFT)
        
        testbutton = tk.Button(self.root, text = "Water Reward-'z'", height = 5, width = 12, command = self.manual_water_dispense)
        testbutton.pack(side = LEFT)
        
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
    
    # resets loop state, starts callback loop
    def start_new_loop(self):
        self.last_new_loop_time = time.monotonic()
        self.new_loop_iter = self.new_loop_gen()
        self.normalized_time = 0
        next(self.new_loop_iter)
        self.after(self.cb_delay_ms, self.progress_new_loop)
    
    def progress_new_loop(self):
        if self.stopped:
            return
        
        cur_time = time.monotonic()
        elapsed_time = cur_time - self.last_new_loop_time
        self.last_new_loop_time = cur_time
        
        if not self.paused:
            self.normalized_time += elapsed_time
        
        self.new_loop_upkeep()
        next(self.new_loop_iter)
        
        self.after(self.cb_delay_ms, self.progress_new_loop)
    
    def new_loop_upkeep(self):
        # self.gathering_data_omni()
        if self.plexon:
            self.gathering_data_omni_new()
    
    def new_loop_gen(self):
        while True:
            # print(self.normalized_time)
            
            trial_start = self.normalized_time
            
            def in_zone():
                return self.Area1_right_pres or self.Area1_left_pres
            
            def trial_t():
                return self.normalized_time - trial_start
            
            def wait(t):
                start_time = trial_t()
                while trial_t() - start_time < t:
                    yield
            
            if winsound is not None:
                winsound.PlaySound(
                    self.OutOfHomeZoneSound,
                    winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT + winsound.SND_LOOP
                ) #Need to change the tone
            
            icon_flash_freq = 2
            # icon period = 1 / freq
            # change period = 0.5 * period
            icon_change_period = 0.5 / icon_flash_freq
            # wait for hand to be in the home zone
            # wait at least inter-trial time before starting
            while True:
                # print(trial_t())
                # print((trial_t() * 1000 // 500))
                if (trial_t() // icon_change_period) % 2:
                    self.counter = 0 # blank
                else:
                    self.counter = -2 # black diamond
                self.next_image()
                
                if trial_t() > self.InterTrialTime and in_zone():
                    break
                yield
            
            # switch to blank to ensure diamond is no longer showing
            self.counter = 0
            self.next_image()
            
            if winsound is not None:
                winsound.PlaySound(winsound.Beep(100,0), winsound.SND_PURGE) #Purge looping sounds
            
            # EV19 Ready # TODO: Take this out when finish the connector since new start of trial comes from hand in home zone
            if self.nidaq:
                self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event7,None,None)
                self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            yield from wait(self.DiscrimStimDuration)
            
            # choose image
            selected_image_key = random.choice(list(self.images))
            selected_image = self.images[selected_image_key]
            image_i = selected_image['list_images_index']
            
            # EV25 , EV27, EV29, EV31
            if image_i in [1,2,3,4]:
                event_array = [None, self.event5, self.event3, self.event1, self.event2][image_i]
                if self.nidaq:
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,event_array,None,None)
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            # display image without red box
            self.counter = image_i
            self.next_image()
            
            yield from wait(self.GoCueDuration)
            
            # EV26, EV28, EV30 EV32
            if image_i in [1,2,3,4]:
                # should this have duplicates with the list of event arrays above?
                event_array = [None, self.event4, self.event2, self.event0, self.event3][image_i]
                if self.nidaq:
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,event_array,None,None)
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            # display image with red box
            self.counter = image_i + self.num_task_images
            self.next_image()
            cue_time = trial_t()
            
            def get_pull_info():
                if self.joystick_pulled: # joystick pulled before prompt
                    return None, 0, 0
                
                # cue_time = trial_t()
                # wait up to MaxTimeAfterSound for the joystick to be pulled
                while not self.joystick_pulled:
                    if trial_t() - cue_time > self.MaxTimeAfterSound:
                        return None, 0, 0
                    yield
                
                pull_start = trial_t()
                
                while self.joystick_pulled:
                    yield
                
                pull_duration = trial_t() - pull_start
                assert self.joystick_pull_remote_ts is not None
                assert self.joystick_release_remote_ts is not None
                remote_pull_duration = self.joystick_release_remote_ts - self.joystick_pull_remote_ts
                assert remote_pull_duration >= 0
                
                # print(pull_duration, remote_pull_duration)
                reward_duration = self.ChooseReward(remote_pull_duration, cue=selected_image_key)
                
                return reward_duration, remote_pull_duration, pull_duration
            
            def get_homezone_exit_info():
                # hand removed from home zone before cue
                if not in_zone():
                    return None, 0, 0
                
                # wait up to MaxTimeAfterSound for the hand to exit the homezone
                while in_zone():
                    if trial_t() - cue_time > self.MaxTimeAfterSound:
                        return None, 0, 0
                    yield
                
                exit_time = trial_t()
                exit_delay = exit_time - cue_time
                
                reward_duration = self.ChooseReward(exit_delay, cue=selected_image_key)
                
                return reward_duration, 0, exit_delay
            
            task_type = self.task_type
            if task_type == 'joystick_pull':
                reward_duration, remote_pull_duration, pull_duration = yield from get_pull_info()
            elif task_type == 'homezone_exit':
                reward_duration, remote_pull_duration, pull_duration = yield from get_homezone_exit_info()
            else:
                assert False, f"invalid task_type {task_type}"
            
            print('Press Duration: {:.4f} ({:.4f})'.format(remote_pull_duration, pull_duration))
            print('Reward Duration: {}'.format(reward_duration))
            
            if reward_duration is None: # pull failed
                # EV21 Pull failure
                if self.nidaq:
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event5,None,None)
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                if self.EnableBlooperNoise:
                    if winsound is not None:
                        winsound.PlaySound(self.Bloop, winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                if self.EnableTimeOut:
                    self.counter = -3
                    self.next_image()
                    yield from wait(self.TimeOut)
            else: # pull suceeded
                if self.ImageReward:
                    self.counter = -1
                    self.next_image()
                #EV20
                if self.nidaq:
                    self.task2.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event6, None, None)
                    self.task2.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
                if winsound is not None:
                    winsound.PlaySound('550Hz_0.5s_test.wav', winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                
                yield from wait(self.RewardDelay)
                
                if self.readyforplexon:
                    #EV23
                    self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event7, None, None)
                    self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
                    # turn water on
                    self.plexdo.set_bit(self.device_number, self.reward_nidaq_bit)
                
                yield from wait(reward_duration)
                
                if self.readyforplexon:
                    self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
                
                self.DiscrimStimDuration = self.random_duration(self.DiscrimStimMin, self.DiscrimStimMax)
                self.GoCueDuration = self.random_duration(self.GoCueMin, self.GoCueMax)
            
            # EV24
            if self.nidaq:
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event6, None, None)
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
    
    def manual_water_dispense(self):
        def gen():
            print("water on")
            if self.readyforplexon:
                #EV23
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event7, None, None)
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
                self.plexdo.set_bit(self.device_number, self.reward_nidaq_bit)
            t = time.monotonic()
            while time.monotonic() - t < self.manual_reward_time:
                yield
            print("water off")
            if self.readyforplexon:
                self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
        
        loop_iter = gen()
        def inner():
            try:
                next(loop_iter)
            except StopIteration:
                pass
            else:
                self.after(self.cb_delay_ms, inner)
        
        inner()
    
    def random_duration(self, d_min, d_max):
        output = round(random.uniform(d_min,d_max),2)
        return output
    
    def ChooseReward(self, duration, cue):
        
        # if self.reward_thresholds is not None:
        for rwd in self.reward_thresholds:
            if duration >= rwd['low'] and duration <= rwd['high']:
                pass
            else:
                continue
            if rwd['cue'] is not None and rwd['cue'] != cue:
                continue
            
            if rwd['type'] == 'flat':
                return rwd['reward_duration']
            elif rwd['type'] == 'linear':
                if duration >= rwd['low'] and duration <= rwd['high']:
                    # get distance from optimal time
                    dist = abs(duration - rwd['mid'])
                    # get distance from closest edge of range
                    dist = (rwd['mid'] - rwd['low']) - dist
                    # get percent of distance from edge of range
                    if duration >= rwd['mid']:
                        perc = dist / (rwd['high'] - rwd['mid'])
                    else:
                        perc = dist / (rwd['mid'] - rwd['low'])
                    # get reward duration from percent
                    rwd_dur = perc * (rwd['reward_max'] - rwd['reward_min']) + rwd['reward_min']
                    return rwd_dur
                
            else:
                assert False
        
        return None
    
    def Start(self):
        self.paused = False
        self.stopped = False
        
        self.start_new_loop()
    
    def Pause(self):
        self.paused = True
        self.plexdo.clear_bit(MonkeyTest.device_number, MonkeyTest.reward_nidaq_bit)
        
        print('pause')
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        if self.readyforplexon == True:
            self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
    
    def Unpause(self):
        self.paused = False
    
    def Stop(self):
        self.stopped = True
        
        if self.readyforplexon == True:
            self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
        self.counter = 0
        self.next_image()
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
    
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
            self.manual_water_dispense()
        elif key == '`':
            sys.exit()
        elif key == '1':
            self.Area1_right_pres = not self.Area1_right_pres
            # self.Area1_left_pres = True
            print('in zone toggled', self.Area1_right_pres)
        elif key == '2':
            if not self.joystick_pulled:
                self.joystick_pull_remote_ts = time.monotonic()
                self.joystick_pulled = True
            else:
                self.joystick_release_remote_ts = time.monotonic()
                self.joystick_pulled = False
            
            print('press', self.joystick_pulled, event)
    
    ### These attach to buttons that will select if Monkey has access to the highly coveted monkey image reward
    def HighLevelRewardOn(self):
        print('Image Reward On')
        self.ImageReward = True

    def HighLevelRewardOff(self):
        print('Image Reward Off')
        self.ImageReward = False

    def next_image(self):
        im = Image.open(self.source / self.list_images[self.counter])    # Bypassing hard-coded path strings (above lines) R.E. 7/29/2020
        if (490-im.size[0])<(390-im.size[1]):
            width = 1600
            height = width*im.size[1]/im.size[0]
            self.next_step(height, width)
        else:
            height = 800
            width = height*im.size[0]/im.size[1]
            self.next_step(height, width)

    def next_step(self, height, width):
        self.im = Image.open(self.source / self.list_images[self.counter])   # Bypassing hard-coded path strings (above lines) R.E. 7/29/2020
        self.im.thumbnail((width, height), Image.ANTIALIAS)
        self.root.photo = ImageTk.PhotoImage(self.im)
        self.photo = ImageTk.PhotoImage(self.im)
        if self.counter == 0:
            self.cv1.create_image(0, 0, anchor = 'nw', image = self.photo)
        else:
            self.im.thumbnail((width, height), Image.ANTIALIAS)
            self.cv1.delete("all")
            self.cv1.create_image(0, 0, anchor = 'nw', image = self.photo)
    
    def gathering_data_omni_new(self):
        self.client.opx_wait(1000)
        new_data = self.client.get_new_data()
        
        JOYSTICK_CHANNEL = 3
        # joystick threshold
        js_thresh = self.joystick_pull_threshold
        
        for i in range(new_data.num_data_blocks):
            num_or_type = new_data.source_num_or_type[i]
            block_type = source_numbers_types[new_data.source_num_or_type[i]]
            chan = new_data.channel[i]
            ts = new_data.timestamp[i]
            
            if block_type == CONTINUOUS_TYPE:
                # Convert the samples from AD units to voltage using the voltage scaler, use tmp_samples[0] because it could be a list.
                voltage_scaler = source_numbers_voltage_scalers[num_or_type]
                samples = new_data.waveform[i][:max_samples_output]
                samples = [s * voltage_scaler for s in samples]
                val = samples[0]
                
                if chan == JOYSTICK_CHANNEL:
                    if self.joystick_last_state is None:
                        self.joystick_last_state = val
                    
                    # joystick has transitioned from not pulled to pulled
                    if self.joystick_last_state < js_thresh and val >= js_thresh:
                        self.joystick_pulled = True
                        self.joystick_pull_remote_ts = ts
                    # joystick has transitioned from pulled to not pulled
                    elif self.joystick_last_state >= js_thresh and val < js_thresh:
                        self.joystick_pulled = False
                        self.joystick_release_remote_ts = ts
                    
                    self.joystick_last_state = val
            elif num_or_type == self.event_source:
                if chan == 9:
                    self.Area1_right_pres = True
                elif chan == 14:
                    self.Area1_right_pres = False

class TestFrame(tk.Frame,):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        
        def x():
            pass
        
        startbutton = tk.Button(parent, text = "Start-'a'", fg='white', height = 5, width = 6, command = x)
        startbutton.pack(side = LEFT)
    

if __name__ == "__main__":
    root = tk.Tk()
    
    MonkeyTest = MonkeyImages(root)
    # MonkeyTest = TestFrame(root)
    
    tk.mainloop()