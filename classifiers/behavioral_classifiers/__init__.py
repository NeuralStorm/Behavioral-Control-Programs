
from typing import Dict, Any, Optional
from pathlib import Path
import json

from .classifier import Classifier
from .eucl_classifier import EuclClassifier
from .random_classifier import RandomClassifier
from .events_file import EventsFileWriter

classifier_map = {
    'eucl': EuclClassifier,
    'psth': EuclClassifier,
    'random': RandomClassifier,
}

def from_config(config: Dict[str, Any], template_path: Optional[Path], baseline: bool = True) -> Classifier:
    ctype = config['type']
    if ctype in ['psth', 'eucl']:
        post_time = config['post_time']
        bin_size = config['bin_size']
        
        classifier = EuclClassifier(
            post_time = post_time,
            bin_size = bin_size,
            labels = config.get('labels'),
        )
        
        if template_path is not None:
            with open(template_path, encoding='utf8') as f:
                template_in = json.load(f)
            assert post_time == template_in['info']['post_time'], f"{post_time} {template_in['info']['post_time']}"
            assert bin_size == template_in['info']['bin_size'], f"{bin_size} {template_in['info']['bin_size']}"
            templates = template_in['templates']
            classifier.templates = templates
        else:
            assert baseline
        
        return classifier
    elif ctype in ['random']:
        rclassifier = RandomClassifier(config['event_types'])
        return rclassifier
    else:
        raise ValueError(f"unknown classifier `{ctype}`")
