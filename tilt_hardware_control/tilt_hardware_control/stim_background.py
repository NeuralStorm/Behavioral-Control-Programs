
from typing import Optional
from collections import deque
from contextlib import ExitStack, AbstractContextManager
from pprint import pprint
from time import perf_counter, sleep
from multiprocessing import Process, Event as PEvent

from event_source import OpxSource, MockSource
from util_intan import Stimulator
from grf_data import RECORD_PROCESS_STOP_TIMEOUT
from util_multiprocess import spawn_process

class State:
    def __init__(self):
        self.stopping = PEvent()
        self.stopped = PEvent()
        self.failed = PEvent()
    
    def stop(self):
        self.stopping.set()
        self.stopped.wait(timeout=RECORD_PROCESS_STOP_TIMEOUT)
    
    def is_stopping(self) -> bool:
        return self.stopping.is_set()

class _Context(AbstractContextManager):
    def __init__(self, state: State):
        self.state: State = state
    
    def __exit__(self, *exc):
        if exc != (None, None, None):
            self.state.failed.set()
        self.state.stopped.set()

def do_stims(*, state: State = None):
    mock = True
    
    with ExitStack() as stack:
        if state is not None:
            stack.enter_context(_Context(state))
        
        if mock:
            source = MockSource(0, 0)
        else:
            source = stack.enter_context(OpxSource())
            stim = stack.enter_context(Stimulator(channels=['a-000', 'a-001']))
        
        events = deque()
        
        last_stim = perf_counter()
        period = 2
        while True:
            
            while True:
                evt = source.next_event()
                events.append(evt)
                now = perf_counter()
                if now - last_stim > period:
                    start_time = perf_counter()
                    break
            
            while start_time - events[0].timestamp > period:
                events.popleft()
            
            if mock:
                import random
                if random.choice([True, False]):
                    events.popleft()
            
            if len(events) % 2 == 0:
                ch = 'a-000'
            else:
                ch = 'a-001'
            
            params = dict(
                channel = ch,
                first_phase_amplitude = 1,
                first_phase_duration = 1,
                second_phase_amplitude = 1,
                second_phase_duration = 1,
                number_of_pulses = 1,
                pulse_train_period = 1,
            )
            # if verbose:
            print(now, len(events), ch)
            # pprint(params)
            if not mock:
                stim.set_stimulation_parameters(
                    **params,
                )
            
            last_stim = start_time
            
            if state is not None and state.is_stopping():
                break

def spawn_stim_process() -> State:
    state = State()
    
    spawn_process(do_stims, state=state)
    
    return state

def main():
    # do_stims()
    
    state = spawn_stim_process()
    sleep(5)
    state.stop()
    print('failed', state.failed.is_set())

if __name__ == '__main__':
    main()
