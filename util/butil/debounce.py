
from typing import Union, Optional
from numbers import Real
from time import perf_counter

class Edge:
    rising: bool = False
    falling: bool = False

class Debounce:
    def __init__(self, *, threshold: Real, high_threshold: Optional[Real], delay: float):
        self._is_high = False
        self._last_state_change = None
        self._threshold = threshold
        self._high_threshold = high_threshold if high_threshold is not None else threshold
        self._delay = delay
    
    @property
    def is_low(self):
        return not self._is_high
    
    @property
    def is_high(self):
        return self._is_high
    
    def sample(self, timestamp: Real, value: Real) -> Edge:
        # check if the state has changed
        if self._is_high and value < self._threshold:
            rising = False
        elif not self._is_high and value >= self._high_threshold:
            rising = True
        else:
            return Edge()
        
        # check that the debounce delay has passed
        # now = perf_counter()
        now = timestamp
        if self._last_state_change is None:
            pass
        elif now - self._last_state_change > self._delay:
            pass
        else:
            return Edge()
        
        self._last_state_change = now
        
        edge = Edge()
        if rising:
            edge.rising = True
            self._is_high = True
        else:
            edge.falling = True
            self._is_high = False
        
        return edge
