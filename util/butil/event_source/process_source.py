
import time
from multiprocessing import Process, Queue as PQueue
from queue import Empty

class SourceProcessError(Exception):
    pass

class _SourceProcess(Process):
    def __init__(self, init_func):
        self._queue = PQueue()
        self._init_func = init_func
        super().__init__(daemon=True)
    
    def run(self):
        try:
            source = self._init_func()
            
            while True:
                time.sleep(0.001)
                data = list(source.get_data())
                if not data:
                    continue
                self._queue.put(data)
        except Exception as e:
            self._queue.put(SourceProcessError())
            raise
    
    def get_data(self):
        try:
            data = self._queue.get(block=False)
        except Empty:
            return []
        return data

class SourceProxy:
    def __init__(self, init_func):
        self._proc = _SourceProcess(init_func)
        self._proc.start()
    
    def wait_for_start(self):
        return {'ts': 0}
    
    def get_data(self):
        res = self._proc.get_data()
        if type(res) == SourceProcessError:
            raise res # type: ignore
        return res
