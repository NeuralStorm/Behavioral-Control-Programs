from kivy.app import App
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.core.text import Label as CoreLabel
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.config import Config
from sys import platform
import serial, time, pickle, datetime #, winsound
from numpy import binary_repr
import struct
import time
import numpy as np
import tables


Config.set('kivy', 'exit_on_escape', 1)
Config.set('graphics', 'resizable', False)
if platform == 'darwin':
    fixed_window_size = (1800, 1000)
elif platform == 'win32':
    fixed_window_size = (1800, 1000)
pix_per_cm = 85.
Config.set('graphics', 'width', str(fixed_window_size[0]))
Config.set('graphics', 'height', str(fixed_window_size[1]))

class Data(tables.IsDescription):
    state = tables.StringCol(24)   # 24-character String
    cursor = tables.Float32Col(shape=(10, 2))
    cursor_ids = tables.Float32Col(shape = (10, ))
    set_ix = tables.Float32Col(shape=(1, ))
    cap_touch = tables.Float32Col()
    time = tables.Float32Col()

class SequenceGame(Widget):
    target1 = ObjectProperty(None)
    target2 = ObjectProperty(None)
    button1_in = ObjectProperty(None)
    button1_out = ObjectProperty(None)
    button2_in = ObjectProperty(None)
    button2_out = ObjectProperty(None)
    button3_in = ObjectProperty(None)
    button3_out = ObjectProperty(None)
    button4_in = ObjectProperty(None)
    button4_out = ObjectProperty(None)
    button5_in = ObjectProperty(None)
    button5_out = ObjectProperty(None)
    button6_in = ObjectProperty(None)
    button6_out = ObjectProperty(None)
    button7_in = ObjectProperty(None)
    button7_out = ObjectProperty(None)
    button8_in = ObjectProperty(None)
    button8_out = ObjectProperty(None)
    button9_in = ObjectProperty(None)
    button9_out = ObjectProperty(None)
    button10_in = ObjectProperty(None)
    button10_out = ObjectProperty(None)
    button11_in = ObjectProperty(None)
    button11_out = ObjectProperty(None)
    button12_in = ObjectProperty(None)
    button12_out = ObjectProperty(None)
    button13_in = ObjectProperty(None)
    button13_out = ObjectProperty(None)
    button14_in = ObjectProperty(None)
    button14_out = ObjectProperty(None)
    button15_in = ObjectProperty(None)
    button15_out = ObjectProperty(None)
    button16_in = ObjectProperty(None)
    button16_out = ObjectProperty(None)
    
    # Time to wait after starting the video before getting to the first set display
    pre_start_vid_ts = 0.1
    
    # Sets per hyperset
    nsets_per_hyperset = 5
    
    # Inter Set Interval
    ISetI_mean = .5
    ISetI_std = .1
    
    # Inter HyperSet Interval
    IHSI_mean = 1.
    IHSI_std = .2
    
    # Target Radius 
    target_rad = 1.5 # cm
    
    # Exit Button Settings 
    # exit_pos1 = np.array([9*fixed_window_size[0]/(10*pix_per_cm), 9*fixed_window_size[1]/(10*pix_per_cm)]) # cm
    # exit_pos2 = np.array([9*fixed_window_size[0]/(10*pix_per_cm), 1*fixed_window_size[1]/(10*pix_per_cm)]) # cm
    exit_pos1 = np.array([18, 2])
    exit_pos2 = np.array([18, 10])
    exit_rad = 1. # cm
    exit_hold = 2 # seconds
    
    # Indicator Light Settings
    indicator_pos = np.array([8, 5]) # cm
    
    # Home Hold Times
    ch_timeout = 10. # ch timeout
    cht = .001 # how long to hold in the center until reward?
    
    # Target Hold Times
    set_timeout_time = 5. # how long does the target stay on the screen until it disappears and move to next trial?
    tht = .001 # how long to hold in target until reward?
    
    # Initialize variables for tracking cursor position 
    cursor = {}
    cursor_start = {}
    cursor_ids = []
    
    # Initialize Touch and Prev Touch Boolean
    anytouch_prev = False
    touch = False
    
    # Error Timeout Times
    touch_error_timeout = 0.
    timeout_error_timeout = 0.
    hold_error_timeout = 0.
    drag_error_timeout = 0.
    
    # T/F Done with Initialization
    done_init = False
    
    # Initialize array of previous exit times?
    prev_exit_ts = np.array([0,0])

    # Number of trials: 
    trial_counter = NumericProperty(0)
    #indicator_txt = StringProperty('o')
    #indicator_txt_color = ListProperty([.5, .5, .5, 1.])
    
    # Percent of hyperset complete
    percent_done = NumericProperty(0)

    t0 = time.time()

    cht_text = StringProperty('')
    tht_text = StringProperty('')
    targ_size_text = StringProperty('')
    big_rew_text = StringProperty('')
    cht_param = StringProperty('')
    tht_param = StringProperty('')
    targ_size_param = StringProperty('')
    big_rew_time_param = StringProperty('')
    
    
    # Define what to do when there is a touch on the screen
    def on_touch_down(self, touch):
        #handle many touchs:
        ud = touch.ud

        # Add new touch to ids: 
        self.cursor_ids.append(touch.uid)

        # Add cursor
        curs = pix2cm(np.array([touch.x, touch.y]))
        self.cursor[touch.uid] =  curs.copy()
        self.cursor_start[touch.uid] = curs.copy()

        # set self.touch to True
        self.touch = True
    
    
    def on_touch_move(self, touch):
        self.cursor[touch.uid] = pix2cm(np.array([touch.x, touch.y]))
        self.touch = True
    
    def on_touch_up(self, touch):
        self.touch = False
        try:
            self.cursor_ids.remove(touch.uid)
            _ = self.cursor.pop(touch.uid)
        except:
            print('removing touch from pre-game screen')
    
    
    # Get the initial parameters
    def init(self, animal_names_dict=None, rew_tone_every=None, rew_in=None, task_in=None,
        set_id_selected = None, test=None, hold=None, error_types_selected=None, nontarg_tol=None,
        autoquit=None, rew_var=None, set_timeout = None, error_timeout_time=None, ):
        
        # Initialize a count of the number of rewards
        # NOTE: this is necessary for scheduling rewards if you are not rewarding
        # 100% of the time, but the option to reward <100% of the time is NOT supported yet
        self.rew_cnt = 0
        self.set_rew_cnt = 0

        # Do you want to use an exxternal capacitive touch sensor?
        self.use_cap_sensor = False

        if self.use_cap_sensor:
            self.serial_port_cap = serial.Serial(port='COM5')
            
        self.rhtouch_sensor = 0.
        
        # Initiralize the 16 target positions
        # self.possible_target_pos_x = np.array([self.center_x-0.375*self.width, self.center_x-0.125*self.width, self.center_x+0.125*self.width, self.center_x+0.375*self.width, 
        #     self.center_x-0.375*self.width, self.center_x-0.125*self.width, self.center_x+0.125*self.width, self.center_x+0.375*self.width, 
        #     self.center_x-0.375*self.width, self.center_x-0.125*self.width, self.center_x+0.125*self.width, self.center_x+0.375*self.width, 
        #     self.center_x-0.375*self.width, self.center_x-0.125*self.width, self.center_x+0.125*self.width, self.center_x+0.375*self.width])
        # self.possible_target_pos_y = np.array([self.center_y+0.375*self.height, self.center_y+0.375*self.height, self.center_y+0.375*self.height, self.center_y+0.375*self.height, 
        #     self.center_y+0.125*self.height, self.center_y+0.125*self.height, self.center_y+0.125*self.height, self.center_y+0.125*self.height, 
        #     self.center_y-0.125*self.height, self.center_y-0.125*self.height, self.center_y-0.125*self.height, self.center_y-0.125*self.height, 
        #     self.center_y-0.375*self.height, self.center_y-0.375*self.height, self.center_y-0.375*self.height, self.center_y-0.375*self.height])
        
        
        self.possible_target_pos_x = np.array([6.75, 9, 11.25, 13.5, 6.75, 9, 11.25, 13.5, 6.75, 9, 11.25, 13.5, 6.75, 9, 11.25, 13.5]) # determined through trial and error
        self.possible_target_pos_y = np.array([2.25, 2.25, 2.25, 2.25, 4.5, 4.5, 4.5, 4.5, 6.75, 6.75, 6.75, 6.75, 9, 9, 9, 9])
        
        # self.possible_target_pos_x = np.array([fixed_window_size[0]/(5*pix_per_cm), 2*fixed_window_size[0]/(5*pix_per_cm), 3*fixed_window_size[0]/(5*pix_per_cm), 4*fixed_window_size[0]/(5*pix_per_cm), 
        #                                        fixed_window_size[0]/(5*pix_per_cm), 2*fixed_window_size[0]/(5*pix_per_cm), 3*fixed_window_size[0]/(5*pix_per_cm), 4*fixed_window_size[0]/(5*pix_per_cm), 
        #                                        fixed_window_size[0]/(5*pix_per_cm), 2*fixed_window_size[0]/(5*pix_per_cm), 3*fixed_window_size[0]/(5*pix_per_cm), 4*fixed_window_size[0]/(5*pix_per_cm), 
        #                                        fixed_window_size[0]/(5*pix_per_cm), 2*fixed_window_size[0]/(5*pix_per_cm), 3*fixed_window_size[0]/(5*pix_per_cm), 4*fixed_window_size[0]/(5*pix_per_cm)])
        # self.possible_target_pos_y = np.array([fixed_window_size[1]/(5*pix_per_cm), fixed_window_size[1]/(5*pix_per_cm), fixed_window_size[1]/(5*pix_per_cm), fixed_window_size[1]/(5*pix_per_cm), 
        #                                        2*fixed_window_size[1]/(5*pix_per_cm), 2*fixed_window_size[1]/(5*pix_per_cm), 2*fixed_window_size[1]/(5*pix_per_cm), 2*fixed_window_size[1]/(5*pix_per_cm), 
        #                                        3*fixed_window_size[1]/(5*pix_per_cm), 3*fixed_window_size[1]/(5*pix_per_cm), 3*fixed_window_size[1]/(5*pix_per_cm), 3*fixed_window_size[1]/(5*pix_per_cm), 
        #                                        4*fixed_window_size[1]/(5*pix_per_cm), 4*fixed_window_size[1]/(5*pix_per_cm), 4*fixed_window_size[1]/(5*pix_per_cm), 4*fixed_window_size[1]/(5*pix_per_cm)])
        
        
        # Which sets comprise the hyperset? 
        self.sets_selected = []
        for i, val in enumerate(set_id_selected['set_sel']):
            if val:
                self.sets_selected.append(i)
        
        # Record the number of sets per hyperset
        self.nsets_per_hyperset = len(self.sets_selected)
        
        # How long does the set stay on the screen until it disappears and move to next trial? 
        set_timeout_opts = [15, 30, 45, 60]
        for i, val in enumerate(set_timeout['tt']):
            if val:
                self.set_timeout_time = set_timeout_opts[i]
        
        # Play reward tone for every correct press?
        if rew_tone_every['rew_tone_every'][0]:
            self.rew_tone_every = True
        else:
            self.rew_tone_every = False
        
        # How long to give rewards for touching any target?
        anytarg_rew_opts = [0., .1, .3, .5]
        for i, val in enumerate(rew_in['anytarg_rew']):
            if val:
                self.anytarg_rew = anytarg_rew_opts[i]
        self.reward_for_targtouch = [self.anytarg_rew > 0, self.anytarg_rew]
        
        # How long to give rewards for a complete set?
        set_rew_opts = [0., .1, .3, .5]
        for i, val in enumerate(rew_in['set_rew']):
            if val:
                self.set_rew = set_rew_opts[i]
        self.reward_for_set = [self.set_rew > 0, self.set_rew]
        
        # How long to give rewards for a complete hyperset?
        hs_rew_opts = [.3, .5, .7]
        for i, val in enumerate(rew_in['hs_rew']):
            if val:
                self.hs_rew = hs_rew_opts[i]
                
        # What counts as an error?
        # self.nontarg_is_error = error_types_selected['error_type'][0]
        self.t2p_first_is_error = error_types_selected['error_type'][0]
        
        # How far away from a target do we tolerate touches?
        nontarg_tol_opts = [100, 3.0, 2.5, 2.0, 1.5, 1.0] # convert the percentage options to proportion of radius
        for i, val in enumerate(nontarg_tol['nontarg_touch_tolerance']):
            if val:
                self.nontarget_error_tolerance = nontarg_tol_opts[i]
        
        # How long is the error timmeout?
        error_timeout_opts = [0.5, 1.0, 1.5, 2.0]
        for i, val in enumerate(error_timeout_time['error_to_time']):
            if val:
                self.error_timeout_time = error_timeout_opts[i]
        
        # Is this a test session?
        self.testing = True
        
        # How big are the targets?
        target_rad_opts = [.5, .75, .82, .91, 1.0, 1.125]
        for i, val in enumerate(task_in['targ_rad']):
            if val:
                self.target_rad = target_rad_opts[i]
        
        # What is the animal's name?
        for i, (nm, val) in enumerate(animal_names_dict.items()):
            if val:
                animal_name = nm
        
        # How long to hold the home and target buttons?
        holdz = [0.0, 0.1, .375, .5, .575, .6, '.4-.6']
        
        self.cht_type = None
        self.tht_type = None

        for i, val in enumerate(hold['hold']):
            if val:
                if type(holdz[i]) is str:
                    mx, mn = holdz[i].split('-')
                    self.tht_type = holdz[i]
                    self.tht =  (float(mn)+float(mx))*.5
                else:
                    self.tht = holdz[i]

        for i, val in enumerate(hold['chold']):
            if val:
                if type(holdz[i]) is str:
                    mx, mn = holdz[i].split('-')
                    self.cht_type = holdz[i]
                    self.cht = (float(mn)+float(mx))*.5
                else:
                    self.cht = holdz[i]
        try:
            pygame.mixer.init()    
        except:
            pass

        # How long is the delay from achieve to receive reward
        self.reward_delay_time = 0.0
        
        # What is the reward variance?
        reward_var_opt = [1.0, .5, .33]
        for i, val in enumerate(rew_var['rew_var']):
            if val:
                self.percent_of_trials_rewarded = reward_var_opt[i]
                if self.percent_of_trials_rewarded == 0.33:
                    self.percent_of_trials_doubled = 0.1
                else:
                    self.percent_of_trials_doubled = 0.0
        
        # Generate the rewards
        self.reward_generator = self.gen_rewards(self.percent_of_trials_rewarded, self.percent_of_trials_doubled,
            self.reward_for_targtouch)
        
        # Auto-quit after how many trials?
        autoquit_trls = [10, 25, 50, 100, 10**10]
        for i, val in enumerate(autoquit['autoquit']):
            if val: 
                self.max_trials = autoquit_trls[i]
        
        # Is it okay to drag fingers into target?
        # drag_ok = [True, False]
        # for i, val in enumerate(drag['drag']):
        #     if val:
        #         self.drag_ok = drag_ok[i]
        self.drag_ok = False;
    
        # Preload sounds: 
        self.reward1 = SoundLoader.load('reward1.wav')
        self.reward2 = SoundLoader.load('reward2.wav')
        
        # Initialize what state we are in
        self.state = 'IHSI'
        self.state_start = time.time()
        self.IHSI = self.IHSI_std + self.IHSI_mean
        
        # Initialize the set number
        self.set_ix = 1
        
        # Initialize targets
        self.target1.set_size(2*self.target_rad)
        self.target1.move(np.array([0., 0.]))
        self.target2.set_size(2*self.target_rad)
        self.target2.move(np.array([0., 0.]))
        
        # Initialize buttons
        self.button1_out.set_size(2*self.target_rad)
        self.button1_out.move(np.array([0., 0.]))
        self.button1_in.set_size(2*self.target_rad-0.1)
        self.button1_in.move(np.array([0., 0.]))
        self.button2_out.set_size(2*self.target_rad)
        self.button2_out.move(np.array([0., 0.]))
        self.button2_in.set_size(2*self.target_rad-0.1)
        self.button2_in.move(np.array([0., 0.]))
        self.button3_out.set_size(2*self.target_rad)
        self.button3_out.move(np.array([0., 0.]))
        self.button3_in.set_size(2*self.target_rad-0.1)
        self.button3_in.move(np.array([0., 0.]))
        self.button4_out.set_size(2*self.target_rad)
        self.button4_out.move(np.array([0., 0.]))
        self.button4_in.set_size(2*self.target_rad-0.1)
        self.button4_in.move(np.array([0., 0.]))
        self.button5_out.set_size(2*self.target_rad)
        self.button5_out.move(np.array([0., 0.]))
        self.button5_in.set_size(2*self.target_rad-0.1)
        self.button5_in.move(np.array([0., 0.]))
        self.button6_out.set_size(2*self.target_rad)
        self.button6_out.move(np.array([0., 0.]))
        self.button6_in.set_size(2*self.target_rad-0.1)
        self.button6_in.move(np.array([0., 0.]))
        self.button7_out.set_size(2*self.target_rad)
        self.button7_out.move(np.array([0., 0.]))
        self.button7_in.set_size(2*self.target_rad-0.1)
        self.button7_in.move(np.array([0., 0.]))
        self.button8_out.set_size(2*self.target_rad)
        self.button8_out.move(np.array([0., 0.]))
        self.button8_in.set_size(2*self.target_rad-0.1)
        self.button8_in.move(np.array([0., 0.]))
        self.button9_out.set_size(2*self.target_rad)
        self.button9_out.move(np.array([0., 0.]))
        self.button9_in.set_size(2*self.target_rad-0.1)
        self.button9_in.move(np.array([0., 0.]))
        self.button10_out.set_size(2*self.target_rad)
        self.button10_out.move(np.array([0., 0.]))
        self.button10_in.set_size(2*self.target_rad-0.1)
        self.button10_in.move(np.array([0., 0.]))
        self.button11_out.set_size(2*self.target_rad)
        self.button11_out.move(np.array([0., 0.]))
        self.button11_in.set_size(2*self.target_rad-0.1)
        self.button11_in.move(np.array([0., 0.]))
        self.button12_out.set_size(2*self.target_rad)
        self.button12_out.move(np.array([0., 0.]))
        self.button12_in.set_size(2*self.target_rad-0.1)
        self.button12_in.move(np.array([0., 0.]))
        self.button13_out.set_size(2*self.target_rad)
        self.button13_out.move(np.array([0., 0.]))
        self.button13_in.set_size(2*self.target_rad-0.1)
        self.button13_in.move(np.array([0., 0.]))
        self.button14_out.set_size(2*self.target_rad)
        self.button14_out.move(np.array([0., 0.]))
        self.button14_in.set_size(2*self.target_rad-0.1)
        self.button14_in.move(np.array([0., 0.]))
        self.button15_out.set_size(2*self.target_rad)
        self.button15_out.move(np.array([0., 0.]))
        self.button15_in.set_size(2*self.target_rad-0.1)
        self.button15_in.move(np.array([0., 0.]))
        self.button16_out.set_size(2*self.target_rad)
        self.button16_out.move(np.array([0., 0.]))
        self.button16_in.set_size(2*self.target_rad-0.1)
        self.button16_in.move(np.array([0., 0.]))
        
        
        #  Initialize the exit buttons
        self.exit_target1.set_size(2*self.exit_rad)
        self.exit_target1.move(self.exit_pos1)
        self.exit_target1.color = (.15, .15, .15, 1)
        self.exit_target2.set_size(2*self.exit_rad)
        self.exit_target2.move(self.exit_pos2)
        self.exit_target2.color = (.15, .15, .15, 1)
        
        # # Initialize PD Indicator
        # self.indicator_targ.set_size(self.exit_rad)
        # self.indicator_targ.move(self.indicator_pos)
        # self.indicator_targ.color = (0., 0., 0., 1.)
        
        # Determine the hypersets (every 2 numbers comprises a set)
        self.target_list = np.array([[1, 12, 4, 15, 14, 3, 4, 11, 7, 0], [5, 6, 7, 8, 9, 10, 11, 12, 13, 14]])
        
        # Initialize the Target and Home position
        self.target_HS_index = 0
        self.target_index = np.array([2*(self.set_ix-1), 2*(self.set_ix-1)+1])
        self.repeat = False
        self.home_position = np.array([0., 0.])
        self.target1_position = np.array([self.possible_target_pos_x[self.target_list[self.target_HS_index, self.target_index[0]]], self.possible_target_pos_y[self.target_list[self.target_HS_index, self.target_index[0]]]])
        self.target2_position = np.array([self.possible_target_pos_x[self.target_list[self.target_HS_index, self.target_index[1]]], self.possible_target_pos_y[self.target_list[self.target_HS_index, self.target_index[1]]]])
        
        # Initialize FSM Dictionary
        self.FSM = dict()
        
        # Determine the relative task update functions for each task state
        self.FSM['IHSI'] = dict(end_IHSI='vid_trig', stop=None)
        self.FSM['vid_trig'] = dict(rhtouch='set', stop=None)
        
        self.FSM['set'] = dict(touch_target1 = 'targ1_hold', touch_target2 = 'targ2_hold', touch_nontarg = 'set_error', set_timeout='timeout_error', stop=None,
            non_rhtouch='RH_touch')#,touch_not_target='touch_error')
        
        self.FSM['targ1_hold'] = dict(finish_targ_hold='targ1_pressed', early_leave_target1_hold = 'hold_error_nopress', 
            targ1_drag_out = 'drag_error_nopress', stop=None, non_rhtouch='RH_touch')
        self.FSM['targ2_hold'] = dict(finish_targ_hold='targ2_pressed', early_leave_target2_hold = 'hold_error_nopress',
            targ2_drag_out = 'drag_error_nopress', stop=None, non_rhtouch='RH_touch')
        
        self.FSM['targ1_pressed'] = dict(touch_target2 ='t1p_targ2_hold', touch_nontarg = 'set_error', set_timeout='timeout_error', stop=None,
            non_rhtouch='RH_touch')
        self.FSM['targ2_pressed'] = dict(t2p_first_error = 'set_error', touch_target1 ='t2p_targ1_hold', touch_nontarg = 'set_error', set_timeout='timeout_error', stop=None,
            non_rhtouch='RH_touch')
        
        self.FSM['t1p_targ2_hold'] = dict(finish_targ_hold='set_complete', early_leave_target2_hold = 'hold_error_t1p',
            targ2_drag_out = 'drag_error_t1p', stop=None, non_rhtouch='RH_touch')
        self.FSM['t2p_targ1_hold'] = dict(finish_targ_hold='set_error', early_leave_target1_hold = 'hold_error_t2p',
            targ1_drag_out = 'drag_error_t2p', stop=None, non_rhtouch='RH_touch')
        
        self.FSM['set_error'] = dict(end_set_error='IHSI', stop=None)
        self.FSM['set_complete'] = dict(hyperset_complete = 'reward_hyperset', next_set = 'reward_set', stop=None, non_rhtouch='RH_touch')
        self.FSM['reward_set'] = dict(end_reward_set = 'set', stop=None, non_rhtouch='RH_touch')
        self.FSM['reward_hyperset'] = dict(end_reward_hyperset = 'IHSI', stop=None, non_rhtouch='RH_touch')
        
        self.FSM['timeout_error'] = dict(end_timeout_error='IHSI', stop=None, non_rhtouch='RH_touch')
        self.FSM['hold_error_nopress'] = dict(end_hold_error_nopress='set', stop=None, non_rhtouch='RH_touch')
        self.FSM['drag_error_nopress'] = dict(end_drag_error_nopress='set', stop=None, non_rhtouch='RH_touch')
        
        self.FSM['hold_error_t1p'] = dict(end_hold_error_t1p='targ1_pressed', stop=None, non_rhtouch='RH_touch')
        self.FSM['drag_error_t1p'] = dict(end_drag_error_t1p='targ1_pressed', stop=None, non_rhtouch='RH_touch')
        
        self.FSM['hold_error_t2p'] = dict(end_hold_error_t2p='targ2_pressed', stop=None, non_rhtouch='RH_touch')
        self.FSM['drag_error_t2p'] = dict(end_drag_error_t2p='targ2_pressed', stop=None, non_rhtouch='RH_touch')
        
        # self.FSM['rew_anytouch'] = dict(end_rewanytouch='target', stop=None, non_rhtouch='RH_touch')
        self.FSM['idle_exit'] = dict(stop=None)
        
        
        # Test the COM ports for the reward and camera
        try:
            self.reward_port = serial.Serial(port='COM4',
                baudrate=115200)
            self.reward_port.close()
        except:
            pass

        try:
            self.dio_port = serial.Serial(port='COM5', baudrate=115200)
            time.sleep(4.)
        except:
            pass

        try:
            self.cam_trig_port = serial.Serial(port='COM6', baudrate=9600)
            time.sleep(3.)
            # Say hello: 
            self.cam_trig_port.write('a'.encode())

            # Start cams @ 50 Hz
            self.cam_trig_port.write('1'.encode())
        except:
            pass

        # save parameters: 
        d = dict(animal_name=animal_name, target_rad=self.target_rad,
            sets_selected = self.sets_selected, 
            ISetI_mean=self.ISetI_mean, ISetI_std = self.ISetI_std, 
            IHSI_mean=self.IHSI_mean, IHSI_std = self.IHSI_std, 
            targ_hold_time = self.tht,
            ch_timeout=self.ch_timeout, 
            anytarg_rew_time=self.anytarg_rew,
            set_rew_time = self.set_rew,
            hs_rew_time=self.hs_rew,
            timeout_error_timeout = self.timeout_error_timeout,
            hold_error_timeout = self.hold_error_timeout,
            drag_error_timeout = self.drag_error_timeout,
            start_time = datetime.datetime.now().strftime('%Y%m%d_%H%M'),
            testing=self.testing,
            rew_delay = self.reward_delay_time,
            use_cap_sensor = self.use_cap_sensor,
            drag_ok = self.drag_ok,
            )

        print(self.anytarg_rew)
        print(self.set_rew)
        print(self.hs_rew)

        try:
            if self.testing:
                pass

            else:
                import os
                path = os.getcwd()
                path = path.split('\\')
                path_data = [p for p in path if np.logical_and('Touchscreen' not in p, 'Targ' not in p)]
                path_root = ''
                for ip in path_data:
                    path_root += ip+'/'
                p = path_root + 'data/'

                # Check if this directory exists: 
                if os.path.exists(p):
                    pass
                else:
                    p = path_root+ 'data_tmp_'+datetime.datetime.now().strftime('%Y%m%d')+'/'
                    if os.path.exists(p):
                        pass
                    else:
                        os.mkdir(p)
                        print('Making temp directory: ', p)

                print ('')
                print ('')
                print('Data saving PATH: ', p)
                print ('')
                print ('')
                self.filename = p+ animal_name+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')
                if self.in_cage:
                    self.filename = self.filename+'_cage'

                pickle.dump(d, open(self.filename+'_params.pkl', 'wb'))
                self.h5file = tables.open_file(self.filename + '_data.hdf', mode='w', title = 'NHP data')
                self.h5_table = self.h5file.create_table('/', 'task', Data, '')
                self.h5_table_row = self.h5_table.row
                self.h5_table_row_cnt = 0

                # Note in python 3 to open pkl files: 
                #with open('xxxx_params.pkl', 'rb') as f:
                #    data_params = pickle.load(f)
        except:
            pass
    
    # Function for Closing the App
    def close_app(self):
        # Save Data Eventually
         #Stop the video: 
        try:
            self.cam_trig_port.write('0'.encode())
        except:
            pass

        if self.use_cap_sensor:
            self.serial_port_cap.close()
        
        if self.idle:
            self.state = 'idle_exit'
            self.trial_counter = -1

            # Set relevant params text: 
            self.cht_text = 'Home Hold Time: '
            self.tht_text = 'Target Hold Time: '
            self.targ_size_text = 'Target Radius: '
            self.big_rew_text = 'Big Reward Time: '

            if type(self.cht_type) is str:
                self.cht_param = self.cht_type
            else:
                self.cht_param = 'Constant: ' + str(self.cht)

            if type(self.tht_type) is str:
                self.tht_param = self.tht_type
            else:
                self.tht_param = 'Constant: ' + str(self.tht)

            self.targ_size_param = str(self.target_rad)
            self.big_rew_time_param = str(self.reward_for_targtouch[1])

        else:
            App.get_running_app().stop()
            Window.close()
    
    def update(self, ts):
        self.state_length = time.time() - self.state_start
        self.rew_cnt += 1
        # self.set_rew_cnt += 1
        
        # Run task update functions: 
        for f, (fcn_test_name, next_state) in enumerate(self.FSM[self.state].items()):
            kw = dict(ts=self.state_length)

            fcn_test = getattr(self, fcn_test_name)
            if fcn_test(**kw):
                # if stop: close the app
                if fcn_test_name == 'stop':
                    self.close_app()

                else:
                    # Run any 'end' fcns from prevoius state: 
                    end_state_fn_name = "_end_%s" % self.state
                    if hasattr(self, end_state_fn_name):
                        end_state_fn = getattr(self, end_state_fn_name)
                        end_state_fn()
                        
                    # Advance to the next state
                    self.prev_state = self.state_length
                    # if next_state is 'set_error':
                    #     import pdb; pdb.set_trace()
                    self.state = next_state
                    
                    self.state_start = time.time()

                    # Run any starting functions: 
                    start_state_fn_name = "_start_%s" % self.state
                    if hasattr(self, start_state_fn_name):
                        start_state_fn = getattr(self, start_state_fn_name)
                        start_state_fn()
            else:
                while_state_fn_name = "_while_%s" % self.state
                if hasattr(self, while_state_fn_name):
                    while_state_fn = getattr(self, while_state_fn_name)
                    while_state_fn()
            
        if self.use_cap_sensor:
            try:
                self.serial_port_cap.flushInput()
                port_read = self.serial_port_cap.read(4)
                if str(port_read[:2]) == "b'N1'":
                    self.rhtouch_sensor = False
                elif str(port_read[:2]) == "b'C1'":
                    self.rhtouch_sensor = True
                    print(self.rhtouch_sensor)
            except:
                print('passing state! ')
                pass  
        
        # Save the data if this is not a test or we arent exiting
        if self.testing:
            pass
        else:
            if self.state == 'idle_exit':
                pass
            else:
                self.write_to_h5file()
    
    # Function for saving the data
    def write_to_h5file(self):
        self.h5_table_row['state']= self.state; 
        cursor = np.zeros((10, 2))
        cursor[:] = np.nan
        for ic, curs_id in enumerate(self.cursor_ids):
            cursor[ic, :] = self.cursor[curs_id]

        self.h5_table_row['cursor'] = cursor

        cursor_id = np.zeros((10, ))
        cursor_id[:] = np.nan
        cursor_id[:len(self.cursor_ids)] = self.cursor_ids
        self.h5_table_row['cursor_ids'] = cursor_id

        self.h5_table_row['set_ix'] = self.set_ix
        self.h5_table_row['time'] = time.time() - self.t0
        self.h5_table_row['cap_touch'] = self.rhtouch_sensor
        self.h5_table_row.append()

        # Write DIO 
        try:
            self.write_row_to_dio()
        except:
            pass
            
        # Upgrade table row: 
        self.h5_table_row_cnt += 1
    
    def write_row_to_dio(self):
        ### FROM TDT TABLE, 5 is GND, BYTE A ###
        row_to_write = self.h5_table_row_cnt % 256

        ### write to arduino: 
        word_str = b'd' + struct.pack('<H', int(row_to_write))
        self.dio_port.write(word_str)
    
    def stop(self, **kwargs):
        # If past number of max trials then auto-quit: 
        if np.logical_and(self.trial_counter >= self.max_trials, self.state == 'IHSI'):
            self.idle = True
            return True
        else:
            # Stop if both exit targets are held
            e = [0, 0]
            e[0] = self.check_if_cursors_in_targ(self.exit_pos1, self.exit_rad)
            e[1] = self.check_if_cursors_in_targ(self.exit_pos2, self.exit_rad)
            t = [0, 0]
            for i in range(2):
                if np.logical_and(self.prev_exit_ts[i] !=0, e[i] == True):
                    t[i] = time.time() - self.prev_exit_ts[i]
                elif np.logical_and(self.prev_exit_ts[i] == 0, e[i]==True):
                    self.prev_exit_ts[i] = time.time()
                else:
                    self.prev_exit_ts[i] = 0
                    
            if t[0] > self.exit_hold and t[1] > self.exit_hold:
                self.idle = False
                return True

            else:
                return False
    
    # IHSI State
    def _start_IHSI(self, **kwargs):
        try:
            self.cam_trig_port.write('0'.encode())
        except:
            pass
        
        # Make the screen dark
        Window.clearcolor = (0., 0., 0., 1.)
        self.change_allbutton_color(0, 0, 0, 1)
        self.exit_target1.color = (.15, .15, .15, 1.)
        self.exit_target2.color = (.15, .15, .15, 1.)
        
        # Set the set index to 1
        self.set_ix = 1;
        
        # Set IHSI, CHT, THT
        self.IHSI = np.random.random()*self.IHSI_std + self.IHSI_mean

        if type(self.cht_type) is str:
            cht_min, cht_max = self.cht_type.split('-')
            self.cht = ((float(cht_max) - float(cht_min)) * np.random.random()) + float(cht_min)

        if type(self.tht_type) is str:
            tht_min, tht_max = self.tht_type.split('-')
            self.tht = ((float(tht_max) - float(tht_min)) * np.random.random()) + float(tht_min)            
        
        # Make all of the targets invisible
        self.target1.color = (0., 0., 0., 0.)
        self.target2.color = (0., 0., 0., 0.)
        # self.indicator_targ.color = (0., 0., 0., 0.)
    
    def end_IHSI(self, **kwargs):
        return kwargs['ts'] > self.IHSI
    
    # Video Trigger State
    def _start_vid_trig(self, **kwargs):
        if self.trial_counter == 0:
            time.sleep(1.)
        try:    
            self.cam_trig_port.write('1'.encode())
        except:
            pass
        
        # Sets that come after the trigger must be the first set
        self.first_set_attempt = True

        if np.logical_and(self.use_cap_sensor, not self.rhtouch_sensor):
            self.target1.color = (1., 0., 0., 1.)
            self.target2.color = (1., 0., 0., 1.)
            Window.clearcolor = (1., 0., 0., 1.)

            # # Turn exit buttons redish:
            self.exit_target1.color = (.9, 0, 0, 1.)
            self.exit_target2.color = (.9, 0, 0, 1.)

    def end_vid_trig(self, **kwargs):
        return kwargs['ts'] > self.pre_start_vid_ts
    
    # Right hand on touch sensor
    def rhtouch(self, **kwargs):
        if self.use_cap_sensor:
            if self.rhtouch_sensor:
                return True
            else:
                return False
        else:
            return True

    def non_rhtouch(self, **kwargs):
        x = not self.rhtouch()
        # if x:
        #     self.repeat = True
        return x
    
    # Start a new set
    def _start_set(self, **kwargs):
        self.touch = False ## We need to start with this being false or else if non-target touch tolerance is not infinity, the previous touch will carry over and cause an error
        Window.clearcolor = (0., 0., 0., 1.)
        
        # Display outlines of all of the buttons
        self.button1_out.move(np.array([self.possible_target_pos_x[0], self.possible_target_pos_y[0]]))
        self.button1_out.color = (1., 1., 0., 1.)
        self.button1_in.move(np.array([self.possible_target_pos_x[0], self.possible_target_pos_y[0]]))
        self.button1_in.color = (0., 0., 0., 1.)
        self.button2_out.move(np.array([self.possible_target_pos_x[1], self.possible_target_pos_y[1]]))
        self.button2_out.color = (1., 1., 0., 1.)
        self.button2_in.move(np.array([self.possible_target_pos_x[1], self.possible_target_pos_y[1]]))
        self.button2_in.color = (0., 0., 0., 1.)
        self.button3_out.move(np.array([self.possible_target_pos_x[2], self.possible_target_pos_y[2]]))
        self.button3_out.color = (1., 1., 0., 1.)
        self.button3_in.move(np.array([self.possible_target_pos_x[2], self.possible_target_pos_y[2]]))
        self.button3_in.color = (0., 0., 0., 1.)
        self.button4_out.move(np.array([self.possible_target_pos_x[3], self.possible_target_pos_y[3]]))
        self.button4_out.color = (1., 1., 0., 1.)
        self.button4_in.move(np.array([self.possible_target_pos_x[3], self.possible_target_pos_y[3]]))
        self.button4_in.color = (0., 0., 0., 1.)
        self.button5_out.move(np.array([self.possible_target_pos_x[4], self.possible_target_pos_y[4]]))
        self.button5_out.color = (1., 1., 0., 1.)
        self.button5_in.move(np.array([self.possible_target_pos_x[4], self.possible_target_pos_y[4]]))
        self.button5_in.color = (0., 0., 0., 1.)
        self.button6_out.move(np.array([self.possible_target_pos_x[5], self.possible_target_pos_y[5]]))
        self.button6_out.color = (1., 1., 0., 1.)
        self.button6_in.move(np.array([self.possible_target_pos_x[5], self.possible_target_pos_y[5]]))
        self.button6_in.color = (0., 0., 0., 1.)
        self.button7_out.move(np.array([self.possible_target_pos_x[6], self.possible_target_pos_y[6]]))
        self.button7_out.color = (1., 1., 0., 1.)
        self.button7_in.move(np.array([self.possible_target_pos_x[6], self.possible_target_pos_y[6]]))
        self.button7_in.color = (0., 0., 0., 1.)
        self.button8_out.move(np.array([self.possible_target_pos_x[7], self.possible_target_pos_y[7]]))
        self.button8_out.color = (1., 1., 0., 1.)
        self.button8_in.move(np.array([self.possible_target_pos_x[7], self.possible_target_pos_y[7]]))
        self.button8_in.color = (0., 0., 0., 1.)
        self.button9_out.move(np.array([self.possible_target_pos_x[8], self.possible_target_pos_y[8]]))
        self.button9_out.color = (1., 1., 0., 1.)
        self.button9_in.move(np.array([self.possible_target_pos_x[8], self.possible_target_pos_y[8]]))
        self.button9_in.color = (0., 0., 0., 1.)
        self.button10_out.move(np.array([self.possible_target_pos_x[9], self.possible_target_pos_y[9]]))
        self.button10_out.color = (1., 1., 0., 1.)
        self.button10_in.move(np.array([self.possible_target_pos_x[9], self.possible_target_pos_y[9]]))
        self.button10_in.color = (0., 0., 0., 1.)
        self.button11_out.move(np.array([self.possible_target_pos_x[10], self.possible_target_pos_y[10]]))
        self.button11_out.color = (1., 1., 0., 1.)
        self.button11_in.move(np.array([self.possible_target_pos_x[10], self.possible_target_pos_y[10]]))
        self.button11_in.color = (0., 0., 0., 1.)
        self.button12_out.move(np.array([self.possible_target_pos_x[11], self.possible_target_pos_y[11]]))
        self.button12_out.color = (1., 1., 0., 1.)
        self.button12_in.move(np.array([self.possible_target_pos_x[11], self.possible_target_pos_y[11]]))
        self.button12_in.color = (0., 0., 0., 1.)
        self.button13_out.move(np.array([self.possible_target_pos_x[12], self.possible_target_pos_y[12]]))
        self.button13_out.color = (1., 1., 0., 1.)
        self.button13_in.move(np.array([self.possible_target_pos_x[12], self.possible_target_pos_y[12]]))
        self.button13_in.color = (0., 0., 0., 1.)
        self.button14_out.move(np.array([self.possible_target_pos_x[13], self.possible_target_pos_y[13]]))
        self.button14_out.color = (1., 1., 0., 1.)
        self.button14_in.move(np.array([self.possible_target_pos_x[13], self.possible_target_pos_y[13]]))
        self.button14_in.color = (0., 0., 0., 1.)
        self.button15_out.move(np.array([self.possible_target_pos_x[14], self.possible_target_pos_y[14]]))
        self.button15_out.color = (1., 1., 0., 1.)
        self.button15_in.move(np.array([self.possible_target_pos_x[14], self.possible_target_pos_y[14]]))
        self.button15_in.color = (0., 0., 0., 1.)
        self.button16_out.move(np.array([self.possible_target_pos_x[15], self.possible_target_pos_y[15]]))
        self.button16_out.color = (1., 1., 0., 1.)
        self.button16_in.move(np.array([self.possible_target_pos_x[15], self.possible_target_pos_y[15]]))
        self.button16_in.color = (0., 0., 0., 1.)
        
        # Update the progress bar
        self.percent_done = 100*(self.set_ix/self.nsets_per_hyperset)
        
        # Determine which targets to show for this set
        self.target_index = np.array([2*(self.sets_selected[self.set_ix-1]), 2*(self.sets_selected[self.set_ix-1])+1])
        
        self.targtouch_rew_given = False
        
        # Change the position of the targets
        if self.repeat is False:
            self.target1_position = np.array([self.possible_target_pos_x[self.target_list[self.target_HS_index, self.target_index[0]]], self.possible_target_pos_y[self.target_list[self.target_HS_index, self.target_index[0]]]])
            self.target2_position = np.array([self.possible_target_pos_x[self.target_list[self.target_HS_index, self.target_index[1]]], self.possible_target_pos_y[self.target_list[self.target_HS_index, self.target_index[1]]]])
            
            # self.target_set_index += 2
            print(self.target1_position)
            print(self.target2_position)
        
        self.target1.move(self.target1_position)
        self.target2.move(self.target2_position)
        self.target1.color = (1., 1., 0., 1.)
        self.target2.color = (1., 1., 0., 1.)
        self.repeat = False
        
        # Turn exit buttons gray
        self.exit_target1.color = (.15, .15, .15, 1)
        self.exit_target2.color = (.15, .15, .15, 1)
        # self.indicator_targ.color = (.25, .25, .25, 1.)
        
        if self.first_set_attempt:
            self.first_set_attempt_t0 = time.time();
            self.first_set_attempt = False
    
    # Touch Targets
    def touch_target1(self, **kwargs):
        if self.drag_ok:
            return self.check_if_cursors_in_targ(self.target1_position, self.target_rad)
        else:
            return np.logical_and(self.check_if_cursors_in_targ(self.target1_position, self.target_rad),
                self.check_if_started_in_targ(self.target1_position, self.target_rad))
    
    def touch_target2(self, **kwargs):
        if self.drag_ok:
            return self.check_if_cursors_in_targ(self.target2_position, self.target_rad)
        else:
            return np.logical_and(self.check_if_cursors_in_targ(self.target2_position, self.target_rad),
                self.check_if_started_in_targ(self.target2_position, self.target_rad))
        
    def touch_nontarg(self, **kwargs):
        nontarg_error = False
        if np.logical_and(self.nontarget_error_tolerance < 100, self.touch):
            nontarg_error = not np.logical_or(self.check_if_cursors_in_targ(self.target1_position, self.nontarget_error_tolerance*self.target_rad), 
                                           self.check_if_cursors_in_targ(self.target2_position, self.nontarget_error_tolerance*self.target_rad))

        return nontarg_error
    
    # Starting with target 2 gives an error
    def t2p_first_error(self, **kwargs):
        return self.t2p_first_is_error
    
    # Start Target Holds --> Change the Color of the target to yellow?
    def _start_targ1_hold(self, **kwargs):
        self.target1.color = (0., 1., 0., 1.)
        # self.indicator_targ.color = (0.75, .75, .75, 1.)
    
    def _start_targ2_hold(self, **kwargs):
        self.target2.color = (0., 1., 0., 1.)
        # self.indicator_targ.color = (0.75, .75, .75, 1.)
        
    def _start_t2p_targ1_hold(self, **kwargs):
        self.target1.color = (0., 1., 0., 1.)
        # self.indicator_targ.color = (0.75, .75, .75, 1.)
    
    def _start_t1p_targ2_hold(self, **kwargs):
        self.target2.color = (0., 1., 0., 1.)
        # self.indicator_targ.color = (0.75, .75, .75, 1.)
        
    # End Target Holds --> Change the color of the target to same as background
    def _end_targ1_hold(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        
    def _end_targ2_hold(self, **kwargs):
        self.target2.color = (0., 0., 0., 1.)
    
    # Finish target hold?
    def finish_targ_hold(self, **kwargs):
        return self.tht <= kwargs['ts']
    
    # One target has been pressed --> make it invisible
    def _start_targ1_pressed(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (1., 1., 0., 1.)
        # self.indicator_targ.color = (0.75, .75, .75, 1.)
        
        if self.rew_tone_every:
            print('rew every correct')
            sound = SoundLoader.load('reward2.wav')
            sound.play()
        
        if self.reward_for_targtouch[0] and not self.targtouch_rew_given:
            self.run_anytarg_rew()
            self.targtouch_rew_given = True
        
    def _start_targ2_pressed(self, **kwargs):
        self.target1.color = (1., 1., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        # self.indicator_targ.color = (0.75, .75, .75, 1.)
        
        if self.reward_for_targtouch[0] and not self.targtouch_rew_given:
            self.run_anytarg_rew()
            self.targtouch_rew_given = True

    
    # Once a set is complete, determine whether to restart or move to the next set
    def hyperset_complete(self, **kwargs):
        return self.set_ix == self.nsets_per_hyperset
    
    def next_set(self, **kwargs):
        return self.set_ix < self.nsets_per_hyperset
    
    
    ################################### REWARD STATES ################################
    def _start_reward_set(self, **kwargs):
        self.trial_counter += 1
        Window.clearcolor = (1., 1., 1., 1.)
        self.target1.color = (1., 1., 1., 1.)
        self.target2.color = (1., 1., 1., 1.)
        
        # # Turn exit targets white
        # self.exit_target1.color = (1., 1., 1., 1.)
        # self.exit_target2.color = (1., 1., 1., 1.)
        self.rew_cnt = 0
        self.cnts_in_rew = 0
        # self.indicator_targ.color = (1., 1., 1., 1.)
        self.repeat = False
        
    def _while_reward_set(self, **kwargs):
        if self.rew_cnt == 0:
            self.run_set_rew()
            self.rew_cnt += 1
            
    def end_reward_set(self, **kwargs):
        # Advance to the next set
        self.set_ix += 1
        
        # The next set will be the first attempt of that set
        self.first_set_attempt = True
        
        return True
    
    def _start_reward_hyperset(self, **kwargs):
        self.trial_counter += 1
        
        # Turn the screen green
        Window.clearcolor = (0., 1., 0., 1.)
        self.change_allbutton_color(0, 1, 0, 1)
        
        self.rew_cnt = 0
        self.cnts_in_rew = 0
        # self.indicator_targ.color = (1., 1., 1., 1.)
        self.repeat = False
        
    def _while_reward_hyperset(self, **kwargs):
        if self.rew_cnt == 0:
            self.run_HS_rew()
            self.rew_cnt += 1
            
    def end_reward_hyperset(self, **kwargs):
        return True
    
    ################################### ERROR STATES ################################
    # Set Error
    def _start_set_error(self, **kwargs):
        # Play an error tone
        if self.anytarg_rew == 0:
            sound = SoundLoader.load('error1.wav')
            sound.play()
        
            # Make the screen red
            self.percent_done = 0
            Window.clearcolor = (1., 0., 0., 1.)
            self.change_allbutton_color(1, 0, 0, 1)
        
    
    def end_set_error(self, **kwargs):
        # end the set error after the timeout period
        return kwargs['ts'] > self.error_timeout_time
    
    # Early leave from target --> hold error (buttons turn invisible)
    def early_leave_target1_hold(self, **kwargs):
        return not self.check_if_cursors_in_targ(self.target1_position, self.target_rad)
    
    def early_leave_target2_hold(self, **kwargs):
        return not self.check_if_cursors_in_targ(self.target2_position, self.target_rad)
    
    def _start_hold_error_nopress(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        self.repeat = True
        
    def end_hold_error_nopress(self, **kwargs):
        return kwargs['ts'] >= self.hold_error_timeout     
    
    def _start_hold_error_t1p(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        self.repeat = True
        
    def end_hold_error_t1p(self, **kwargs):
        return kwargs['ts'] >= self.hold_error_timeout  
    
    def _start_hold_error_t2p(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        self.repeat = True
        
    def end_hold_error_t2p(self, **kwargs):
        return kwargs['ts'] >= self.hold_error_timeout 
    
    
    # Drag outside of target --> drag error (buttons turn invisible)
    def targ1_drag_out(self, **kwargs):
        touch = self.touch
        self.touch = True
        stay_in = self.check_if_cursors_in_targ(self.target1_position, self.target_rad)
        self.touch = touch
        return not stay_in
    
    def targ2_drag_out(self, **kwargs):
        touch = self.touch
        self.touch = True
        stay_in = self.check_if_cursors_in_targ(self.target2_position, self.target_rad)
        self.touch = touch
        return not stay_in
    
    def _start_drag_error_nopress(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        self.repeat = True
    
    def end_drag_error_nopress(self, **kwargs):
        return kwargs['ts'] >= self.drag_error_timeout
    
    def _start_drag_error_t1p(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        self.repeat = True
        
    def end_drag_error_t1p(self, **kwargs):
        return kwargs['ts'] >= self.hold_error_timeout  
    
    def _start_drag_error_t2p(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        self.repeat = True
        
    def end_drag_error_t2p(self, **kwargs):
        return kwargs['ts'] >= self.hold_error_timeout 
    
    
    # Timeout error
    def set_timeout(self, **kwargs):
        #return kwargs['ts'] > self.target_timeout_time
        if time.time() - self.first_set_attempt_t0 > self.set_timeout_time:
            self.repeat = False
            return True
    
    def _start_timeout_error(self, **kwargs):
        self.target1.color = (0., 0., 0., 1.)
        self.target2.color = (0., 0., 0., 1.)
        #self.repeat = True
        
    def end_timeout_error(self, **kwargs):
        return kwargs['ts'] >= self.timeout_error_timeout
    
    # Check if the cursor is in the target and started in the target
    def check_if_started_in_targ(self, targ_center, targ_rad):
        startedInTarg = False
        if self.touch:
            for id_ in self.cursor_ids:
                # If in target: 
                if np.linalg.norm(np.array(self.cursor[id_]) - targ_center) < targ_rad:
                    if np.linalg.norm(np.array(self.cursor_start[id_]) - targ_center) < targ_rad:
                        startedInTarg = True
        return startedInTarg

    def check_if_cursors_in_targ(self, targ_center, targ_rad):
        if self.touch:
            inTarg = False
            for id_ in self.cursor_ids:
                if np.linalg.norm(np.array(self.cursor[id_]) - targ_center) < targ_rad:
                    inTarg = True

            return inTarg
        else:
            return False
    
    
    # Generate reward schedule
    def gen_rewards(self, perc_trials_rew, perc_trials_2x, reward_for_grasp):
        mini_block = int(2*(np.round(1./self.percent_of_trials_rewarded)))
        rew = []
        trial_cnt_bonus = 0

        for i in range(500):
            mini_block_array = np.zeros((mini_block))
            ix = np.random.permutation(mini_block)
            mini_block_array[ix[:2]] = reward_for_grasp[1]

            trial_cnt_bonus += mini_block
            if perc_trials_2x > 0:
                if trial_cnt_bonus > int(1./(perc_trials_rew*perc_trials_2x)):
                    mini_block_array[ix[0]] = reward_for_grasp[1]*2.
                    trial_cnt_bonus = 0

            rew.append(mini_block_array)
        return np.hstack((rew))
    
    # Run Rewards
    def run_anytarg_rew(self, **kwargs):
        print('Run anytarg reward')
        try:
            ### To trigger reward make sure reward is > 0:
            if self.anytarg_rew > 0:
                self.reward_port.open()
                rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.anytarg_rew)+' sec\n']
                self.reward_port.write(rew_str)
                time.sleep(.25)
                run_str = [ord(r) for r in 'run\n']
                self.reward_port.write(run_str)
                self.reward_port.close()
        except:
            pass

        #self.repeat = True
    
    def run_set_rew(self, **kwargs):
        try:
            #winsound.PlaySound('beep1.wav', winsound.SND_ASYNC)
            sound = SoundLoader.load('reward2.wav')
            sound.play()

            ### To trigger reward make sure reward is > 0:
            if self.set_rew > 0:
                self.reward_port.open()
                rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.set_rew)+' sec\n']
                self.reward_port.write(rew_str)
                time.sleep(.25)
                run_str = [ord(r) for r in 'run\n']
                self.reward_port.write(run_str)
                self.reward_port.close()
        except:
            pass

        #self.repeat = True
    
    def run_HS_rew(self, **kwargs):
        try:
            #winsound.PlaySound('beep1.wav', winsound.SND_ASYNC)
            sound = SoundLoader.load('reward1.wav')
            sound.play()
            
            print('in big reward:')
            self.repeat = False
            #winsound.PlaySound('beep1.wav', winsound.SND_ASYNC)
            #sound = SoundLoader.load('reward1.wav')
            #print(str(self.reward_generator[self.trial_counter]))
            #print(self.trial_counter)
            #print(self.reward_generator[:100])
            # self.reward1.play()

            # if not self.skip_juice:
                # if self.reward_generator[self.trial_counter] > 0:
            self.reward_port.open()
            #rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_for_targtouch[1])+' sec\n']
            rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.hs_rew)+' sec\n']
            self.reward_port.write(rew_str)
            time.sleep(.25 + self.reward_delay_time)
            run_str = [ord(r) for r in 'run\n']
            self.reward_port.write(run_str)
            self.reward_port.close()
        except:
            pass
    
    # Other utilities
    def change_allbutton_color(self, r, g, b, a):
        self.exit_target1.color = (r, g, b, a)
        self.exit_target2.color = (r, g, b, a)
        self.target1.color = (r, g, b, a)
        self.target2.color = (r, g, b, a)
        self.button1_out.color = (r, g, b, a)
        self.button1_in.color = (r, g, b, a)
        self.button2_out.color = (r, g, b, a)
        self.button2_in.color = (r, g, b, a)
        self.button3_out.color = (r, g, b, a)
        self.button3_in.color = (r, g, b, a)
        self.button4_out.color = (r, g, b, a)
        self.button4_in.color = (r, g, b, a)
        self.button5_out.color = (r, g, b, a)
        self.button5_in.color = (r, g, b, a)
        self.button6_out.color = (r, g, b, a)
        self.button6_in.color = (r, g, b, a)
        self.button7_out.color = (r, g, b, a)
        self.button7_in.color = (r, g, b, a)
        self.button8_out.color = (r, g, b, a)
        self.button8_in.color = (r, g, b, a)
        self.button9_out.color = (r, g, b, a)
        self.button9_in.color = (r, g, b, a)
        self.button10_out.color = (r, g, b, a)
        self.button10_in.color = (r, g, b, a)
        self.button11_out.color = (r, g, b, a)
        self.button11_in.color = (r, g, b, a)
        self.button12_out.color = (r, g, b, a)
        self.button12_in.color = (r, g, b, a)
        self.button13_out.color = (r, g, b, a)
        self.button13_in.color = (r, g, b, a)
        self.button14_out.color = (r, g, b, a)
        self.button14_in.color = (r, g, b, a)
        self.button15_out.color = (r, g, b, a)
        self.button15_in.color = (r, g, b, a)
        self.button16_out.color = (r, g, b, a)
        self.button16_in.color = (r, g, b, a)
        
    
    
class Splash(Widget):
    def init(self, *args):
        self.args = args
        # from sound import Sound
        # Sound.volume_max() 
    
class Target(Widget):
    color = ListProperty([0., 0., 0., 1.])

    def set_size(self, size):
        size_pix = [cm2pix(size), cm2pix(size)]
        self.size=size_pix

    def move(self, pos):
        # Convert cm to pixels
        pos_pix = cm2pix(pos).astype(int)
        pos_pix_int = tuple((int(pos_pix[0]), int(pos_pix[1])))
        self.center = pos_pix_int
    
    
class Manager(ScreenManager):
    pass 
    
    
class SequenceApp(App):
    def build(self, **kwargs):
        if platform == 'darwin':
            screenx = 1800
            screeny = 1000
        elif platform =='win32':
            from win32api import GetSystemMetrics
            screenx = GetSystemMetrics(0)
            screeny = GetSystemMetrics(1)
        
        Window.size = (1800, 1000)
        Window.left = (screenx - 1800)/2
        Window.top = (screeny - 1000)/2
        return Manager()    
    
def cm2pix(pos_cm, fixed_window_size=fixed_window_size, pix_per_cm=pix_per_cm):
    # Convert from CM to pixels: 
    pix_pos = pix_per_cm*pos_cm

    if type(pix_pos) is np.ndarray:
        # Translate to coordinate system w/ 0, 0 at bottom left
        pix_pos[0] = pix_pos[0] #+ (fixed_window_size[0]/2.)
        pix_pos[1] = pix_pos[1] #+ (fixed_window_size[1]/2.)

    return pix_pos    
    
def pix2cm(pos_pix, fixed_window_size=fixed_window_size, pix_per_cm=pix_per_cm):
    # First shift coordinate system: 
    pos_pix[0] = pos_pix[0] #- (fixed_window_size[0]/2.)
    pos_pix[1] = pos_pix[1] #- (fixed_window_size[1]/2.)

    pos_cm = pos_pix*(1./pix_per_cm)
    return pos_cm    
    
def reset():
    import kivy.core.window as window
    from kivy.base import EventLoop
    if not EventLoop.event_listeners:
        from kivy.cache import Cache
        window.Window = window.core_select_lib('window', window.window_impl, True)
        Cache.print_usage()
        for cat in Cache._categories:
            Cache._objects[cat] = {}

if __name__ == '__main__':
   # reset()
   SequenceApp().run()
