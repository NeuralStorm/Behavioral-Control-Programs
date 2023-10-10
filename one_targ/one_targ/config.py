
from typing import Any, Optional
from pathlib import Path
from sys import platform
from datetime import datetime
import os

def _parse_hold(x) -> tuple[float, float]:
    if type(x) is str:
        _min, _max = x.split('-')
        _min = float(_min)
        _max = float(_max)
        a = (_min+_max)*.5
    else:
        _min = float(x)
        a = _min
        # _max = None
        _max = _min
    
    return (_min, _max)

class Config:
    def __init__(self, raw: Any):
        self.max_trials: Optional[int] = raw['autoquit_after']
        
        # 3/12.7 is a correction factor based on tina's measurments on the lab computer
        self.px_per_cm: float = 85. * (3/12.7)
        
        self.center_target_radius: float = float(raw['target_radius'])
        self.periph_target_radius: float = float(raw['target_radius'])
        self.periph_target_shape: str = raw['peripheral_target_shape']
        r, g, b, a = raw['peripheral_target_color'].split('_')
        self.periph_target_color: tuple[float, float, float, float] = (
            float(r), float(g), float(b), float(a),
        )
        
        self.corner_dist: float = float(raw['corner_non_cage_target_distance'])
        
        self.nudge: tuple[float, float] = (float(raw['nudge_x']), float(raw['nudge_y']))
        
        self.center_hold_time: tuple[float, float] = _parse_hold(raw['center_hold_time'])
        self.periph_hold_time: tuple[float, float] = _parse_hold(raw['target_hold_time'])
        
        self.center_touch_timeout: float = float(raw['ch_timeout'])
        self.periph_touch_timeout: float = float(raw['target_timeout'])
        
        self.center_target_reward: float = float(raw['center_target_reward'])
        self.percent_of_trials_rewarded: float = float(raw['reward_variability'])
        self.percent_of_rewards_doubled: float = float(raw['reward_double_chance'])
        
        self.animal_name: str = raw['animal_name']
        
        monkey_names = {
            'Donut': 'donu', 'Sandpiper': 'sand', 'Sabotage': 'sabo',
        }
        
        # https://github.com/NeuralStorm/Behavioral-Control-Programs/blob/61a9baa6d198e3dc13d30326901ea78bd42dc77f/touchscreen_co/Touchscreen/one_targ_new/main.py#L431
        p = Path.cwd()
        # the program would split the path on \ creating platform specific behavior
        # attempt to recreate that here
        if platform == 'win32':
            p = p.resolve()
            path_parts = [x for x in p.parts if 'Touch' not in x and 'Targ' not in x]
            p = Path(*path_parts)
        data_p = p / 'data'
        if data_p.exists():
            p = data_p
        else:
            p = p / f"data_tmp_{datetime.now().strftime('%Y%m%d')}/"
            # p.mkdir(exist_ok=True)
        self.output_dir: Path = p
        
        out_animal_name = monkey_names.get(self.animal_name, self.animal_name)
        self.out_file_name: str = f"{out_animal_name}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        self.plexon_enabled: bool = bool(os.environ.get('plexon'))
        self.nidaq_enabled: bool = bool(os.environ.get('nidaq'))
        
        self.skip_start: bool = bool(os.environ.get('skip_start'))
    
    def to_json_dict(self):
        out = {}
        for k, v in self.__dict__.items():
            if k in ['raw_config', 'images']:
                continue
            if isinstance(v, Path):
                v = str(v)
            out[k] = v
        return out
