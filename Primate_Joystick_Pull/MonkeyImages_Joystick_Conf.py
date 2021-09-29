"""
    Sound effects obtained from https://www.zapsplat.com
    """
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

from typing import List, Tuple, Optional, Literal

try:
    from pyopxclient import PyOPXClientAPI, OPX_ERROR_NOERROR, SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, OTHER_TYPE
    from pyplexdo import PyPlexDO, DODigitalOutputInfo
    import PyDAQmx
    from PyDAQmx import Task
except ImportError:
    plexon_import_failed = True
else:
    plexon_import_failed = False

import tkinter as tk
# from tkinter import *
from tkinter import filedialog
from tkinter.font import Font
from PIL import Image, ImageTk
import pyscreenshot as ImageGrab
import csv
import json
import os
import os.path
from pathlib import Path
import time
from datetime import datetime, timedelta
import random
import sys
from contextlib import ExitStack
try:
    import winsound
except ImportError:
    winsound = None # type: ignore
import math
import statistics
from collections import defaultdict, Counter
import sys, traceback
from pprint import pprint
import numpy

# This will be filled in later. Better to store these once rather than have to call the functions
# to get this information on every returned data block
source_numbers_types = {}
source_numbers_names = {}
source_numbers_rates = {}
source_numbers_voltage_scalers = {}

# To avoid overwhelming the console output, set the maximum number of data
# blocks to print information about
max_block_output = 1

# To avoid overwhelming the console output, set the maximum number of continuous
# samples or waveform samples to output
max_samples_output = 1

# img: output of pillow Image
# color: (r, g, b)
def recolor(img, color, *, two_tone=False):
    # img = img.copy()
    # create copy of image and ensure there is an alpha channel
    img = img.convert("RGBA")
    data = img.load()
    
    nr, ng, nb = color
    
    for x in range(img.size[0]):
        for y in range(img.size[1]):
            r, g, b, a = data[x, y]
            
            v = (r + g + b) // 3
            v = 255 - v
            
            if two_tone and v > 0:
                v = 255
            
            data[x, y] = (nr, ng, nb, v)
    
    return img

def _screenshot_region(x: int, y: int, w: int, h: int) -> Image:
    # x //= 2
    # y //= 2
    
    bbox = (x, y, x+w, y+h)
    
    # img = ImageGrab.grab(bbox=bbox, backend='grim')
    img = ImageGrab.grab(bbox=bbox)
    return img

def screenshot_widgets(widgets, path):
    if not widgets:
        return
    
    # for widget in widgets:
    #     print('-')
    #     print(' ', widget.winfo_rooty())
    #     print(' ', widget.winfo_y())
    
    x_min = min(x.winfo_rootx() for x in widgets)
    x_max = max(x.winfo_rootx() + x.winfo_width() for x in widgets)
    y_min = min(x.winfo_rooty() for x in widgets)
    y_max = max(x.winfo_rooty() + x.winfo_height() for x in widgets)
    
    # print(x_min, x_max, y_min, y_max)
    
    img = _screenshot_region(x_min, y_min, x_max-x_min, y_max-y_min)
    img.save(path, 'PNG')

def screenshot_widget(widget, path):
    # x = widget.winfo_rootx() + widget.winfo_x()
    # y = widget.winfo_rooty() + widget.winfo_y()
    # x //= 2
    # y //= 2
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    
    w = widget.winfo_width()
    h = widget.winfo_height()
    # x_ = x + widget.winfo_width()
    # y_ = y + widget.winfo_height()
    
    # bbox = (x, y, x_, y_)
    # print(bbox)
    # (4916, 3910, 5760, 4254)
    # 2604,1890 572x401
    
    img = _screenshot_region(x, y, w, h)
    # img = ImageGrab.grab(bbox=bbox, backend='grim')
    
    # img = ImageGrab.grab(backend='grim')
    img.save(path, 'PNG')

class RegisteredCallback:
    def __init__(self, cb, _clear_callback):
        self._cb = cb
        self._clear_callback = _clear_callback
    
    def __enter__(self):
        pass
    
    def __exit__(self, *exc):
        self.clear()
    
    def clear(self):
        self._clear_callback(self._cb)

class Waiter:
    def __init__(self, parent: 'MonkeyImages', trial_t):
        self.parent = parent
        self.trial_t = trial_t
        
        self.trigger: Literal['time', 'event', 'cond'] = 'time'
        self.time_waited: float = 0
    
    def wait(self, t: Optional[float], *, event: Optional[str] = None, cond=None):
        start_time = self.trial_t()
        with ExitStack() as wait_stack:
            event_triggered = [False]
            if event is not None:
                def event_cb():
                    event_triggered[0] = True
                cb = self.parent._register_callback(event, event_cb)
                wait_stack.enter_context(cb)
            while 1:
                if t is not None and self.trial_t() - start_time >= t:
                    self.trigger = 'time'
                    break
                if event_triggered[0]:
                    self.trigger = 'event'
                    break
                if cond is not None and cond():
                    self.trigger = 'cond'
                    break
                yield
        
        self.time_waited = self.trial_t() - start_time

