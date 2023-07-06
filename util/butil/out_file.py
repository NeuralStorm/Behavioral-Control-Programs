
from typing import Optional
import json
from pathlib import Path
from contextlib import ExitStack
import gzip
import bz2

class EventFile:
    def __init__(self, *, file_obj=None, path: Optional[Path]):
        self._stack = ExitStack()
        if path is not None:
            assert file_obj is None
            if path.name.endswith('.gz'):
                self._f = self._stack.enter_context(gzip.open(path, 'at', encoding='utf8', newline='\n'))
            elif path.name.endswith('.bz2'):
                self._f = self._stack.enter_context(bz2.open(path, 'at', encoding='utf8', newline='\n'))
            else:
                self._f = self._stack.enter_context(open(path, 'a', encoding='utf8', newline='\n'))
            self._managing_file = True
        elif file_obj is not None:
            self._f = file_obj
            self._managing_file = False
        else:
            raise ValueError()
        
        self._first_event = True
        
        # write a newline so it's easier to fix broken records if appending to
        # a file that was interrupted mid write
        self._f.write('\n')
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self._stack.__exit__(*exc)
    
    def close(self):
        self._stack.close()
    
    def write_record(self, data):
        json.dump(data, self._f, separators=(',', ':'))
        self._f.write('\n')
        
        self._f.flush()

class EventReader:
    def __init__(self, *, file_obj=None, path: Optional[Path], ignore_error: bool = True):
        self._stack = ExitStack()
        self.ignore_error: bool = ignore_error
        
        if path is not None:
            assert file_obj is None
            if path.name.endswith('.gz'):
                self._f = self._stack.enter_context(gzip.open(path, 'rt', encoding='utf8', newline='\n'))
            elif path.name.endswith('.bz2'):
                self._f = self._stack.enter_context(bz2.open(path, 'rt', encoding='utf8', newline='\n'))
            else:
                self._f = self._stack.enter_context(open(path, 'r', encoding='utf8', newline='\n'))
            self._managing_file = True
        elif file_obj is not None:
            self._f = file_obj
            self._managing_file = False
        else:
            raise ValueError()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self._stack.__exit__(*exc)
    
    def close(self):
        self._stack.close()
    
    def read_records(self):
        try:
            for line in self._f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                yield data
        # EOFError happens when compressed file is truncated
        except (EOFError, json.decoder.JSONDecodeError):
            if not self.ignore_error:
                raise
