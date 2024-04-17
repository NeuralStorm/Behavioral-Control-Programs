
from typing import Optional, Any, List
import time
from time import perf_counter
from datetime import datetime
from contextlib import ExitStack
from sys import platform
import sys
import os
import random
from math import pi, sin, cos
import threading
from threading import Thread, Lock

from pathlib import Path
import argparse
from pprint import pprint
import json

import hjson
import pygame

from butil.sound import get_sound_provider, SoundProvider
from butil import EventFile
from butil.out_file import EventFileProcess

from . import game_ui
from .game_ui import BackgroundOverlay, GameRenderer, MultiWindow
from .config import Config
from . import nidaq

SOUND_PATH_BASE = Path(__file__).parent / 'assets/audio'

class Timeout:
    def __init__(self, p, timeout, get_time):
        self.hit_timeout = False
        
        self.get_time = get_time
        self.p = p
        self.timeout: float = timeout
    
    def __iter__(self):
        if self.timeout == 0.:
            return
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

class GameState:
    def __init__(self, config: Config, game_obj, events_file: EventFile):
        self.renderer: GameRenderer = game_obj
        
        self.config = config
        
        self.game_time = 0
        self._last_progress_time = time.perf_counter()
        
        self.events_file: EventFile = events_file
        self.event_i = 0
        
        self.trial_i = 0
        
        self.nidaq_enabled = self.config.nidaq_device is not None
        self.plexon_event_types = nidaq.build_event_types(self.config.nidaq_device or '')
        pin_list = [x['nidaq_pin'] for x in self.plexon_event_types.values()]
        if self.nidaq_enabled:
            self.nidaq = nidaq.Nidaq(pin_list)
            self.nidaq.start()
        else:
            self.nidaq = None
        
        # self._gen = self._main_loop()
        self._gen: Optional[Any] = None
        
        self.periph_pos_gen = self._get_corner_target_gen(config.corner_dist)
        
        if config.plexon_enabled:
            from butil.plexon.plexdo import PlexDo
            self.plex_do = PlexDo()
        else:
            self.plex_do = None
        
        self.sound: SoundProvider = get_sound_provider(disable=config.no_audio)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        if self.nidaq is not None:
            self.nidaq.stop()
    
    def log_event(self, name: str, *, tags: List[str]=[], info=None):
        if info is None:
            info = {}
        mono_time = time.perf_counter()
        out = {
            'id': self.event_i,
            'time_m': mono_time,
            'name': name,
            'tags': tags,
            'info': info,
        }
        self.event_i += 1
        
        self.events_file.write_record(out)
    
    def flash_marker(self, name: str):
        self.renderer.flash_marker(self.config.photodiode_flash_duration)
        self.log_event('photodiode_expected', tags=['hw'], info={
            'name': name,
        })
    
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
    
    def start(self):
        self._gen = self._main_loop()
    
    def stop(self):
        self.renderer.center_target.hide()
        self.renderer.periph_target.hide()
        self._gen = None
    
    def progress_gen(self):
        cur_time = time.perf_counter()
        
        elapsed_time = cur_time - self._last_progress_time
        self._last_progress_time = cur_time
        self.game_time += elapsed_time
        
        if self._gen is not None:
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
        while True:
            if self.config.max_trials is not None and self.trial_i >= self.config.max_trials:
                break
            yield from self.run_trial()
            self.trial_i += 1
    
    def _get_corner_target_gen(self, dist: float):
        n = 4
        max_angle = 2*pi
        angles = [(i/n+1/8)*max_angle for i in range(n)]
        positions = [
            (cos(angle)*dist, sin(angle)*dist)
            for angle in angles
        ]
        while True:
            angle = random.choice(positions)
            yield angle
            # random.shuffle(positions)
            # for pos in positions:
            #     yield pos
    
    def run_punish(self):
        renderer = self.renderer
        with renderer.overlay((255, 0, 0)):
            self.sound.play_file(SOUND_PATH_BASE / 'zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_negative_66204.wav')
            # default of 1.2 is duration of sound effect
            yield from self._wait(self.config.punish_delay)
        yield from self._wait(self.config.post_punish_delay)
    
    def run_trial(self):
        renderer = self.renderer
        
        # game.flash_marker(self.config.photodiode_flash_duration)
        # yield from self._wait(2)
        # return
        
        with ExitStack() as trial_stack:
            def pick_hold_time(x):
                if x[0] == x[1]:
                    return x[0]
                _min, _max = x
                t = ((float(_max) - float(_min)) * random.random()) + float(_min)
                return t
            
            inter_trial_time = pick_hold_time(self.config.inter_trial_time)
            center_hold_time = pick_hold_time(self.config.center_hold_time)
            periph_hold_time = pick_hold_time(self.config.periph_hold_time)
            
            self.log_event('trial_start', info={
                'trial_i': self.trial_i,
                'inter_trial_time': inter_trial_time,
                'center_hold_time': center_hold_time,
                'periph_hold_time': periph_hold_time,
            })
            
            yield from self._wait(inter_trial_time)
            
            renderer.center_target.show()
            self.flash_marker('center_show')
            self.send_plexon_event('center_show')
            yield
            
            def check_touch_center():
                return \
                    renderer.target_touched(renderer.center_target)
            
            timeout = self._timeout(lambda: (not check_touch_center()), self.config.center_touch_timeout)
            yield from timeout
            if timeout.hit_timeout: # center target not pressed soon enough
                self.send_plexon_event('trial_incorrect')
                renderer.center_target.hide()
                # TODO does this need to be time synced? also other places target is hidden
                # TODO targets disappear at same time other targets appear, unclear how that would be synced
                self.send_plexon_event('center_hide')
                yield from self.run_punish()
                return {'result': 'fail'}
            
            self.send_plexon_event('center_touch')
            with renderer.center_target.overlay((0, 255, 0)):
                
                # check that touch remains on center for "cht"
                def on_target():
                    return renderer.target_touched(renderer.center_target)
                timeout = self._timeout(on_target, center_hold_time)
                yield from timeout
                renderer.center_target.hide()
                self.send_plexon_event('center_hide')
                if not timeout.hit_timeout: # target was released early
                    self.send_plexon_event('trial_incorrect')
                    yield from self.run_punish()
                    return {'result': 'fail'}
            
            x, y = next(self.periph_pos_gen)
            renderer.move_periph(x, y)
            
            if x < 0 and y > 0:
                self.send_plexon_event('top_left')
            elif x > 0 and y > 0:
                self.send_plexon_event('top_right')
            elif x < 0 and y < 0:
                self.send_plexon_event('bottom_left')
            elif x > 0 and y < 0:
                self.send_plexon_event('bottom_right')
            
            renderer.periph_target.show()
            self.flash_marker('periph_show')
            self.send_plexon_event('periph_show')
            yield
            
            # wait for periph target to be touched
            race = self._race(
                touch=self._until(lambda: renderer.target_touched(renderer.periph_target)),
                timeout=self._wait(self.config.periph_touch_timeout)
            )
            yield from race
            
            if race.first == 'timeout':
                renderer.periph_target.hide()
                self.send_plexon_event('periph_hide')
                yield from self.run_punish()
                return {'result': 'fail'}
            
            assert race.first == 'touch'
            
            self.send_plexon_event('periph_touch')
            with renderer.periph_target.overlay((0, 255, 0)):
                # wait to see if periph target is held long enough
                race = self._race(
                    early_release=self._until(lambda: not renderer.target_touched(renderer.periph_target)),
                    hold_complete=self._wait(periph_hold_time)
                )
                yield from race
                
                if race.first == 'early_release':
                    self.send_plexon_event('trial_incorrect')
                    renderer.periph_target.hide()
                    self.send_plexon_event('periph_hide')
                    yield from self.run_punish()
                    return {'result': 'fail'}
                elif race.first == 'hold_complete':
                    self.send_plexon_event('trial_correct')
                    with renderer.overlay((255, 255, 255)):
                        renderer.trial_counter += 1
                        renderer.periph_target.hide()
                        self.send_plexon_event('periph_hide')
                        
                        self.sound.play_file(SOUND_PATH_BASE / 'zapsplat_multimedia_game_sound_kids_fun_cheeky_layered_mallets_complete_66202.wav')
                        yield from self._wait(self.config.pre_reward_delay)
                        if self.plex_do is not None:
                            reward_nidaq_bit = 17
                            self.plex_do.bit_on(reward_nidaq_bit)
                            yield from self._wait(self.config.center_target_reward)
                            self.plex_do.bit_off(reward_nidaq_bit)
                        yield from self._wait(self.config.post_reward_delay)
                    
                    return {'result': 'success'}

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--config',
        help='config file')
    
    args = parser.parse_args()
    
    return args

