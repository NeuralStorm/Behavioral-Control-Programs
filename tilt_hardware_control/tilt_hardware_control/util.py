
import hashlib
from pathlib import Path

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
