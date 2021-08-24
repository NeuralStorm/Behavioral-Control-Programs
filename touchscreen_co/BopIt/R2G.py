from kivy.app import App
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.config import Config
import serial, time, pickle, datetime, winsound, struct
import time
import numpy as np
import tables
import subprocess, signal

Config.set('graphics', 'resizable', False)
fixed_window_size = (1800, 1000)
Config.set('graphics', 'width', str(fixed_window_size[0]))
Config.set('graphics', 'height', str(fixed_window_size[1]))

class Data(tables.IsDescription):
    state = tables.StringCol(24)   # 24-character String
    time = tables.Float32Col()
    time_abs = tables.Float32Col()
    force = tables.Float32Col()
    beam = tables.Float32Col()
    start_led = tables.Float32Col()
    start_button = tables.Float32Col()

class R2Game(Widget):
    pre_start_vid_ts = 0.1

    ITI_mean = 1.
    ITI_std = .2

    start_timeout = 5000. 
    start_holdtime = .001

    grasp_timeout_time = 5000.
    grasp_holdtime = .001

    # Number of trials: 
    trial_counter = NumericProperty(0)
    t0 = time.time()

    big_reward_cnt = NumericProperty(0)
    small_reward_cnt = NumericProperty(0)
    tried = NumericProperty(0)

    # Set relevant params text: 
    grasp_rew_txt = StringProperty('')
    grasp_rew_param = StringProperty('')

    button_rew_txt = StringProperty('')
    button_rew_param = StringProperty('')

    grasp_hold_param = StringProperty('')
    grasp_hold_txt = StringProperty('')   
    button_hold_txt = StringProperty('')
    button_hold_param = StringProperty('')

    n_trials_txt = StringProperty('')
    n_trials_param = StringProperty('')

    def init(self, animal_names_dict=None, rew_in=None, rew_var=None,
        test=None, hold=None, autoquit=None, use_start=None, only_start=None, 
        grasp_to=None, use_cap=None):

        self.h5_table_row_cnt = 0
        self.idle = False


        cap = [True, False]
        for i, val in enumerate(use_cap['use_cap']):
            if val:
                self.use_cap_not_button = cap[i]

        button_holdz = ['.12-.2', '.15-.25', '.2-.3', '.25-.45', '.2-.5']
        grasp_holdz = [0., .15, .25, .35, .50]

        for i, val in enumerate(hold['start_hold']):
            if val:
                if type(button_holdz[i]) is str:
                    self.start_hold_type = button_holdz[i]
                    self.start_hold = 0.
                else:
                    self.start_hold_type = 0
                    self.start_hold = button_holdz[i]

        for i, val in enumerate(hold['grasp_hold']):
            if val:
                if type(grasp_holdz[i]) is str:
                    self.grasp_hold_type = grasp_holdz[i]
                    self.grasp_hold = 0.
                else:
                    self.grasp_hold_type = 0
                    self.grasp_hold = grasp_holdz[i]

        small_rew_opts = [.1, .3, .5]
        for i, val in enumerate(rew_in['small_rew']):
            if val:
                small_rew = small_rew_opts[i]

        big_rew_opts = [.3, .5, .7]
        for i, val in enumerate(rew_in['big_rew']):
            if val:
                big_rew = big_rew_opts[i]

        if np.logical_or(rew_in['rew_start'], rew_in['rew_start_and_grasp']):
            self.reward_for_start = [True, small_rew]
        else:
            self.reward_for_start = [False, 0]

        if np.logical_or(rew_in['rew_grasp'], rew_in['rew_start_and_grasp']):
            self.reward_for_grasp = [True, big_rew]
        else:
            self.reward_for_grasp = [False, 0]

        if rew_in['snd_only']:
            self.reward_for_grasp = [True, 0.]
            self.reward_for_start = [True, 0.]
            self.skip_juice = True
        else:
            self.skip_juice = False

        for i, (nm, val) in enumerate(animal_names_dict.items()):
            if val:
                animal_name = nm

        try:
            pygame.mixer.init()    
        except:
            pass

        reward_var_opt = [1.0, .5, .33]
        for i, val in enumerate(rew_var['rew_var']):
            if val:
                self.percent_of_trials_rewarded = reward_var_opt[i]
                if self.percent_of_trials_rewarded == 0.33:
                    self.percent_of_trials_doubled = 0.1
                else:
                    self.percent_of_trials_doubled = 0.0
        
        self.reward_generator = self.gen_rewards(self.percent_of_trials_rewarded, self.percent_of_trials_doubled,
            self.reward_for_grasp)

        self.reward_delay_time = 0. #reward_delay_opts[i]

        test_vals = [True, False, False]
        for i, val in enumerate(test['test']):
            if val:
                self.testing = test_vals[i]
        
        autoquit_trls = [25, 50, 10**10]
        for i, val in enumerate(autoquit['autoquit']):
            if val: 
                self.max_trials = autoquit_trls[i]

        start = [True, False]
        for i, val in enumerate(use_start['start']):
            if val:
                self.use_start = start[i]
        for i, val in enumerate(only_start['start']):
            if val:
                self.only_start = start[i]

        grasp_tos = [5., 10., 999999999.]

        for i, val in enumerate(grasp_to['gto']):
            if val:
                self.grasp_timeout_time = grasp_tos[i]

        # Preload reward buttons: 
        self.reward1 = SoundLoader.load('reward1.wav')
        self.reward2 = SoundLoader.load('reward2.wav')

        self.state = 'ITI'
        self.state_start = time.time()
        self.ITI = np.random.random()*self.ITI_std + self.ITI_mean

        self.start_led = 0
        self.button = 0
        self.cap_button = 0.

        # State transition matrix: 
        self.FSM = dict()
        self.FSM['ITI'] = dict(end_ITI='vid_trig', stop=None)
        self.FSM['vid_trig'] = dict(end_vid_trig='start_button')
        self.FSM['start_button'] = dict(pushed_start='start_hold', start_button_timeout='ITI', stop=None)
        self.FSM['start_hold'] = dict(end_start_hold='grasp_trial_start', start_early_release = 'start_button', stop=None)
        self.FSM['grasp_trial_start'] = dict(clear_LED='grasp_hold', grasp_timeout='ITI', stop=None)
        self.FSM['grasp_hold'] = dict(end_grasp_hold='reward', drop='grasp', grasp_timeout='ITI', stop=None)
        self.FSM['grasp'] = dict(clear_LED='grasp_hold', grasp_timeout='ITI', stop=None) # state to indictate 'grasp' w/o resetting timer
        self.FSM['reward'] = dict(end_reward='ITI', stop=None)
        self.FSM['idle_exit'] = dict(stop=None)
        if not self.use_start:
            self.FSM['ITI'] = dict(end_ITI='grasp_trial_start', stop=None)

        if self.only_start:
            self.FSM = dict()
            self.FSM['ITI'] = dict(end_ITI='start_button', stop=None)
            self.FSM['start_button'] = dict(pushed_start='start_hold', start_button_timeout='ITI', stop=None)
            self.FSM['start_hold'] = dict(end_start_hold='reward', start_early_release = 'start_button', stop=None)
            self.FSM['reward'] = dict(end_reward='ITI', stop=None)

        try:
            self.reward_port = serial.Serial(port='COM4',
                baudrate=115200)
            self.reward_port.close()
            reward_fcn = True
        except:
            reward_fcn = False
            pass

        try:
            self.dio_port = serial.Serial(port='COM7', baudrate=115200)
            time.sleep(4.)
        except:
            pass

        try:
            self.cam_trig_port = serial.Serial(port='COM6', baudrate=9600)
            time.sleep(3.)
            # Say hello: 
            self.cam_trig_port.write('a'.encode())

            # Pause
            time.sleep(1.)

            # Start cams @ 50 Hz
            self.cam_trig_port.write('1'.encode())
        except:
            pass

        if self.use_cap_not_button:
            self.cap_ard = serial.Serial(port='', baudrate=9600)

        # save parameters: 
        d = dict(animal_name=animal_name,
            ITI_mean=self.ITI_mean, ITI_std = self.ITI_std, start_hold=self.start_hold,
            grasp_hold = self.grasp_hold, start_timeout = self.start_timeout, 
            grasp_timeout = self.grasp_timeout_time, big_rew=big_rew, 
            small_rew = small_rew, rew_for_start = self.reward_for_start[0], 
            reward_for_grasp = self.reward_for_grasp[0], skip_juice=self.skip_juice,
            rew_delay = self.reward_delay_time, use_start = self.use_start, 
            only_start = self.only_start, reward_fcn=reward_fcn, use_cap=self.use_cap_not_button)

        # Open task arduino
        self.task_ard = serial.Serial(port='COM5')

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
            p = path_root+'data/'

            # Check if this directory exists: 
            if os.path.exists(p):
                pass

            else:
                p = path_root+ 'data_tmp_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')+'/'
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

            self.filename = p+ animal_name+'_Grasp_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')
            pickle.dump(d, open(self.filename+'_params.pkl', 'wb'))

            self.h5file = tables.open_file(self.filename + '_data.hdf', mode='w', title = 'NHP data')
            self.h5_table = self.h5file.create_table('/', 'task', Data, '')
            self.h5_table_row = self.h5_table.row

            # Get the task to start the accelerometer process
            # Start the accelerometer: 
            self.acc_process = subprocess.Popen(['python run_acc.py', p + animal_name + '_Grasp'])

            # Note in python 3 to open pkl files: 
            #with open('xxxx_params.pkl', 'rb') as f:
            #    data_params = pickle.load(f)
            self.baseline_force = []
            self.trial_force = []
            self.baseline_done = False

    def gen_rewards(self, perc_trials_rew, perc_trials_2x, reward_for_grasp):
        mini_block = int(2*(np.round(1./self.percent_of_trials_rewarded)))
        rew = []
        mini_block_count = 0
        for i in range(500):
            mini_block_array = np.zeros((mini_block))
            ix = np.random.permutation(mini_block)
            mini_block_array[ix[:2]] = reward_for_grasp[1]
            mini_block_count += mini_block
            if (perc_trials_2x * perc_trials_rew) > 0:
                if mini_block_count > int(1./(perc_trials_2x*perc_trials_rew)):
                    mini_block_array[ix[0]] = 2*reward_for_grasp[1]
                    mini_block_count = 0
            rew.append(mini_block_array)
        return np.hstack((rew))

    def close_app(self):
        try:
            self.cam_trig_port.write('0'.encode())
        except:
            pass

        # Stop the accelerometer: 
        self.acc_process.send_signal(signal.CTRL_C_EVENT)

        # Turn off LED when cloisng : 
        self.task_ard.flushInput()
        self.task_ard.write('n'.encode()) #morn
        
        if self.idle:
            self.state = 'idle_exit'
            self.trial_counter = -1

            # Set relevant params text: 
            self.grasp_rew_txt = 'Grasp Rew Time: '
            self.grasp_rew_param = str(self.reward_for_grasp[1])

            self.button_rew_txt = 'Button Rew Time: '
            self.button_rew_param = str(self.reward_for_start[1])


            self.grasp_hold_txt = 'Grasp Hold Time: '
            if type(self.grasp_hold_type) is str:
                self.grasp_hold_param = self.grasp_hold_type
            else:
                self.grasp_hold_param = str(self.grasp_hold)
                
            self.button_hold_txt = 'Button Hold Time: '
            if type(self.start_hold_type) is str:
                self.button_hold_param = self.start_hold_type
            else:
                self.button_hold_param = str(self.start_hold)

            self.n_trials_txt = '# Trials: '
            self.n_trials_param = str(self.big_reward_cnt)
        else:
            App.get_running_app().stop()
            Window.close()

    def quit_from_app(self):
        # If second click: 

        if self.idle:
            self.idle = False

        # If first click: 
        else:
            self.idle = True

        self.close_app()

    def update(self, ts):
        self.state_length = time.time() - self.state_start
        
        # Read from task arduino: 
        ser = self.task_ard.flushInput()
        _ = self.task_ard.readline()
        port_read = self.task_ard.readline()
        port_splits = port_read.decode('ascii').split('/t')
        #print(port_splits)
        #print(self.state)
        if len(port_splits) != 4:
            ser = self.task_ard.flushInput()
            _ = self.task_ard.readline()
            port_read = self.task_ard.readline()
            port_splits = port_read.decode('ascii').split('/t')            
        self.force = int(port_splits[0])
        self.beam = int(port_splits[1])
        self.button = int(port_splits[2])

        if self.use_cap_not_button:
            tmp = self.cap_ard.flushInput()
            _ = self.cap_ard.readline()
            tmp_read = self.cap_ard.readline()
            if tmp_read == 'C5':
                self.cap_button = 1.
            elif tmp_read = ='N5':
                self.cap_button = 0.
        
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
                    self.prev_state = self.state
                    self.state = next_state
                    self.state_start = time.time()

                    # Run any starting functions: 
                    start_state_fn_name = "_start_%s" % self.state
                    if hasattr(self, start_state_fn_name):
                        start_state_fn = getattr(self, start_state_fn_name)
                        start_state_fn()
            
        if self.testing:
            pass
        else:
            if self.state == 'idle_exit':
                pass
            else:
                self.write_to_h5file()

    def write_to_h5file(self):
        self.h5_table_row['state']= self.state
        self.h5_table_row['time'] = time.time() - self.t0
        self.h5_table_row['time_abs'] = time.time()
        self.h5_table_row['force'] = self.force
        self.h5_table_row['beam'] = self.beam
        self.h5_table_row['start_button'] = self.button
        self.h5_table_row.append()

        if self.baseline_done:
            if 'grasp' in self.state:
                self.trial_force.append(self.force)
        else:
            self.baseline_force.append(self.force)
            

        # Write DIO 
        try:
            self.write_row_to_dio()
        except:
            pass
            
        # Upgrade table row: 
        self.h5_table_row_cnt += 1

    def write_row_to_dio(self):
        ### FROM TDT TABLE, 5 is GND, BYTE A #
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
            return False

    def _start_ITI(self, **kwargs):
        # Stop video
        self.cam_trig_port.write('0'.encode())
        self.ITI = np.random.random()*self.ITI_std + self.ITI_mean
        
        if type(self.start_hold_type) is str:
            cht_min, cht_max = self.start_hold_type.split('-')
            self.start_hold = ((float(cht_max) - float(cht_min)) * np.random.random()) + float(cht_min)

        if type(self.grasp_hold_type) is str:
            tht_min, tht_max = self.grasp_hold_type.split('-')
            self.grasp_hold = ((float(tht_max) - float(tht_min)) * np.random.random()) + float(tht_min) 

        if self.baseline_done:
            self.trial_force = np.array(self.trial_force)
            print('thresh: ')
            print(self.baseline_thresh)
            print('trial: ')
            print(self.trial_force)
            ix = np.nonzero(self.trial_force > self.baseline_thresh)[0]
            if len(ix) > 0:
                self.tried += 1


    def _start_grasp_trial_start(self, **kwargs):
        self.start_grasp = time.time(); 

        if self.baseline_done:
            self.trial_force = []
        else:
            print(' computing baseline force ')
            self.baseline_thresh = np.mean(self.baseline_force) + 5*np.std(self.baseline_force)
            print('mean: ')
            print(np.mean(self.baseline_force))
            print('std: ')
            print(np.std(self.baseline_force))
            self.baseline_done = True

    def end_ITI(self, **kwargs):
        return kwargs['ts'] > self.ITI

    def _start_vid_trig(self, **kwargs):
        self.cam_trig_port.write('1'.encode())

    def end_vid_trig(self, **kwargs):
        return kwargs['ts'] > self.pre_start_vid_ts

    def _start_start_button(self, **kwargs):
        self.task_ard.flushInput()
        self.task_ard.write('m'.encode()) #morning

    def pushed_start(self, **kwargs):
        if self.use_cap_not_button:
            return self.cap_button
        else:
            return self.button


    def start_button_timeout(self, **kwargs):
        return kwargs['ts'] > self.start_timeout

    def end_start_hold(self, **kwargs):
        if kwargs['ts'] > self.start_hold:
            #if self.reward_for_start[0]:
            self.task_ard.flushInput()
            self.task_ard.write('n'.encode()) #night
            self._start_rew_start()
            
            return True
        else:
            return False

    def start_early_release(self, **kwargs):
        but = self.button
        if self.use_cap_not_button:
            but = self.cap_button
        if but == 0:
            if kwargs['ts'] < self.start_hold:
                return True
        return False

    def clear_LED(self, **kwargs):
    	if self.beam == 0:
    		return True
    	else:
    		return False

    def grasp_timeout(self, **kwargs):
        return (time.time() - self.start_grasp) > self.grasp_timeout_time

    def end_grasp_hold(self, **kwargs):
        return kwargs['ts'] > self.grasp_hold

    def drop(self, **kwargs):
        if self.beam == 1:
        	return True
        else:
        	return False

    def _start_reward(self, **kwargs):
        try:
            self.reward1.play()
            if self.reward_for_grasp[0]:
                #winsound.PlaySound('beep1.wav', winsound.SND_ASYNC)
                #sound = SoundLoader.load('reward1.wav')
                print('in reward: ')
                if not self.skip_juice:
                    if self.reward_generator[self.trial_counter] > 0:
                        self.reward_port.open()
                        rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_generator[self.trial_counter])+' sec\n']
                        self.reward_port.write(rew_str)
                        time.sleep(.5 + self.reward_delay_time)
                        run_str = [ord(r) for r in 'run\n']
                        self.reward_port.write(run_str)
                        self.reward_port.close()
        except:
            pass

        self.trial_counter += 1
        self.big_reward_cnt += 1
        
    def _start_rew_start(self, **kwargs):
        self.small_reward_cnt += 1

        try:
            #if self.reward_for_start[0]:
                #sound = SoundLoader.load('reward2.wav')
                #sound.play()
            self.reward2.play()
            if self.reward_for_start[1] > 0.:
                
                self.reward_port.open()
                rew_str = [ord(r) for r in 'inf 50 ml/min '+str(self.reward_for_start[1])+' sec\n']
                self.reward_port.write(rew_str)
                time.sleep(.5)
                run_str = [ord(r) for r in 'run\n']
                self.reward_port.write(run_str)
                self.reward_port.close()
        except:
            pass

    def end_reward(self, **kwargs):
        return True

class Manager(ScreenManager):
    pass

class R2GApp(App):
    def build(self, **kwargs):
        from win32api import GetSystemMetrics
        screenx = GetSystemMetrics(0)
        screeny = GetSystemMetrics(1)
        Window.size = (1800, 1000)
        Window.left = (screenx - 1800)/2
        Window.top = (screeny - 1000)/2
        return Manager()
        
if __name__ == '__main__':
    R2GApp().run()