
from os import PathLike
from typing import Optional, Any, Dict
from pathlib import Path
import json
import time
import logging
from contextlib import ExitStack

logger = logging.getLogger(__name__)

from butil import EventFile

from ..classifier import Classifier
from ..eucl_classifier import EuclClassifier, build_templates_from_new_events_file
from ..random_classifier import RandomClassifier

from .events_file import EventsFileWriter

def from_templates(templates: Dict[str, Any]) -> Classifier:
    ctype = templates['type']
    match ctype:
        case 'eucl':
            template_chans = set()
            for _cue, template in templates['templates'].items():
                for chan_str in template['spike_counts'].keys():
                    template_chans.add(chan_str)
            
            classifier = EuclClassifier(
                post_time = templates['post_time'],
                bin_size = templates['bin_size'],
                channel_filter = template_chans,
            )
            def prep_templates():
                for cue, cue_templates in templates['templates'].items():
                    n = cue_templates['event_count']
                    def build_cue_template():
                        for chan, counts in cue_templates['spike_counts'].items():
                            yield chan, [x / n for x in counts]
                    yield cue, dict(build_cue_template())
            classifier.templates = dict(prep_templates())
            
            return classifier
        case 'random':
            assert isinstance(templates['event_types'], list)
            return RandomClassifier(templates['event_types'])
        case _:
            raise ValueError("Unknown classifier type {ctype}")

class Helper:
    def __init__(self, *,
        templates: Optional[Any] = None,
        event_file: Optional[EventFile] = None,
        wait_timeout: Optional[float] = None,
    ):
        self._stack = ExitStack()
        ec = self._stack.enter_context
        
        if templates is None:
            self.classifier: Optional[Classifier] = None
            self.wait_time = 0
            self.event_class = ''
        else:
            self.event_class: str = templates['event_class']
            self.wait_time: float = templates['wait_time'] / 1000
            self.classifier = from_templates(templates)
        self.wait_timeout: Optional[float] = wait_timeout
        
        if event_file is not None:
            self._events_file = ec(EventsFileWriter(callback=event_file.write_record))
        else:
            self._events_file: Optional[EventsFileWriter] = None
        
        # set to the timestamp of the last received event from plexon
        self._last_external_ts: Optional[float] = None
        # set to the last timestamp of the last received classification event of each type
        # e.g. {'joystick_pull': 10}
        self._last_classification_events: Dict[str, float] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self._stack.__exit__(*exc)
    
    def close(self):
        self._stack.close()
    
    def trial_start(self):
        """call at the start of each trial"""
        if self.classifier is not None:
            self.classifier.clear()
        
        self._last_classification_events.clear()
    
    def any_event(self, timestamp: float):
        """call when any timestamped event is received from external system"""
        self._last_external_ts = timestamp
    
    def event(self, event_type: str, event_class: str, timestamp: float):
        """call when classification event occurs"""
        self._last_classification_events[event_class] = timestamp
        if self.classifier is not None and self.event_class == event_class:
            self.classifier.event(timestamp=timestamp)
        
        if self._events_file is not None:
            self._events_file.write_event(
                event_type = event_type,
                timestamp = timestamp,
                event_class = event_class,
            )
    
    def spike(self, channel: int, unit: int, timestamp: float):
        """call when a spike is received"""
        out_chan = f'{channel}_{unit}'
        if self.classifier is not None:
            self.classifier.spike(
                channel = out_chan,
                timestamp = timestamp,
            )
        
        if self._events_file is not None:
            self._events_file.write_spike(
                channel = out_chan,
                timestamp = timestamp,
            )
    
    def wait_for_event(self, wait_time: float, timeout: Optional[float] = None):
        """yields until an external timestamp `wait_time` after event or timeout"""
        local_start = time.perf_counter()
        event_time = None
        last_ts = None
        while True:
            if timeout is not None:
                now = time.perf_counter()
                if now - local_start > timeout:
                    logger.warning("external event wait timed out")
                    return {
                        'error': 'timeout',
                        'event_class': self.event_class,
                        'event_time': event_time,
                        'last_event_ts': last_ts,
                        'local_start': local_start,
                        'local_end': now,
                        'local_dur': now - local_start,
                    }
            
            last_ts = self._last_external_ts
            if last_ts is None:
                yield
                continue
            if self.event_class not in self._last_classification_events:
                yield
                continue
            event_time = self._last_classification_events[self.event_class]
            time_since_evt = last_ts - event_time
            
            if time_since_evt >= wait_time:
                break
            yield
        
        now = time.perf_counter()
        return {
            'event_class': self.event_class,
            'event_time': event_time,
            'last_event_ts': last_ts,
            'time_since_event': time_since_evt,
            'local_start': local_start,
            'local_end': now,
            'local_dur': now - local_start,
        }
    
    def classify(self, *,
        wait: bool = True
    ):
        if self.classifier is None:
            return {'error': 'no_classifier'}
        if wait and self.wait_time != 0:
            wait_res = yield from self.wait_for_event(self.wait_time, timeout=self.wait_timeout)
            if 'error' in wait_res:
                return {
                    'error': 'timeout',
                    '_wait_res': wait_res,
                }
        else:
            wait_res = None
        
        prediction, debug_info = self.classifier.classify_debug_info()
        res = {
            'prediction': prediction,
            '_wait_res': wait_res,
            '_classify_debug': debug_info,
        }
        return res
