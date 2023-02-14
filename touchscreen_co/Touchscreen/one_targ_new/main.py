from kivy.app import App
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.core.text import Label as CoreLabel
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.config import Config
from kivy.graphics import Color, Rectangle, Triangle, Ellipse
from kivy.graphics.instructions import Callback
try:
    import serial
except ImportError:
    pass
import time, pickle, datetime
from contextlib import ExitStack
from typing import Optional, Any, List

from numpy import binary_repr
import struct
from sys import platform
import sys
import os
import argparse
from pathlib import Path
import threading
import json
import hjson

# errors will happen if more trials than MAX_TRIALS are done
# this value is used to generate some fixed size lists used by the program
# the max_trials config value is checked to ensure it's below or equal to this value
MAX_TRIALS = 10000

SAFE_MODE = 'safe' in os.environ
if SAFE_MODE:
    print('safe mode')

game_state_holder: Any = [None]

Config.set('graphics', 'resizable', False)
if platform == 'darwin':
    fixed_window_size = (3072, 1920)
    pix_per_cm = 89.
elif platform == 'win32':
    fixed_window_size = (1800, 1000)
    # 3/12.7 is a correction factor based on tina's measurments on the lab computer
    pix_per_cm = 85. * (3/12.7)
    import winsound
elif platform == 'linux':
    fixed_window_size = (1800, 1000)
    pix_per_cm = 85.
    if '--test' in sys.argv:
        fixed_window_size = (500, 500)
        pix_per_cm = 30.

Config.set('graphics', 'width', str(fixed_window_size[0]))
Config.set('graphics', 'height', str(fixed_window_size[1]))

import time
import numpy as np
try:
    import tables
except ImportError:
    h5 = False
else:
    h5 = True

if h5:
    class Data(tables.IsDescription):
        state = tables.StringCol(24)   # 24-character String
        cursor = tables.Float32Col(shape=(10, 2))
        cursor_ids = tables.Float32Col(shape = (10, ))
        target_pos = tables.Float32Col(shape=(2, ))
        cap_touch = tables.Float32Col()
        time = tables.Float32Col()

