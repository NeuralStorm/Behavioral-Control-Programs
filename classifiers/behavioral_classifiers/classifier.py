


class Classifier:
    def event(self, event_type: str, timestamp: float):
        pass
    
    def spike(self, channel: int, unit: int, timestamp: float):
        pass
    
    def clear(self):
        pass
    
    def classify(self) -> str:
        raise NotImplementedError()
