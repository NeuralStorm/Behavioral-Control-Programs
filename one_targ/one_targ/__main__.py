
from typing import Optional, Any, List
import time
from datetime import datetime
from contextlib import ExitStack
from sys import platform
import sys
import os
import random
from math import pi, sin, cos

from pathlib import Path
import argparse
from pprint import pprint
import json
import hjson

if platform == 'win32':
    import winsound

from . import game_ui
from .game_ui import COApp, COGame, BackgroundOverlay
from .config import Config
from . import nidaq
from . import reward_calc

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

class GameState:
    def __init__(self, config: Config):
        self.co_game: Optional[COGame] = None
        
        self.config = config
        
        self.game_time = 0
        self._last_progress_time = time.perf_counter()
        
        self.event_log = []
        
        
        self.plexon_event_types = nidaq.build_event_types('Dev3')
        self.nidaq_enabled = self.config.nidaq_enabled
        pin_list = [x['nidaq_pin'] for x in self.plexon_event_types.values()]
        if self.nidaq_enabled:
            self.nidaq = nidaq.Nidaq(pin_list)
            self.nidaq.start()
        else:
            self.nidaq = None
        
        self._gen = self._main_loop()
        
        self.periph_pos_gen = self._get_corner_target_gen(config.corner_dist)
        self.reward_gen = reward_calc.get_reward_gen(
            perc_trials_2x = config.percent_of_rewards_doubled,
            perc_trials_rew = config.percent_of_trials_rewarded,
            reward_for_grasp = [True, config.center_target_reward],
        )
        
        if config.plexon_enabled:
            import plexon
            self.plex_do = plexon.init_plex_do()
        else:
            self.plex_do = None
        
        # game logic state
        self.repeat = False
    
    def log_event(self, name: str, *, tags: List[str], info=None):
        if info is None:
            info = {}
        mono_time = time.perf_counter()
        out = {
            'time_m': mono_time,
            'name': name,
            'tags': tags,
            'info': info,
        }
        
        self.event_log.append(out)
    
    def flash_marker(self, name: str):
        assert self.co_game is not None
        flash_duration = 0.016
        self.co_game.flash_marker(flash_duration)
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
    
    def progress_gen(self):
        cur_time = time.perf_counter()
        
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
        game = self.co_game
        assert game is not None
        x, y = next(self.periph_pos_gen)
        game.move_periph(x, y)
        
        trial_i = 0
        while True:
            if self.config.max_trials is not None and trial_i >= self.config.max_trials:
                break
            yield from self.run_trial()
            trial_i += 1
    
    def _get_corner_target_gen(self, dist: float):
        n = 4
        max_angle = 2*pi
        angles = [(i/n+1/8)*max_angle for i in range(n+1)][:-1]
        positions = [
            (cos(angle)*dist, sin(angle)*dist)
            for angle in angles
        ]
        while True:
            random.shuffle(positions)
            for pos in positions:
                yield pos
    
    def run_center(self, center_done, *, center_hold_time, periph_hold_time):
        assert self.co_game is not None
        game = self.co_game
        
        game.center_target.show()
        self.flash_marker('center_show')
        self.send_plexon_event('center_show')
        yield
        
        def check_touch_center():
            return \
                game.target_touched(game.center_target) and \
                game.target_touched(game.center_target, start=True)
        
        # wait for touch to be on center
        timeout = self._timeout(lambda: (not check_touch_center()), self.config.center_touch_timeout)
        yield from timeout
        if timeout.hit_timeout:
            self.send_plexon_event('trial_incorrect')
            game.center_target.hide()
            self.send_plexon_event('center_hide')
            return
        
        self.send_plexon_event('center_touch')
        with game.center_target.overlay((0, 1, 0, 1)):
            
            # check that touch remains on center for "cht"
            def on_target():
                return game.target_touched(game.center_target)
            timeout = self._timeout(on_target, center_hold_time)
            yield from timeout
            game.center_target.hide()
            self.send_plexon_event('center_hide')
            if not timeout.hit_timeout:
                self.send_plexon_event('trial_incorrect')
                self.repeat = True
                return
        
        # center target has been pressed, peripheral target from here down
        
        # the target position actually doesn't change if the center target wasn't held
        # long enough then pressed after. I've confirmed this is the original behavior
        if not self.repeat:
            x, y = next(self.periph_pos_gen)
            game.move_periph(x, y)
            
            if x < 0 and y > 0:
                self.send_plexon_event('top_left')
            elif x > 0 and y > 0:
                self.send_plexon_event('top_right')
            elif x < 0 and y < 0:
                self.send_plexon_event('bottom_left')
            elif x > 0 and y < 0:
                self.send_plexon_event('bottom_right')
        
        self.repeat = False
        game.periph_target.show()
        self.flash_marker('periph_show')
        self.send_plexon_event('periph_show')
        yield
        
        # wait for periph target to be touched
        race = self._race(
            touch=self._until(lambda: game.target_touched(game.periph_target)),
            timeout=self._wait(self.config.periph_touch_timeout)
        )
        yield from race
        
        if race.first == 'touch':
            self.send_plexon_event('periph_touch')
            
            with game.periph_target.overlay((0, 1, 0, 1)):
                # wait to see if periph target is held long enough
                race = self._race(
                    early_release=self._until(lambda: not game.target_touched(game.periph_target)),
                    timeout=self._wait(periph_hold_time)
                )
                yield from race
                
                if race.first == 'early_release':
                    self.send_plexon_event('trial_incorrect')
                    game.periph_target.hide()
                    self.send_plexon_event('periph_hide')
                    return
                elif race.first == 'timeout':
                    self.send_plexon_event('trial_correct')
                    with BackgroundOverlay((1,1,1,1)):
                        game.trial_counter += 1
                        game.periph_target.hide()
                        self.send_plexon_event('periph_hide')
                        
                        game.run_big_rew_sound()
                        reward_val = next(self.reward_gen)
                        if self.plex_do is not None:
                            # https://github.com/NeuralStorm/Behavioral-Control-Programs/blob/61a9baa6d198e3dc13d30326901ea78bd42dc77f/touchscreen_co/Touchscreen/one_targ_new/main.py#L815
                            if reward_val > 0:
                                plex_do_device_number = 1
                                reward_nidaq_bit = 17
                                self.plex_do.set_bit(plex_do_device_number, reward_nidaq_bit)
                                yield from self._wait(self.config.center_target_reward)
                                self.plex_do.clear_bit(plex_do_device_number, reward_nidaq_bit)
                        
                        yield from self._wait(2.5)
                else:
                    raise ValueError()
        elif race.first == 'timeout':
            game.periph_target.hide()
            self.send_plexon_event('periph_hide')
            yield from self._wait(2)
        else:
            raise ValueError()
        
        center_done[0] = True
    
    def run_trial(self):
        assert self.co_game is not None
        game = self.co_game
        
        # game.flash_marker(0.016)
        # yield from self._wait(2)
        # return
        
        with ExitStack() as trial_stack:
            def pick_hold_time(x):
                if x[0] == x[1]:
                    return x[0]
                _min, _max = x
                t = ((float(_max) - float(_min)) * random.random()) + float(_min)
                return t
            
            center_hold = pick_hold_time(self.config.center_hold_time)
            periph_hold = pick_hold_time(self.config.periph_hold_time)
            
            iti_mean = 1.
            iti_std = 0.2
            iti = random.random()*iti_std + iti_mean
            yield from self._wait(iti)
            
            if game.trial_counter == 0:
                yield from self._wait(1)
            
            yield from self._wait(0.1)
            
            center_done = [False]
            while not center_done[0]:
                yield from self.run_center(
                    center_done,
                    center_hold_time = center_hold,
                    periph_hold_time = periph_hold,
                )

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--config', default='./config.hjson',
        help='config file')
    
    args = parser.parse_args()
    
    return args

def main():
    args = parse_args()
    
    config_path = Path(args.config)
    assert config_path.is_file()
    
    with open(config_path, encoding='utf8') as f:
        raw_config = hjson.load(f)
    config = Config(raw_config)
    game_ui.config = config
    
    game_state = GameState(config)
    game_ui.game_state = game_state
    
    game_state.log_event('config_loaded', tags=[], info={
        'time_utc': datetime.utcnow().isoformat(),
        'config': config.to_json_dict(),
        'raw': raw_config,
    })
    
    try:
        COApp(config_path, config).run()
    finally:
        out = {
            'events': game_state.event_log,
        }
        config.output_dir.mkdir(exist_ok=True)
        with open(f"{config.output_dir / config.out_file_name}_meta.json", 'w', encoding='utf8', newline='\n') as f:
            json.dump(out, f, indent=4)
        if game_state.nidaq is not None:
            game_state.nidaq.stop()

if __name__ == '__main__':
    main()