class InfoView:
    def __init__(self, root, *, monkey_images=None):
        self.monkey_images = monkey_images
        _orig_root = root
        self.window = tk.Toplevel(root)
        root = self.window
        root.geometry('800x600')
        root.bind('<Key>', self.key_handler)
        
        font = Font(family='consolas', size=15)
        self.label = tk.Label(root, text = '-', justify=tk.LEFT, font=font)
        self.label.pack(side=tk.TOP, anchor=tk.NW)
        
        self.rows = []
    
    def key_handler(self, event):
        if self.monkey_images is not None:
            self.monkey_images.KeyPress(event)
    
    @staticmethod
    def gen_histogram(event_log, *, h_range):
        events = [e for e in event_log if e['name'] == 'task_completed']
        
        def get_bin_ranges():
            start, end = h_range
            step = 0.5
            
            ws = start # window start
            we = step # window end
            while ws < end:
                yield ws, we
                ws = we
                if we < 1.999999999:
                    we = ws + 0.2
                else:
                    we = ws + step
        bins = {
            k: []
            for k in get_bin_ranges()
        }
        errors = Counter()
        
        for e in events:
            a_d = e['info']['action_duration']
            if a_d == 0 and e['info']['failure_reason'] is not None:
                errors[e['info']['failure_reason']] += 1
                continue
            for (bin_s, bin_e), bin_events in bins.items():
                if bin_s <= a_d < bin_e:
                    bin_events.append(e['info']['success'])
                    break
        
        # bins = {(start:float, end:float): [success:bool,...],...}
        # errors = {errors:str: error_count:int}
        return bins, errors
    
    def update_info(self, end_info, event_log):
        out = []
        
        ad = end_info['action_duration']
        out.append("duration")
        out.append(f"  min-max: {ad['min']:.3f}-{ad['max']:.3f}")
        out.append(f"  mean: {ad['mean']:.3f} stdev: {ad['stdev']:.3f}")
        
        out.append(f"trials: {end_info['count']}")
        out.append("")
        errors = end_info['errors']
        if errors:
            error_col_width = max(len(e) for e in errors)
            for error, error_info in errors.items():
                count = error_info['count']
                perc = error_info['percent']
                out.append(f"{error.rjust(error_col_width)} {count:>2} {perc*100:.1f}%")
            out.append("")
        
        print("\n".join(out))
        self.label['text'] = "\n".join(out)
        # import pdb;pdb.set_trace()
        
        h_min = math.floor(ad['min'])
        h_max = math.ceil(ad['max'])
        bins, errors = self.gen_histogram(event_log, h_range=(h_min, h_max))
        
        for row in self.rows:
            row.destroy()
        self.rows = []
        
        for (start, end), results in bins.items():
            frame = tk.Frame(self.window,
                # width = canvas_x, height = canvas_y,
                height = 5,
                bd = 0, bg='yellow',
                highlightthickness=0,)
            frame.pack(side = tk.TOP, anchor='nw', fill='x')
            font = Font(size=15)
            label = tk.Label(frame, text = f"{start:.2f}-{end:.2f}", justify=tk.LEFT, font=font,
                width=10, bg='#F0B000')
            label.pack(side=tk.LEFT, anchor=tk.NW, expand=False)
            
            canvas = tk.Canvas(frame,
                # width = canvas_x, height = canvas_y,
                height=0,
                # background = '#D0D0D0',
                background = 'black',
                bd = 0, relief = tk.FLAT,
                highlightthickness=0,)
            canvas.pack(side = tk.LEFT, expand=True, fill='both')
            
            x = 0
            for res in results:
                canvas.create_rectangle(x, 0, x+10, 100,
                    fill='green' if res else 'red')
                x += 12
            
            self.rows.append(frame)

