
import os
from typing import Any, Tuple, Literal, Optional, Dict, List, Union
import csv
from pathlib import Path
from datetime import datetime

import hjson
from PIL import Image, ImageTk

class GameConfig:
    def __init__(self, *,
        config_path: Union[Path, str],
        load_images: bool = True,
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
        
        self.enable_old_output = bool(os.environ.get('old_outputs'))
        
        self.raw_config = config_dict
        # PARAMETERS META DATA
        self.study_id: str = config_dict['Study ID'][0]       # 3 letter study code
        self.session_id: str = config_dict['Session ID'][0] # Type of Session
        self.experimental_group: str = get('experimental_group', 'NOTSET')
        self.experimental_condition: str = get('experimental_condition', 'NOTSET')
        self.animal_id: str = config_dict['Animal ID'][0]   # 3 digit number
        if start_dt is None:
            start_dt = datetime.now()
        self.start_time: str = start_dt.strftime('%Y%m%d_%H%M%S')
        start_date_str = start_dt.strftime('%Y%m%d')
        start_time_str = start_dt.strftime('%H%M%S')
        
        self.TaskType: str = config_dict['Task Type'][0]
        
        self.save_path: Path = Path(config_dict['Task Data Save Dir'][0])
        if os.environ.get('out_file_name'):
            self.log_file_name_base = os.environ['out_file_name']
        else:
            self.log_file_name_base: str = f"{self.study_id}{self.animal_id}_{self.experimental_group}_{self.experimental_condition}_{self.session_id}_{start_date_str}_{start_time_str}{self.TaskType}"
        
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
        
        pspd = config_dict.get('post_succesful_pull_delay')
        if pspd in [[''], []]:
            pspd = None
        if pspd is not None:
            pspd = float(pspd[0])
        self.post_succesful_pull_delay: Optional[float] = pspd
        
        jc = config_dict.get('joystick_channel')
        if jc in [[''], [], None]:
            jc = [3]
        jc = int(jc[0])
        self.joystick_channel: int = jc
        
        num_trials = config_dict.get('no_trials')
        if num_trials == ['true']:
            num_trials = [0]
        elif num_trials in [[''], [], ['0']]:
            num_trials = None
        if num_trials is not None:
            num_trials = int(num_trials[0])
        self.max_trials: Optional[int] = num_trials
        
        image_ratios = config_dict.get('image_ratios')
        if image_ratios is not None:
            if len(image_ratios) == 0:
                image_ratios = None
            else:
                image_ratios = [int(x.strip()) for x in image_ratios]
        
        if load_images:
            self.load_images(config_dict['images'], image_ratios)
        else:
            self.selectable_images = list(set(x.strip() for x in config_dict['images']))
        self.selectable_images: List[str]
        # image selection list has keys duplicated based on image_ratios
        self.image_selection_list: List[str]
        self.images: Dict[str, Dict[str, Any]]
        
        if load_images:
            self.load_thresholds(config_dict['reward_thresholds'])
        self.reward_thresholds: List[Dict[str, Any]]
        
        photodiode_range = config_dict.get('photodiode_range')
        if photodiode_range in [None, [], ['']]:
            self.photodiode_range: Optional[Tuple[float, float]] = None
        else:
            assert photodiode_range is not None
            pmin, pmax = config_dict['photodiode_range']
            self.photodiode_range = float(pmin), float(pmax)
        
        record_events = config_dict.get('record_events')
        if record_events in [None, [], [''], ['false']]:
            self.record_events: bool = False
        elif record_events in [['true']]:
            self.record_events = True
        else:
            raise ValueError(f"invalid setting for record_events `{record_events}`")
        
        allowed_event_classes = [
            'joystick_pull',
            'joystick_released',
            'homezone_enter',
            'joystick_zone_enter',
            'homezone_exit',
            'homezone_exit',
        ]
        evt, = config_dict.get('classification_event', (None,))
        evt = evt or None
        assert evt is None or evt in allowed_event_classes
        self.classification_event: Optional[str] = evt
        if evt is not None:
            # always record events if classification is enabled
            self.record_events = True
            
            self.post_time = int(config_dict['post_time_ms'][0])
            self.bin_size = int(config_dict['bin_size_ms'][0])
            
            template_in_path = config_dict.get('template_in')
            if template_in_path in [None, [], ['']]:
                self.template_in_path: Optional[Path] = None
            else:
                assert template_in_path is not None
                self.template_in_path = Path(template_in_path[0])
                assert self.template_in_path.is_file()
            
            baseline = config_dict.get('baseline')
            if baseline in [None, [], [''], ['true']]:
                self.baseline: bool = True
            elif baseline in [['false']]:
                self.baseline = False
            else:
                raise ValueError(f"invalid setting for baseline `{baseline}`")
            
            classify_wait_time = config_dict.get('classify_wait_time')
            if classify_wait_time in [None, [], ['']]:
                self.classify_wait_time: float = self.post_time / 1000
            else:
                assert classify_wait_time is not None
                self.classify_wait_time = float(classify_wait_time[0])
            
            classify_wait_timeout: Optional[List[str]] = config_dict.get('classify_wait_timeout')
            if classify_wait_timeout in [None, [], ['']]:
                self.classify_wait_timeout: Optional[float] = None
            else:
                assert classify_wait_timeout is not None
                self.classify_wait_timeout = float(classify_wait_timeout[0])
            
            # local, plexon
            wait_mode: Literal['local', 'plexon'] = config_dict.get('classify_wait_mode', ['plexon'])[0] # type: ignore
            assert wait_mode in ['local', 'plexon']
            self.classify_wait_mode: Literal['local', 'plexon'] = wait_mode
            
            self.classify_reward_duration: Optional[Dict[Optional[str], float]] = self.parse_reward_durations(config_dict['correct_reward_dur'])
            
            labels_path: Optional[str] = config_dict.get('labels', [None])[0]
            if labels_path is None:
                self.labels: Optional[Dict[str, List[int]]] = None
            else:
                p = Path(labels_path)
                assert p.exists(), "labels file must exist if specified"
                with open(p) as f:
                    labels_data = hjson.load(f)
                self.labels = labels_data['channels']
        else:
            self.post_time = 1
            self.bin_size = 1
            self.template_in_path = None
            self.baseline = True
            self.classify_wait_time = 0.2
            self.classify_reward_duration = None
            self.labels = None
    
    def load_images(self, config_images: List[str], image_ratios: Optional[List[int]]):
        base = Path(__file__).parent / 'images_gen'
        # config_images = config_dict['images']
        def build_image_entry(i, name):
            name = name.strip()
            assert '.' not in name, f"{name}"
            
            obj = {}
            
            for color in ['white', 'red', 'green']:
                img = Image.open(base / f"./{color}/{name}.png")
                width = img.size[0]
                height = img.size[1]
                obj[color] = img
            
            obj[None] = obj['green']
            
            return name, {
                'width': width,
                'height': height,
                'img': obj,
                'nidaq_event_index': i+1,
            }
        
        images = dict(
            build_image_entry(i, x)
            for i, x in enumerate(config_images)
        )
        
        self.selectable_images = list(images)
        if image_ratios is None:
            self.image_selection_list = self.selectable_images
        else:
            assert len(image_ratios) == len(self.selectable_images)
            sel_list: List[str] = []
            for count, key in zip(image_ratios, self.selectable_images):
                sel_list.extend(key for _ in range(count))
            assert len(sel_list) == sum(image_ratios)
            self.image_selection_list = sel_list
        
        img = Image.open(base / './prepare.png')
        
        images['yPrepare'] = {
            'width': img.size[0],
            'height': img.size[1],
            'img': {None: img},
        }
        
        red = Image.open(base / './box_red.png')
        green = Image.open(base / './box_green.png')
        white = Image.open(base / './box_white.png')
        
        images['box'] = {
            'width': green.size[0],
            'height': green.size[1],
            'img': {
                'red': red,
                'green': green,
                'white': white,
                None: green,
            }
        }
        
        for image in images.values():
            image['tk'] = {
                k: ImageTk.PhotoImage(img)
                for k, img in image['img'].items()
            }
        
        self.images = images
    
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
    
    def parse_reward_durations(self, raw) -> Dict[Optional[str], float]:
        out = {}
        for cell in raw:
            cell = cell.strip()
            if not cell:
                continue
            if ':' in cell:
                a, b = cell.split(':')
                out[a] = float(b)
            else:
                out[None] = float(cell)
        
        # ensure there is either a default or all cues have durations
        if None not in out:
            for cue in self.selectable_images:
                assert cue in out, f"cue {cue} has no classify reward duration"
        
        return out
    
    def classifier_config(self, baseline=None):
        if baseline is None:
            baseline = self.baseline
        if baseline:
            # disable classification for baseline
            return {
                'type': '',
                'event_class': '',
                'baseline': True,
            }
        assert self.classification_event is not None
        conf = {
            'type': 'eucl',
            'event_class': self.classification_event,
            'baseline': self.baseline,
            'post_time': self.post_time,
            'bin_size': self.bin_size,
            'labels': self.labels,
            'template_path': self.template_in_path,
        }
        return conf
    
    def to_json_dict(self):
        out = {}
        for k, v in self.__dict__.items():
            if k in ['raw_config', 'images']:
                continue
            if isinstance(v, Path):
                v = str(v)
            out[k] = v
        return out
