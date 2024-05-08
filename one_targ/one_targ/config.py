
from typing import Any, Optional
from pathlib import Path
from sys import platform
from datetime import datetime
import os

def get_pos() -> tuple[int, int, int , int] | None:
    # -1920,0<-1920x1086
    # ^ x pos
    #       ^ y pos
    #          ^ width
    #               ^ height
    try:
        s = os.environ['pos']
    except KeyError:
        return None
    
    pos, size = s.split('<-')
    px, py = pos.split(',')
    px = int(px)
    py = int(py)
    sx, sy = size.split('x')
    sx = int(sx)
    sy = int(sy)
    
    return (px, py, sx, sy)

def _parse_hold(x) -> tuple[float, float]:
    if type(x) is str:
        _min, _max = x.split('-')
        _min = float(_min)
        _max = float(_max)
    else:
        _min = float(x)
        _max = _min
    
    return (_min, _max)

Color = tuple[int, int, int]
def _parse_color(raw) -> Color:
    if isinstance(raw, str):
        split = raw.split('_')
        if len(split) == 4:
            r, g, b, a = split
            assert a == '1', f"alpha must be 1 in `{raw}`"
        else:
            r, g, b = split
        def conv(v) -> int:
            return round(float(v)*255)
        return conv(r), conv(g), conv(b)
    
    assert isinstance(raw, list)
    assert len(raw) == 3
    assert all(isinstance(x, int) for x in raw)
    assert all(0 <= x <= 255 for x in raw)
    return tuple(raw)

class Config:
    def __init__(self, raw: Any):
        self.max_trials: Optional[int] = raw['autoquit_after']
        
        self.fullscreen_position: tuple[int, int, int , int] | None = get_pos()
        
        # 85. is the value used in the original code
        # 3/12.7 is a correction factor based on tina's measurments on the lab computer
        # 85. / (3/12.7) is roughly 20.08 and that is preserved as the default
        self.px_per_cm: float = float(os.environ.get('px_per_cm', 20.08))
        
        self.center_target_radius: float = float(raw['target_radius'])
        self.periph_target_radius: float = float(raw['target_radius'])
        self.periph_target_shape: str = raw['peripheral_target_shape']
        self.periph_target_color: Color = _parse_color(raw['peripheral_target_color'])
        
        self.corner_dist: float = float(raw['corner_non_cage_target_distance'])
        self.periph_target_count: int = int(raw.get('peripheral_target_count'))
        
        self.nudge: tuple[float, float] = (float(raw['nudge_x']), float(raw['nudge_y']))
        
        self.inter_trial_time: tuple[float, float] = _parse_hold(raw['inter_trial_time'])
        self.center_hold_time: tuple[float, float] = _parse_hold(raw['center_hold_time'])
        self.periph_hold_time: tuple[float, float] = _parse_hold(raw['target_hold_time'])
        
        self.center_touch_timeout: float = float(raw['ch_timeout'])
        self.periph_touch_timeout: float = float(raw['target_timeout'])
        
        self.pre_reward_delay: float = float(raw.get('pre_reward_delay', 1.87))
        self.post_reward_delay: float = float(raw.get('post_reward_delay', 0))
        self.reward_duration: float = float(raw['center_target_reward'])
        self.center_target_reward_duration: float = float(raw.get('actual_center_target_reward', 0.0))
        
        self.punish_delay: float = float(raw.get('punish_delay', 1.2))
        self.post_punish_delay: float = float(raw.get('post_punish_delay', 0))
        
        self.animal_name: str = raw['animal_name']
        
        self.output_dir: Path = Path(os.environ.get('output_dir', './output'))
        
        self.out_file_name: str = f"{self.animal_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.output_device: str = os.environ.get('output_device', 'none')
        self.nidaq_device: str|None = os.environ.get('nidaq')
        if self.nidaq_device == '':
            self.nidaq_device = None
        
        # default to 18ms, longer than 1 refresh at 60hz (16.7 ms)
        self.photodiode_flash_duration: Optional[float] = float(os.environ.get('photodiode_flash_duration', 0.018))
        if self.photodiode_flash_duration == 0.0:
            self.photodiode_flash_duration = None
        
        self.no_audio: bool = bool(os.environ.get('no_audio'))
    
    def to_json_dict(self):
        out = {}
        for k, v in self.__dict__.items():
            if k in ['raw_config', 'images']:
                continue
            if isinstance(v, Path):
                v = str(v)
            out[k] = v
        return out
