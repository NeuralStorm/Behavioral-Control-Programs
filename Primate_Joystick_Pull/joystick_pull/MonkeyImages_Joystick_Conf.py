"""
    Sound effects obtained from https://www.zapsplat.com
    """
# For keypad controls, search "def handle_key_press"

from typing import List, Tuple, Optional, Literal, Dict, Any, Union
import types
import os
import os.path
import sys
import logging
import traceback
from contextlib import ExitStack
import random
from pathlib import Path
import time
from datetime import datetime
from pprint import pprint
import inspect
from uuid import uuid1

try:
    import winsound
except ImportError:
    winsound = None # type: ignore

import tkinter as tk
from tkinter import filedialog

import behavioral_classifiers
from butil import EventFile, Debounce, get_git_info

from .game_frame import GameFrame, InfoView, screenshot_widgets, screenshot_widget
from .photodiode import PhotoDiode
from .config import GameConfig
from .zone import Zone

logger = logging.getLogger(__name__)

debug = logger.debug
def trace(*args, **kwargs):
    return logger.log(5, *args, **kwargs)

SOUND_PATH_BASE = Path(__file__).parent / 'assets/audio'

def get_event_id(evt):
    if evt is None:
        return None
    return evt['id']

class Sentinel:
    """used to check if callbacks have been called"""
    def __init__(self):
        self.triggered: bool = False
        self.event: Optional[Any] = None
    
    def __bool__(self) -> bool:
        return self.triggered
    
    def set(self, evt):
        self.triggered = True
        if self.event is None:
            self.event = evt

def get_config_path() -> Path:
    if 'config_path' in os.environ:
        return Path(os.environ['config_path'])
    else:
        prompt_root = tk.Tk()
        config_path = filedialog.askopenfilename(initialdir = "/",title = "Select file",filetypes = (("all files","*.*"), ("csv files","*.csv")))
        prompt_root.withdraw()
        del prompt_root
        return Path(config_path)

