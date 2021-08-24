from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.config import Config

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen


class MainScreen(Screen):
    pass

class AnotherScreen(Screen):
    pass

class ScreenManagement(ScreenManager):
    pass

presentation = Builder.load_file("CO.kv")


Config.set('graphics', 'resizable', False)

fixed_window_size = (1800, 1000)
pix_per_cm = 40.

Config.set('graphics', 'width', str(fixed_window_size[0]))
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
        self.cursor_ids.remove(touch.id)
        _ = self.cursor.pop(touch.id)

    def init(self):
        self.state = 'ITI'
        self.state_start = time.time()

        self.ITI = np.random.random()*self.ITI_std + self.ITI_mean

        # Initialize targets: 
        self.center_target.set_size(2*self.center_target_rad)
        self.center_target.move(np.array([0., 0.]))

        self.periph_target.set_size(2*self.periph_target_rad)

        self.target_list = self.get_targets(self.ntargets, self.target_distance)
        self.target_index = 0
        self.repeat = False
        self.center_target_position = np.array([0., 0.])
        self.periph_target_position = self.target_list[self.target_index, :]



        self.FSM = dict()
        self.FSM['ITI'] = dict(end_ITI='center')
        self.FSM['center'] = dict(touch_center='center_hold', center_timeout='timeout_error') #touch_not_center='touch_error')
        self.FSM['center_hold'] = dict(finish_center_hold='target', early_leave_center_hold='hold_error', 
            center_drag_out = 'drag_error')
        
        self.FSM['target'] = dict(touch_target = 'targ_hold', target_timeout='timeout_error')#,touch_not_target='touch_error')

        self.FSM['targ_hold'] = dict(finish_targ_hold='reward', early_leave_target_hold = 'hold_error',
         targ_drag_out = 'drag_error')

        self.FSM['reward'] = dict(end_reward = 'ITI')
        self.FSM['touch_error'] = dict(end_touch_error='center')
        self.FSM['timeout_error'] = dict(end_timeout_error='center')
        self.FSM['hold_error'] = dict(end_hold_error='center')
        self.FSM['drag_error'] = dict(end_drag_error='center')

    def update(self, ts):
        self.state_length = time.time() - self.state_start
        
        # Run task update functions: 
        for f, (fcn_test_name, next_state) in enumerate(self.FSM[self.state].items()):
            kw = dict(ts=self.state_length)
            
            fcn_test = getattr(self, fcn_test_name)
            if fcn_test(**kw):

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

    def end_reward(self, **kwargs):
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

class Target(Widget):
    
    color = ListProperty([0., 0., 0., 1.])

    def set_size(self, size):
        size_pix = [cm2pix(size), cm2pix(size)]
        self.size=size_pix

    def move(self, pos):
        pos_pix = cm2pix(pos).astype(int)
        pos_pix_int = tuple((int(pos_pix[0]), int(pos_pix[1])))
        self.center = pos_pix_int

class COApp(App):
    def build(self):
        game = COGame()
        game.init()
        Clock.schedule_interval(game.update, 1./10.)
        return game

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