def main_inner(stack):
    args = parse_args()
    
    path_str = args.config
    if path_str is None:
        path_str = os.environ.get('config_path')
    if path_str is None:
        path_str = './config.hjson'
    config_path = Path(path_str)
    
    assert config_path.is_file()
    
    with open(config_path, encoding='utf8') as f:
        raw_config = hjson.load(f)
    config = Config(raw_config)
    
    events_path = config.output_dir / f"{config.out_file_name}.json.gz"
    
    config.output_dir.mkdir(exist_ok=True)
    events_file: EventFile = stack.enter_context(EventFileProcess(path=events_path))
    
    renderer = GameRenderer(config)
    game_state = stack.enter_context(GameState(config, renderer, events_file))
    
    game_state.log_event('config_loaded', tags=[], info={
        'time_utc': datetime.utcnow().isoformat(),
        'config': config.to_json_dict(),
        'raw': raw_config,
    })
    
    user_pos = config.window_position
    if user_pos is not None:
        window_size = user_pos[2], user_pos[3]
        # os.environ['SDL_VIDEO_WINDOW_POS'] = f"{user_pos[0]},{user_pos[1]}"
        window_pos = user_pos[0], user_pos[1]
    else:
        window_size = None
        window_pos = None
    
    pygame.display.init()
    stack.callback(pygame.quit)
    # return
    
    window_task = MultiWindow(title = 'CO Task', size=window_size, position=window_pos)
    stack.callback(window_task.destroy)
    
    # window_info = MultiWindow(title = 'CO Info')
    # stack.callback(window_info.destroy)
    window_info = None
    
    cursor_pos = {}
    renderer.cursor_px = cursor_pos
    
    last_frame_time = 0
    calibration_shown = False
    
    lock = Lock()
    exiting = threading.Event()
    def game_thread():
        while True:
            if exiting.is_set():
                return
            with lock:
                game_state.progress_gen()
    logic_thread = Thread(target=game_thread, daemon=True)
    logic_thread.start()
    
    def stop_logic_thread():
        exiting.set()
        logic_thread.join
    stack.callback(stop_logic_thread)
    
    while True:
        for event in pygame.event.get():
            # print(event)
            window = getattr(event, 'window', None)
            if window == window_task.window:
                # lock required around modifying cursor_pos
                # to avoid `dictionary changed size during iteration` error
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button != 1:
                        continue
                    with lock:
                        cursor_pos[None] = [event.pos, event.pos]
                if event.type == pygame.MOUSEMOTION:
                    if None in cursor_pos:
                        with lock:
                            cursor_pos[None][1] = event.pos
                if event.type == pygame.MOUSEBUTTONUP:
                    try:
                        with lock:
                            del cursor_pos[None]
                    except KeyError:
                        pass
            
            if event.type == pygame.MOUSEMOTION and event.touch is not False:
                print(event)
            if event.type == pygame.FINGERDOWN:
                print(event)
            if event.type == pygame.FINGERMOTION:
                print(event)
            if event.type == pygame.FINGERUP:
                print(event)
            
            if event.type == pygame.KEYDOWN:
                if event.unicode == 'a':
                    with lock:
                        game_state.start()
                elif event.unicode == 's':
                    with lock:
                        game_state.stop()
                elif event.unicode == '~':
                    return
                elif event.unicode == 'f':
                    window_task.toggle_fullscreen()
                elif event.unicode == 'c':
                    calibration_shown = not calibration_shown
            
            if event.type == pygame.WINDOWCLOSE and event.window == window_task:
                return
            if event.type == pygame.QUIT:
                return
        
        # game_state.progress_gen()
        
        cur_time = perf_counter()
        # 60 fps
        if cur_time - last_frame_time < 0.016666666:
            continue
        
        assert logic_thread.is_alive()
        with lock:
            s = perf_counter()
            renderer.render(window_task.surface)
            e = perf_counter()
        # if e-s > 0.001:
        #     print('long render', e-s)
        
        if calibration_shown:
            pygame.draw.rect(window_task.surface, (0,255,0), (300, 300, 200, 200))
        
        # keys = pygame.key.get_pressed()
        # if keys[pygame.K_w]:
        #     pygame.draw.circle(window_task.surface, "green", (300,300), 100)
        
        window_task.present()
        if window_info is not None:
            window_info.present()
        
        last_frame_time = perf_counter()
        
        # clock.tick(60) # limits FPS to 60

def main():
    with ExitStack() as stack:
        main_inner(stack)

if __name__ == '__main__':
    main()