def get_gen_stack(gen, stack=None):
    if stack is None:
        stack = []
    stack.append(gen)
    if gen.gi_yieldfrom is not None:
        if isinstance(gen.gi_yieldfrom, types.GeneratorType):
            get_gen_stack(gen.gi_yieldfrom, stack)
            return stack
    f_locals = gen.gi_frame.f_locals
    if 'gen' in f_locals:
        local_gen = f_locals['gen']
        gen_state = inspect.getgeneratorstate(local_gen)
        # if the generator is suspended it's probably still running
        if gen_state == inspect.GEN_SUSPENDED:
            get_gen_stack(local_gen, stack)
            return stack
    return stack

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
        ability_mode = 'ability' in sys.argv
        if ability_mode:
            use_hardware = True
        
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
        self.joystick_pull_event: Optional[Any] = None
        self.joystick_pull_remote_ts = None
        self.joystick_release_remote_ts = None
        
        # used in gathering_data_omni_new to track changes in joystick position
        self.joystick_debounce = Debounce(threshold=2, high_threshold=4, delay=0.001)
        
        # callbacks triggered by external events
        # Dict[str, Set[Callable[[], None]]]
        self._callbacks = {
            'homezone_enter': set(),
            'homezone_exit': set(),
        }
        
        # event_log currently only holds task_completed events
        # for info view/histogram generation
        self.event_log = []
        
        if use_hardware:
            if ability_mode:
                from .data_bridge import DataBridge
                self.plexon = DataBridge()
            else:
                from .plexon import Plexon
                self.plexon: Optional[Plexon] = Plexon()
        else:
            self.plexon = None
        
        self.auto_water_reward_enabled = True
        
        if test_config and 'config_path' not in os.environ:
            self.config_path = 'dev_config.csv'
        else:
            self.config_path = get_config_path()
        print(self.config_path)
        
        # index of logged events so each can receive a unique id
        self.event_i = 0
        
        # self.new_events_path = self.config.save_path / f"{self.config.log_file_name_base}_new_events.json.gz"
        # self.new_events_file = EventFile(path=self.new_events_path)
        self.new_events_path: Path
        self.new_events_file: EventFile
        self.start_dt = datetime.now()
        
        self.config: GameConfig
        self.load_config(first_load=True) # set self.config
        
        self.zones = [
            Zone('homezone', 14, None),
            Zone('joystick_zone', 11, None),
        ]
        self.zone_by_name = {x.name: x for x in self.zones}
        self.zone_by_chan = {x.chan: x for x in self.zones}
        self.zone_by_exit_chan = {x.exit_chan: x for x in self.zones if x.exit_chan is not None}
        
        self.trial_stack: ExitStack = ExitStack()
        
        # set to the selected image key at the start of the trial for use in classification event log
        self._classifier_event_type: Optional[str] = None
        
        if self.config.photodiode_channel is None:
            self._photodiode: Optional[PhotoDiode] = None
        else:
            self._photodiode = PhotoDiode()
            if self.config.photodiode_range is not None:
                pmin, pmax = self.config.photodiode_range
                self._photodiode.set_range(pmin, pmax)
        
        # tracks the time that the photodiode should turn off at
        self._photodiode_off_time: Optional[float] = None
        
        if self.config.record_events:
            self.classifier_events_path = self.config.save_path / f"{self.config.log_file_name_base}_classifier_events.json.bz2"
        else:
            self.classifier_events_path = None
        # self.template_out_path = self.config.save_path / f"{self.config.log_file_name_base}_templates.json"
        
        self._cl_helper = self._stack.enter_context(behavioral_classifiers.helpers.Helper(
            config = self.config.classifier_config(),
            event_file = self.new_events_file,
            # events_file_path = self.classifier_events_path,
        ))
        
        print("ready for plexon:" , bool(self.plexon))
        self.root = parent
        self.root.wm_title("MonkeyImages")
        
        game_frame = GameFrame(self.root, layout_debug=layout_debug, hide_buttons=hide_buttons)
        game_frame.load_images(self.config.selectable_images)
        self.game_frame = game_frame
        
        # exit cleanly when main window is closed with the X button
        self.root.protocol('WM_DELETE_WINDOW', self.close_application)
        
        btn = game_frame.add_button
        
        btn("Start-'a'", self.start)
        btn("Stop-'f'", self.stop)
        btn("Water Reward-'z'", self.manual_water_dispense)
        
        def water_rw_cb(val):
            def inner():
                self.auto_water_reward_enabled = val
            return inner
        btn("Water Reward\nOn", water_rw_cb(True))
        btn("Water Reward\nOff", water_rw_cb(False))
        
        # btn("Reload Config", self.load_config)
        
        self.root.bind('<Key>', lambda a : self.handle_key_press(a))
        
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
            assert self._cl_helper is not None
            from behavioral_classifiers.helpers.debug_tools import DebugSpikeSource
            self._stack.enter_context(DebugSpikeSource(self._cl_helper))
        
        if not os.environ.get('no_git'):
            try:
                git_info = get_git_info()
            except Exception as e:
                traceback.print_exc()
                git_info = {'error': str(e)}
            self.log_event('git_info', info=git_info)
    
    def __enter__(self):
        pass
    
    def __exit__(self, *exc):
        if self.plexon:
            try:
                self.plexon.water_off()
            except:
                traceback.print_exc()
        self.trial_stack.__exit__(*exc)
        self._stack.__exit__(*exc)
        self.new_events_file.close()
    
    def load_config(self, *, first_load=False):
        self.config = GameConfig(config_path=self.config_path, start_dt = self.start_dt)
        
        new_events_path = self.config.save_path / f"{self.config.log_file_name_base}.json.gz"
        is_opening = True
        if not first_load:
            if self.new_events_path == new_events_path:
                is_opening = False
            else:
                self.new_events_file.close()
        if is_opening:
            self.new_events_path = new_events_path
            self.new_events_file = EventFile(path=self.new_events_path)
        
        self.log_event('config_loaded', tags=[], info={
            'time_utc': datetime.utcnow().isoformat(),
            'config': self.config.to_json_dict(),
            'raw': self.config.raw_config,
        })
    
    def log_event(self, name: str, *, tags: List[str]=[], info=None):
        if info is None:
            info = {}
        # human_time = datetime.utcnow().isoformat()
        mono_time = time.perf_counter()
        out = {
            # 'time_human': human_time,
            'id': self.event_i,
            # 'id': uuid1().hex,
            'time_m': mono_time,
            'name': name,
            'tags': tags,
            'info': info,
        }
        self.event_i += 1
        
        self.new_events_file.write_record(out)
        
        self._trigger_event(name, event=out)
        
        return out
    
    def log_hw(self, name, *, sim: bool = False, info=None, plexon_ts: Optional[float] = None):
        tags = ['hw']
        if info is None:
            info = {}
        if sim: # event actually triggered manually via keyboard
            tags.append('hw_simulated')
        if plexon_ts is not None:
            info['time_ext'] = plexon_ts
        return self.log_event(name, tags=tags, info=info)
    
    def _register_callback(self, event_key, cb):
        # handle callback without a parameter
        sig = inspect.signature(cb)
        if not sig.parameters:
            _cb = cb
            cb = lambda evt: _cb() # type: ignore
        
        if event_key not in self._callbacks:
            self._callbacks[event_key] = set()
        self._callbacks[event_key].add(cb)
        cb_obj = RegisteredCallback(cb, self._clear_callback)
        return cb_obj
    
    def _clear_callback(self, cb):
        for v in self._callbacks.values():
            v.discard(cb)
    
    def _clear_callbacks(self):
        for v in self._callbacks.values():
            v.clear()
    
    def sentinel(self, event_key) -> Sentinel:
        """create a sentinel set by event_key bound to the current trial"""
        sentinel = Sentinel()
        cb = self._register_callback(event_key, sentinel.set)
        self.trial_stack.enter_context(cb)
        return sentinel
    
    # call callbacks registered for event key
    def _trigger_event(self, key, event=None):
        if self.paused:
            return
        if key not in self._callbacks:
            return
        for cb in self._callbacks[key]:
            cb(event)
    
    def flash_marker(self, name=None, *, level=1.0):
        if self._photodiode is None:
            return
        info = {}
        if name is not None:
            info['name'] = name
        if self._photodiode_off_time is not None:
            info['already_on'] = True
        self.log_event('photodiode_expected', info=info)
        self.game_frame.set_marker_level(level)
        # update screen immediately to ensure a consistent marker flash duration
        # update_idletasks won't call the game logic callback, only update drawn geometry
        self.root.update_idletasks()
        self._photodiode_off_time = time.perf_counter() + self.config.photodiode_flash_duration
    
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
        if logger.isEnabledFor(5) and elapsed_time > 0.002:
            inner_gen = get_gen_stack(self.new_loop_iter)[-1]
            file_name = Path(inner_gen.gi_code.co_filename).name
            line_no = inner_gen.gi_frame.f_lineno
            
            trace("callback delay at %s delay %sms to %s:%s",
                round(cur_time, 2), round(elapsed_time*1000, 2), file_name, line_no)
        self.last_new_loop_time = cur_time
        
        if self._photodiode_off_time is not None:
            if cur_time >= self._photodiode_off_time:
                self._photodiode_off_time = None
                self.game_frame.set_marker_level(0)
        
        if not self.paused:
            self.normalized_time += elapsed_time
        
        s = time.perf_counter()
        self.new_loop_upkeep()
        e = time.perf_counter()
        d = e - s
        if d > 0.001:
            trace("upkeep %sms", round(d*1000, 2))
        
        if not self.paused:
            start_line_no = self.new_loop_iter.gi_frame.f_lineno
            s = time.perf_counter()
            next(self.new_loop_iter)
            e = time.perf_counter()
            d = s - e
            if logger.isEnabledFor(5) and d > 0.001:
                inner_gen = get_gen_stack(self.new_loop_iter)[-1]
                file_name = Path(inner_gen.gi_code.co_filename).name
                line_no = inner_gen.gi_frame.f_lineno
                trace("long loop iter %sms | %s:%s -> %s", round(d*1000, 2),
                    file_name, start_line_no, line_no)
        
        self.game_frame.after(self.cb_delay_ms, self.progress_new_loop)
    
    def new_loop_upkeep(self):
        # self.gathering_data_omni()
        if self.plexon:
            self.gathering_data_omni_new()
    
    def new_loop_gen(self):
        if self._photodiode is not None and self._photodiode.calibrating:
            cal_res = yield from self._photodiode.run_calibration(self.game_frame.set_marker_level)
            self.log_event("photodiode_calibration", info=cal_res)
        
        completed_trials = 0
        while True:
            if self.config.max_trials is not None and completed_trials >= self.config.max_trials:
                yield
                continue
            yield from self.run_trial(trial_i=completed_trials)
            completed_trials += 1
            if self.config.max_trials is not None:
                print(f"trial {completed_trials}/{self.config.max_trials} complete")
    
    def show_cues(self, *, pre_discrim_delay: float, pre_go_cue_delay: float, selected_image_key: str):
        local_start = self.normalized_time
        def local_t():
            return self.normalized_time - local_start
        waiter = Waiter(self, local_t)
        
        yield from waiter.wait(t=pre_discrim_delay)
        
        self.log_event('discrim_shown', tags=['game_flow'], info={
            'selected_image': selected_image_key,
        })
        # display image without red box
        self.show_image(selected_image_key, variant='pending')
        self.flash_marker('discrim_shown')
        
        yield from waiter.wait(t=pre_go_cue_delay)
        
        self.log_event('go_cue_shown', tags=['game_flow'], info={
            'selected_image': selected_image_key,
        })
        self.show_image(selected_image_key, variant='pending', boxed=True)
        self.flash_marker('go_cue_shown')
        
        if winsound is not None:
            winsound.PlaySound(
                str(SOUND_PATH_BASE / 'mixkit-unlock-game-notification-253.wav'),
                winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
    
    def run_trial(self, trial_i=0):
        self.trial_stack.close()
        self.trial_stack = ExitStack()
        with ExitStack() as trial_stack:
            def clear_photo_marker():
                self._photodiode_off_time = None
                self.game_frame.set_marker_level(0)
            trial_stack.callback(clear_photo_marker)
            
            discrim_delay = random.uniform(*self.config.discrim_delay_range)
            go_cue_delay = random.uniform(*self.config.go_cue_delay_range)
            
            # choose image
            selected_image_key = random.choice(self.config.image_selection_list)
            self._classifier_event_type = selected_image_key
            
            if self._cl_helper is not None:
                self._cl_helper.trial_start()
            
            # print(self.normalized_time)
            
            # reset state for new trial
            self.joystick_pull_remote_ts = None
            self.joystick_release_remote_ts = None
            
            trial_start = self.normalized_time
            
            def in_zone():
                return self.zone_by_name['homezone'].in_zone
            
            def trial_t():
                return self.normalized_time - trial_start
            
            waiter = Waiter(self, trial_t)
            
            def wait(t: float):
                start_time = trial_t()
                while trial_t() - start_time < t:
                    yield
            
            self.log_event('trial_start', tags=['game_flow'], info={
                'discrim': selected_image_key,
                'discrim_delay': discrim_delay,
                'go_cue_delay': go_cue_delay,
                'task_type': self.config.task_type,
                'trial_index': trial_i,
            })
            
            # if winsound is not None:
            #     winsound.PlaySound(
            #         self.OutOfHomeZoneSound,
            #         winsound.SND_ALIAS + winsound.SND_ASYNC + winsound.SND_NOWAIT + winsound.SND_LOOP
            #     ) #Need to change the tone
            
            prep_flash = False
            
            if prep_flash:
                in_zone_cbs = []
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
                        # only flash the marker if it won't interfere with the discrim marker flash
                        if self.config.discrim_delay_range[0] > self.config.photodiode_flash_duration+0.1:
                            self.flash_marker('prep_diamond')
                        if winsound is not None:
                            winsound.PlaySound(
                                str(SOUND_PATH_BASE / 'mixkit-arcade-bonus-229.wav'),
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
                    if trial_t() > self.config.InterTrialTime and in_zone() and not self.joystick_pulled:
                        break
                    yield
            
            # switch to blank to ensure diamond is no longer showing
            if prep_flash:
                self.clear_image()
            
            joystick_pulled = self.sentinel('joystick_pulled')
            joystick_released = self.sentinel('joystick_released')
            homezone_exited = self.sentinel('homezone_exit')
            
            for cb in in_zone_cbs:
                cb.clear()
            
            gen = self.show_cues(
                pre_discrim_delay = discrim_delay,
                pre_go_cue_delay = go_cue_delay,
                selected_image_key = selected_image_key,
            )
            for _ in gen:
                if homezone_exited:
                    break
                if joystick_pulled:
                    break
                yield
            # delete gen so debugging code knows it's
            # done on early termination
            del gen
            
            cue_time = trial_t()
            
            log_failure_reason = [None]
            def fail_r(s):
                assert log_failure_reason[0] is None
                log_failure_reason[0] = s
            
            def get_pull_info():
                if joystick_pulled: # joystick pulled before prompt
                    fail_r('joystick pulled before cue')
                    return None, 0, 0
                
                if homezone_exited:
                    fail_r('hand removed before cue')
                    return None, 0, 0
                
                # wait up to MaxTimeAfterSound for the joystick to be pulled
                while not joystick_pulled:
                    if trial_t() - cue_time > self.config.MaxTimeAfterSound:
                        fail_r('joystick not pulled within MaxTimeAfterSound')
                        return None, 0, 0
                    yield
                
                pull_start = trial_t()
                
                while not joystick_released:
                    yield
                
                pull_start = joystick_pulled.event
                pull_end = joystick_released.event
                assert pull_start is not None
                assert pull_end is not None
                
                pull_duration = pull_end['time_m'] - pull_start['time_m']
                remote_pull_duration = pull_end['info']['time_ext'] - pull_start['info']['time_ext']
                
                # print(pull_duration, remote_pull_duration)
                reward_duration = self.choose_reward(remote_pull_duration, cue=selected_image_key)
                
                if reward_duration is None:
                    fail_r('joystick pulled for incorrect amount of time')
                
                return reward_duration, remote_pull_duration, pull_duration
            
            def get_homezone_exit_info():
                # hand removed from home zone before cue
                if homezone_exited:
                    fail_r('hand removed before cue')
                    return None, 0, 0
                # if not in_zone_at_go_cue:
                #     fail_r('hand removed from homezone before go cue')
                #     return None, 0, 0
                
                # wait up to MaxTimeAfterSound for the hand to exit the homezone
                while in_zone():
                    if trial_t() - cue_time > self.config.MaxTimeAfterSound:
                        fail_r('hand not removed from home zone within MaxTimeAfterSound')
                        return None, 0, 0
                    yield
                
                exit_time = trial_t()
                exit_delay = exit_time - cue_time
                
                reward_duration = self.choose_reward(exit_delay, cue=selected_image_key)
                
                if reward_duration is None:
                    fail_r('hand removed after incorrect amount of time')
                
                return reward_duration, 0, exit_delay
            
            def get_classification_info():
                debug("waiting to classify")
                assert self._cl_helper is not None
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
                    assert self.config.classify_reward_duration is not None
                    if self._classifier_event_type in self.config.classify_reward_duration:
                        return self.config.classify_reward_duration[self._classifier_event_type], 0, 0
                    else:
                        return self.config.classify_reward_duration[None], 0, 0
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
            
            task_completed_info = {
                'reward_duration': reward_duration, # Optional[float]
                'remote_pull_duration': remote_pull_duration, # float
                'pull_duration': pull_duration, # float
                'action_duration': action_duration, # float
                'js_pull_event': get_event_id(joystick_pulled.event), # Optional[int]
                'js_release_event': get_event_id(joystick_released.event), # Optional[int]
                'homezone_exit_event': get_event_id(homezone_exited.event), # Optional[int]
                'success': reward_duration is not None, # bool
                'failure_reason': log_failure_reason[0], # Optional[str]
                'discrim': selected_image_key, # str
            }
            self.log_event('task_completed', tags=['game_flow'], info=task_completed_info)
            self.event_log.append({
                'time_m': time.perf_counter(),
                'name': 'task_completed',
                'info':task_completed_info,
            })
            
            print('Press Duration: {:.4f} (remote: {:.4f} local: {:.4f})'.format(action_duration, remote_pull_duration, pull_duration))
            print('Reward Duration: {}'.format(reward_duration))
            if log_failure_reason[0]:
                print(log_failure_reason[0])
            try:
                if not os.environ.get('no_print_stats'):
                    InfoView.print_histogram(self.event_log)
                if self.info_view is not None:
                    self.info_view.update_info(self.event_log)
            except:
                traceback.print_exc()
            
            if reward_duration is None: # pull failed
                if self.config.EnableBlooperNoise:
                    if winsound is not None:
                        winsound.PlaySound(
                            str(SOUND_PATH_BASE / 'zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_negative_66204.wav'),
                            winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                
                self.log_event('image_reward_shown', tags=['game_flow'], info={
                    'selected_image': selected_image_key,
                    'variant': 'fail',
                })
                self.show_image(selected_image_key, variant='fail', boxed=True)
                self.flash_marker('punish')
                # 1.20 is the duration of the sound effect
                yield from wait(1.20)
                if self.config.EnableTimeOut:
                    self.log_event('time_out_shown', tags=['game_flow'], info={
                        'duration': self.config.TimeOut,
                    })
                    self.clear_image()
                    yield from wait(self.config.TimeOut)
            else: # pull suceeded
                self.log_event('image_reward_shown', tags=['game_flow'], info={
                    'selected_image': selected_image_key,
                    'variant': 'success',
                })
                self.show_image(selected_image_key, variant='success', boxed=True)
                self.flash_marker('reward')
                
                if winsound is not None:
                    winsound.PlaySound(
                        str(SOUND_PATH_BASE / 'zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_complete_66202.wav'),
                        winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT)
                
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
            
            self.log_event("trial_end", tags=['game_flow'], info={})
            
    
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
    
    def choose_reward(self, duration, cue) -> Optional[float]:
        
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
    
    def start(self):
        already_started = not self.stopped
        self.paused = False
        self.stopped = False
        
        if not already_started:
            self.log_event('game_start', tags=['game_flow'])
            self.start_new_loop()
    
    def stop(self):
        self.log_event('game_stop', tags=['game_flow'], info={'was_stopped': self.stopped})
        self.stopped = True
        self._clear_callbacks()
        
        if self.plexon:
            self.plexon.water_off()
        self.clear_image()
        if winsound is not None:
            winsound.PlaySound(None, winsound.SND_PURGE)
        if not os.environ.get('no_print_stats'):
            pprint(InfoView.calc_end_info(self.event_log))
    
    def handle_key_press(self, event):
        key = event.char
        if key == 'a':
            self.start()
        elif key == 'f':
            self.stop()
        elif key == 'z':
            self.manual_water_dispense()
        elif key == 'p':
            screenshot_widget(self.root, 'test.png')
            if self.info_view is not None:
                screenshot_widget(self.info_view.window, 'test2.png')
                screenshot_widgets(self.info_view.rows, 'test3.png')
        elif key == '`':
            self.close_application()
        elif key == '1':
            zone = self.zone_by_name['homezone']
            if not zone.in_zone:
                zone.enter()
                self.log_hw('homezone_enter', plexon_ts=time.perf_counter(), sim=True)
                self.dbg_classification_event('homezone_enter')
                print('homezone enter')
            else:
                zone.exit()
                # self.log_hw('zone_exit', sim=True, info={'simulated_zone': 'homezone'})
                self.log_hw('homezone_exit', plexon_ts=time.perf_counter(), sim=True, info={'simulated_zone': 'homezone'})
                self.dbg_classification_event('homezone_exit')
                print('homezone exit')
        elif key == '2':
            if not self.joystick_pulled:
                self.joystick_pull_remote_ts = time.perf_counter()
                self.joystick_pulled = True
                evt = self.log_hw('joystick_pulled', plexon_ts=time.perf_counter(), sim=True)
                self.joystick_pull_event = evt
                self.dbg_classification_event('joystick_pull')
            else:
                self.joystick_release_remote_ts = time.perf_counter()
                self.joystick_pulled = False
                self.log_hw('joystick_released', plexon_ts=time.perf_counter(), sim=True, info={
                    'pull_event': get_event_id(self.joystick_pull_event),
                })
                self.joystick_pull_event = None
                self.dbg_classification_event('joystick_released')
            
            print('joystick', self.joystick_pulled)
    
    def close_application(self):
        try:
            self.stop()
        except:
            traceback.print_exc()
        self.root.quit()
    
    def show_image(self, k, *, variant=None, boxed=False, _clear=True):
        if _clear:
            self.clear_image()
        
        img = self.game_frame.images[k]['tk'][variant]
        
        canvas_size = self.game_frame.cv1.winfo_width(), self.game_frame.cv1.winfo_height()
        
        x_offset = (canvas_size[0]) / 2
        y_offset = (canvas_size[1]) / 2
        
        self.game_frame.cv1.create_image(x_offset, y_offset, anchor = 'c', image = img)
        
        if boxed:
            self.show_image('box', variant=variant, _clear=False)
    
    def clear_image(self):
        self.game_frame.cv1.delete(tk.ALL)
    
    def handle_classification_event(self, event_class, timestamp):
        if self._cl_helper is not None:
            # assert self._classifier_event_type is not None
            self._cl_helper.event(
                event_type = self._classifier_event_type,
                timestamp = timestamp,
                event_class = event_class,
            )
    
    def dbg_classification_event(self, event_class):
        if self.classifier_dbg:
            self.handle_classification_event(event_class, time.perf_counter())
    
    def gathering_data_omni_new(self):
        assert self.plexon
        for d in self.plexon.get_data():
            if self._cl_helper is not None:
                self._cl_helper.any_event(d.ts)
            
            if d.type == d.ANALOG:
                if d.chan == self.config.joystick_channel:
                    edge = self.joystick_debounce.sample(d.ts, d.value)
                    
                    if edge.rising:
                        evt = self.log_hw('joystick_pulled', plexon_ts=d.ts)
                        self.joystick_pull_event = evt
                        self.joystick_pulled = True
                        self.joystick_pull_remote_ts = d.ts
                        
                        self.handle_classification_event('joystick_pull', d.ts)
                    elif edge.falling:
                        self.log_hw('joystick_released', plexon_ts=d.ts, info={
                            'pull_event': get_event_id(self.joystick_pull_event),
                        })
                        self.joystick_pull_event = None
                        self.joystick_pulled = False
                        self.joystick_release_remote_ts = d.ts
                        
                        self.handle_classification_event('joystick_released', d.ts)
                elif self._photodiode is not None and d.chan == self.config.photodiode_channel:
                    edge = self._photodiode.handle_value(d.value, d.ts)
                    if edge.rising:
                        self.log_hw('photodiode_on', plexon_ts=d.ts)
                    if edge.falling:
                        self.log_hw('photodiode_off', plexon_ts=d.ts)
            elif d.type == d.SPIKE:
                if self._cl_helper is not None:
                    self._cl_helper.spike(
                        channel = d.chan,
                        unit = d.unit,
                        timestamp = d.ts,
                    )
            elif d.type == d.EVENT:
                zone = self.zone_by_chan.get(d.chan)
                if zone is not None:
                    if d.falling: # zone exit
                        zone.exit()
                    else: # zone enter
                        zone.enter()
                else:
                    # handle dedicated exit events from plexon
                    zone = self.zone_by_exit_chan.get(d.chan)
                    if zone is not None:
                        zone.exit()
                
                # neuorkey interface won't send channel 12
                if zone is None and d.chan == 12 and d.rising:
                    homezone = self.zone_by_name['homezone']
                    joystick_zone = self.zone_by_name['joystick_zone']
                    self.log_hw('zone_exit', plexon_ts=d.ts, info={
                        'was_in_homezone': homezone.in_zone,
                        'was_in_joystick_zone': joystick_zone.in_zone,
                    })
                    
                    if homezone.in_zone:
                        zone = homezone
                        zone.exit()
                    elif joystick_zone.in_zone:
                        zone = joystick_zone
                        zone.exit()
                
                if zone is not None:
                    self.log_hw(zone.event_name, plexon_ts=d.ts, info={
                        'changed': zone.changed,
                    })
                    self.handle_classification_event(zone.event_name, d.ts)
                else:
                    self.log_hw('hw_event', plexon_ts=d.ts, info={'channel': d.chan})
            elif d.type == d.OTHER_EVENT:
                if d.chan == 1:
                    # not sure what this is but plexon sends them every 10ms or so
                    pass
                elif d.chan == 2:
                    self.log_hw('plexon_recording_start', plexon_ts=d.ts)
                else:
                    self.log_hw('plexon_other_event', plexon_ts=d.ts, info={'channel': d.chan})

def main():
    logging.addLevelName(5, "trace")
    FORMAT = "%(levelname)s:%(message)s"
    if os.environ.get('trace'):
        logging.basicConfig(level=5, format=FORMAT)
    elif os.environ.get('log'):
        # logging.basicConfig(filename='debug.log', encoding='utf-8', level=logging.DEBUG)
        logging.basicConfig(level=logging.DEBUG, format=FORMAT)
    else:
        logging.basicConfig(level=logging.WARNING, format=FORMAT)
    logging.getLogger('PIL.PngImagePlugin').setLevel(logging.WARNING)
    
    debug("program start %s", datetime.now())
    
    root = tk.Tk()
    root.configure(bg='black', bd=0)
    
    with MonkeyImages(root):
        tk.mainloop()

if __name__ == "__main__":
    main()
