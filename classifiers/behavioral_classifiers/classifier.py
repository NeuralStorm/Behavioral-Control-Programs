
from typing import Any

class Classifier:
    def event(self, *, event_type: str = '', timestamp: float):
        pass
    
    def spike(self, channel: str, timestamp: float):
        pass
    
    def clear(self):
        pass
    
    def classify(self) -> str:
        res, _ = self.classify_debug_info()
        return res
    
    def classify_debug_info(self) -> tuple[str, Any]:
        raise NotImplementedError()
