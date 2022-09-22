
import hashlib
from pathlib import Path
import logging

def _hash_file(path: Path, fhash):
    if path.is_dir():
        def gen():
            for sub_path in path.glob('**'):
                if sub_path.is_file():
                    sub_path = sub_path.relative_to(path)
                    yield sub_path
        sub_paths = sorted(gen(), key=lambda x: str(x))
        for sub_path in sub_paths:
            _hash_file(sub_path, fhash)
    else:
        BUF_SIZE = 1 * 1024 * 1024 # 1MB buffer
        
        with open(path, 'rb') as f:
            while True:
                data = f.read(BUF_SIZE)
                if not data:
                    break
                fhash.update(data)

def hash_file(path: Path) -> str:
    fhash = hashlib.sha256()
    
    _hash_file(path, fhash)
    
    return fhash.hexdigest()

class _BraceString(str):
    def __mod__(self, other):
        return self.format(*other)
    def __str__(self):
        return self

class _StyleAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra=None):
        super(_StyleAdapter, self).__init__(logger, extra)
    
    def process(self, msg, kwargs):
        # if kwargs.pop('style', "%") == "{":  # optional
        #     msg = BraceString(msg)
        msg = _BraceString(msg)
        return msg, kwargs

def get_logger(name):
    return _StyleAdapter(logging.getLogger(name))