##############################################################################################
###M onkey Images Class set up for Tkinter GUI
class MonkeyImages(tk.Frame,):
    def __init__(self, parent):
        test_config = 'test' in sys.argv or 'tc' in sys.argv
        no_wait_for_start = 'nw' in sys.argv
        use_hardware = 'test' not in sys.argv and 'nohw' not in sys.argv
        
        show_info_view = 'noinfo' not in sys.argv
        hide_buttons = 'nobtn' in sys.argv
        layout_debug = 'layout_debug' in sys.argv
        
        # self.nidaq = use_hardware
        self.nidaq = False
        self.plexon = use_hardware
        
        if self.plexon:
            assert not plexon_import_failed
        
        # delay for how often state is updated, only used for new loop
        self.cb_delay_ms: int = 1
        
        # False while the game is running or paused
        self.stopped: bool = True
        self.paused: bool = False
        
        self.joystick_pulled: bool = False # wether the joystick is currently pulled
        self.joystick_pull_remote_ts = None
        self.joystick_release_remote_ts = None
        
        # set in gathering_data_omni_new
        # if joystick_zone_enter is not None and joystick_zone_exit is None the hand is currently in the joystick zone
        # these track the time reported by plexon
        self.joystick_zone_enter = None # Optional[float]
        self.joystick_zone_exit = None # Optional[float]
        
        # used in gathering_data_omni_new to track changes in joystick position
        self.joystick_last_state = None
        
        # callbacks triggered by external events
        # Dict[str, Set[Callable[[], None]]]
        self._callbacks = {
            'homezone_enter': set(),
            'homezone_exit': set(),
        }
        
        self.trial_log = []
        self.event_log = []
        
        if self.plexon == True:
            ## Setup Plexon Server
            # Initialize the API class
            self.client = PyOPXClientAPI()
            # Connect to OmniPlex Server, check for success
            self.client.connect()
            if not self.client.connected:
                print("Client isn't connected, exiting.\n")
                print("Error code: {}\n".format(self.client.last_result))
                self.plexon = False

            print("Connected to OmniPlex Server\n")
            # Get global parameters
            global_parameters = self.client.get_global_parameters()

            for source_id in global_parameters.source_ids:
                source_name, _, _, _ = self.client.get_source_info(source_id)
                print('source', source_name, source_id)
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
                    source_types = { SPIKE_TYPE: "Spike", EVENT_TYPE: "Event", CONTINUOUS_TYPE: "Continuous", OTHER_TYPE: "Other" }
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
        
        if self.nidaq == True:
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
        
        self.auto_water_reward_enabled = True
        
        if test_config:
            self.ConfigFilename = 'dev_config.csv'
        else:
            root = tk.Tk()
            self.ConfigFilename =  filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("csv files","*.csv")))
            root.withdraw()
            del root
        
        print (self.ConfigFilename)
        csvreaderdict = {}
        data = []
        with open(self.ConfigFilename, newline='') as csvfile:
            spamreader = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
            for row in spamreader:
                #data = list(spamreader)
                data.append(row)
        csvfile.close()
        
        for row in data:
            k = row[0].strip()
            vs = [v.strip() for v in row[1:]]
            # remove empty cells after the key and first value column
            vs[1:] = [v for v in vs[1:] if v]
            if not k or k.startswith('#'):
                continue
            csvreaderdict[k] = vs
        
        config_dict = csvreaderdict
        # PARAMETERS META DATA
        self.study_id = config_dict['Study ID'][0]       # 3 letter study code
        self.session_id = csvreaderdict['Session ID'][0] # Type of Session
        self.animal_id = csvreaderdict['Animal ID'][0]   # 3 digit number
        self.start_time = time.strftime('%Y%m%d_%H%M%S')
        
        #self.TaskType = 'Joystick'
        #self.TaskType = 'HomezoneExit'
        self.TaskType = csvreaderdict['Task Type'][0]
        
        if 'images' in config_dict:
            config_images = config_dict['images']
            def build_image_entry(i, name):
                name = name.strip()
                assert '.' not in name, f"{name}"
                
                obj = {}
                
                for color in ['white', 'red', 'green']:
                    img = Image.open(f"./images_gen/{color}/{name}.png")
                    width = img.size[0]
                    height = img.size[1]
                    obj[color] = img
                
                obj[None] = obj['green']
                
                return name, {
                    'width': width,
                    'height': height,
                    'img': obj,
                    'nidaq_event_index': i+1,
                }
            
            images = dict(
                build_image_entry(i, x)
                for i, x in enumerate(config_images)
            )
            
            self.selectable_images = list(images)
            
            img = Image.open('./images_gen/prepare.png')
            
            images['yPrepare'] = {
                'width': img.size[0],
                'height': img.size[1],
                'img': {None: img},
            }
            
            red = Image.open('./images_gen/box_red.png')
            green = Image.open('./images_gen/box_green.png')
            white = Image.open('./images_gen/box_white.png')
            
            images['box'] = {
                'width': green.size[0],
                'height': green.size[1],
                'img': {
                    'red': red,
                    'green': green,
                    'white': white,
                    None: green,
                }
            }
            
            for image in images.values():
                image['tk'] = {
                    k: ImageTk.PhotoImage(img)
                    for k, img in image['img'].items()
                }
            
            self.images = images
        else:
            assert False, "config images is now required"
        
        def parse_threshold(s):
            s = s.strip()
            s = s.split('\'')
            s = [x.split('=') for x in s]
            rwd = {k.strip(): v.strip() for k, v in s}
            
            if 'cue' in rwd:
                assert rwd['cue'] in self.selectable_images, f"unknown cue {rwd['cue']}"
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
            elif rwd['type'] == 'trapezoid':
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
        
        # ensure that there are reward thresholds for all images or a threshold for all cues
        if all(x['cue'] is not None for x in rw_thr):
            for img in self.selectable_images:
                assert any(x['cue'] == img for x in rw_thr), f"cue {img} has no reward threshold"
        
        self.reward_thresholds = rw_thr
        
        self.save_path = Path(csvreaderdict['Task Data Save Dir'][0])
        self.log_file_name_base = f"{self.study_id}_{self.animal_id}_{self.session_id}_{self.start_time}_{self.TaskType}"
        self.ensure_log_file_creatable()
        
        self.discrim_delay_range = (
            float(config_dict['Pre Discriminatory Stimulus Min delta t1'][0]),
            float(config_dict['Pre Discriminatory Stimulus Max delta t1'][0]),
        )
        self.go_cue_delay_range = (
            float(config_dict['Pre Go Cue Min delta t2'][0]),
            float(config_dict['Pre Go Cue Max delta t2'][0]),
        )
        
        self.MaxTimeAfterSound = int(csvreaderdict['Maximum Time After Sound'][0])
        self.NumEvents = int(csvreaderdict['Number of Events'][0])
        
        if self.NumEvents == 0:
            self.NumEvents = 1
            self.task_type = 'homezone_exit'
        else:
            self.task_type = 'joystick_pull'
        
        self.InterTrialTime = float(csvreaderdict['Inter Trial Time'][0])
        
        self.manual_reward_time = float(csvreaderdict['manual_reward_time'][0])
        self.TimeOut = float(csvreaderdict['Time Out'][0])
        self.EnableTimeOut = bool(self.TimeOut)
        self.EnableBlooperNoise = (csvreaderdict['Enable Blooper Noise'][0] == 'TRUE')
        
        pspd = config_dict.get('post_succesful_pull_delay')
        if pspd in [[''], []]:
            pspd = None
        if pspd is not None:
            pspd = float(pspd[0])
        self.post_succesful_pull_delay: Optional[float] = pspd
        
        ############# Initializing vars
        # self.DurationList()                                 # Creates dict of lists to encapsulate press durations. Will be used for Adaptive Reward Control
        # self.counter = 0 # Counter Values: Alphabetic from TestImages folder
        # Blank(white screen), disc stim 1, disc stim 2, disc stim 3, disc stim go 1, disc stim go 2, disc stim go 3, black(timeout), Prepare(to put hand in position), Monkey image
        # self.current_counter = 0 
        # self.excluded_events = [] #Might want this for excluded events
        
        self.reward_nidaq_bit = 17 # DO Channel
        
        jc = config_dict.get('joystick_channel')
        if jc in [[''], [], None]:
            jc = [3]
        jc = int(jc[0])
        self.joystick_channel = jc
        
        num_trials = config_dict.get('no_trials')
        if num_trials == ['true']:
            num_trials = [0]
        elif num_trials in [[''], [], ['0']]:
            num_trials = None
        if num_trials is not None:
            num_trials = int(num_trials[0])
        self.max_trials = num_trials
        
        self.Area1_right_pres = False   # Home Area
        # self.Area2_right_pres = False   # Joystick Area
        # self.Area1_left_pres = False    # Home Area
        # self.Area2_left_pres = False    # Joystick Area
        self.ImageReward = True        # Default Image Reward set to True
        
        print("ready for plexon:" , self.plexon)
        tk.Frame.__init__(self, parent)
        self.root = parent
        self.root.wm_title("MonkeyImages")


        # hide_buttons = False
        # layout_debug = False
        def bgc(color):
            return color if layout_debug else 'black'
        
        ###Adjust width and height to fit monitor### bd is for if you want a border
        self.frame1 = tk.Frame(self.root,
            # width = canvas_x, height = canvas_y,
            bd = 0, bg=bgc('yellow'),
            highlightthickness=0,)
        self.frame1.pack(side = tk.BOTTOM, expand=True, fill=tk.BOTH)
        self.cv1 = tk.Canvas(self.frame1,
            # width = canvas_x, height = canvas_y,
            background = bgc('#F0B000'), bd = 0, relief = tk.FLAT,
            highlightthickness=0,)
        self.cv1.pack(side = tk.BOTTOM, expand=True, fill=tk.BOTH)
        
        btn_frame = tk.Frame(self.root,
            # width = canvas_x, height = canvas_y,
            bd = 0, bg=bgc('green'),
            highlightthickness=0)
        btn_frame.pack(side = tk.TOP, expand=False, fill=tk.BOTH)
        
        def btn(text, cmd):
            if hide_buttons:
                return
            b = tk.Button(
                # self.root, text = text,
                btn_frame, text = text,
                height = 5,
                # width = 6,
                command = cmd,
                background = bgc('lightgreen'), foreground='grey',
                bd=1,
                relief = tk.FLAT,
                highlightthickness=1,
                highlightcolor='grey',
                highlightbackground='grey',
            )
            b.pack(side = tk.LEFT)
        
        btn("Start-'a'", self.Start)
        btn("Pause-'s'", self.Pause)
        btn("Unpause-'d'", self.Unpause)
        btn("Stop-'f'", self.Stop)
        btn("ImageReward\nOn", self.HighLevelRewardOn)
        btn("ImageReward\nOff", self.HighLevelRewardOff)
        btn("Water Reward-'z'", self.manual_water_dispense)
        
        def water_rw_cb(val):
            def inner():
                self.auto_water_reward_enabled = val
            return inner
        btn("Water Reward\nOn", water_rw_cb(True))
        btn("Water Reward\nOff", water_rw_cb(False))
        
        self.root.bind('<Key>', lambda a : self.KeyPress(a))
        
        if show_info_view:
            self.info_view = InfoView(self.root, monkey_images=self)
        else:
            self.info_view = None
        
        if self.plexon == True:
            WaitForStart = not no_wait_for_start
            if WaitForStart:
                print('Start Plexon Recording now')
            while WaitForStart == True:
                #self.client.opx_wait(1)
                new_data = self.client.get_new_data()
                # if new_data.num_data_blocks < max_block_output:
                #     num_blocks_to_output = new_data.num_data_blocks
                # else:
                #     num_blocks_to_output = max_block_output
                for i in range(new_data.num_data_blocks):
                    if new_data.source_num_or_type[i] == self.other_event_source and new_data.channel[i] == 2: # Start event timestamp is channel 2 in 'Other Events' source
                        print ("Recording start detected. All timestamps will be relative to a start time of {} seconds.".format(new_data.timestamp[i]))
                        WaitForStart = False
                        self.RecordingStartTimestamp = new_data.timestamp[i]
    
    def __enter__(self):
        pass
    
    def __exit__(self, *exc):
        if self.plexon:
            self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
        self.save_log_files()
    
    def log_event(self, name: str, *, tags: List[str], info=None):
        if info is None:
            info = {}
        human_time = datetime.utcnow().isoformat()
        mono_time = time.monotonic()
        out = {
            'time_human': human_time,
            'time_m': mono_time,
            'name': name,
            'tags': tags,
            'info': info,
        }
        
        self.event_log.append(out)
    
    def log_hw(self, name, *, sim: bool = False, info=None):
        tags = ['hw']
        if info is None:
            info = {}
        if sim: # event actually triggered manually via keyboard
            tags.append('hw_simulated')
        self.log_event(name, tags=tags, info=info)
    
    def _register_callback(self, event_key, cb):
        self._callbacks[event_key].add(cb)
        cb_obj = RegisteredCallback(cb, self._clear_callback)
        return cb_obj
    
    def _clear_callback(self, cb):
        for v in self._callbacks.values():
            v.discard(cb)
    
    def _clear_callbacks(self):
        for v in self._callbacks.values():
            v.clear()
    
    # call callbacks registered for event key
    def _trigger_event(self, key):
        if self.paused:
            return
        for cb in self._callbacks[key]:
            cb()
    
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
        
        if not self.paused:
            next(self.new_loop_iter)
        
        self.after(self.cb_delay_ms, self.progress_new_loop)
    
    def new_loop_upkeep(self):
        # self.gathering_data_omni()
        if self.plexon:
            self.gathering_data_omni_new()
    
    def new_loop_gen(self):
        completed_trials = 0
        while True:
            if self.max_trials is not None and completed_trials >= self.max_trials:
                yield
                continue
            yield from self.run_trial()
            completed_trials += 1
            if self.max_trials is not None:
                print(f"trial {completed_trials}/{self.max_trials} complete")
    
    def run_trial(self):
        with ExitStack() as trial_stack:
            discrim_delay = random.uniform(*self.discrim_delay_range)
            go_cue_delay = random.uniform(*self.go_cue_delay_range)
            
            # print(self.normalized_time)
            
            # reset state for new trial
            self.joystick_pull_remote_ts = None
            self.joystick_release_remote_ts = None
            self.joystick_zone_enter = None
            self.joystick_zone_exit = None
            
            trial_start = self.normalized_time
            
            def in_zone():
                return self.Area1_right_pres
            
            def trial_t():
                return self.normalized_time - trial_start
            
            waiter = Waiter(self, trial_t)
            
            def wait(t: float):
                start_time = trial_t()
                while trial_t() - start_time < t:
                    yield
            
            self.log_event('trial_start', tags=['game_flow'], info={
                'discrim_delay': discrim_delay,
                'go_cue_delay': go_cue_delay,
                'task_type': self.task_type,
            })
            
            # if winsound is not None:
            #     winsound.PlaySound(
            #         self.OutOfHomeZoneSound,
            #         winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT + winsound.SND_LOOP
            #     ) #Need to change the tone
            
            prep_flash = False
            
            if prep_flash:
                icon_flash_freq = 2
                # icon period = 1 / freq
                # change period = 0.5 * period
                icon_change_period = 0.5 / icon_flash_freq
                prep_shown = False
                # wait for hand to be in the home zone
                # wait at least inter-trial time before starting
                while True:
                    # print(trial_t())
                    # print((trial_t() * 1000 // 500))
                    if (trial_t() // icon_change_period) % 2:
                        # blank
                        if prep_shown:
                            self.clear_image()
                            prep_shown = False
                    else:
                        # black diamond
                        if not prep_shown:
                            self.show_image('yPrepare')
                            prep_shown = True
                    
                    if trial_t() > self.InterTrialTime and in_zone():
                        break
                    yield
            else:
                # self.show_image('yPrepare')
                def register_in_zone_cb():
                    def _enter():
                        self.show_image('yPrepare')
                        if winsound is not None:
                            winsound.PlaySound(
                                str(Path('./TaskSounds/mixkit-arcade-bonus-229.wav')),
                                winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                    
                    def _exit():
                        self.clear_image()
                    
                    if in_zone():
                        _enter()
                    
                    enter_cb = self._register_callback('homezone_enter', _enter)
                    trial_stack.enter_context(enter_cb)
                    exit_cb = self._register_callback('homezone_exit', _exit)
                    trial_stack.enter_context(exit_cb)
                    
                    return enter_cb, exit_cb
                
                in_zone_cbs = register_in_zone_cb()
                while True:
                    if trial_t() > self.InterTrialTime and in_zone():
                        break
                    yield
            
            # switch to blank to ensure diamond is no longer showing
            if prep_flash:
                self.clear_image()
            
            # if winsound is not None:
            #     winsound.PlaySound(winsound.Beep(100,0), winsound.SND_PURGE) #Purge looping sounds
            
            # EV19 Ready # TODO: Take this out when finish the connector since new start of trial comes from hand in home zone
            if self.nidaq:
                self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event7,None,None)
                self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            gc_hand_removed_early = False
            # yield from waiter.wait(t=discrim_delay, event='homezone_exit')
            yield from waiter.wait(t=discrim_delay, cond=lambda: not in_zone())
            if waiter.trigger != 'time':
                gc_hand_removed_early = True
            
            # choose image
            selected_image_key = random.choice(list(self.selectable_images))
            selected_image = self.images[selected_image_key]
            image_i = selected_image['nidaq_event_index']
            
            # EV25 , EV27, EV29, EV31
            if image_i in [1,2,3,4]:
                event_array = [None, self.event5, self.event3, self.event1, self.event2][image_i]
                if self.nidaq:
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,event_array,None,None)
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            for cb in in_zone_cbs:
                cb.clear()
            
            if not gc_hand_removed_early:
                # display image without red box
                self.show_image(selected_image_key)
                self.log_event('discrim_shown', tags=['game_flow'], info={
                    'selected_image': selected_image_key,
                })
            
            if not gc_hand_removed_early:
                yield from waiter.wait(t=go_cue_delay, cond=lambda: not in_zone())
                if waiter.trigger != 'time':
                    gc_hand_removed_early = True
            
            # EV26, EV28, EV30 EV32
            if image_i in [1,2,3,4]:
                # should this have duplicates with the list of event arrays above?
                event_array = [None, self.event4, self.event2, self.event0, self.event3][image_i]
                if self.nidaq:
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,event_array,None,None)
                    self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
            
            if gc_hand_removed_early:
                in_zone_at_go_cue = False
            else:
                # display image with box
                self.show_image(selected_image_key, boxed=True)
                self.log_event('go_cue_shown', tags=['game_flow'], info={
                    'selected_image': selected_image_key,
                })
                
                in_zone_at_go_cue = in_zone()
            
            if in_zone_at_go_cue:
                if winsound is not None:
                    winsound.PlaySound(
                        str(Path('./TaskSounds/mixkit-unlock-game-notification-253.wav')),
                        winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
            cue_time = trial_t()
            
            log_failure_reason = [None]
            def fail_r(s):
                assert log_failure_reason[0] is None
                log_failure_reason[0] = s
            
            def get_pull_info():
                if not in_zone_at_go_cue:
                    fail_r('hand removed from homezone before cue')
                    return None, 0, 0
                
                if self.joystick_pulled: # joystick pulled before prompt
                    fail_r('joystick pulled before cue')
                    return None, 0, 0
                
                # cue_time = trial_t()
                # wait up to MaxTimeAfterSound for the joystick to be pulled
                while not self.joystick_pulled:
                    if trial_t() - cue_time > self.MaxTimeAfterSound:
                        fail_r('joystick not pulled within MaxTimeAfterSound')
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
                
                if reward_duration is None:
                    fail_r('joystick pulled for incorrect amount of time')
                
                return reward_duration, remote_pull_duration, pull_duration
            
            def get_homezone_exit_info():
                # hand removed from home zone before cue
                if not in_zone_at_go_cue:
                    fail_r('hand removed before cue')
                    return None, 0, 0
                
                # wait up to MaxTimeAfterSound for the hand to exit the homezone
                while in_zone():
                    if trial_t() - cue_time > self.MaxTimeAfterSound:
                        fail_r('hand not removed from home zone within MaxTimeAfterSound')
                        return None, 0, 0
                    yield
                
                exit_time = trial_t()
                exit_delay = exit_time - cue_time
                
                reward_duration = self.ChooseReward(exit_delay, cue=selected_image_key)
                
                if reward_duration is None:
                    fail_r('hand removed after incorrect amount of time')
                
                return reward_duration, 0, exit_delay
            
            task_type = self.task_type
            if task_type == 'joystick_pull':
                reward_duration, remote_pull_duration, pull_duration = yield from get_pull_info()
                action_duration = remote_pull_duration
            elif task_type == 'homezone_exit':
                reward_duration, remote_pull_duration, pull_duration = yield from get_homezone_exit_info()
                action_duration = pull_duration
            else:
                assert False, f"invalid task_type {task_type}"
            
            self.log_event('task_completed', tags=['game_flow'], info={
                'reward_duration': reward_duration,
                'remote_pull_duration': remote_pull_duration,
                'pull_duration': pull_duration,
                'action_duration': action_duration,
                'success': reward_duration is not None,
                'failure_reason': log_failure_reason[0],
            })
            
            print('Press Duration: {:.4f} (remote: {:.4f})'.format(action_duration, pull_duration))
            print('Reward Duration: {}'.format(reward_duration))
            if log_failure_reason[0]:
                print(log_failure_reason[0])
            try:
                self.print_histogram()
                if self.info_view is not None:
                    self.info_view.update_info(self.get_end_info(), self.event_log)
            except:
                traceback.print_exc()
            
            if reward_duration is None: # pull failed
                # EV21 Pull failure
                if self.nidaq:
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.event5,None,None)
                    self.task2.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,self.begin,None,None)
                if self.EnableBlooperNoise:
                    if winsound is not None:
                        winsound.PlaySound(
                            str(Path('./TaskSounds/zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_negative_66204.wav')),
                            winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                
                if self.ImageReward:
                    self.show_image(selected_image_key, variant='red', boxed=True)
                    self.log_event('image_reward_shown', tags=['game_flow'], info={
                        'selected_image': selected_image_key,
                        'color': 'red',
                    })
                if self.ImageReward or self.EnableBlooperNoise:
                    # 1.20 is the duration of the sound effect
                    yield from wait(1.20)
                if self.EnableTimeOut:
                    self.log_event('time_out_shown', tags=['game_flow'], info={
                        'duration': self.TimeOut,
                    })
                    self.clear_image()
                    yield from wait(self.TimeOut)
            else: # pull suceeded
                if self.ImageReward:
                    self.show_image(selected_image_key, variant='white', boxed=True)
                    self.log_event('image_reward_shown', tags=['game_flow'], info={
                        'selected_image': selected_image_key,
                        'color': 'white',
                    })
                
                #EV20
                if self.nidaq:
                    self.task2.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event6, None, None)
                    self.task2.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
                if winsound is not None:
                    winsound.PlaySound(
                        str(Path('./TaskSounds/zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_complete_66202.wav')),
                        winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                
                if self.ImageReward:
                    if self.post_succesful_pull_delay is not None:
                        yield from wait(self.post_succesful_pull_delay)
                    else:
                        # 1.87 is the duration of the sound effect
                        yield from wait(1.87)
                
                if self.auto_water_reward_enabled and reward_duration > 0:
                    self.log_event("water_dispense", tags=['game_flow'], info={'duration': reward_duration})
                    if self.nidaq:
                        #EV23
                        self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event7, None, None)
                        self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
                    if self.plexon:
                        # turn water on
                        self.plexdo.set_bit(self.device_number, self.reward_nidaq_bit)
                
                yield from wait(reward_duration)
                
                if self.plexon:
                    self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
                
                self.clear_image()
            
            # EV24
            if self.nidaq:
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event6, None, None)
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
            
            log_entry = {
                'reward_duration': reward_duration, # Optional[float]
                'pull_duration': pull_duration, # float
                'discrim_delay': discrim_delay,
                'go_cue_delay': go_cue_delay,
                'failure_reason': log_failure_reason[0], # Optional[str]
                'joystick_zone_enter': self.joystick_zone_enter, # Optional[float]
                'joystick_zone_exit': self.joystick_zone_exit, # Optional[float]
            }
            self.trial_log.append(log_entry)
            self.log_event("trial_end", tags=['game_flow'], info={})
            self.save_log_files(partial=True)
    
    def manual_water_dispense(self):
        self.log_event("manual_water_dispense", tags=[], info={'duration': self.manual_reward_time})
        def gen():
            print("water on")
            if self.nidaq:
                #EV23
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.event7, None, None)
                self.task.WriteDigitalLines(1, 1, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel, self.begin, None, None)
            if self.plexon:
                self.plexdo.set_bit(self.device_number, self.reward_nidaq_bit)
            t = time.monotonic()
            while time.monotonic() - t < self.manual_reward_time:
                yield
            print("water off")
            if self.plexon:
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
    
    def random_duration(self, d_min, d_max) -> float:
        output = round(random.uniform(d_min,d_max),2)
        return output
    
    def ChooseReward(self, duration, cue) -> Optional[float]:
        
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
            elif rwd['type'] in ['linear', 'trapezoid']:
                if duration >= rwd['low'] and duration <= rwd['high']:
                    # get distance from optimal time
                    dist = abs(duration - rwd['mid'])
                    # get distance from closest edge of range
                    dist = (rwd['mid'] - rwd['low']) - dist
                    # get percent of distance from edge of range 0-1
                    if duration >= rwd['mid']:
                        if rwd['type'] == 'trapezoid':
                            perc = 1
                        else:
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
        already_started = not self.stopped
        self.paused = False
        self.stopped = False
        
        if not already_started:
            self.log_event('game_start', tags=['game_flow'])
            self.start_new_loop()
    
    def Pause(self):
        self.log_event('game_pause', tags=['game_flow'], info={'was_paused': self.paused})
        self.paused = True
        
        print('pause')
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        if self.plexon == True:
            self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
        
        self.save_log_files(partial=True)
    
    def Unpause(self):
        self.log_event('game_unpause', tags=['game_flow'], info={'was_paused': self.paused})
        self.paused = False
    
    def Stop(self):
        self.log_event('game_stop', tags=['game_flow'], info={'was_stopped': self.stopped})
        self.stopped = True
        self._clear_callbacks()
        
        if self.plexon == True:
            self.plexdo.clear_bit(self.device_number, self.reward_nidaq_bit)
        self.clear_image()
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        self.save_log_files(partial=True)
        pprint(self.get_end_info())
    
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
        elif key == 'p':
            screenshot_widget(self.root, 'test.png')
            screenshot_widget(self.info_view.window, 'test2.png')
            screenshot_widgets(self.info_view.rows, 'test3.png')
        elif key == '`':
            self.Stop()
            self.root.quit()
            # sys.exit()
        elif key == '1':
            self.Area1_right_pres = not self.Area1_right_pres
            if self.Area1_right_pres:
                self._trigger_event('homezone_enter')
                self.log_hw('homezone_enter', sim=True)
            else:
                self._trigger_event('homezone_exit')
                self.log_hw('zone_exit', sim=True, info={'simulated_zone': 'homezone'})
            print('in zone toggled', self.Area1_right_pres)
        elif key == '2':
            if not self.joystick_pulled:
                self.joystick_pull_remote_ts = time.monotonic()
                self.joystick_pulled = True
                self.log_hw('joystick_pulled', sim=True)
            else:
                self.joystick_release_remote_ts = time.monotonic()
                self.joystick_pulled = False
                self.log_hw('joystick_released', sim=True)
            
            print('joystick', self.joystick_pulled)
        elif key == '3':
            if self.joystick_zone_enter is None:
                self.joystick_zone_enter = time.monotonic()
                self.log_hw('joystick_zone_enter', sim=True)
            elif self.joystick_zone_exit is None:
                self.joystick_zone_exit = time.monotonic()
                self.log_hw('zone_exit', sim=True, info={'simulated_zone': 'joystick_zone'})
            
            print('joystick zone', self.joystick_zone_enter, self.joystick_zone_exit)
    
    ### These attach to buttons that will select if Monkey has access to the highly coveted monkey image reward
    def HighLevelRewardOn(self):
        print('Image Reward On')
        self.ImageReward = True

    def HighLevelRewardOff(self):
        print('Image Reward Off')
        self.ImageReward = False
    
    def show_image(self, k, *, variant=None, boxed=False, _clear=True):
        if _clear:
            self.clear_image()
        
        img = self.images[k]['tk'][variant]
        
        canvas_size = self.cv1.winfo_width(), self.cv1.winfo_height()
        # w = self.images[k]['width']
        # offset = (canvas_size[0] - w) / 2
        offset = (canvas_size[0]) / 2
        
        # h = self.images[k]['height']
        # y_offset = (canvas_size[1] - h) / 2
        y_offset = (canvas_size[1]) / 2
        
        if boxed:
            self.show_image('box', variant=variant, _clear=False)
        
        self.cv1.create_image(offset, y_offset, anchor = 'c', image = img)
    
    def clear_image(self):
        self.cv1.delete("all")
    
    def gathering_data_omni_new(self):
        self.client.opx_wait(1000)
        new_data = self.client.get_new_data()
        
        # joystick threshold
        js_thresh = self.joystick_pull_threshold
        
        for i in range(new_data.num_data_blocks):
            num_or_type = new_data.source_num_or_type[i]
            block_type = source_numbers_types[new_data.source_num_or_type[i]]
            source_name = source_numbers_names[new_data.source_num_or_type[i]]
            chan = new_data.channel[i]
            ts = new_data.timestamp[i]
            
            if block_type == CONTINUOUS_TYPE and source_name == 'AI':
                # Convert the samples from AD units to voltage using the voltage scaler, use tmp_samples[0] because it could be a list.
                voltage_scaler = source_numbers_voltage_scalers[num_or_type]
                samples = new_data.waveform[i][:max_samples_output]
                samples = [s * voltage_scaler for s in samples]
                val = samples[0]
                
                if chan == self.joystick_channel:
                    if self.joystick_last_state is None:
                        self.joystick_last_state = val
                    
                    # joystick has transitioned from not pulled to pulled
                    if self.joystick_last_state < js_thresh and val >= js_thresh:
                        self.log_hw('joystick_pulled')
                        self.joystick_pulled = True
                        self.joystick_pull_remote_ts = ts
                    # joystick has transitioned from pulled to not pulled
                    elif self.joystick_last_state >= js_thresh and val < js_thresh:
                        self.log_hw('joystick_released')
                        self.joystick_pulled = False
                        self.joystick_release_remote_ts = ts
                    
                    self.joystick_last_state = val
            elif num_or_type == self.event_source:
                if chan == 14: # enter home zone
                    self.log_hw('homezone_enter')
                    self.Area1_right_pres = True
                    self._trigger_event('homezone_enter')
                elif chan == 11: # enter joystick zone
                    self.log_hw('joystick_zone_enter')
                    if self.joystick_zone_enter is None:
                        self.joystick_zone_enter = ts
                elif chan == 12: # exit either zone
                    self.log_hw('zone_exit')
                    if self.Area1_right_pres:
                        self.Area1_right_pres = False
                        self._trigger_event('homezone_exit')
                    if self.joystick_zone_enter is not None and self.joystick_zone_exit is None:
                        self.joystick_zone_exit = ts
    
    def get_log_file_paths(self) -> Tuple[Path, Path]:
        base = self.log_file_name_base
        csv_path = Path(self.save_path) / f"{base}.csv"
        event_log_path = Path(self.save_path) / f"{base}_events.json"
        
        return csv_path, event_log_path
    
    def ensure_log_file_creatable(self):
        """Attempts to create, write to and delete the non partial log files.
            raises an exception if this fails
            raises an exception if any of the files already exist"""
        paths = self.get_log_file_paths()
        
        for path in paths:
            assert not path.exists()
            with open(path, 'x') as f:
                f.write('_')
            path.unlink()
    
    def save_log_files(self, *, partial: bool = False):
        base = self.log_file_name_base
        if partial:
            partial_dir = Path(self.save_path) / "partial"
            partial_dir.mkdir(exist_ok=True)
            gen_time = str(time.monotonic())
            csv_path = partial_dir / f"{base}_{gen_time}.csv"
            event_log_path = partial_dir / f"{base}_{gen_time}_events.json"
            histo_path = partial_dir / f"{base}_{gen_time}_histogram.png"
        else:
            csv_path, event_log_path = self.get_log_file_paths()
            histo_path = Path(self.save_path) / f"{self.log_file_name_base}_histogram.png"
        
        out = {
            'events': self.event_log,
        }
        
        with open(event_log_path, 'w') as f:
            json.dump(out, f, indent=2)
        
        with open(csv_path, 'w') as f:
            writer = csv.writer(f)
            
            writer.writerow([
                'trial',
                'success',
                'failure reason',
                'time in homezone',
                'pull duration',
                'reward duration',
                'joystick_zone_enter',
                'joystick_zone_exit',
                'discrim_delay',
                'go_cue_delay',
            ])
            
            for i, entry in enumerate(self.trial_log):
                is_success = entry['reward_duration'] is not None
                reason = entry['failure_reason'] or ''
                if self.task_type == 'homezone_exit':
                    time_in_homezone = entry['pull_duration']
                    pull_duration = 0
                elif self.task_type == 'joystick_pull':
                    time_in_homezone = 0
                    pull_duration = entry['pull_duration']
                else:
                    assert False
                
                writer.writerow([
                    i+1,
                    is_success,
                    reason,
                    time_in_homezone,
                    pull_duration,
                    entry['reward_duration'] or 0,
                    entry['joystick_zone_enter'] or '',
                    entry['joystick_zone_exit'] or '',
                    entry['discrim_delay'],
                    entry['go_cue_delay'],
                ])
            
            def get_time_in_game():
                for e in self.event_log:
                    if e['name'] == 'game_start':
                        delta = time.monotonic() - e['time_m']
                        delta = timedelta(seconds=delta)
                        return str(delta)
                return None
            
            end_info = self.get_end_info()
            dur = end_info['action_duration']
            writer.writerow([
                'count', end_info['count'],
                'percent_correct', end_info['percent_correct'],
                'time_in_game', get_time_in_game(),
            ])
            writer.writerow([
                'min', dur['min'],
                'max', dur['max'],
                'mean', dur['mean'],
                'stdev', dur['stdev'],
            ])
            writer.writerow(['error', 'count', 'percent'])
            for e, ei in end_info['errors'].items():
                writer.writerow([e, ei['count'], ei['percent']])
        
        screenshot_widgets([*self.info_view.rows, self.info_view.label], histo_path)
    
    def print_histogram(self):
        events = [e for e in self.event_log if e['name'] == 'task_completed']
        
        def get_bin_ranges():
            start = 0
            # end = math.ceil(self.MaxTimeAfterSound)
            end = max(rwd.get('high', 0) for rwd in self.reward_thresholds)
            step = (end - start) / 10
            
            ws = start # window start
            we = step # window end
            while ws < end:
                yield ws, we
                ws = we
                if we < 1.999999999:
                    we = ws + 0.2
                else:
                    we = ws + step
        bins = {
            k: []
            for k in get_bin_ranges()
        }
        errors = Counter()
        
        for e in events:
            a_d = e['info']['action_duration']
            if a_d == 0 and e['info']['failure_reason'] is not None:
                errors[e['info']['failure_reason']] += 1
                continue
            for (bin_s, bin_e), bin_events in bins.items():
                if bin_s <= a_d < bin_e:
                    bin_events.append(e['info']['success'])
                    break
        
        if errors:
            print('-'*20)
            error_col_width = max(len(e) for e in errors)
            for error, count in errors.items():
                print(f"{error.rjust(error_col_width)} {count}")
        
        for i, ((bin_s, bin_e), bin_events) in enumerate(bins.items()):
            if i%4==0:
                print('-'*20)
            events_str = "".join('O' if e else 'X' for e in bin_events)
            print(f"{bin_s:>5.1f}-{bin_e:<5.1f} {events_str}")
    
    def get_end_info(self):
        events = [e for e in self.event_log if e['name'] == 'task_completed']
        
        n = len(events)
        def perc(count):
            if n == 0:
                return 0
            return count/n
        
        error_counts = Counter()
        for e in events:
            reason = e['info']['failure_reason']
            if reason is None:
                continue
            error_counts[reason] += 1
        error_info = {
            reason: {'count': c, 'percent': perc(c)}
            for reason, c in error_counts.items()
        }
        
        correct = [e for e in events if e['info']['success']]
        correct_n = len(correct)
        
        pull_durations = [e['info']['action_duration'] for e in events]
        pull_durations = [x for x in pull_durations if x != 0]
        
        info = {
            'count': n,
            'percent_correct': perc(correct_n),
            'action_duration': {
                'min': min(pull_durations, default=0),
                'max': max(pull_durations, default=0),
                'mean': statistics.mean(pull_durations) if pull_durations else 0,
                'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
            },
            'errors': error_info,
        }
        
        return info

