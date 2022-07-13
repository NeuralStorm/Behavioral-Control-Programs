
from typing import Optional, Tuple, List, Dict

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
        self.event_spike_list: List[int] = []
        
        self.templates: Dict[str, List[float]] = {}
    
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
        self.event_spike_list.append(timestamp_ms)
    
    def build_psth(self) -> List[int]:
        psth = [0 for _ in range(self._bins_n)]
        if self._current_event is None:
            return psth
        _, event_ts = self._current_event
        for ts in self.event_spike_list:
            bin_ = (ts - event_ts) // self.bin_size
            try:
                psth[bin_] += 1
            except IndexError:
                pass
        
        return psth
    
    def classify(self) -> str:
        event_psth = self.build_psth()
        
        def calc_eucl_dist(template_psth):
            assert len(template_psth) == len(event_psth)
            acc = 0
            for a, b in zip(event_psth, template_psth):
                acc += (a - b)**2
            acc **= 0.5 # square root
            
            return acc
        
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

def build_templates(tilt_record, *, post_time: int, bin_size: int, events_record = None) -> Dict[str, List[float]]:
    """builds templates from a record of tilts and spikes
        
        tilt_record corresponsd to the `tilts` key in template files
        """
    psths: Dict[str, List[List[int]]] = {}
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
        
        psth = builder.build_psth()
        if tilt_type not in psths:
            psths[tilt_type] = []
        psths[tilt_type].append(psth)
    
    builder = EuclClassifier(post_time=post_time, bin_size=bin_size)
    # build_psth will create a list of zeros of the correct size since no event was created
    
    templates = {}
    for tilt_type, tilt_type_psths in psths.items():
        acc = builder.build_psth()
        n = 0
        for psth in tilt_type_psths:
            assert len(acc) == len(psth)
            for i, x in enumerate(psth):
                acc[i] += x
                n += 1
        template = [x / n for x in acc]
        templates[tilt_type] = template
    
    return templates
