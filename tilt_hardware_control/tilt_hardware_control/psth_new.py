
from typing import Optional, Tuple, List, Dict, Set
from pathlib import Path
import json

# chan -> spike frequency
PsthDict = Dict[str, List[float | int]]

class EuclClassifier:
    """classifies tilts using a euclidian distance classifier
        """
    
    def __init__(self, *, post_time: int, bin_size: int):
        """
            post_time: time after event to classify in in ms
            bin_size: in ms
            """
        
        assert post_time % bin_size == 0
        bins_n = post_time // bin_size
        self.post_time = post_time
        self._bins_n = bins_n
        self.bins = [0 for _ in range(bins_n)]
        self.bin_size = bin_size
        
        # (event type, timestamp in ms)
        self._current_event: Optional[Tuple[str, int]] = None
        # list of spike timestamps in ms
        self.event_spike_list: List[Tuple[str, int]] = []
        
        # event_type -> psth dict
        self.templates: Dict[str, PsthDict] = {}
    
    def clear(self):
        self._current_event = None
        self.event_spike_list = []
    
    def event(self, event_type: str, timestamp: float):
        # convert to integer ms
        timestamp_ms = round(timestamp * 1000)
        
        self._current_event = (event_type, timestamp_ms)
        # self.event_spike_list = []
    
    def spike(self, channel: int, unit: int, timestamp: float):
        timestamp_ms = round(timestamp * 1000)
        key = f"{channel}_{unit}"
        self.event_spike_list.append((key, timestamp_ms))
    
    def zero_psth(self) -> List[int]:
        """creates a list of the correct length filled with zeros"""
        return [0 for _ in range(self._bins_n)]
    
    def get_keys(self) -> Set[str]:
        return set(k for k, _ in self.event_spike_list)
    
    def build_key_psth(self, target_key: Optional[str] = None) -> List[int]:
        psth = self.zero_psth()
        if self._current_event is None:
            return psth
        _, event_ts = self._current_event
        for key, ts in self.event_spike_list:
            if target_key is None or key != target_key:
                continue
            
            bin_ = (ts - event_ts) // self.bin_size
            try:
                psth[bin_] += 1
            except IndexError:
                pass
        
        return psth
    
    def build_per_key_psth(self) -> PsthDict:
        keys = self.get_keys()
        psths = {
            key: self.build_key_psth(target_key=key)
            for key in keys
        }
        return psths
    
    def classify(self) -> str:
        event_psths = self.build_per_key_psth()
        
        def _avg(xs):
            if not xs: # return 0 if no items
                return 0
            return sum(xs) / len(xs)
        
        def calc_chan_eucl_dist(a, b):
            assert len(a) == len(b)
            acc = 0
            for a, b in zip(a, b):
                acc += (a - b)**2
            acc **= 0.5 # square root
            return acc
        
        def calc_eucl_dist(template: PsthDict):
            chan_dists = []
            for chan, template_psth in template.items():
                try:
                    chan_psth = event_psths[chan]
                except KeyError:
                    continue
                
                chan_dist = calc_chan_eucl_dist(template_psth, chan_psth)
                chan_dists.append(chan_dist)
            
            dist = _avg(chan_dists)
            
            return dist
        
        dists = {
            event_type: calc_eucl_dist(template_psth)
            for event_type, template_psth in self.templates.items()
        }
        
        closest_event_type, _ = min(dists.items(), key=lambda x: x[1])
        
        return closest_event_type
    
    def build_template_from_record(self, tilt_record):
        self.templates = build_templates(
            tilt_record,
            post_time = self.post_time,
            bin_size = self.bin_size,
        )
    
    def build_template_from_events(self, tilt_record, events_record):
        self.templates = build_templates(
            tilt_record,
            post_time = self.post_time,
            bin_size = self.bin_size,
            events_record = events_record,
        )

def _find_tilt(events):
    for evt in events:
        if evt.get('tilt_type') is not None:
            return evt['tilt_type'], evt['time']
    raise ValueError('could not find tilt in event list')

def build_templates(tilt_record, *, post_time: int, bin_size: int, events_record = None) -> Dict[str, PsthDict]:
    """builds templates from a record of tilts and spikes
        
        tilt_record corresponsd to the `tilts` key in meta files
        events_record is the entire events file
        """
    psths: Dict[str, List[EuclClassifier]] = {}
    for tilt in tilt_record:
        if tilt.get('paused'):
            continue
        if tilt.get('failed'):
            continue
        
        events = [
            evt for evt in tilt['events']
            if evt['relevent'] is True
        ]
        
        _evt_tilt_type, tilt_time = _find_tilt(events)
        
        tilt_type = tilt['tilt_name']
        
        builder = EuclClassifier(post_time=post_time, bin_size=bin_size)
        builder.event(tilt_type, tilt_time)
        
        if events_record is not None:
            events = events_record
        
        for evt in events:
            if evt['type'] == 'spike' and evt['relevent'] is True:
                builder.spike(evt['channel'], evt['unit'], evt['time'])
        
        if tilt_type not in psths:
            psths[tilt_type] = []
        psths[tilt_type].append(builder)
    
    builder = EuclClassifier(post_time=post_time, bin_size=bin_size)
    # build_psth will create a list of zeros of the correct size since no event was created
    
    templates = {}
    for tilt_type, classifiers in psths.items():
        def average_psths(psths: List[List[int|float]]) -> List[float]:
            acc = builder.zero_psth()
            n = 0
            
            for psth in psths:
                assert len(psth) == len(acc)
                for i, x in enumerate(psth):
                    acc[i] += x
                    n += 1
            return [x / n for x in acc]
        
        chans = {}
        chan_keys = set()
        for classifier in classifiers:
            chan_keys |= classifier.get_keys()
        
        for chan_key in chan_keys:
            chan_psths = [c.build_key_psth(chan_key) for c in classifiers]
            chans[chan_key] = average_psths(chan_psths)
        
        templates[tilt_type] = chans
    
    return templates

def build_template_file(meta_path: Path, events_path: Path, template_path: Path, *, post_time: int, bin_size: int):
    with open(meta_path) as f:
        meta_data = json.load(f)
    with open(events_path) as f:
        events = json.load(f)
    
    templates = build_templates(
        tilt_record = meta_data['tilts'],
        events_record = events,
        post_time = post_time,
        bin_size = bin_size,
    )
    
    out_data = {
        'info': {
            'post_time': post_time,
            'bin_size': bin_size,
        },
        'templates': templates,
    }
    
    with open(template_path, 'w') as f:
        json.dump(out_data, f, indent=2)