class TestFrame(tk.Frame,):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        
        def x():
            pass
        
        startbutton = tk.Button(parent, text = "Start-'a'", fg='white', height = 5, width = 6, command = x)
        startbutton.pack(side = tk.LEFT)
    

def gen_images():
    CANVAS_SIZE = 1600, 800
    
    # saturation of colors
    SAT = 255 // 2
    
    out_path = Path('./images_gen')
    out_path.mkdir(exist_ok=True)
    src = Path('./TaskImages_Joystick')
    
    prep_path = out_path / 'prepare.png'
    img = Image.open(src / 'yPrepare.png')
    img.thumbnail(CANVAS_SIZE)
    img = recolor(img, (0, SAT, 0))
    img.save(prep_path, 'PNG')
    
    img = Image.open(src / 'eBlank.png')
    img.thumbnail(CANVAS_SIZE)
    cimg = recolor(img, (0, SAT, 0), two_tone=True)
    p = out_path / 'box_green.png'
    cimg.save(p, 'PNG')
    
    cimg = recolor(img, (SAT, 0, 0), two_tone=True)
    p = out_path / 'box_red.png'
    cimg.save(p, 'PNG')
    
    cimg = recolor(img, (SAT, SAT, SAT), two_tone=True)
    p = out_path / 'box_white.png'
    cimg.save(p, 'PNG')
    
    green_dir = out_path / 'green'
    red_dir = out_path / 'red'
    white_dir = out_path / 'white'
    colors = [
        (green_dir, (0, SAT, 0)),
        (red_dir, (SAT, 0, 0)),
        (white_dir, (SAT, SAT, SAT)),
    ]
    for p, _ in colors:
        p.mkdir(exist_ok=True)
    
    for image_p in src.glob('*.png'):
        c = image_p.stem[0]
        name = image_p.stem
        if c != 'b':
            continue
        print(image_p)
        img = Image.open(image_p)
        img.thumbnail(CANVAS_SIZE)
        for cdir, color in colors:
            cimg = recolor(img, color)
            p = cdir / f"{name}.png"
            cimg.save(p, 'PNG')

def main():
    try:
        cmd = sys.argv[1]
    except IndexError:
        cmd = None
    
    if cmd == 'gen':
        gen_images()
        return
    
    root = tk.Tk()
    root.configure(bg='black', bd=0)
    
    # MonkeyTest = MonkeyImages(root)
    # MonkeyTest = TestFrame(root)
    
    with MonkeyImages(root):
        tk.mainloop()

if __name__ == "__main__":
    main()