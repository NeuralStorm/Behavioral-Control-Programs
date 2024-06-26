
from typing import Optional, Tuple, List, Dict, Set, Union, Any
from pathlib import Path
import json
from collections import deque
from struct import Struct
from base64 import b85decode
import os
from math import isclose

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
        self.post_time: float = post_time / 1000
        self.bin_size: float = bin_size / 1000
        bins_n: int = round(self.post_time / self.bin_size)
        
        self._bins_n: int = bins_n
        self.bins: list[int] = [0 for _ in range(bins_n)]
        
        # (event type, timestamp in ms)
        self._current_event: Optional[Tuple[str, float]] = None
        # list of (channel, spike timestamps in ms)
        self.event_spike_list: deque[Tuple[str, float]] = deque()
        
        # event_type -> psth dict
        self.templates: Dict[str, PsthDict] = {}
        
        self.channel_filter: set[str] | None = channel_filter
        
        self._buffer_time: float | None = self.post_time*1.5
        if self._buffer_time < 2:
            self._buffer_time = 2
    
    def clear(self):
        self._current_event = None
    
    def event(self, *, event_type: str = '', timestamp: float):
        self._current_event = (event_type, timestamp)
    
    def spike(self, channel: str, timestamp: float):
        if self.channel_filter is not None and channel not in self.channel_filter:
            return
        
        self.event_spike_list.append((channel, timestamp))
        while self._buffer_time is not None and timestamp - self.event_spike_list[0][1] > self._buffer_time:
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
            
            d = ts - event_ts
            if d < 0:
                continue
            
            bin_ = d / self.bin_size
            # is_on_left_edge = bin_.is_integer()
            bin_ = int(bin_)
            
            # make right edge inclusive instead of left
            # if is_on_left_edge:
            #     bin_ -= 1
            
            if bin_ < 0:
                continue
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
        
        def calc_chan_eucl_dist(a, b):
            assert len(a) == len(b)
            acc = 0
            for a, b in zip(a, b):
                acc += (a - b)**2
            acc **= 0.5 # square root
            return acc
        
        def calc_eucl_dist(template: PsthDict, new=False):
            # combined list of counts for all channels
            event_counts: list[float] = []
            template_counts: list[float] = []
            
            for chan, template_psth in template.items():
                template_counts.extend(template_psth)
                try:
                    chan_psth = event_psths[chan]
                except KeyError:
                    event_counts.extend([0]*len(template_psth))
                else:
                    event_counts.extend(chan_psth)
                
                assert len(event_counts) == len(template_counts)
            
            dist = calc_chan_eucl_dist(event_counts, template_counts)
            
            return dist
        
        dists = {
            event_type: calc_eucl_dist(template_psth, new=True)
            for event_type, template_psth in self.templates.items()
        }
        
        debug_info['dists'] = dists
        debug_info['templates'] = self.templates
        debug_info['event'] = event_psths
        
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
    template_path: Optional[Path] = None,
    event_class: Optional[str],
    post_time: int, bin_size: int,
    labels: Optional[Dict[str, List[int]]],
):
    def map_channel_name(k):
        channel, unit = k.split('_')
        return f"{channel:0>4}_{unit:0>4}"
    
    if labels is None:
        chan_filter: set[str] | None = None
    else:
        chan_filter = set()
        if labels is not None:
            for channel, units in labels.items():
                if units is None:
                    chan_filter.add(channel)
                    continue
                for unit in units:
                    chan_filter.add(f"{channel:0>4}_{unit:0>4}")
    
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
                        chan = map_channel_name(chan)
                        if chan_filter is not None and chan not in chan_filter:
                            continue
                        # remove unsorted spikes
                        if chan.endswith('_0') or chan.endswith('_0000'):
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
        # disable discarding of old spikes to ensure
        # all spikes in buf are processed, even if the classifier
        # would normally keep a window smaller than buf covers
        builder._buffer_time = None
        
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
            assert set(template['spike_counts']) == chan_filter
        
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
    
    if template_path is not None:
        with open(template_path, 'w', encoding='utf8', newline='\n') as f:
            json.dump(out_data, f, indent=2)
    
    return out_data
