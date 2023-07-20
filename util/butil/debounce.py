
from typing import Union
from numbers import Real
from time import perf_counter

class Edge:
    rising: bool = False
    falling: bool = False

class Debounce:
    def __init__(self, *, threshold: Real, delay: float):
        self._is_high = False
        self._last_state_change = None
        self._threshold = threshold
        self._delay = delay
    
    def sample(self, value: Real) -> Edge:
        # check if the state has changed
        if self._is_high and value < self._threshold:
            rising = False
        elif not self._is_high and value >= self._threshold:
            rising = True
        else:
            return Edge()
        
        # check that the debounce delay has passed
        now = perf_counter()
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
        else:
            edge.falling = True
        
        return edge
