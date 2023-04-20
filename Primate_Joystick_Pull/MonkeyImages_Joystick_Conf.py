"""
    Sound effects obtained from https://www.zapsplat.com
    """
# For keypad controls, search "def KeyPress"

from typing import List, Tuple, Optional, Literal, Dict, Any
import os
import os.path
import sys
import logging
import traceback
from contextlib import ExitStack
from itertools import groupby
import random
import statistics
import csv
import json
from pathlib import Path
import time
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pprint import pprint

try:
    import winsound
except ImportError:
    winsound = None # type: ignore

import tkinter as tk
from tkinter import filedialog

import behavioral_classifiers

from game_frame import GameFrame, InfoView, screenshot_widgets, screenshot_widget
from photodiode import PhotoDiode
from gen_templates import gen_templates_main
from config import GameConfig

logger = logging.getLogger(__name__)

debug = logger.debug

def sgroup(data, key):
    return groupby(sorted(data, key=key), key=key)

def get_config_path() -> Path:
    if 'config_path' in os.environ:
        return Path(os.environ['config_path'])
    else:
        prompt_root = tk.Tk()
        config_path = filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("csv files","*.csv")))
        prompt_root.withdraw()
        del prompt_root
        return Path(config_path)

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

class MonkeyImages:
    def __init__(self, parent):
        self._stack = ExitStack()
        
        test_config = 'test' in sys.argv or 'tc' in sys.argv
        no_wait_for_start = 'nw' in sys.argv
        use_hardware = 'test' not in sys.argv and 'nohw' not in sys.argv
        
        show_info_view = 'noinfo' not in sys.argv
        hide_buttons = 'nobtn' in sys.argv
        layout_debug = 'layout_debug' in sys.argv
        
        self.classifier_dbg = 'clsdbg' in sys.argv
        
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
        
        if use_hardware:
            from plexon import Plexon
            self.plexon: Optional[Plexon] = Plexon()
        else:
            self.plexon = None
        
        self.joystick_pull_threshold = 4
        
        self.auto_water_reward_enabled = True
        
        if test_config and 'config_path' not in os.environ:
            self.config_path = 'dev_config.csv'
        else:
            self.config_path = get_config_path()
        print(self.config_path)
        
        self.config: GameConfig
        self.load_config() # set self.config
        self.ensure_log_file_creatable()
        
        self.Area1_right_pres = False   # Home Area
        # self.Area2_right_pres = False   # Joystick Area
        # self.Area1_left_pres = False    # Home Area
        # self.Area2_left_pres = False    # Joystick Area
        self.ImageReward = True        # Default Image Reward set to True
        
        # set to the selected image key at the start of the trial for use in classification event log
        self._classifier_event_type: Optional[str] = None
        
        self._current_photodiode_value: Optional[float] = None
        self._photodiode = PhotoDiode()
        if self.config.photodiode_range is not None:
            pmin, pmax = self.config.photodiode_range
            self._photodiode.set_range(pmin, pmax)
        
        self.classifier_events_path = self.config.save_path / f"{self.config.log_file_name_base}_classifier_events.json.bz2"
        self.template_out_path = self.config.save_path / f"{self.config.log_file_name_base}_templates.json"
        
        # save log files must be added to the stack first so the classifier events
        # file will be closed before template generation is attempted
        self._stack.callback(self.save_log_files)
        
        self._cl_helper = self._stack.enter_context(behavioral_classifiers.helpers.Helper(
            config = self.config.classifier_config(),
            events_file_path = self.classifier_events_path,
        ))
        
        print("ready for plexon:" , bool(self.plexon))
        self.root = parent
        self.root.wm_title("MonkeyImages")
        
        game_frame = GameFrame(self.root, layout_debug=layout_debug, hide_buttons=hide_buttons)
        self.game_frame = game_frame
        
        btn = game_frame.add_button
        
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
        
        btn("Reload Config", self.load_config)
        
        self.root.bind('<Key>', lambda a : self.KeyPress(a))
        
        if show_info_view:
            self.info_view = InfoView(self.root, monkey_images=self)
        else:
            self.info_view = None
        
        if self.plexon is not None:
            if not no_wait_for_start:
                print('Start Plexon Recording now')
                wait_res = self.plexon.wait_for_start()
                self.log_hw('plexon_recording_start', plexon_ts=wait_res['ts'], info={'wait': True})
                print ("Recording start detected.")
        
        if self.classifier_dbg:
            from behavioral_classifiers.helpers.debug_tools import DebugSpikeSource
            self._stack.enter_context(DebugSpikeSource(self._cl_helper))
    
    def __enter__(self):
        pass
    
    def __exit__(self, *exc):
        if self.plexon:
            try:
                self.plexon.water_off()
            except:
                traceback.print_exc()
        self._stack.__exit__(*exc)
    
    def load_config(self):
        self.config = GameConfig(config_path=self.config_path)
        self.log_event('config_loaded', tags=[], info={'config': self.config.raw_config})
    
    def log_event(self, name: str, *, tags: List[str]=[], info=None):
        if info is None:
            info = {}
        human_time = datetime.utcnow().isoformat()
        mono_time = time.perf_counter()
        out = {
            'time_human': human_time,
            'time_m': mono_time,
            'name': name,
            'tags': tags,
            'info': info,
        }
        
        self.event_log.append(out)
    
    def log_hw(self, name, *, sim: bool = False, info=None, plexon_ts: Optional[float] = None):
        tags = ['hw']
        if info is None:
            info = {}
        if sim: # event actually triggered manually via keyboard
            tags.append('hw_simulated')
        if plexon_ts is not None:
            info['plexon_ts'] = plexon_ts
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
        self.last_new_loop_time = time.perf_counter()
        self.new_loop_iter = self.new_loop_gen()
        self.normalized_time = 0
        next(self.new_loop_iter)
        self.game_frame.after(self.cb_delay_ms, self.progress_new_loop)
    
    def progress_new_loop(self):
        if self.stopped:
            return
        
        cur_time = time.perf_counter()
        elapsed_time = cur_time - self.last_new_loop_time
        self.last_new_loop_time = cur_time
        
        if not self.paused:
            self.normalized_time += elapsed_time
        
        self.new_loop_upkeep()
        
        if not self.paused:
            next(self.new_loop_iter)
        
        self.game_frame.after(self.cb_delay_ms, self.progress_new_loop)
    
    def new_loop_upkeep(self):
        # self.gathering_data_omni()
        if self.plexon:
            self.gathering_data_omni_new()
    
    def new_loop_gen(self):
        if self._photodiode.calibrating:
            cal_res = yield from self._photodiode.run_calibration(self.game_frame.set_marker_level)
            self.log_event("photodiode_calibration", info=cal_res)
        
        completed_trials = 0
        while True:
            if self.config.max_trials is not None and completed_trials >= self.config.max_trials:
                yield
                continue
            yield from self.run_trial()
            completed_trials += 1
            if self.config.max_trials is not None:
                print(f"trial {completed_trials}/{self.config.max_trials} complete")
    
    def run_trial(self):
        with ExitStack() as trial_stack:
            trial_stack.callback(lambda: self.game_frame.set_marker_level(0))
            discrim_delay = random.uniform(*self.config.discrim_delay_range)
            go_cue_delay = random.uniform(*self.config.go_cue_delay_range)
            
            # choose image
            selected_image_key = random.choice(self.config.image_selection_list)
            self._classifier_event_type = selected_image_key
            
            self._cl_helper.trial_start()
            
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
                'task_type': self.config.task_type,
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
                    
                    if trial_t() > self.config.InterTrialTime and in_zone():
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
                    if trial_t() > self.config.InterTrialTime and in_zone():
                        break
                    yield
            
            # switch to blank to ensure diamond is no longer showing
            if prep_flash:
                self.clear_image()
            
            # if winsound is not None:
            #     winsound.PlaySound(winsound.Beep(100,0), winsound.SND_PURGE) #Purge looping sounds
            
            self.game_frame.set_marker_level(1)
            
            gc_hand_removed_early = False
            # yield from waiter.wait(t=discrim_delay, event='homezone_exit')
            yield from waiter.wait(t=discrim_delay, cond=lambda: not in_zone())
            if waiter.trigger != 'time':
                gc_hand_removed_early = True
            
            # show image
            selected_image = self.config.images[selected_image_key]
            image_i = selected_image['nidaq_event_index']
            
            for cb in in_zone_cbs:
                cb.clear()
            
            if not gc_hand_removed_early:
                self.log_event('discrim_shown', tags=['game_flow'], info={
                    'selected_image': selected_image_key,
                })
                # display image without red box
                self.show_image(selected_image_key)
                self.game_frame.set_marker_level(0.6)
            
            if not gc_hand_removed_early:
                yield from waiter.wait(t=go_cue_delay, cond=lambda: not in_zone())
                if waiter.trigger != 'time':
                    gc_hand_removed_early = True
            
            if gc_hand_removed_early:
                in_zone_at_go_cue = False
            else:
                # display image with box
                self.log_event('go_cue_shown', tags=['game_flow'], info={
                    'selected_image': selected_image_key,
                })
                self.show_image(selected_image_key, boxed=True)
                self.game_frame.set_marker_level(0.2)
                
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
                    if trial_t() - cue_time > self.config.MaxTimeAfterSound:
                        fail_r('joystick not pulled within MaxTimeAfterSound')
                        return None, 0, 0
                    yield
                
                pull_start = trial_t()
                # self.game_frame.set_marker_level(0.2)
                
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
                    if trial_t() - cue_time > self.config.MaxTimeAfterSound:
                        fail_r('hand not removed from home zone within MaxTimeAfterSound')
                        return None, 0, 0
                    yield
                
                exit_time = trial_t()
                exit_delay = exit_time - cue_time
                # self.game_frame.set_marker_level(0.2)
                
                reward_duration = self.ChooseReward(exit_delay, cue=selected_image_key)
                
                if reward_duration is None:
                    fail_r('hand removed after incorrect amount of time')
                
                return reward_duration, 0, exit_delay
            
            def get_classification_info():
                debug("waiting to classify")
                if self.config.classify_wait_mode == 'local':
                    yield from wait(self.config.classify_wait_time)
                elif self.config.classify_wait_mode == 'plexon':
                    assert self.config.classification_event is not None
                    
                    wait_res = yield from self._cl_helper.external_wait(self.config.classify_wait_time, self.config.classify_wait_timeout)
                    if wait_res is None:
                        # if the correct classification event hasn't been received
                        # the classifier will still be using an event from a previous trial
                        # and produce incorrect results
                        return None, 0, 0
                else:
                    raise ValueError(f"Unknown classify wait mode `{self.config.classify_wait_mode}`")
                
                debug("before classify")
                assert self._cl_helper.classifier is not None
                res = self._cl_helper.classifier.classify()
                debug("after classify")
                correct = self._classifier_event_type == res
                
                self.log_event('classification_attempted', tags=[], info={
                    'actual': self._classifier_event_type,
                    'predicted': res,
                    'is_correct': correct,
                })
                
                if correct:
                    return self.config.classify_reward_duration, 0, 0
                else:
                    return None, 0, 0
            
            task_type = self.config.task_type
            if not self.config.baseline:
                reward_duration, remote_pull_duration, pull_duration = yield from get_classification_info()
                action_duration = 0
            elif task_type == 'joystick_pull':
                reward_duration, remote_pull_duration, pull_duration = yield from get_pull_info()
                action_duration = remote_pull_duration
            elif task_type == 'homezone_exit':
                reward_duration, remote_pull_duration, pull_duration = yield from get_homezone_exit_info()
                action_duration = pull_duration
            else:
                assert False, f"invalid task_type {task_type}"
            
            self.game_frame.set_marker_level(0)
            
            self.log_event('task_completed', tags=['game_flow'], info={
                'reward_duration': reward_duration,
                'remote_pull_duration': remote_pull_duration,
                'pull_duration': pull_duration,
                'action_duration': action_duration,
                'success': reward_duration is not None,
                'failure_reason': log_failure_reason[0],
                'discrim': selected_image_key,
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
                if self.config.EnableBlooperNoise:
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
                if self.ImageReward or self.config.EnableBlooperNoise:
                    # 1.20 is the duration of the sound effect
                    yield from wait(1.20)
                if self.config.EnableTimeOut:
                    self.log_event('time_out_shown', tags=['game_flow'], info={
                        'duration': self.config.TimeOut,
                    })
                    self.clear_image()
                    yield from wait(self.config.TimeOut)
            else: # pull suceeded
                if self.ImageReward:
                    self.show_image(selected_image_key, variant='white', boxed=True)
                    self.log_event('image_reward_shown', tags=['game_flow'], info={
                        'selected_image': selected_image_key,
                        'color': 'white',
                    })
                
                if winsound is not None:
                    winsound.PlaySound(
                        str(Path('./TaskSounds/zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_complete_66202.wav')),
                        winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                
                if self.ImageReward:
                    if self.config.post_succesful_pull_delay is not None:
                        yield from wait(self.config.post_succesful_pull_delay)
                    else:
                        # 1.87 is the duration of the sound effect
                        yield from wait(1.87)
                
                if self.auto_water_reward_enabled and reward_duration > 0:
                    self.log_event("water_dispense", tags=['game_flow'], info={'duration': reward_duration})
                    if self.plexon:
                        self.plexon.water_on()
                
                yield from wait(reward_duration)
                
                if self.plexon:
                    self.plexon.water_off()
                
                self.clear_image()
            
            log_entry = {
                'discrim': selected_image_key, # str
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
        self.log_event("manual_water_dispense", tags=[], info={'duration': self.config.manual_reward_time})
        def gen():
            print("water on")
            if self.plexon:
                self.plexon.water_on()
            t = time.perf_counter()
            while time.perf_counter() - t < self.config.manual_reward_time:
                yield
            print("water off")
            if self.plexon:
                self.plexon.water_off()
        
        loop_iter = gen()
        def inner():
            try:
                next(loop_iter)
            except StopIteration:
                pass
            else:
                self.game_frame.after(self.cb_delay_ms, inner)
        
        inner()
    
    def random_duration(self, d_min, d_max) -> float:
        output = round(random.uniform(d_min,d_max),2)
        return output
    
    def ChooseReward(self, duration, cue) -> Optional[float]:
        
        # if self.reward_thresholds is not None:
        for rwd in self.config.reward_thresholds:
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
        if self.plexon:
            self.plexon.water_off()
        
        self.save_log_files(partial=True)
    
    def Unpause(self):
        self.log_event('game_unpause', tags=['game_flow'], info={'was_paused': self.paused})
        self.paused = False
    
    def Stop(self):
        self.log_event('game_stop', tags=['game_flow'], info={'was_stopped': self.stopped})
        self.stopped = True
        self._clear_callbacks()
        
        if self.plexon:
            self.plexon.water_off()
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
            if self.info_view is not None:
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
                self.dbg_classification_event('homezone_enter')
            else:
                self._trigger_event('homezone_exit')
                self.log_hw('zone_exit', sim=True, info={'simulated_zone': 'homezone'})
                self.dbg_classification_event('homezone_exit')
            print('in zone toggled', self.Area1_right_pres)
        elif key == '2':
            if not self.joystick_pulled:
                self.joystick_pull_remote_ts = time.perf_counter()
                self.joystick_pulled = True
                self.log_hw('joystick_pulled', sim=True)
                self.dbg_classification_event('joystick_pull')
            else:
                self.joystick_release_remote_ts = time.perf_counter()
                self.joystick_pulled = False
                self.log_hw('joystick_released', sim=True)
                self.dbg_classification_event('joystick_released')
            
            print('joystick', self.joystick_pulled)
        elif key == '3':
            if self.joystick_zone_enter is None:
                self.joystick_zone_enter = time.perf_counter()
                self.log_hw('joystick_zone_enter', sim=True)
            elif self.joystick_zone_exit is None:
                self.joystick_zone_exit = time.perf_counter()
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
        
        img = self.config.images[k]['tk'][variant]
        
        canvas_size = self.game_frame.cv1.winfo_width(), self.game_frame.cv1.winfo_height()
        # w = self.images[k]['width']
        # offset = (canvas_size[0] - w) / 2
        offset = (canvas_size[0]) / 2
        
        # h = self.images[k]['height']
        # y_offset = (canvas_size[1] - h) / 2
        y_offset = (canvas_size[1]) / 2
        
        if boxed:
            self.show_image('box', variant=variant, _clear=False)
        
        self.game_frame.cv1.create_image(offset, y_offset, anchor = 'c', image = img)
    
    def clear_image(self):
        self.game_frame.cv1.delete("all")
    
    def handle_classification_event(self, event_class, timestamp):
        if self._classifier_event_type is not None:
            self._cl_helper.event(
                event_type = self._classifier_event_type,
                timestamp = timestamp,
                event_class = event_class,
            )
    
    def dbg_classification_event(self, event_class):
        if self.classifier_dbg:
            self.handle_classification_event(event_class, time.perf_counter())
    
    def gathering_data_omni_new(self):
        # joystick threshold
        js_thresh = self.joystick_pull_threshold
        
        assert self.plexon
        for d in self.plexon.get_data():
            self._cl_helper.any_event(d.ts)
            
            if d.type == d.ANALOG:
                if d.chan == self.config.joystick_channel:
                    if self.joystick_last_state is None:
                        self.joystick_last_state = d.value
                    
                    # joystick has transitioned from not pulled to pulled
                    if self.joystick_last_state < js_thresh and d.value >= js_thresh:
                        self.log_hw('joystick_pulled', plexon_ts=d.ts)
                        self.joystick_pulled = True
                        self.joystick_pull_remote_ts = d.ts
                        
                        self.handle_classification_event('joystick_pull', d.ts)
                    
                    # joystick has transitioned from pulled to not pulled
                    elif self.joystick_last_state >= js_thresh and d.value < js_thresh:
                        self.log_hw('joystick_released', plexon_ts=d.ts)
                        self.joystick_pulled = False
                        self.joystick_release_remote_ts = d.ts
                        
                        self.handle_classification_event('joystick_released', d.ts)
                    
                    self.joystick_last_state = d.value
                elif d.chan == 1: # photodiode
                    self._photodiode.handle_value(d.value, d.ts)
                    if self._photodiode.changed:
                        self.log_hw('photodiode_changed', plexon_ts=d.ts, info={'value': d.value})
            elif d.type == d.SPIKE:
                self._cl_helper.spike(
                    channel = d.chan,
                    unit = d.unit,
                    timestamp = d.ts,
                )
            elif d.type == d.EVENT:
                if d.chan == 14: # enter home zone
                    self.log_hw('homezone_enter', plexon_ts=d.ts)
                    self.Area1_right_pres = True
                    self._trigger_event('homezone_enter')
                    
                    self.handle_classification_event('homezone_enter', d.ts)
                elif d.chan == 11: # enter joystick zone
                    self.log_hw('joystick_zone_enter', plexon_ts=d.ts)
                    if self.joystick_zone_enter is None:
                        self.joystick_zone_enter = d.ts
                    
                    self.handle_classification_event('joystick_zone_enter', d.ts)
                elif d.chan == 12: # exit either zone
                    self.log_hw('zone_exit', plexon_ts=d.ts)
                    if self.Area1_right_pres:
                        self.Area1_right_pres = False
                        self._trigger_event('homezone_exit')
                        
                        self.handle_classification_event('homezone_exit', d.ts)
                    if self.joystick_zone_enter is not None and self.joystick_zone_exit is None:
                        self.joystick_zone_exit = d.ts
                        
                        self.handle_classification_event('joystick_zone_exit', d.ts)
                else:
                    self.log_hw('plexon_event', plexon_ts=d.ts, info={'channel': d.chan})
            elif d.type == d.OTHER_EVENT:
                if d.chan == 1:
                    # not sure what this is but plexon sends them every 10ms or so
                    pass
                elif d.chan == 2:
                    self.log_hw('plexon_recording_start', plexon_ts=d.ts)
                else:
                    self.log_hw('plexon_other_event', plexon_ts=d.ts, info={'channel': d.chan})
    
    def get_log_file_paths(self) -> Tuple[Path, Path]:
        base = self.config.log_file_name_base
        csv_path = Path(self.config.save_path) / f"{base}.csv"
        event_log_path = Path(self.config.save_path) / f"{base}_events.json"
        
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
        if os.environ.get('no_partial') and partial:
            return
        
        base = self.config.log_file_name_base
        if partial:
            partial_dir = Path(self.config.save_path) / "partial"
            partial_dir.mkdir(exist_ok=True)
            gen_time = str(time.perf_counter())
            csv_path = partial_dir / f"{base}_{gen_time}.csv"
            event_log_path = partial_dir / f"{base}_{gen_time}_events.json"
            histo_path = partial_dir / f"{base}_{gen_time}_histogram.png"
        else:
            csv_path, event_log_path = self.get_log_file_paths()
            histo_path = Path(self.config.save_path) / f"{self.config.log_file_name_base}_histogram.png"
        
        out = {
            'events': self.event_log,
        }
        
        with open(event_log_path, 'w') as f:
            json.dump(out, f, indent=2)
        
        with open(csv_path, 'w', newline='\n') as f:
            writer = csv.writer(f)
            
            writer.writerow([
                'trial',
                'discrim',
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
                if self.config.task_type == 'homezone_exit':
                    time_in_homezone = entry['pull_duration']
                    pull_duration = 0
                elif self.config.task_type == 'joystick_pull':
                    time_in_homezone = 0
                    pull_duration = entry['pull_duration']
                else:
                    assert False
                
                writer.writerow([
                    i+1,
                    entry['discrim'],
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
            writer.writerow([])
            
            def get_time_in_game():
                for e in self.event_log:
                    if e['name'] == 'game_start':
                        delta = time.perf_counter() - e['time_m']
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
            
            writer.writerow([])
            writer.writerow(['discrim', 'correct', 'pulls', 'count', 'min', 'max', 'mean', 'stdev'])
            for discrim, dad in end_info['discrim_action_duration'].items():
                writer.writerow([
                    discrim, dad['correct_count'], dad['pull_count'], dad['count'],
                    dad['min'], dad['max'], dad['mean'], dad['stdev'],
                ])
            
            writer.writerow([])
            writer.writerow(['error', 'count', 'percent'])
            for e, ei in end_info['errors'].items():
                writer.writerow([e, ei['count'], ei['percent']])
        
        # self.events_file.generate_templates_at(
        #     self.classifier, self.config.save_path / f"{self.config.log_file_name_base}_templates.json",
        #     event_class = self.config.classification_event,
        # )
        if not partial:
            if not os.environ.get('skip_template_gen'):
                behavioral_classifiers.eucl_classifier.build_templates_from_new_events_file(
                    events_path = self.classifier_events_path,
                    template_path = self.template_out_path,
                    event_class = self.config.classification_event,
                    post_time = self.config.post_time,
                    bin_size = self.config.bin_size,
                    labels = self.config.labels,
                )
        
        # if self.info_view is not None:
        #     screenshot_widgets([*self.info_view.rows, self.info_view.label], histo_path)
    
    def print_histogram(self):
        events = [e for e in self.event_log if e['name'] == 'task_completed']
        
        def get_bin_ranges():
            start = 0
            # end = math.ceil(self.MaxTimeAfterSound)
            end = max(rwd.get('high', 0) for rwd in self.config.reward_thresholds)
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
        
        def get_discrim_durations():
            for discrim, d_events in sgroup(events, lambda x: x['info']['discrim']):
                d_events = list(d_events)
                d_correct = [e for e in d_events if e['info']['success']]
                pull_durations = [
                    e['info']['action_duration']
                    for e in d_events
                ]
                count = len(pull_durations)
                pull_durations = [x for x in pull_durations if x != 0]
                out = {
                    'count': count, # number of times discrim appeared
                    'pull_count': len(pull_durations), # number of pulls in response to discrim
                    'correct_count': len(d_correct),
                    'min': min(pull_durations, default=0),
                    'max': max(pull_durations, default=0),
                    'mean': statistics.mean(pull_durations) if pull_durations else 0,
                    'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
                }
                yield discrim, out
        
        info = {
            'count': n,
            'correct_count': len(correct),
            'percent_correct': perc(correct_n),
            'action_duration': {
                'min': min(pull_durations, default=0),
                'max': max(pull_durations, default=0),
                'mean': statistics.mean(pull_durations) if pull_durations else 0,
                'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
            },
            'discrim_action_duration': dict(get_discrim_durations()),
            'errors': error_info,
        }
        
        return info

def generate_histograms(overwrite=False):
    from gen_histogram import gen_histogram
    
    config_path = get_config_path()
    
    config = GameConfig(config_path=config_path, load_images=False)
    output_dir = config.save_path
    
    for input_path in output_dir.glob('*_events.json'):
        output_path = input_path.parent / f"{input_path.stem}_histogram.png"
        
        if output_path.is_file() and not overwrite:
            continue
        
        gen_histogram(input_path, output_path)

def main():
    FORMAT = "%(levelname)s:%(message)s"
    if os.environ.get('log'):
        # logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
        logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
    else:
        logging.basicConfig(level=logging.WARNING, format=FORMAT)
    
    debug("program start %s", datetime.now())
    
    try:
        cmd = sys.argv[1]
    except IndexError:
        cmd = None
    
    if cmd == 'gen':
        from gen_images import gen_images
        gen_images()
        return
    
    if cmd == 'gen_histograms':
        generate_histograms()
        return
    
    if cmd == 'gen_templates':
        gen_templates_main(sys.argv[2:])
        return
    
    root = tk.Tk()
    root.configure(bg='black', bd=0)
    
    with MonkeyImages(root):
        tk.mainloop()

if __name__ == "__main__":
    main()