


class Classifier:
    def event(self, *, event_type: str = '', timestamp: float):
        pass
    
    def spike(self, channel: str, timestamp: float):
        pass
    
    def clear(self):
        pass
    
    def classify(self) -> str:
        raise NotImplementedError()
