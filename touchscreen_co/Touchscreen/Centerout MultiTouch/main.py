from kivy.app import App
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.config import Config
import serial, time, pickle, datetime
# to install -- pyserial, pygame, 

Config.set('graphics', 'resizable', False)

fixed_window_size = (1800, 1000)
pix_per_cm = 40.

Config.set('graphics', 'width', str(fixed_windowf_size[0]))
Config.set('graphics', 'height', str(fixed_window_size[1]))

import time
import numpy as np

class COGame(Widget):
    center = ObjectProperty(None)
    target = ObjectProperty(None)

    ITI_mean = 1.
    ITI_std = .2
    center_target_rad = 2.
    periph_target_rad = 2.

    exit_pos = np.array([8, 8])
    exit_rad = 1.
    exit_hold = 5 #seconds

    ch_timeout = 10. # ch timeout
    cht = .2 # center hold time

    target_timeout_time = 10.
    tht = .2

    cursor = {}
    cursor_ids = []

    reward_time = 1.
    touch_error_timeout = 0.
    timeout_error_timeout = 0.
    hold_error_timeout = 0.
    drag_error_timeout = 0.

    ntargets = 4.
    target_distance = 8.
    touch = False

    center_target = ObjectProperty(None)
    periph_target = ObjectProperty(None)

    done_init = False

    def on_touch_down(self, touch):
        #handle many touchs:
        ud = touch.ud

        # Add new touch to ids: 
        self.cursor_ids.append(touch.uid)

        # Add cursor
        self.cursor[touch.uid] =  pix2cm(np.array([touch.x, touch.y]))

        # set self.touch to True
        self.touch = True

    def on_touch_move(self, touch):
        self.cursor[touch.uid] = pix2cm(np.array([touch.x, touch.y]))
        self.touch = True

    def on_touch_up(self, touch):
        self.cursor_ids.remove(touch.uid)
        _ = self.cursor.pop(touch.uid)

    def init(self, animal_names_dict):

        for i, (nm, val) in enumerate(animal_names_dict.items()):
            if val:
                animal_name = nm

        try:
            pygame.mixer.init()    
        except:
            pass

        self.state = 'ITI'
        self.state_start = time.time()
        self.ITI = np.random.random()*self.ITI_std + self.ITI_mean

        # Initialize targets: 
        self.center_target.set_size(2*self.center_target_rad)
        self.center_target.move(np.array([0., 0.]))
        self.periph_target.set_size(2*self.periph_target_rad)

        self.exit_target1.set_size(2*self.exit_rad)
        self.exit_target2.set_size(2*self.exit_rad)
        self.exit_target1.move(self.exit_pos)
        self.exit_pos2 = np.array([-1*self.exit_pos[0], self.exit_pos[1]])
        self.exit_target2.move(self.exit_pos2)
        self.exit_target1.color = (.15, .15, .15, .15)
        self.exit_target2.color = (.15, .15, .15, .15)
        self.prev_exit = [0, 0]
        self.prev_exit_ts = [0, 0]

        self.target_list = self.get_targets(self.ntargets, self.target_distance)
        self.target_index = 0
        self.repeat = False
        self.center_target_position = np.array([0., 0.])
        self.periph_target_position = self.target_list[self.target_index, :]

        self.FSM = dict()
        self.FSM['ITI'] = dict(end_ITI='center', stop=None)
        self.FSM['center'] = dict(touch_center='center_hold', center_timeout='timeout_error', stop=None) #touch_not_center='touch_error')
        self.FSM['center_hold'] = dict(finish_center_hold='target', early_leave_center_hold='hold_error', 
            center_drag_out = 'drag_error', stop=None)
        self.FSM['target'] = dict(touch_target = 'targ_hold', target_timeout='timeout_error', stop=None)#,touch_not_target='touch_error')
        self.FSM['targ_hold'] = dict(finish_targ_hold='reward', early_leave_target_hold = 'hold_error',
         targ_drag_out = 'drag_error', stop=None)
        self.FSM['reward'] = dict(end_reward = 'ITI', stop=None)
        self.FSM['touch_error'] = dict(end_touch_error='center', stop=None)
        self.FSM['timeout_error'] = dict(end_timeout_error='center', stop=None)
        self.FSM['hold_error'] = dict(end_hold_error='center', stop=None)
        self.FSM['drag_error'] = dict(end_drag_error='center', stop=None)

        try:
            self.reward_port = serial.Serial(port='/dev/tty.usbserial-A8008Jh',
                baudrate=115200)
            self.reward_port.close()
        except:
            pass

        # save parameters: 
        d = dict(animal_name=animal_name, center_target_rad=self.center_target_rad,
            periph_target_rad=self.periph_target_rad, target_list = self.target_list, 
            ITI_mean=self.ITI_mean, ITI_std = self.ITI_std, ch_timeout=self.ch_timeout, 
            cht=self.cht, reward_time=self.reward_time, 
            touch_error_timeout = self.touch_error_timeout,
            timeout_error_timeout = self.timeout_error_timeout,
            hold_error_timeout = self.hold_error_timeout,
            drag_error_timeout = self.drag_error_timeout,
            ntargets = self.ntargets,
            target_distance = self.target_distance,
            start_time = datetime.datetime.now().strftime('%Y%m%d_%H%M'))

        try:
            pickle.dump(d, open('C:/Users/scientist/Documents/Preeya/data/'+animal_name+'_'+datetime.datetime.now().strftime('%Y%m%d_%H%M')+'params.pkl', 'wb'))
        except:
            pass

    def close_app(self):
        # Save Data Eventually

        App.get_running_app().stop()
        Window.close()

    def update(self, ts):
        self.state_length = time.time() - self.state_start
        
        # Run task update functions: 
        for f, (fcn_test_name, next_state) in enumerate(self.FSM[self.state].items()):
            kw = dict(ts=self.state_length)
            
            fcn_test = getattr(self, fcn_test_name)
            if fcn_test(**kw):
                # if stop: close the app
                if fcn_test_name == 'stop':
                    self.close_app()

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

    def stop(self, **kwargs):
        e = [0, 0]
        e[0] = self.check_if_cursors_in_targ(self.exit_pos, self.exit_rad)
        e[1] = self.check_if_cursors_in_targ(self.exit_pos2, self.exit_rad)
        t = [0, 0]
        for i in range(2):
            if self.prev_exit[i] and e[i]:
                t[i] = time.time() - self.prev_exit_ts

            if not self.prev_exit[i] and e[i]:
                self.prev_exit_ts[i] = time.time()
                t[i] = 0

            else:
                t[i] = 0

        if t[0] > self.exit_hold and t[1] > self.exit_hold:
            return True

    def _start_ITI(self, **kwargs):
        self.ITI = np.random.random()*self.ITI_std + self.ITI_mean
        self.center_target.color = (0., 0., 0., 0.)
        self.periph_target.color = (0., 0., 0., 0.)

    def end_ITI(self, **kwargs):
        return kwargs['ts'] > self.ITI

    def _start_center(self, **kwargs):
        self.center_target.color = (1., 0., 0., 1.)

    def _start_center_hold(self, **kwargs):
        self.center_target.color = (1., 1., 0., 1.)

    def _start_targ_hold(self, **kwargs):
        self.periph_target.color = (1., 1., 0., 1.)

    def _end_center_hold(self, **kwargs):
        self.center_target.color = (0., 0., 0., 1.)

    def _end_target_hold(self, **kwargs):
        self.periph_target.color = (0., 0., 0., 1.)

    def _start_touch_error(self, **kwargs):
        self.center_target.color = (0., 0., 0., 1.)
        self.periph_target.color = (0., 0., 0., 1.)
        self.repeat = True

    def _start_timeout_error(self, **kwargs):
        self.center_target.color = (0., 0., 0., 1.)
        self.periph_target.color = (0., 0., 0., 1.)
        self.repeat = True

    def _start_hold_error(self, **kwargs):
        self.center_target.color = (0., 0., 0., 1.)
        self.periph_target.color = (0., 0., 0., 1.)
        self.repeat = True

    def _start_drag_error(self, **kwargs):
        self.center_target.color = (0., 0., 0., 1.)
        self.periph_target.color = (0., 0., 0., 1.)
        self.repeat = True

    def _start_target(self, **kwargs):
        self.center_target.color = (0., 0., 0., 0.)

        if self.repeat is False:
            self.periph_target_position = self.target_list[self.target_index, :]
            self.target_index += 1

        self.periph_target.move(self.periph_target_position)
        self.periph_target.color = (1., 0., 0., 1.)
        self.repeat = False

    def _start_reward(self, **kwargs):
        self.periph_target.color = (0., 1., 0., 1.)
        
        try:
            self.reward_port.open()
            self.reward_port.write('inf 25 ml/min .8 sec\n')
            time.sleep(.5)
            self.reward_port.write('run\n')
            self.reward_port.close()
        except:
            pass
        
        try:
            pygame.mixer.music.load('reward_beep.wav')
            pygame.mixer.music.play()
        except:
            pass

    def end_reward(self, **kwargs):
        try:
            return not pygame.mixer.music.get_busy()
        except:
            return True

    def end_touch_error(self, **kwargs):
        return kwargs['ts'] >= self.touch_error_timeout

    def end_timeout_error(self, **kwargs):
        return kwargs['ts'] >= self.timeout_error_timeout

    def end_hold_error(self, **kwargs):
        return kwargs['ts'] >= self.hold_error_timeout

    def end_drag_error(self, **kwargs):
        return kwargs['ts'] >= self.drag_error_timeout

    def touch_center(self, **kwargs):
        return self.check_if_cursors_in_targ(self.center_target_position, self.center_target_rad)

    def center_timeout(self, **kwargs):
        return kwargs['ts'] > self.ch_timeout

    def finish_center_hold(self, **kwargs):
        return self.cht <= kwargs['ts']

    def early_leave_center_hold(self, **kwargs):
        return not self.check_if_cursors_in_targ(self.center_target_position, self.center_target_rad)
        
    def center_drag_out(self, **kwargs):
        touch = self.touch
        self.touch = True
        stay_in = self.check_if_cursors_in_targ(self.center_target_position, self.center_target_rad)
        self.touch = touch
        return not stay_in

    def touch_target(self, **kwargs):
        return self.check_if_cursors_in_targ(self.periph_target_position, self.periph_target_rad)

    def target_timeout(self, **kwargs):
        return kwargs['ts'] > self.target_timeout_time

    def finish_targ_hold(self, **kwargs):
        return self.tht <= kwargs['ts']

    def early_leave_target_hold(self, **kwargs):
        return not self.check_if_cursors_in_targ(self.periph_target_position, self.periph_target_rad)

    def targ_drag_out(self, **kwargs):

        touch = self.touch
        self.touch = True
        stay_in = self.check_if_cursors_in_targ(self.periph_target_position, self.periph_target_rad)
        self.touch = touch
        return not stay_in

    def get_targets(self, ntargets, target_distance):
        # Targets in CM: 
        angle = np.linspace(0, 2*np.pi, ntargets+1)[:-1]
        x = np.cos(angle)*target_distance
        y = np.sin(angle)*target_distance
        tmp = np.hstack((x[:, np.newaxis], y[:, np.newaxis]))

        tgs = []
        for blks in range(100):
            ix = np.random.permutation(tmp.shape[0])
            tgs.append(tmp[ix, :])
        return np.vstack((tgs))

    def check_if_cursors_in_targ(self, targ_center, targ_rad):
        if self.touch:
            inTarg = False
            for id_ in self.cursor_ids:
                if np.linalg.norm(np.array(self.cursor[id_]) - targ_center) < targ_rad:
                    inTarg = True
            return inTarg
        else:
            return False

# class COGamesScreen(Screen):
#     def __init__(self, **kwargs):
#         super(COGamesScreen, self).__init__(**kwargs)
#         self.game = COGame()
#         self.add_widget(self.game)
#         Clock.schedule_interval(self.game.update, 1.0 / 60.0)

class Target(Widget):
    
    color = ListProperty([0., 0., 0., 1.])

    def set_size(self, size):
        size_pix = [cm2pix(size), cm2pix(size)]
        self.size=size_pix

    def move(self, pos):
        pos_pix = cm2pix(pos).astype(int)
        pos_pix_int = tuple((int(pos_pix[0]), int(pos_pix[1])))
        self.center = pos_pix_int

class Manager(ScreenManager):
    pass

class COApp(App):
    def build(self, **kwargs):
        return Manager()


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

if __name__ == '__main__':
    COApp().run()
