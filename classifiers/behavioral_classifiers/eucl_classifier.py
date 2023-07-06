
from typing import Optional, Tuple, List, Dict, Set, Union, Any
from pathlib import Path
import json
import bz2
from collections import deque

from .classifier import Classifier

from butil import EventReader

# chan -> spike frequency
PsthDict = Dict[str, List[Union[float, int]]]

class EuclClassifier(Classifier):
    """classifies tilts using a euclidian distance classifier
        """
    
    def __init__(self, *,
        post_time: int, bin_size: int,
        labels: Optional[Dict[str, List[int]]] = None,
    ):
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
        
        self.labels: Optional[Dict[str, List[int]]] = labels
    
    def clear(self):
        self._current_event = None
        self.event_spike_list = []
    
    def event(self, *, event_type: str = '', timestamp: float):
        # convert to integer ms
        timestamp_ms = round(timestamp * 1000)
        
        self._current_event = (event_type, timestamp_ms)
        # self.event_spike_list = []
    
    def spike(self, channel: int, unit: int, timestamp: float):
        if self.labels is not None:
            if str(channel) in self.labels and unit in self.labels[str(channel)]:
                pass
            else:
                return
        
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
        
        assert dists
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
        builder.event(timestamp = tilt_time)
        
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
        def average_psths(psths: List[List[Union[int, float]]]) -> List[float]:
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

def _build_templates_from_psths(
    psths: Dict[str, List[EuclClassifier]],
    builder: EuclClassifier,
):
    # builder = EuclClassifier(post_time=post_time, bin_size=bin_size)
    # build_psth will create a list of zeros of the correct size since no event was created
    
    def average_psths(psths: List[List[int]]) -> List[float]:
        acc = builder.zero_psth()
        n = 0
        
        for psth in psths:
            assert len(psth) == len(acc)
            for i, x in enumerate(psth):
                acc[i] += x
                n += 1
        return [x / n for x in acc]
        # return [x for x in acc]
    
    templates = {}
    for tilt_type, classifiers in psths.items():
        chans = {}
        chan_keys = set()
        for classifier in classifiers:
            chan_keys |= classifier.get_keys()
        
        for chan_key in chan_keys:
            chan_psths = [c.build_key_psth(chan_key) for c in classifiers]
            chans[chan_key] = average_psths(chan_psths)
        
        templates[tilt_type] = chans
    
    return templates

def group_trials(data):
    trial_events = None
    for x in data:
        if x.get('name') == 'trial_start':
            if trial_events:
                yield trial_events
            trial_events = []
        if trial_events is not None:
            trial_events.append(x)
    
    if trial_events:
        yield trial_events

def get_rel_events(data, event_class):
    """get events to use from each trial that are of event_class"""
    for trial in group_trials(data):
        # print(trial)
        comp = None
        for e in trial:
            if e.get('name') == 'task_completed':
                comp = e
                break
        if comp is None:
            continue
        # print(comp)
        if comp['info']['success']:
            skip_until = None
            if event_class == 'joystick_pulled':
                skip_until = 'go_cue_shown'
            
            for e in data:
                if skip_until:
                    if e.get('name') == skip_until:
                        skip_until = None
                elif e.get('event_class') == event_class:
                    yield e
                    break
        
        # yield None

def build_templates_from_new_events_file(*,
    events_path: Path,
    template_path: Path,
    event_class: Optional[str],
    post_time: int, bin_size: int,
    labels: Optional[Dict[str, List[int]]],
):
    # with bz2.open(events_path, 'rt', encoding='utf8', newline='\n') as f:
    #     events_data = json.load(f)
    
    with EventReader(path=events_path) as reader:
        rel_events = list(get_rel_events(reader.read_records(), event_class))
        rel_event_times = set(x['ext_t'] for x in rel_events)
    
    def get_events():
        with EventReader(path=events_path) as reader:
            for rec in reader.read_records():
                if 'type' in rec and 'ext_t' in rec:
                    yield rec
        # with bz2.open(events_path, 'rt', encoding='utf8', newline='\n') as f:
        #     try:
        #         next(f) # skip [
        #     except StopIteration:
        #         assert False
        #     while True:
        #         try:
        #             l = next(f)
        #         except StopIteration:
        #             break
        #         l = l.rstrip('\r\n')
        #         if l == ']':
        #             break
        #         if l == '':
        #             continue
        #         l = l.rstrip(',')
        #         yield json.loads(l)
    
    psths: Dict[str, List[EuclClassifier]] = {}
    
    def is_rel_event(rec):
        return rec['ext_t'] in rel_event_times and rec['event_class'] == event_class
        # if rec['type'] != 'event':
        #     return False
        
        # correct_class = rec.get('event_class') == event_class
        # if not correct_class:
        #     return False
        
        # return True
    
    def build_psth(buf: 'deque[Dict[str, Any]]', event: Dict[str, Any]) -> EuclClassifier:
        builder = EuclClassifier(post_time=post_time, bin_size=bin_size, labels=labels)
        
        builder.event(timestamp = event['ext_t'])
        
        for rec in buf:
            if rec['type'] != 'spike':
                continue
            builder.spike(rec['channel'], rec['unit'], rec['ext_t'])
        
        return builder
    
    max_dist = post_time/1000*1.1
    buf: 'deque[Dict[str, Any]]' = deque()
    for event in get_events():
        buf.append(event)
        while event['ext_t'] - buf[0]['ext_t'] > max_dist:
            event = buf.popleft()
            if is_rel_event(event):
                et = event['event_type']
                psth = build_psth(buf, event)
                if et not in psths:
                    psths[et] = []
                psths[et].append(psth)
    
    # def get_spikes_near(t):
    #     # convert to seconds and double
    #     max_dist = post_time/1000*2
    #     for rec in events_data:
    #     # for rec in get_events():
    #         if rec['type'] != 'spike':
    #             continue
    #         # print(abs(t - rec['ext_t']))
    #         if abs(t - rec['ext_t']) < max_dist:
    #             yield rec
    
    # event_recs = (x for x in events_data if is_rel_event(x))
    # # event_recs = (x for x in get_events() if is_rel_event(x))
    # # print(list(event_recs))
    # for event_rec in event_recs:
    #     builder = EuclClassifier(post_time=post_time, bin_size=bin_size, labels=labels)
        
    #     builder.event(timestamp = event_rec['ext_t'])
        
    #     # print(list(get_spikes_near(event_rec['ext_t'])))
    #     for rec in get_spikes_near(event_rec['ext_t']):
    #         builder.spike(rec['channel'], rec['unit'], rec['ext_t'])
        
    #     et = event_rec['event_type']
    #     if et not in psths:
    #         psths[et] = []
    #     psths[et].append(builder)
    
    templates = _build_templates_from_psths(
        psths = psths,
        builder = EuclClassifier(post_time=post_time, bin_size=bin_size, labels=labels),
    )
    
    out_data = {
        'info': {
            'post_time': post_time,
            'bin_size': bin_size,
            'event_class': event_class,
            'labels': labels,
        },
        'templates': templates,
    }
    
    with open(template_path, 'w', encoding='utf8', newline='\n') as f:
        json.dump(out_data, f, indent=2)