class COGame(Widget):
    center = ObjectProperty(None)
    target = ObjectProperty(None)
    
    nudge_x = 0.
    # nudge_y = -2.

    # Time to wait after starting the video before getting to the center target display. 
    pre_start_vid_ts = 0.1

    ITI_mean = 1.
    ITI_std = .2
    center_target_rad = 1.5
    periph_target_rad = 1.5
    
    if platform == 'darwin':
        exit_pos = np.array([14, 8])
        indicator_pos = np.array([16, 10])
    elif platform == 'win32':
        # exit_pos = np.array([7, 4])
        # move off screen
        exit_pos = np.array([100, 100])
        indicator_pos = np.array([8, 5])
    elif platform == 'linux':
        # exit_pos = np.array([14, 8])
        exit_pos = np.array([100, 100])
        indicator_pos = np.array([16, 10])
    exit_rad = 1.
    exit_hold = 2 #seconds

    ch_timeout = 10. # ch timeout
    cht = .001 # center hold time

    target_timeout_time = 5.
    tht = .001

    cursor = {}
    cursor_start = {}
    cursor_ids = []

    anytouch_prev = False
    touch_error_timeout = 0.
    timeout_error_timeout = 0.
    hold_error_timeout = 0.
    drag_error_timeout = 0.

    ntargets = 4.
    target_distance = 4.
    touch = False

    center_target = ObjectProperty(None)
    periph_target = ObjectProperty(None)

    done_init = False
    prev_exit_ts = np.array([0,0])

    # Number of trials: 
    trial_counter = NumericProperty(0)
    #indicator_txt = StringProperty('o')
    #indicator_txt_color = ListProperty([.5, .5, .5, 1.])

    t0 = time.time()

    cht_text = StringProperty('')
    tht_text = StringProperty('')
    generatorz_text = StringProperty('')
    targ_size_text = StringProperty('')
    big_rew_text = StringProperty('')
    cht_param = StringProperty('')
    tht_param = StringProperty('')
    targ_size_param = StringProperty('')
    big_rew_time_param = StringProperty('')
    generatorz_param = StringProperty('')
    nudge_text = StringProperty('')
    nudge_param = StringProperty('')
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
        try:
            self.cursor_ids.remove(touch.uid)
            _ = self.cursor.pop(touch.uid)
        except:
            print('removing touch from pre-game screen')
            
    def init(self, animal_names_dict=None, rew_in=None, task_in=None,
        test=None, hold=None, targ_structure=None,
        autoquit=None, rew_var=None, targ_timeout = None, nudge_x=None, nudge_y=None,
        peripheral_target=None, corner_non_cage_target_distance=None
    ):

        self.plexon = '--test' not in sys.argv
        
        self.update_callback: Optional[Any] = None
        
        assert peripheral_target is not None
        self.peripheral_target_param = peripheral_target
        if peripheral_target is not None:
            p_targ = self.periph_target
            # hide the initial shown circle
            p_targ.color = (0,0,0,0)
            self._hide_periph()
            # shape, color = peripheral_target

        self.rew_cnt = 0
        self.small_rew_cnt = 0


        self.use_cap_sensor = False

        if self.use_cap_sensor:
            self.serial_port_cap = serial.Serial(port='COM5')

        self.rhtouch_sensor = 0.


        self.target_timeout_time = targ_timeout['tt']
        self.ch_timeout = targ_timeout['ch_timeout']

        small_rew = rew_in['small_rew']
        big_rew = rew_in['big_rew']


        if rew_in['rew_anytouch']:
            self.reward_for_anytouch = [True, small_rew]
        else:
            self.reward_for_anytouch = [False, 0]

        if np.logical_or(rew_in['rew_targ'], rew_in['rew_center_pls_targ']):
            self.reward_for_targtouch = [True, big_rew]
        else:
            self.reward_for_targtouch = [False, 0]

        if rew_in['rew_center_pls_targ']:
            self.reward_for_center = [True, small_rew]
        else:
            self.reward_for_center = [False, 0]

        if rew_in['snd_only']:
            self.reward_for_targtouch = [True, 0.]
            self.skip_juice = True
        else:
            self.skip_juice = False

        self.periph_target_rad = task_in['targ_rad']
        self.center_target_rad = task_in['targ_rad']

        for i, (nm, val) in enumerate(animal_names_dict.items()):
            if val:
                animal_name = nm

        self.use_center = False
        for i, (nm, val) in enumerate(targ_structure.items()):
            if val:
                generatorz = getattr(self, nm)
                self.generatorz_param2 = nm
                if 'co' in nm:
                    self.use_center = True

        holdz = [0.0, 0.1, 0.2, 0.3, 0.4, .5, .6, '.4-.6']
        
        self.cht_type = None
        self.tht_type = None

        def _parse_hold(x):
            if type(x) is str:
                mx, mn = x.split('-')
                b = x
                a = (float(mn)+float(mx))*.5
            else:
                b = None
                a = x
            
            return a, b
        
        self.tht, self.tht_type = _parse_hold(hold['hold'])
        self.cht, self.cht_type = _parse_hold(hold['chold'])
        
        # for i, val in enumerate(hold['hold']):
        #     if val:
        #         if type(holdz[i]) is str:
        #             mx, mn = holdz[i].split('-')
        #             self.tht_type = holdz[i]
        #             self.tht =  (float(mn)+float(mx))*.5
        #         else:
        #             self.tht = holdz[i]

        # for i, val in enumerate(hold['chold']):
        #     if val:
        #         if type(holdz[i]) is str:
        #             mx, mn = holdz[i].split('-')
        #             self.cht_type = holdz[i]
        #             self.cht = (float(mn)+float(mx))*.5
        #         else:
        #             self.cht = holdz[i]
                    
        
        self.nudge_x = nudge_x['nudge_x']
        self.nudge_y = nudge_y['nudge_y']
        # nudge_x_opts = [-6, -4, -2, 0, 2, 4, 6]    
        # for i, val in enumerate(nudge_x['nudge_x']):
        #     if val:
        #         self.nudge_x = nudge_x_opts[i]
        
        # nudge_y_opts = [-3, -2, -1, 0, 1, 2, 3]    
        # for i, val in enumerate(nudge_y['nudge_y']):
        #     if val:
        #         self.nudge_y = nudge_y_opts[i]
        
        
        try:
            pygame.mixer.init()    
        except:
            pass

        # reward_delay_opts = [0., .4, .8, 1.2]
        # for i, val in enumerate(rew_del['rew_del']):
        #     if val:
        self.reward_delay_time = 0.0

        self.percent_of_trials_rewarded = rew_var['rew_var']
        self.percent_of_trials_doubled = rew_var['perc_doubled']
        # reward_var_opt = [1.0, .5, .33]
        # for i, val in enumerate(rew_var['rew_var']):
        #     if val:
        #         self.percent_of_trials_rewarded = reward_var_opt[i]
        #         if self.percent_of_trials_rewarded == 0.33:
        #             self.percent_of_trials_doubled = 0.1
        #         else:
        #             self.percent_of_trials_doubled = 0.0
        
        self.reward_generator = self.gen_rewards(self.percent_of_trials_rewarded, self.percent_of_trials_doubled,
            self.reward_for_targtouch)


        # white_screen_opts = [True, False]
        # for i, val in enumerate(white_screen['white_screen']):
        #     if val:
        self.use_white_screen = False

        test_vals = [True, False, False]
        in_cage_vals = [False, False, True]
        for i, val in enumerate(test['test']):
            if val:
                self.testing = test_vals[i]
                #self.in_cage = in_cage_vals[i]
        
        import os 
        path = os.getcwd()
        if 'BasalGangulia' in path:
            self.in_cage = True
        else:
            self.in_cage = False
        
        self.max_trials = autoquit['autoquit']
        # autoquit_trls = [10, 25, 50, 100, 10**10]
        # for i, val in enumerate(autoquit['autoquit']):
        #     if val: 
        #         self.max_trials = autoquit_trls[i]

        # drag_ok = [True, False]
        # for i, val in enumerate(drag['drag']):
        #     if val:
        #         self.drag_ok = drag_ok[i]
        self.drag_ok = False;
        
        # nudge_9am_dist = [0., .5, 1.]
        # for i, val in enumerate(nudge['nudge']):
        #     if val:
        self.nudge_dist = 0.
        
        # targ_pos = ['corners', None]
        # for i, val in enumerate(targ_pos['targ_pos']):
        #     if val:
        self.generator_kwarg = 'corners'
        
        # Preload sounds: 
        self.reward1 = SoundLoader.load('reward1.wav')
        self.reward2 = SoundLoader.load('reward2.wav')
        
        # Initialize targets: 
        self.center_target.set_size(2*self.center_target_rad)
        
        self.center_target_position = np.array([0., 0.])
        if self.in_cage:
            self.center_target_position[0] = self.center_target_position[0] - 4
        else:
            self.center_target_position[0] = self.center_target_position[0] + self.nudge_x
            self.center_target_position[1] = self.center_target_position[1] + self.nudge_y
        self.center_target.move(self.center_target_position)
        self.periph_target.set_size(2*self.periph_target_rad)

        self.exit_target1.set_size(2*self.exit_rad)
        self.exit_target2.set_size(2*self.exit_rad)
        self.indicator_targ.set_size(self.exit_rad)
        self.indicator_targ.move(self.indicator_pos)
        self.indicator_targ.color = (0., 0., 0., 1.)

        self.exit_target1.move(self.exit_pos)
        self.exit_pos2 = np.array([self.exit_pos[0], -1*self.exit_pos[1]])
        self.exit_target2.move(self.exit_pos2)
        self.exit_target1.color = (.15, .15, .15, 1)
        self.exit_target2.color = (.15, .15, .15, 1)

        self.corner_dist = corner_non_cage_target_distance
        assert self.corner_dist is not None
        
        self.target_list = generatorz(self.target_distance, self.nudge_dist, self.generator_kwarg)
        self.target_list[:, 0] = self.target_list[:, 0] + self.nudge_x
        self.target_list[:, 1] = self.target_list[:, 1] + self.nudge_y
        self.target_index = 0
        self.repeat = False
        
        self.periph_target_position = self.target_list[self.target_index, :]
        
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
        d = dict(animal_name=animal_name, center_target_rad=self.center_target_rad,
            periph_target_rad=self.periph_target_rad, target_structure = generatorz.__name__, 
            target_list = self.target_list, 
            ITI_mean=self.ITI_mean, ITI_std = self.ITI_std, ch_timeout=self.ch_timeout, 
            cht=self.cht, reward_time_small=self.reward_for_center[1],
            reward_time_big=self.reward_for_targtouch[1],
            reward_for_anytouch=self.reward_for_anytouch[0],
            reward_for_center = self.reward_for_center[0],
            reward_for_targtouch=self.reward_for_targtouch[0], 
            touch_error_timeout = self.touch_error_timeout,
            timeout_error_timeout = self.timeout_error_timeout,
            hold_error_timeout = self.hold_error_timeout,
            drag_error_timeout = self.drag_error_timeout,
            ntargets = self.ntargets,
            target_distance = self.target_distance,
            start_time = datetime.datetime.now().strftime('%Y%m%d_%H%M'),
            testing=self.testing,
            rew_delay = self.reward_delay_time,
            use_cap_sensor = self.use_cap_sensor,
            drag_ok = self.drag_ok,
            )

        print(self.reward_for_center)
        print(self.reward_for_targtouch)
        print(self.reward_for_anytouch)

        # self.testing = True
        #try:
        if self.testing:
            pass

        else:
            import os
            path = os.getcwd()
            path = path.split('\\')
            path_data = [p for p in path if np.logical_and('Touch' not in p, 'targ' not in p)]
            path_root = ''
            for ip in path_data:
                path_root += ip+'/'
            p = path_root + 'data/'
            print('Auto path : %s'%p)
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
            # input()
            print ('')
            print ('')
            self.filename = p+ animal_name+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')
            
            if self.in_cage:
                self.filename = self.filename+'_cage'

            from pprint import pprint
            pprint({(k, v) for k, v in d.items() if k != 'target_list'})
            
            pickle.dump(d, open(self.filename+'_params.pkl', 'wb'))
            if h5:
                self.h5file = tables.open_file(self.filename + '_data.hdf', mode='w', title = 'NHP data')
                self.h5_table = self.h5file.create_table('/', 'task', Data, '')
                self.h5_table_row = self.h5_table.row
            self.h5_table_row_cnt = 0

            # Note in python 3 to open pkl files: 
            #with open('xxxx_params.pkl', 'rb') as f:
            #    data_params = pickle.load(f)
            
            self.plex_do = None
            self.plex_do_device_number = 1
            self.reward_nidaq_bit = 17 # DO Channel
            if self.plexon:
                self._init_plex_do()
        # except:
        #     pass
    
    def _init_plex_do(self):
        from pyplexdo import PyPlexDO
        
        ## Setup for Plexon DO
        compatible_devices = ['PXI-6224', 'PXI-6259']
        self.plex_do = PyPlexDO()
        doinfo = self.plex_do.get_digital_output_info()
        device_number = None
        device_strings = []
        for k in range(doinfo.num_devices):
            dev_string = self.plex_do.get_device_string(doinfo.device_numbers[k])
            device_strings.append(dev_string)
            if dev_string in compatible_devices:
                device_number = doinfo.device_numbers[k]
        if device_number == None:
            print("No compatible devices found. Exiting.")
            print("Found devices", device_strings)
            sys.exit(1)
        else:
            print("{} found as device {}".format(self.plex_do.get_device_string(device_number), device_number))
        res = self.plex_do.init_device(device_number)
        if res != 0:
            print("Couldn't initialize device. Exiting.")
            sys.exit(1)
        self.plex_do.clear_all_bits(device_number)
    
    def _set_periph_color(self, color):
        shape, _ = self.peripheral_target_param
        p_targ = self.periph_target
        if shape == 'circle':
            p_targ.color = color
        elif shape == 'square':
            p_targ.rect_color = color
        elif shape == 'triangle':
            p_targ.triangle_color = color
        else:
            raise ValueError()
    
    def _show_periph(self):
        # self.periph_target.color = (1., 1., 0., 1.)
        _, color = self.peripheral_target_param
        self._set_periph_color(color)
    
    def _green_periph(self):
        # self.periph_target.color = (0., 1., 0., 1.)
        self._set_periph_color((0., 1., 0., 1.))
    
    def _red_periph(self):
        # self.periph_target.color = (0., 1., 0., 1.)
        self._set_periph_color((1, 0, 0, 1))
    
    def _hide_periph(self):
        # self.periph_target.color = (0., 0., 0., 0.)
        self._set_periph_color((0., 0., 0., 0.))
    
    def gen_rewards(self, perc_trials_rew, perc_trials_2x, reward_for_grasp):
        mini_block = int(2*(np.round(1./self.percent_of_trials_rewarded)))
        rew = []
        trial_cnt_bonus = 0

        for i in range(MAX_TRIALS):
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
            self.cht_text = 'Center Hold Time: '
            self.tht_text = 'Target Hold Time: '
            self.generatorz_text = 'Target Structure: '
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

            self.targ_size_param = str(self.center_target_rad)
            self.big_rew_time_param = str(self.reward_for_targtouch[1])
            self.generatorz_param = self.generatorz_param2

            self.nudge_text = 'Nudge 9oclock targ? '
            self.nudge_param = str(self.nudge_dist)
        else:
            App.get_running_app().stop()
            Window.close()

    def update(self, ts):
        """
            each key in self.FSM (=state) (set in self.init) is a state the game can be in
                each value is a dict mapping (describing a condition and resulting behaviour)
                    a function (=fn) to check if the condition is currently met
                        _start_{state} is called when a state is initially activated
                        _end_{state} is called when switching out of state (unless the new state is "stop")
                        _while_{state} is called repeatedly while a state is active
                    mapped to
                    a new state that is triggered when the condition is met
                        if the new state is "stop" the program is stopped
            """
        
        if self.update_callback is not None:
            self.update_callback()
        

    def write_to_h5file(self):
        if h5:
            self.h5_table_row['state']= self.state; 
        cursor = np.zeros((10, 2))
        cursor[:] = np.nan
        for ic, curs_id in enumerate(self.cursor_ids):
            cursor[ic, :] = self.cursor[curs_id]

        if h5:
            self.h5_table_row['cursor'] = cursor

        cursor_id = np.zeros((10, ))
        cursor_id[:] = np.nan
        cursor_id[:len(self.cursor_ids)] = self.cursor_ids
        if h5:
            self.h5_table_row['cursor_ids'] = cursor_id

            self.h5_table_row['target_pos'] = self.periph_target_position
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
        if np.logical_and(self.trial_counter >= self.max_trials, self.state == 'ITI'):
            self.idle = True
            return True
        else:
            e = [0, 0]
            e[0] = self.check_if_cursors_in_targ(self.exit_pos, self.exit_rad)
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

    def _start_reward(self, **kwargs):
        self.trial_counter += 1
        Window.clearcolor = (1., 1., 1., 1.)
        # self.periph_target.color = (1., 1., 1., 1.)
        self._hide_periph()
        self.exit_target1.color = (1., 1., 1., 1.)
        self.exit_target2.color = (1., 1., 1., 1.)
        self.rew_cnt = 0
        self.cnts_in_rew = 0
        self.indicator_targ.color = (1., 1., 1., 1.)
        self.repeat = False

    def run_big_rew(self, **kwargs):
        try:
            print('in big reward:')
            self.repeat = False
            if self.reward_for_targtouch[0]:
                #winsound.PlaySound('beep1.wav', winsound.SND_ASYNC)
                #sound = SoundLoader.load('reward1.wav')
                print('in big reward 2')
                #print(str(self.reward_generator[self.trial_counter]))
                #print(self.trial_counter)
                #print(self.reward_generator[:100])
                self.reward1 = SoundLoader.load('reward1.wav')
                self.reward1.play()
                
                if SAFE_MODE:
                    return
                if not self.skip_juice:
                    if self.reward_generator[self.trial_counter] > 0:
                        if self.plexon:
                            self.plex_do.set_bit(self.plex_do_device_number, self.reward_nidaq_bit)
                            time.sleep(self.reward_for_targtouch[1])
                            self.plex_do.clear_bit(self.plex_do_device_number, self.reward_nidaq_bit)
                        
                        self.reward_port.open()
                        #rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_for_targtouch[1])+' sec\n']
                        rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_generator[self.trial_counter])+' sec\n']
                        self.reward_port.write(rew_str)
                        time.sleep(.25 + self.reward_delay_time)
                        run_str = [ord(r) for r in 'run\n']
                        self.reward_port.write(run_str)
                        self.reward_port.close()
        except:
            pass
        
    def run_small_rew(self, **kwargs):
        try:
            if np.logical_or(self.reward_for_anytouch[0], self.reward_for_center[0]):
                #winsound.PlaySound('beep1.wav', winsound.SND_ASYNC)
                sound = SoundLoader.load('reward2.wav')
                sound.play()
                
                if SAFE_MODE:
                    return
                ### To trigger reward make sure reward is > 0:
                if np.logical_or(np.logical_and(self.reward_for_anytouch[0], self.reward_for_anytouch[1] > 0), 
                    np.logical_and(self.reward_for_center[0], self.reward_for_center[1] > 0)):

                    if self.plexon:
                        self.plex_do.set_bit(self.plex_do_device_number, self.reward_nidaq_bit)
                        time.sleep(self.reward_for_anytouch[1])
                        self.plex_do.clear_bit(self.plex_do_device_number, self.reward_nidaq_bit)

                    self.reward_port.open()
                    if self.reward_for_anytouch[0]:
                        rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_for_anytouch[1])+' sec\n']
                    elif self.reward_for_center[0]:
                        rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_for_center[1])+' sec\n']
                    self.reward_port.write(rew_str)
                    time.sleep(.25)
                    run_str = [ord(r) for r in 'run\n']
                    self.reward_port.write(run_str)
                    self.reward_port.close()
        except:
            pass
            # print('eeeee')

        #self.repeat = True

    def end_reward(self, **kwargs):
        self.indicator_txt_color = (1.,1., 1., 1.)
        if self.use_white_screen:
            if len(self.cursor_ids)== 0:
                return True
        else:
            if self.cnts_in_rew > 30:
                return True
            else:
                self.cnts_in_rew += 1
                return False

    def targ_drag_out(self, **kwargs):
        touch = self.touch
        self.touch = True
        # stay_in = self.check_if_cursors_in_targ(self.periph_target_position, self.periph_target_rad)
        stay_in = self.periph_target_touched()
        self.touch = touch
        return not stay_in

    def anytouch(self, **kwargs):
        if not self.periph_target_touched():
            current_touch = len(self.cursor_ids) > 0
            rew = False
            if current_touch and not self.anytouch_prev:
                rew = True
            self.anytouch_prev = current_touch
            return rew
        else:
            return False

    # get_targets functions are called as generatorz()
    # currently hard coded to use get_targets_co with gen_kwarg == 'corners'
    def get_4targets(self, target_distance=4, nudge=0., gen_kwarg=None):
        return self.get_targets_co(target_distance=target_distance, nudge=0.)

    def get_targets_co(self, target_distance=4, nudge=0., gen_kwarg=None, ntargets=4):
        # Targets in CM: 
        if gen_kwarg ==  'corners':
            angle = np.linspace(0, 2*np.pi, 5)[:-1] + (np.pi/4.)
            # target_distance = 6.
            target_distance = self.corner_dist
        else:
            angle = np.linspace(0, 2*np.pi, ntargets+1)[:-1]

        if self.in_cage:
            offset = np.array([-4., 0.])
            nudge_targ = np.array([0, 0, 0, 0])
            target_distance = 3.
        else:
            offset = np.array([0., 0.])
            nudge_targ = np.array([0, 0, 1., 0])
        
        if '--test' in sys.argv:
            pass
            # target_distance = 6
        
        x = np.cos(angle)*target_distance
        y = np.sin(angle)*target_distance
        tmp = np.hstack((x[:, np.newaxis], y[:, np.newaxis]))
        


        ### Add offset to the target positions 
        tmp = tmp + offset[np.newaxis, :]

        tgs = []
        nudges = []
        for blks in range(MAX_TRIALS // 4 + 1):
            ix = np.random.permutation(tmp.shape[0])
            tgs.append(tmp[ix, :])
            nudges.append(nudge_targ[ix])

        tgs = np.vstack((tgs))
        nudges = np.hstack((nudges))
        nudge_ix = np.nonzero(nudges==1)[0]
        #print('Nudges: ')
        #print(len(nudge_ix))

        to_nudge = np.array([-1., 1.])*nudge
        tgs[nudge_ix, :] = tgs[nudge_ix, :] + to_nudge[np.newaxis, :]

        return tgs

    def get_targets_rand(self, target_distance=4):
        # Targets in CM: 
        angle = np.linspace(0, 2*np.pi, 1000)
        target_distance = np.linspace(target_distance/4., target_distance, 1000)

        ix_ang = np.random.permutation(1000)
        ix_dist = np.random.permutation(1000)

        x = np.cos(angle[ix_ang])*target_distance[ix_dist]
        y = np.sin(angle[ix_ang])*target_distance[ix_dist]
        return np.hstack((x[:, np.newaxis], y[:, np.newaxis]))

    def check_if_started_in_targ(self, targ_center, targ_rad):
        startedInTarg = False
        if self.touch:
            for id_ in self.cursor_ids:
                # If in target: 
                # this probably finds euclidian distance and checks if it's less than targ_rad
                if np.linalg.norm(np.array(self.cursor[id_]) - targ_center) < targ_rad:
                    # this probably does the same thing as the identical line above it
                    if np.linalg.norm(np.array(self.cursor_start[id_]) - targ_center) < targ_rad:
                        startedInTarg = True
        return startedInTarg

    def check_if_cursors_in_targ(self, targ_center, targ_rad):
        if self.touch:
            inTarg = False
            for id_ in self.cursor_ids:
                # this probably finds euclidian distance and checks if it's less than targ_rad
                if np.linalg.norm(np.array(self.cursor[id_]) - targ_center) < targ_rad:
                    inTarg = True

            return inTarg
        else:
            return False
    
    def periph_target_touched(self) -> bool:
        """returns true if a touch is currently within the peripheral target"""
        shape, _ = self.peripheral_target_param
        for id_ in self.cursor_ids:
            c_x, c_y = self.cursor[id_]
            t_x, t_y = self.periph_target_position
            hs = self.periph_target_rad # half size
            if shape == 'circle':
                d = ((t_x - c_x)**2 + (t_y - c_y)**2)**0.5
                return d <= hs
            elif shape == 'square':
                return abs(c_x - t_x) <= hs and abs(c_y - t_y) <= hs
            elif shape == 'triangle':
                # if not in bounding rectangle return false
                if not (abs(c_x - t_x) <= hs and abs(c_y - t_y) <= hs):
                    return False
                
                # distance (y) from top of triangle
                from_top = t_y - c_y + hs
                # percent of width that is filled at y
                perc = from_top / (hs*2)
                # distance (x) touch can be from center while still being in triangle at y
                ok_dx = perc * hs
                if abs(t_x - c_x) > ok_dx:
                    return False
                
                return True
            else:
                raise ValueError()
        
        return False

class Splash(Widget):
    def init(self, *args):
        self.args = args
        if platform =='win32':
            from sound import Sound
            Sound.volume_max()

class Target(Widget):
    
    color = ListProperty([0., 0., 0., 1.])
    triangle_points = ListProperty()

    def set_size(self, size):
        size_pix = [cm2pix(size), cm2pix(size)]
        self.size=size_pix

    def move(self, pos):
        pos_pix = cm2pix(pos).astype(int)
        pos_pix_int = tuple((int(pos_pix[0]), int(pos_pix[1])))
        self.center = pos_pix_int
        # print(pos, self.center)
        x, y = self.center
        hs = self.size[0] / 2 # half of size
        self.triangle_points = [
            x, y + hs,
            x - hs, y - hs,
            x + hs, y - hs,
        ]
        # self.center = 0, 0

class Manager(ScreenManager):
    _splash = ObjectProperty(None)
    
    def __init__(self, config_path: Path):
        super(Manager, self).__init__()
        print(self._splash)
        self.params = None
        
        
        monkey_list = self.ids['starting2']
        self.monkey_checkboxes = {}
        
        def add_monkey(name: str, key, *, active=False):
            label = Label(text=name, fontsize=28, halign='center')
            check = CheckBox(group='check')
            if active:
                check.active = True
            monkey_list.add_widget(label)
            monkey_list.add_widget(check)
            self.monkey_checkboxes[key] = check
        
        monkey_names = {
            'Donut': 'donu', 'Sandpiper': 'sand', 'Sabotage': 'sabo',
            'test': 'test', 'Frappe': 'Frappe', 'Walleye': 'Walleye',
            'Steve': 'Steve', 'Erskine': 'Erskine',
        }
        first = True
        for name, key in monkey_names.items():
            add_monkey(name, key, active=first)
            first = False
        
        self.store_co_game_params_config_file(config_path)
        self.current = 'splash_start'
    
    def store_co_game_params_config_file(self, config_path: Path):
        with open(config_path) as f:
            raw = hjson.load(f)
        
        params = {}
        
        params['animal_names_dict'] = {
            raw['animal_name']: True,
        }
        
        params['rew_in'] = {
            'rew_manual': False, 'rew_anytouch': False,
            'rew_center_pls_targ': raw['reward_setup'],
            'rew_targ': not raw['reward_setup'],
            'snd_only': False,
            'small_rew': raw['peripheral_target_reward'],
            'big_rew': raw['center_target_reward'],
        }
        
        params['task_in'] = {
            'targ_rad': raw['target_radius'],
        }
        
        params['test'] = {'test': [False, True, False]}
        
        params['hold'] = {
            'chold': raw['center_hold_time'],
            'hold': raw['target_hold_time'],
        }
        
        params['targ_structure'] = {
            'get_targets_rand': False,
            'get_4targets': False,
            'get_targets_co': True,
        }
        
        assert raw['autoquit_after'] <= MAX_TRIALS
        params['autoquit'] = {
            'autoquit': raw['autoquit_after'],
        }
        
        params['rew_var'] = {
            'rew_var': raw['reward_variability'],
            'perc_doubled': raw['reward_double_chance'],
        }
        
        params['targ_timeout'] = {
            'tt': raw['target_timeout'],
            'ch_timeout': raw['ch_timeout'],
        }
        
        params['nudge_x'] = {
            'nudge_x': raw['nudge_x'],
        }
        params['nudge_y'] = {
            'nudge_y': raw['nudge_y'],
        }
        
        params['peripheral_target'] = (
            raw['peripheral_target_shape'],
            raw['peripheral_target_color'].split('_')
        )
        
        params['corner_non_cage_target_distance'] = raw['corner_non_cage_target_distance']
        
        from pprint import pp
        pp(tuple(params.values()))
        
        self.params = params
    
    def store_co_game_params(self):
        # print(self._splash)
        # print(self.ids)
        def g(k):
            """get an object by id"""
            return self.ids[k]
        
        def get_prefixed_value(prefix):
            """get an id postfix by finding the active checkbox with id prefix `prefix`"""
            value = None
            for wid, widget in self.ids.items():
                if not wid.startswith(prefix):
                    continue
                if widget.active:
                    # value = wid.removeprefix(prefix)
                    if wid.startswith(prefix):
                        value = wid[len(prefix):]
                    else:
                        value = wid
            assert value is not None
            return value
        
        params = {}
        params['animal_names_dict'] = {
            k: check.active for k, check in self.monkey_checkboxes.items()
        }
        
        small_reward_durations = ['zero', 'pt1', 'pt3', 'pt5']
        big_reward_durations = ['zero', 'pt3', 'pt5', 'pt7']
        params['rew_in'] = {
            'rew_manual': False, 'rew_anytouch': False,
            'rew_center_pls_targ': g('rew_center_pls_targ_chk').active,
            'rew_targ': g('rew_targ_chk').active, 'snd_only': False,
            'small_rew': [
                g(f"small_rew_{x}_sec").active for x in small_reward_durations
            ],
            'big_rew': [
                g(f"big_rew_{x}_sec").active for x in big_reward_durations
            ],
        }
        
        target_radii = [5, 75, 82, 91, 10, 15, 22, 30]
        params['task_in'] = {
            'targ_rad':[g(f"targ_rad_{x}").active for x in target_radii],
        }
        
        params['test'] = {'test': [False, True, False]}
        
        holds = [
            'zero_sec',
            'hund_sec', 'twohund_sec', 'threehund_sec' ,'fourhund_sec',
            'half_sec', '60', 'big_rand',
        ]
        params['hold'] = {
            'chold': [g(f"c_{x}").active for x in holds],
            'hold': [g('t_60' if x == '60' else x).active for x in holds],
        }
        
        params['targ_structure'] = {
            'get_targets_rand': False,
            'get_4targets': False,
            'get_targets_co': True,
        }
        
        auto_quits = [
            'ten_trials', 'twenty_five_trials', 'fifty_trials',
            'hundred_trials', 'no_trials',
        ]
        params['autoquit'] = {
            'autoquit': [g(x).active for x in auto_quits],
        }
        
        rew_vars = ['rew_all', 'rew_50', 'rew_30']
        params['rew_var'] = {
            'rew_var': [g(x).active for x in rew_vars],
        }
        
        targ_timeouts = ['tt_15_sec', 'tt_30_sec', 'tt_45_sec', 'tt_60_sec']
        params['targ_timeout'] = {
            'tt': [g(x).active for x in targ_timeouts],
        }
        
        x_nudges = ['neg6', 'neg4', 'neg2', 'zero', 'pos2', 'pos4', 'pos6']
        params['nudge_x'] = {
            'nudge_x': [g(f"nudge_x_{x}").active for x in x_nudges],
        }
        
        y_nudges = ['neg3', 'neg2', 'neg1', 'zero', 'pos1', 'pos2', 'pos3']
        params['nudge_y'] = {
            'nudge_y': [g(f"nudge_y_{x}").active for x in y_nudges],
        }
        
        pt_shape = get_prefixed_value('p_targ_shape_')
        pt_color = get_prefixed_value('p_targ_color_')
        pt_color = pt_color.split('_')
        
        params['peripheral_target'] = (pt_shape, pt_color)
        
        raw_targ_dist = get_prefixed_value('c_nc_targ_dist_')
        targ_dist = int(raw_targ_dist)
        params['corner_non_cage_target_distance'] = int(targ_dist)
        
        from pprint import pp
        pp(tuple(params.values()))
        # pp(self._splash.args)
        # print('same?', tuple(params.values()) == self._splash.args)
        # assert tuple(params.values()) == self._splash.args
        
        self.params = params
    
    def start_co_game(self):
        # print(self.current)
        self.current = 'game_screen'
        game = self.ids['game']
        game.init(**self.params)
        game_state_holder[0] = GameState(game)
        Clock.schedule_interval(game.update, 1.0 / 60.0)

class COApp(App):
    def __init__(self, config_path: Path):
        super(COApp, self).__init__()
        self._config_path = config_path
    
    def build(self, **kwargs):
        if platform == 'darwin':
            screenx = 1800
            screeny = 1000
        elif platform =='win32':
            from win32api import GetSystemMetrics
            screenx = GetSystemMetrics(0)
            screeny = GetSystemMetrics(1)
        elif platform == 'linux':
            screenx = 1800
            screeny = 1000

        Window.size = (1800, 1000)
        Window.left = (screenx - 1800)/2
        Window.top = (screeny - 1000)/2
        return Manager(self._config_path)

def cm2pix(pos_cm, fixed_window_size=fixed_window_size, pix_per_cm=pix_per_cm):
    # Convert from CM to pixels: 
    pix_pos = pix_per_cm*pos_cm

    if type(pix_pos) is np.ndarray:
        # Translate to coordinate system w/ 0, 0 at bottom left
        pix_pos[0] = pix_pos[0] + (fixed_window_size[0]/2.)
        pix_pos[1] = pix_pos[1] + (fixed_window_size[1]/2.)

    return pix_pos

def pix2cm(pos_pix, fixed_window_size=fixed_window_size, pix_per_cm=pix_per_cm):
    # First shift coordinate system: 
    pos_pix[0] = pos_pix[0] - (fixed_window_size[0]/2.)
    pos_pix[1] = pos_pix[1] - (fixed_window_size[1]/2.)

    pos_cm = pos_pix*(1./pix_per_cm)
    return pos_cm

class Timeout:
    def __init__(self, p, timeout, get_time):
        self.hit_timeout = False
        
        self.get_time = get_time
        self.p = p
        self.timeout = timeout
    
    def __iter__(self):
        start_time = self.get_time()
        while True:
            if not self.p():
                return
            if self.get_time() - start_time > self.timeout:
                self.hit_timeout = True
                return
            yield

class SelectAny:
    def __init__(self, gens):
        self.gens = gens
        self.first = None
    
    def __iter__(self):
        while True:
            for k, gen in self.gens.items():
                try:
                    next(gen)
                except StopIteration:
                    self.first = k
                    return
            yield

class Nidaq:
    def __init__(self, pins: List[str]):
        import nidaqmx
        from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
        from nidaqmx.constants import RegenerationMode
        self.pins = pins
        self.tasks = [nidaqmx.Task() for _ in pins]
        
        # self.task = nidaqmx.Task()
        # task = self.task
        
        for pin, task in zip(pins, self.tasks):
            task.do_channels.add_do_chan(pin, line_grouping = LineGrouping.CHAN_PER_LINE)
            
            # print(task.timing.samp_timing_type)
            # input()
            # task.timing.cfg_samp_clk_timing(
            #     1000,
            #     sample_mode = AcquisitionType.CONTINUOUS,
            # )
            # task.out_stream.output_buf_size = 1000
            # task.out_stream.regen_mode = RegenerationMode.DONT_ALLOW_REGENERATION
        
        # 4ms pulse
        # self.pulse = [
        #     *([1]*4),
        #     0
        # ]
        
        # pin_list = pins
        # port = 1
        # self.task.do_channels.add_do_chan(f"/Dev6/port{port}/line0:7", line_grouping = LineGrouping.CHAN_PER_LINE)
        
        
        
        
    
    def start(self):
        for task in self.tasks:
            task.start()
    
    def stop(self):
        for task in self.tasks:
            task.stop()
    
    def pulse_pin(self, pin):
        idx = self.pins.index(pin)
        # self.tasks[idx].write(self.pulse)
        self.tasks[idx].write(True)
        def pulse_end():
            time.sleep(0.004) # 4ms wait
            self.tasks[idx].write(False)
        thread = threading.Thread(target=pulse_end)
        thread.start()
        # time.sleep(0.006)
        # self.tasks[idx].write(False)

class GameState:
    def __init__(self, co_game: COGame):
        co_game.update_callback = self.progress_gen
        co_game.state = 'none'
        self.co_game: COGame = co_game
        
        self.game_time = 0
        self._last_progress_time = time.monotonic()
        
        self.event_log = []
        
        dev = 'Dev3'
        self.plexon_event_types = {
            'center_show': {
                'nidaq_pin': f'/{dev}/port0/line0',
                'plexon_channel': 17,
            },
            'center_touch': {
                'nidaq_pin': f'/{dev}/port0/line1',
                'plexon_channel': 18,
            },
            'center_hide': {
                'nidaq_pin': f'/{dev}/port0/line2',
                'plexon_channel': 19,
            },
            'periph_show': {
                'nidaq_pin': f'/{dev}/port0/line3',
                'plexon_channel': 20,
            },
            'periph_touch': {
                'nidaq_pin': f'/{dev}/port0/line4',
                'plexon_channel': 21,
            },
            'periph_hide': {
                'nidaq_pin': f'/{dev}/port0/line5',
                'plexon_channel': 22,
            },
            'top_left': {
                'nidaq_pin': f'/{dev}/port0/line6',
                'plexon_channel': 23,
            },
            'top_right': {
                'nidaq_pin': f'/{dev}/port0/line7',
                'plexon_channel': 24,
            },
            'bottom_left': {
                'nidaq_pin': f'/{dev}/port1/line0',
                'plexon_channel': 25,
            },
            'bottom_right': {
                'nidaq_pin': f'/{dev}/port1/line1',
                'plexon_channel': 26,
            },
            'trial_correct': {
                'nidaq_pin': f'/{dev}/port1/line2',
                'plexon_channel': 27,
            },
            'trial_incorrect': {
                'nidaq_pin': f'/{dev}/port1/line3',
                'plexon_channel': 28,
            },
        }
        self.nidaq_enabled = '--test' not in sys.argv
        pin_list = [x['nidaq_pin'] for x in self.plexon_event_types.values()]
        if self.nidaq_enabled:
            self.nidaq = Nidaq(pin_list)
            self.nidaq.start()
        else:
            self.nidaq = None
        
        self._gen = self._main_loop()
    
    def log_event(self, name: str, *, tags: List[str], info=None):
        if info is None:
            info = {}
        human_time = datetime.datetime.utcnow().isoformat()
        mono_time = time.perf_counter()
        out = {
            'time_human': human_time,
            'time_m': mono_time,
            'name': name,
            'tags': tags,
            'info': info,
        }
        
        self.event_log.append(out)
    
    def send_plexon_event(self, name, *, info=None):
        print(name)
        tags = ['plexon_send']
        if info is None:
            info = {}
        event_info = self.plexon_event_types[name]
        info['nidaq_pin'] = event_info['nidaq_pin']
        info['plexon_channel'] = event_info['plexon_channel']
        if self.nidaq is not None:
            self.nidaq.pulse_pin(event_info['nidaq_pin'])
        else:
            info['no_hardware'] = True
        self.log_event(name, tags=tags, info=info)
    
    def progress_gen(self):
        cur_time = time.monotonic()
        
        elapsed_time = cur_time - self._last_progress_time
        self._last_progress_time = cur_time
        self.game_time += elapsed_time
        
        next(self._gen)
    
    def _timeout(self, p, timeout: float):
        timeout_obj = Timeout(p, timeout, lambda: self.game_time)
        return timeout_obj
    
    def _wait(self, t: float):
        timeout = Timeout(lambda: True, t, lambda: self.game_time)
        yield from timeout
    
    def _until(self, p):
        while not p():
            yield
    
    def _race(self, **gens):
        return SelectAny(gens)
    
    def _main_loop(self):
        trial_i = 0
        while True:
            if trial_i >= self.co_game.max_trials:
                break
            # print('main loop')
            yield from self.run_trial()
            trial_i += 1
            # break
    
    def run_center(self, center_done):
        game = self.co_game
        
        # self.co_game.state = 'center'
        # game.state = 'none'
        # game._start_center()
        Window.clearcolor = (0., 0., 0., 1.)
        self.send_plexon_event('center_show')
        game.center_target.color = (1., 1., 0., 1.)
        game.exit_target1.color = (.15, .15, .15, 1)
        game.exit_target2.color = (.15, .15, .15, 1)
        # self.periph_target.color = (0., 0., 0., 0.) ### Make peripheral target alpha = 0 so doesn't obscure 
        self.send_plexon_event('periph_hide')
        game._hide_periph()
        game.indicator_targ.color = (.25, .25, .25, 1.)
        
        def check_touch_center():
            if game.drag_ok:
                return game.check_if_cursors_in_targ(game.center_target_position, game.center_target_rad)
            else:
                return \
                    game.check_if_cursors_in_targ(game.center_target_position, game.center_target_rad) and \
                    game.check_if_started_in_targ(game.center_target_position, game.center_target_rad)
        
        # wait for touch to be on center
        timeout = self._timeout(lambda: (not check_touch_center()), game.ch_timeout)
        yield from timeout
        if timeout.hit_timeout:
            self.send_plexon_event('trial_incorrect')
            self.send_plexon_event('center_hide')
            game.center_target.color = (0., 0., 0., 1.)
            game._hide_periph()
            yield from self._wait(game.timeout_error_timeout)
            return
        self.send_plexon_event('center_touch')
        
        # print('state center_hold')
        # game.state = 'center_hold'
        # game.state = 'none'
        game.center_target.color = (0., 1., 0., 1.)
        game.indicator_targ.color = (0.75, .75, .75, 1.)
        
        # check that touch remains on center for "cht"
        def on_target():
            return game.check_if_cursors_in_targ(game.center_target_position, game.center_target_rad)
        timeout = self._timeout(on_target, game.cht)
        yield from timeout
        if not timeout.hit_timeout:
            self.send_plexon_event('trial_incorrect')
            # game.state = 'hold_error'
            self.send_plexon_event('center_hide')
            game.center_target.color = (0., 0., 0., 1.)
            game._hide_periph()
            game.repeat = True
            return
        
        if game.reward_for_center[0]:
            game.run_small_rew()
        
        self.send_plexon_event('center_hide')
        # game.state = 'target'
        # game.state = 'none'
        Window.clearcolor = (0., 0., 0., 1.)
        game.center_target.color = (0., 0., 0., 0.)
        
        if game.repeat is False:
            # print('target idx', game.target_index)
            game.periph_target_position = game.target_list[game.target_index, :]
            # print(game.periph_target_position)
            x, y = game.periph_target_position
            if x < 0 and y > 0:
                self.send_plexon_event('top_left')
            elif x > 0 and y > 0:
                self.send_plexon_event('top_right')
            elif x < 0 and y < 0:
                self.send_plexon_event('bottom_left')
            elif x > 0 and y < 0:
                self.send_plexon_event('bottom_right')
            game.target_index += 1
        game.periph_target.move(game.periph_target_position)
        self.send_plexon_event('periph_show')
        game._show_periph()
        game.repeat = False
        game.exit_target1.color = (.15, .15, .15, 1)
        game.exit_target2.color = (.15, .15, .15, 1)
        game.indicator_targ.color = (.25, .25, .25, 1.)
        if game.first_target_attempt:
            game.first_target_attempt_t0 = time.time();
            game.first_target_attempt = False
        
        race = self._race(
            touch=self._until(lambda: game.periph_target_touched()),
            # anytouch=self._until(lambda: game.anytouch()),
            timeout=self._wait(game.target_timeout_time)
        )
        yield from race
        
        if race.first == 'touch':
            self.send_plexon_event('periph_touch')
            
            # game.state = 'targ_hold'
            # game._start_targ_hold()
            # game.state = 'none'
            game._green_periph()
            game.indicator_targ.color = (0.75, .75, .75, 1.)
            
            race = self._race(
                early_release=self._until(lambda: not game.periph_target_touched()),
                drag_out=self._until(lambda: game.targ_drag_out()),
                timeout=self._wait(game.tht)
            )
            yield from race
            
            if race.first == 'early_release':
                yield from self._wait(game.hold_error_timeout)
                self.send_plexon_event('trial_incorrect')
                return
            elif race.first == 'drag_out':
                yield from self._wait(game.drag_error_timeout)
                self.send_plexon_event('trial_incorrect')
                return
            elif race.first == 'timeout':
                self.send_plexon_event('periph_hide')
                self.send_plexon_event('trial_correct')
                game._start_reward()
                
                while not game.end_reward():
                    if game.rew_cnt == 1:
                        game.run_big_rew()
                        game.rew_cnt += 1
                    yield
                
            else:
                raise ValueError()
            
        elif race.first == 'anytouch':
            # game.state = 'rew_anytouch'
            # game._start_rew_anytouch()
            # game.state = 'none'
            
            print('anytouch')
            if game.reward_for_anytouch[0]:
                game.run_small_rew()
            else:
                return
        elif race.first == 'timeout':
            self.send_plexon_event('periph_hide')
            game.center_target.color = (0., 0., 0., 1.)
            game._hide_periph()
            center_done[0] = True
            return
        else:
            raise ValueError()
        
        # yield from self._until(lambda: game.state == 'center')
        
        center_done[0] = True
    
    def run_trial(self):
        game = self.co_game
        with ExitStack() as trial_stack:
            # ITI_mean + ITI_std
            Window.clearcolor = (0., 0., 0., 1.)
            self.co_game.exit_target1.color = (.15, .15, .15, 1.)
            self.co_game.exit_target2.color = (.15, .15, .15, 1.)
            
            if type(self.co_game.cht_type) is str:
                cht_min, cht_max = self.co_game.cht_type.split('-')
                self.cht = ((float(cht_max) - float(cht_min)) * np.random.random()) + float(cht_min)
            
            if type(self.co_game.tht_type) is str:
                tht_min, tht_max = self.co_game.tht_type.split('-')
                self.tht = ((float(tht_max) - float(tht_min)) * np.random.random()) + float(tht_min)
            
            self.send_plexon_event('center_hide')
            self.send_plexon_event('periph_hide')
            self.co_game.center_target.color = (0., 0., 0., 0.)
            self.co_game._hide_periph()
            self.co_game.indicator_targ.color = (0., 0., 0., 0.)
            
            iti = np.random.random()*self.co_game.ITI_std + self.co_game.ITI_mean
            yield from self._wait(iti)
            
            # game.state = 'vid_trig'
            game.state = 'none'
            # game._start_vid_trig()
            if game.trial_counter == 0:
                yield from self._wait(1)
            game.first_target_attempt = True
            
            # wait for self.pre_start_vid_ts
            yield from self._wait(0.1)
            
            center_done = [False]
            while not center_done[0]:
                yield from self.run_center(center_done)
            
            yield from self._wait(2)
    

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--config', default='./config.hjson',
        help='config file')
    
    parser.add_argument('--test', action='store_true',
        help="run in test mode")
    
    args = parser.parse_args()
    
    return args

def main():
    args = parse_args()
    
    config_path = Path(args.config)
    assert config_path.is_file()
    
    try:
        COApp(config_path).run()
    finally:
        if game_state_holder[0] is not None:
            state: GameState = game_state_holder[0]
            # print(state.co_game.filename)
            out = {
                'events': state.event_log,
            }
            with open(f"{state.co_game.filename}_meta.json", 'w') as f:
                json.dump(out, f, indent=4)
            if state.nidaq is not None:
                state.nidaq.stop()

if __name__ == '__main__':
    main()
