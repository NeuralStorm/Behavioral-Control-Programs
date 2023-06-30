
from typing import Optional, Any, Dict, List
from pathlib import Path
import json

import hjson

class Config:
    ctype: str
    baseline: bool
    event_class: str

class EuclConfig(Config):
    post_time: int
    bin_size: int
    template_path: Optional[Path]
    labels: Optional[Any]
    
    def __init__(self):
        self.ctype: str = 'eucl'
    
    def load_templates(self) -> Optional[Any]:
        if self.template_path is not None:
            with open(self.template_path, encoding='utf8', newline='\n') as f:
                template_in = json.load(f)
            def validate_key(k, expected=None):
                if expected is None:
                    expected = self.__dict__[k]
                actual = template_in['info'][k]
                if expected != actual:
                    raise ValueError(f"template settings mismatch `{k}` current: {expected} template: {actual}")
            
            validate_key('post_time')
            validate_key('bin_size')
            validate_key('event_class')
            # assert self.post_time == template_in['info']['post_time'], f"{post_time} {template_in['info']['post_time']}"
            # assert bin_size == template_in['info']['bin_size'], f"{bin_size} {template_in['info']['bin_size']}"
            # assert event_class == template_in['info']['event_class'], f"mismatched event class {event_class} {template_in['info']['event_class']}"
            # templates = template_in['templates']
            # conf.templates = templates
            # return templates
            return template_in['templates']
        else:
            assert self.baseline
            return None
        
        # return template_in

class RandomConfig(Config):
    event_types: List[str]
    def __init__(self):
        self.ctype: str = 'random'

def load_config(config: Dict[str, Any]) -> Config:
    ctype: str = config['type']
    assert isinstance(ctype, str)
    baseline: bool = config['baseline']
    assert isinstance(baseline, bool)
    
    event_class = config['event_class']
    assert isinstance(event_class, str)
    
    if ctype == '':
        assert baseline
        nconfig = Config()
        nconfig.baseline = True
        nconfig.ctype = ''
        nconfig.event_class = ''
        return nconfig
    
    def get_template_path():
        _template_path = config['template_path']
        assert _template_path is None or isinstance(_template_path, str) or isinstance(_template_path, Path)
        if _template_path is None:
            template_path: Optional[Path] = None
        else:
            template_path = Path(_template_path)
        
        return template_path
    
    if ctype in ['psth', 'eucl']:
        conf = EuclConfig()
        conf.baseline = baseline
        conf.event_class = event_class
        
        conf.post_time = config['post_time']
        assert isinstance(conf.post_time, int)
        conf.bin_size = config['bin_size']
        assert isinstance(conf.bin_size, int)
        
        conf.template_path = get_template_path()
        
        labels = config['labels']
        if isinstance(labels, str) or isinstance(labels, Path):
            labels_path = Path(labels)
            assert labels_path.is_file()
            with open(labels_path, encoding='utf8', newline='\n') as f:
                data = hjson.load(f)
            conf.labels = data['channels']
        else:
            conf.labels = labels
        
        return conf
    elif ctype in ['random']:
        rconf = RandomConfig()
        rconf.event_class = event_class
        rconf.event_types = config['event_types']
        return rconf
    else:
        raise ValueError(f"unknown classifier `{ctype}`")
