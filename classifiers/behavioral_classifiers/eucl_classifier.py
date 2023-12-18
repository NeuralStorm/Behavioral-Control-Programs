
from typing import Optional, Tuple, List, Dict, Set, Union, Any
from pathlib import Path
import json
from collections import deque
from struct import Struct
from base64 import b85decode
import os

from .classifier import Classifier

from butil import EventReader

# chan -> spike frequency
PsthDict = Dict[str, List[Union[float, int]]]

class EuclClassifier(Classifier):
    """classifies tilts using a euclidian distance classifier
        """
    
    def __init__(self, *,
        post_time: int, bin_size: int,
        channel_filter: set[str] | None = None,
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
        # list of (channel, spike timestamps in ms)
        self.event_spike_list: deque[Tuple[str, int]] = deque()
        
        # event_type -> psth dict
        self.templates: Dict[str, PsthDict] = {}
        
        self.channel_filter: set[str] | None = channel_filter
        
        self._buffer_time = self.post_time*1.2
        if self._buffer_time < 2:
            self._buffer_time = 2
    
    def clear(self):
        self._current_event = None
    
    def event(self, *, event_type: str = '', timestamp: float):
        # convert to integer ms
        timestamp_ms = round(timestamp * 1000)
        
        self._current_event = (event_type, timestamp_ms)
    
    def spike(self, channel: str, timestamp: float):
        if self.channel_filter is not None and channel not in self.channel_filter:
            return
        
        timestamp_ms = round(timestamp * 1000)
        self.event_spike_list.append((channel, timestamp_ms))
        while timestamp_ms - self.event_spike_list[0][1] > self._buffer_time:
            self.event_spike_list.popleft()
    
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
    
    def classify_debug_info(self) -> tuple[str, Any]:
        debug_info = {}
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
        
        def calc_dist_from_zero(a):
            acc = 0
            for a in a:
                acc += a**2
            acc **= 0.5 # square root
            return acc
        
        def calc_eucl_dist(template: PsthDict):
            chan_dists = []
            for chan, template_psth in template.items():
                try:
                    chan_psth = event_psths[chan]
                except KeyError:
                    chan_dist = calc_dist_from_zero(template_psth)
                else:
                    chan_dist = calc_chan_eucl_dist(template_psth, chan_psth)
                
                chan_dists.append(chan_dist)
            
            dist = _avg(chan_dists)
            
            return dist
        
        dists = {
            event_type: calc_eucl_dist(template_psth)
            for event_type, template_psth in self.templates.items()
        }
        
        debug_info['dists'] = dists
        debug_info['templates'] = self.templates
        debug_info['event'] = event_psths
        # debug_info['spike_count'] = len(self.event_spike_list)
        dbg_path = os.environ.get('eucl_debug')
        if dbg_path:
            import time
            dbg: Any = {
                'now': time.perf_counter(),
                'current_event': self._current_event,
                'dists': dists,
            }
            if dbg_path.startswith('!'):
                dbg['spikes'] = sorted(self.event_spike_list)
            with open(dbg_path.lstrip('!'), 'a') as f:
                json.dump(dbg, f)
        
        assert dists
        closest_event_type, _ = min(dists.items(), key=lambda x: x[1])
        
        return closest_event_type, debug_info

def _build_templates_from_psths(
    psths: Dict[str, List[EuclClassifier]],
    builder: EuclClassifier,
):
    def average_psths(psths: List[List[int]]) -> List[int]:
        acc = builder.zero_psth()
        
        for psth in psths:
            assert len(psth) == len(acc)
            for i, x in enumerate(psth):
                acc[i] += x
        # return [(x / n, n) for x in acc]
        return [x for x in acc]
    
    templates = {}
    for event_class, events in psths.items():
        # events is a list of classifiers, one for each event
        chans = {}
        chan_keys = set()
        for classifier in events:
            chan_keys |= classifier.get_keys()
        
        for chan_key in chan_keys:
            chan_psths = [c.build_key_psth(chan_key) for c in events]
            chans[chan_key] = average_psths(chan_psths)
        
        templates[event_class] = {
            'spike_counts': chans,
            'event_count': len(events),
        }
    
    return templates

def build_templates_from_new_events_file(*,
    ts_list: list[tuple[str, float]],
    events_path: Path,
    template_path: Path,
    event_class: Optional[str],
    post_time: int, bin_size: int,
    labels: Optional[Dict[str, List[int]]],
):
    if labels is None:
        chan_filter: set[str] | None = None
    else:
        chan_filter = set()
        if labels is not None:
            for channel, units in labels.items():
                for unit in units:
                    chan_filter.add(f"{channel}_{unit}")
    
    def get_spikes():
        unpacker = Struct('<d')
        with EventReader(path=events_path) as reader:
            for rec in reader.read_records():
                rt = rec.get('type')
                if rt != 'spikes':
                    continue
                
                def get_chunk_spikes():
                    """get spikes for the next chunk and put the timestamps in order"""
                    for chan, v in rec['s'].items():
                        if chan_filter is not None and chan not in chan_filter:
                            continue
                        # remove unsorted spikes
                        if chan.endswith('_0'):
                            continue
                        for s in unpacker.iter_unpack(b85decode(v)):
                            ts, = s
                            # print(k, ts)
                            yield chan, ts
                
                chunk_spikes = list(get_chunk_spikes())
                chunk_spikes.sort(key=lambda x: x[1])
                yield from chunk_spikes
    
    ts_list.sort(key=lambda x: x[1])
    def get_events():
        """yields (type, timestamp, extra)"""
        ts_i = 0
        for spike in get_spikes():
            # print(spike)
            
            while ts_i < len(ts_list) and ts_list[ts_i][1] < spike[1]:
                yield ('e', ts_list[ts_i][1], ts_list[ts_i][0])
                ts_i += 1
            yield ('s', spike[1], spike[0])
        
        while ts_i < len(ts_list):
            yield ('e', ts_list[ts_i][1], ts_list[ts_i][0])
            ts_i += 1
    
    psths: Dict[str, List[EuclClassifier]] = {}
    
    def build_psth(buf: 'deque[tuple[str, float, Any]]', event_ts: float) -> EuclClassifier:
        builder = EuclClassifier(
            post_time=post_time, bin_size=bin_size,
            channel_filter = chan_filter,
        )
        
        builder.event(timestamp = event_ts)
        
        for t, ts, ch in buf:
            if t != 's':
                continue
            builder.spike(ch, ts)
        
        return builder
    
    chan_list = set()
    max_dist = post_time/1000*1.1 + 0.500
    buf: 'deque[tuple[str, float, Any]]' = deque()
    def pop_event():
        event = buf.popleft()
        if event[0] == 's':
            chan_list.add(event[2])
        if event[0] == 'e':
            et = event[2]
            psth = build_psth(buf, event[1])
            if et not in psths:
                psths[et] = []
            psths[et].append(psth)
    
    for event in get_events():
        buf.append(event)
        while event[1] - buf[0][1] > max_dist:
            pop_event()
    while buf:
        pop_event()
    
    templates = _build_templates_from_psths(
        psths = psths,
        builder = EuclClassifier(post_time=post_time, bin_size=bin_size),
    )
    
    if chan_filter is not None:
        chan_list = chan_filter
    
    builder = EuclClassifier(post_time=post_time, bin_size=bin_size)
    for _cue, template in templates.items():
        template_chans = set(template['spike_counts'])
        # add zeros for channels in the channel filter but that had no spikes
        for chan in chan_list - template_chans:
            template['spike_counts'][chan] = builder.zero_psth()
        
        def key(x):
            a, b = x[0].split('_')
            return int(a), int(b)
        template['spike_counts'] = {k: v for k, v in sorted(template['spike_counts'].items(), key=key)}
        
        if chan_filter is not None:
            assert set(template) == chan_filter
        
        templates[_cue] = template
    
    if chan_filter is None:
        chan_filter_list = None
    else:
        chan_filter_list = list(chan_filter)
    
    # list of all channels in the output
    out_chans_list = set()
    for _, chan_templates in templates.items():
        out_chans_list.update(chan_templates['spike_counts'].keys())
    def sort_key(x):
        try:
            a, b = x.split('_')
            return int(a), int(b)
        except:
            return x
    chan_filter_list = sorted(out_chans_list, key=sort_key)
    
    #"templates": {
    #  "sun": { cue
    #    "1_2": [ channel_unit
    #      0.0,
    #      0.03333333333333333,
    #      0.0,
    #      0.0,
    #      0.0,
    #      0.0,
    #      0.0,
    #      0.0,
    #      0.0,
    #      0.0
    #    ],
    
    out_data = {
        'type': 'eucl',
        'event_class': event_class,
        'wait_time': post_time,
        'post_time': post_time,
        'bin_size': bin_size,
        'channel_filter': chan_filter_list,
        'templates': templates,
    }
    
    with open(template_path, 'w', encoding='utf8', newline='\n') as f:
        json.dump(out_data, f, indent=2)
    
    return out_data
