
from typing import Optional

class Zone:
    def __init__(self, name: str, chan: int, exit_chan: Optional[int] = None):
        # True when in zone
        self._state = False
        self.changed = False
        
        self.name: str = name
        self.chan: int = chan
        self.exit_chan: Optional[int] = exit_chan
        
        self._enter_event = f"{name}_enter"
        self._exit_event = f"{name}_exit"
        
    
    @property
    def in_zone(self):
        return self._state
    
    @property
    def event_name(self):
        if self._state:
            return self._enter_event
        else:
            return self._exit_event
    
    def enter(self):
        if self._state: # already in zone
            self.changed = False
        else:
            self.changed = True
            self._state = True
    
    def exit(self):
        if not self._state: # already out of zone
            self.changed = False
        else:
            self.changed = True
            self._state = False
