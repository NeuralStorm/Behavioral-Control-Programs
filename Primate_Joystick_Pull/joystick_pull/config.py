
import os
from typing import Any, Tuple, Literal, Optional, Dict, List, Union, TypedDict
import csv
from pathlib import Path
from datetime import datetime
import json

import hjson
from PIL import Image, ImageTk

class GameConfig:
    def __init__(self, *,
        config_path: Union[Path, str],
        start_dt: Optional[datetime] = None,
    ):
        def load_csv():
            data = []
            with open(config_path, newline='') as csvfile:
                spamreader = csv.reader(csvfile) #, delimiter=' ', quotechar='|')
                for row in spamreader:
                    #data = list(spamreader)
                    data.append(row)
            csvreaderdict = {}
            for row in data:
                if not row:
                    continue
                k = row[0].strip()
                vs = [v.strip() for v in row[1:]]
                # remove empty cells after the key and first value column
                vs[1:] = [v for v in vs[1:] if v]
                if not k or k.startswith('#'):
                    continue
                csvreaderdict[k] = vs
            return csvreaderdict
        
        config_dict = load_csv()
        
        NO_DEFAULT = object()
        def get(key, default=NO_DEFAULT, *, multi=False) -> Any:
            val = config_dict.get(key)
            if val in [None, [], ['']]:
                if default is NO_DEFAULT:
                    raise KeyError(key)
                return default
            else:
                if multi:
                    return val
                else:
                    assert val is not None
                    return val[0]
            
            assert False
        
        self.raw_config = config_dict
        # PARAMETERS META DATA
        self.study_id: str = get('Study ID')       # 3 letter study code
        self.session_id: str = get('Session ID') # Type of Session
        self.experimental_group: str = get('experimental_group')
        self.experimental_condition: str = get('experimental_condition')
        self.animal_id: str = get('Animal ID')   # 3 digit number
        self.file_name_task_type: str = get('Task Type')
        
        if start_dt is None:
            start_dt = datetime.now()
        self.start_time: str = start_dt.strftime('%Y%m%d_%H%M%S')
        start_date_str = start_dt.strftime('%Y%m%d')
        start_time_str = start_dt.strftime('%H%M%S')
        
        self.save_path: Path = Path(config_dict['Task Data Save Dir'][0])
        if os.environ.get('out_file_name'):
            self.log_file_name_base = os.environ['out_file_name']
        else:
            self.log_file_name_base: str = f"{self.study_id}{self.animal_id}_{self.experimental_group}_{self.experimental_condition}_{self.session_id}_{start_date_str}_{start_time_str}{self.file_name_task_type}"
        
        self.discrim_delay_range: Tuple[float, float] = (
            float(config_dict['Pre Discriminatory Stimulus Min delta t1'][0]),
            float(config_dict['Pre Discriminatory Stimulus Max delta t1'][0]),
        )
        self.go_cue_delay_range: Tuple[float, float] = (
            float(config_dict['Pre Go Cue Min delta t2'][0]),
            float(config_dict['Pre Go Cue Max delta t2'][0]),
        )
        
        self.MaxTimeAfterSound: int = int(config_dict['Maximum Time After Sound'][0])
        self.InterTrialTime: float = float(config_dict['Inter Trial Time'][0])
        self.manual_reward_time: float = float(config_dict['manual_reward_time'][0])
        self.TimeOut: float = float(config_dict['Time Out'][0])
        self.EnableTimeOut: bool = bool(self.TimeOut)
        self.EnableBlooperNoise: bool = config_dict['Enable Blooper Noise'][0] == 'TRUE'
        
        self.task_type: Literal['homezone_exit', 'joystick_pull']
        num_events: int = int(config_dict['Number of Events'][0])
        if num_events == 0:
            self.task_type = 'homezone_exit'
        else:
            self.task_type = 'joystick_pull'
        
        pspd = get('post_successful_pull_delay', None)
        if pspd is None:
            pspd = get('post_succesful_pull_delay', None)
        if pspd is None:
            pspd = 1.87
        else:
            pspd = float(pspd)
        self.post_successful_pull_delay: float = pspd
        
        self.joystick_channel: int = int(get('joystick_channel', 3))
        
        num_trials = int(get('no_trials', 0))
        if num_trials == 0:
            num_trials = None
        self.max_trials: Optional[int] = num_trials
        
        self.selectable_images: List[str] = list(set(x.strip() for x in config_dict['images']))
        
        image_ratios = config_dict.get('image_ratios')
        if image_ratios is not None:
            if len(image_ratios) == 0:
                image_ratios = None
            else:
                image_ratios = [int(x.strip()) for x in image_ratios]
        
        if image_ratios is None:
            self.image_selection_list: List[str] = self.selectable_images
        else:
            assert len(image_ratios) == len(self.selectable_images)
            sel_list: List[str] = []
            for count, key in zip(image_ratios, self.selectable_images):
                sel_list.extend(key for _ in range(count))
            assert len(sel_list) == sum(image_ratios)
            self.image_selection_list = sel_list
        
        self.load_thresholds(config_dict['reward_thresholds'])
        self.reward_thresholds: List[Dict[str, Any]]
        
        # example
        # export photodiode='{
        #     channel: 8
        #     threshold: [0.005, 0.02]
        #     min_pulse_width: 4
        #     edge_offset: -0.003
        # }'
        pd_ = os.environ.get('photodiode')
        if pd_ is None:
            self.pd_channel: Optional[int] = None
            self.pd_threshold: Tuple[float, float] = 0, 0
            self.pd_min_pulse_width: int = 0
            self.pd_edge_offset: float = 0.0
        else:
            pd = hjson.loads(pd_)
            self.pd_channel = int(pd['channel'])
            a, b = pd['threshold']
            self.pd_threshold = float(a), float(b)
            self.pd_min_pulse_width = int(pd['min_pulse_width'])
            self.pd_edge_offset = float(pd['edge_offset'])
        
        # default to 18ms, longer than 1 refresh at 60hz (16.7 ms)
        self.photodiode_flash_duration: float = float(os.environ.get('photodiode_flash_duration', 0.018))
        
        self.record_events: bool = not bool(os.environ.get('disable_record_events'))
        
        def load_record_analog() -> Dict[str, int]:
            ra = os.environ.get('record_analog')
            if not ra:
                return {}
            
            data = hjson.loads(ra)
            def load_auto(k: str, ch: int | None):
                if data.get(k) != 'auto':
                    return
                if ch is None:
                    del data[k]
                else:
                    data[k] = ch
            load_auto('photodiode', self.pd_channel)
            load_auto('joystick', self.joystick_channel)
            
            data = {str(a): int(b) for a, b in data.items()}
            return data
        self.record_analog: Dict[str, int] = load_record_analog()
        
        template_in_path = get('template', None)
        if template_in_path is None:
            self.template_in_path: Optional[Path] = None
        else:
            assert template_in_path is not None
            self.template_in_path = Path(template_in_path)
        
        wait_timeout = get('classify_wait_timeout', None)
        if wait_timeout is not None:
            wait_timeout = float(wait_timeout)
        self.classify_wait_timeout = wait_timeout
        
        self.classifier_debug: bool = bool(os.environ.get('classifier_debug'))
        self.simulate_photodiode: bool = bool(os.environ.get('simulate_photodiode'))
        
        self.event_source: Optional[str] = os.environ.get('event_source')
        
        self.no_git: bool = bool(os.environ.get('no_git'))
        self.no_print_stats: bool = bool(os.environ.get('no_print_stats'))
        
        self.no_wait_for_start: bool = bool(os.environ.get('no_wait_for_start'))
        self.no_info_view: bool = bool(os.environ.get('no_info_view'))
        self.hide_buttons: bool = bool(os.environ.get('hide_buttons'))
        self.layout_debug: bool = bool(os.environ.get('layout_debug'))
    
    def parse_threshold(self, s):
        s = s.strip()
        s = s.split('\'')
        s = [x.split('=') for x in s]
        rwd = {k.strip(): v.strip() for k, v in s}
        
        if 'cue' in rwd:
            assert rwd['cue'] in self.selectable_images, f"unknown cue {rwd['cue']}"
        else:
            rwd['cue'] = None
        
        for x in ['low', 'mid', 'high']:
            if x in rwd:
                rwd[x] = float(rwd[x])
        
        if 'mid' not in rwd:
            rwd['mid'] = rwd['low'] + (rwd['high'] - rwd['low']) / 2
        elif 'low' not in rwd:
            rwd['low'] = rwd['mid'] - (rwd['high'] - rwd['mid'])
        elif 'high' not in rwd:
            rwd['high'] = rwd['mid'] + (rwd['mid'] - rwd['low'])
        
        assert rwd['low'] < rwd['mid'] < rwd['high']
        
        if rwd['type'] == 'linear':
            for x in ['reward_max', 'reward_min']:
                rwd[x] = float(rwd[x])
        elif rwd['type'] == 'trapezoid':
            for x in ['reward_max', 'reward_min']:
                rwd[x] = float(rwd[x])
        elif rwd['type'] == 'flat':
            rwd['reward_duration'] = float(rwd['reward_duration'])
        else:
            raise ValueError(f"invalid reward type {rwd['type']}")
        
        return rwd
    
    def load_thresholds(self, raw_thresholds):
        
        rw_thr = [self.parse_threshold(x) for x in raw_thresholds]
        
        # ensure that there are reward thresholds for all images or a threshold for all cues
        if all(x['cue'] is not None for x in rw_thr):
            for img in self.selectable_images:
                assert any(x['cue'] == img for x in rw_thr), f"cue {img} has no reward threshold"
        
        self.reward_thresholds = rw_thr
    
    def to_json_dict(self):
        out = {}
        for k, v in self.__dict__.items():
            if k in ['raw_config', 'images']:
                continue
            if isinstance(v, Path):
                v = str(v)
            out[k] = v
        return out
