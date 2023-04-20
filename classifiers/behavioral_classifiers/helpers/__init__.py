
from os import PathLike
from typing import Optional, Any, Dict
from pathlib import Path
import json
import time
import logging
from contextlib import ExitStack

logger = logging.getLogger(__name__)

from ..classifier import Classifier
from ..eucl_classifier import EuclClassifier, build_templates_from_new_events_file
from ..random_classifier import RandomClassifier

from .config import load_config, Config, EuclConfig, RandomConfig
from .events_file import EventsFileWriter

classifier_map = {
    'eucl': EuclClassifier,
    'psth': EuclClassifier,
    'random': RandomClassifier,
}

def from_config(config: Dict[str, Any]) -> Classifier:
    _config = load_config(config)
    return classifier_from_config(_config)

def classifier_from_config(config: Config) -> Classifier:
    # _config = load_config(config)
    
    if isinstance(config, EuclConfig):
        classifier = EuclClassifier(
            post_time = config.post_time,
            bin_size = config.bin_size,
            labels = config.labels,
        )
        
        templates = config.load_templates()
        if templates is not None:
            classifier.templates = templates
        
        return classifier
    elif isinstance(config, RandomConfig):
        return RandomClassifier(config.event_types)
    else:
        assert False

def generate_template_with_config(*, config: Config, events_file: Path, template_out: Path):
    if isinstance(config, EuclConfig):
        build_templates_from_new_events_file(
            events_path = events_file,
            template_path = template_out,
            event_class = config.event_class,
            post_time = config.post_time,
            bin_size = config.bin_size,
            labels = config.labels,
        )
    else:
        raise ValueError(f"Can't generate template with classifier {config}")

def generate_template_main(*, config: Dict[str, Any], events_file: Path, template_out: Path):
    _config = load_config(config)
    
    generate_template_with_config(config=_config, events_file=events_file, template_out=template_out)

class Helper:
    def __init__(self, *,
        config: Dict[str, Any],
        events_file_path: Optional[PathLike],
    ):
        self._stack = ExitStack()
        ec = self._stack.enter_context
        
        _config: Config = load_config(config)
        if not _config.baseline:
            self.classifier: Optional[Classifier] = classifier_from_config(_config)
        else:
            self.classifier = None
        self.event_class: str = _config.event_class
        
        if events_file_path is None:
            self.events_file_path: Optional[Path] = None
            self.events_file: Optional[EventsFileWriter] = None
        else:
            self.events_file_path = Path(events_file_path)
            self.events_file = ec(EventsFileWriter(path=self.events_file_path))
        
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
        
        if self.events_file is not None:
            self.events_file.write_event(
                event_type = event_type,
                timestamp = timestamp,
                event_class = event_class,
            )
    
    def spike(self, channel: int, unit: int, timestamp: float):
        """call when a spike is received"""
        if self.classifier is not None:
            self.classifier.spike(
                channel = channel,
                unit = unit,
                timestamp = timestamp,
            )
        
        if self.events_file is not None:
            self.events_file.write_spike(
                channel = channel,
                unit = unit,
                timestamp = timestamp,
            )
    
    def external_wait(self, wait_time: float, timeout: Optional[float] = None):
        """yields until an external timestamp `wait_time` after event or timeout"""
        local_start = time.perf_counter()
        while True:
            if timeout is not None:
                if time.perf_counter() - local_start > timeout:
                    logger.warning("plexon event wait timed out")
                    return None
            
            if self._last_external_ts is None:
                yield
                continue
            if self.event_class not in self._last_classification_events:
                yield
                continue
            time_since_evt = self._last_external_ts - self._last_classification_events[self.event_class]
            
            if time_since_evt >= wait_time:
                break
            yield
        return time_since_evt
