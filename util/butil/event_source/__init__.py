
from typing import Iterable, Dict, Any

class Event:
    ANALOG = 'analog'
    SPIKE = 'spike'
    EVENT = 'event'
    OTHER_EVENT = 'other_event'
    
    def __init__(self, ts, event_type, *,
        value: float = 0,
        chan: int = 0,
        unit: int = 0,
        falling: bool = False,
    ):
        self.ts: float = ts
        self.type: str = event_type
        self.value: float = value
        self.chan: int = chan
        self.unit: int = unit
        self.falling: bool = falling
    
    @property
    def rising(self) -> bool:
        return not self.falling

class EventSource:
    def wait_for_start(self) -> Dict[str, Any]:
        return {'ts': 0}
    
    def get_data(self) -> Iterable[Event]:
        return []
