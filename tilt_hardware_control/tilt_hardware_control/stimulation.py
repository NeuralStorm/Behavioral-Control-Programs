
from typing import Set
import random
import time
from pprint import pprint

from util_intan import Stimulator
from util_multiprocess import spawn_process
from contextlib import ExitStack, AbstractContextManager, contextmanager
from multiprocessing import Process, Event as PEvent, Queue, Value
from queue import Empty

from grf_data import RECORD_PROCESS_STOP_TIMEOUT

class TiltStimulation:
    def __init__(self, *, stim_params, tilt_types: Set[str], mock: bool, verbose: bool = False):
        self._verbose = verbose
        self._mock = mock
        
        assert stim_params['mode'] == 'classifier'
        
        # ensure we have settings for all tilt types
        assert set(stim_params['predicted'].keys()) >= tilt_types
        
        for tilt_type, tilt_params in stim_params['predicted'].items():
            for k in ['channel', 'first_phase', 'second_phase', 'num_pulses', 'pulse_period']:
                assert k in tilt_params, f"missing key `{k}` in config for tilt type {tilt_type}"
            for k in ['first_phase', 'second_phase']:
                for sk in ['duration', 'current']:
                    assert sk in tilt_params[k], f"missing key `{k}.{sk}` in config for tilt type {tilt_type}"
        
        self._tilt_types = stim_params['predicted']
        if not mock:
            self._stim = Stimulator(channels=['a-000'])
        
        self.event_log: List[Dict[str, Any]] = []
    
    def prediction_made(self, predicted_tilt_type, actual_tilt_type):
        stim_params = self._tilt_types[predicted_tilt_type]
        
        params = dict(
            channel = stim_params['channel'],
            first_phase_amplitude = stim_params['first_phase']['current'],
            first_phase_duration = stim_params['first_phase']['duration'],
            second_phase_amplitude = stim_params['second_phase']['current'],
            second_phase_duration = stim_params['second_phase']['duration'],
            number_of_pulses = stim_params['num_pulses'],
            pulse_train_period = stim_params['pulse_period'],
        )
        if self._verbose:
            pprint(params)
        if not self._mock:
            self._stim.set_stimulation_parameters(
                **params,
            )
            event_log_item = {
                'system_time': time.perf_counter(),
                'type': 'trigger_stimulus',
                'params': params,
            }
            self.event_log.append(event_log_item)
            self._stim.trigger_stimulus()
        
        # return {
        #     'event_log': [event_log_item],
        # }
    
    def __enter__(self):
        self._stim.__enter__()
    
    def __exit__(self, *exc):
        self._stim.__exit__()

class State:
    def __init__(self):
        # set to request the process to stop 
        self.stopping = PEvent()
        # set when the process completes
        self.stopped = PEvent()
        # set if stim process fails
        self.failed = PEvent()
        # set if stim is not paused
        self._not_paused = PEvent()
        self._not_paused.set()
        
        self.event_log = Queue()
    
    def context(self):
        return ProcessContext(self)
    
    def is_stopping(self):
        return self.stopping.is_set()
    
    def pause(self):
        self._not_paused.clear()
    
    def unpause(self):
        self._not_paused.set()
    
    def stop(self):
        self.stopping.set()
        self._not_paused.set()
        self.stopped.wait(timeout=RECORD_PROCESS_STOP_TIMEOUT)
    
    def event_list(self):
        out = []
        while True:
            try:
                out.append(self.event_log.get(block=False))
            except Empty:
                break
        return out

class ProcessContext(AbstractContextManager):
    def __init__(self, state: State):
        self.state: State = state
    
    def __exit__(self, *exc):
        if exc != (None, None, None):
            self.state.failed.set()
        # print('debug wait for stop')
        # time.sleep(5)
        self.state.stopped.set()

def _random_stimulus(state: State, params_config, *, mock, verbose):
    with ExitStack() as stack:
        stack.enter_context(state.context())
        
        channels = params_config['channel']
        
        if not mock:
            stim = stack.enter_context(Stimulator(channels=channels))
        
        delay_range = params_config['delay_range']
        
        while True:
            
            # params_config = {
            #     'first_phase': {
            #         'duration': [1, 2],
            #         'current': [1, 2],
            #     },
            #     'second_phase': {
            #         'duration': [1, 2],
            #         'current': [1, 2],
            #     },
            # }
            # first duration/current
            f_d = random.choice(params_config['first_phase']['duration'])
            f_c = random.choice(params_config['first_phase']['current'])
            # second duration/current
            s_d = random.choice(params_config['second_phase']['duration'])
            s_c = random.choice(params_config['second_phase']['current'])
            
            # pulse number
            p_n = random.choice(params_config['num_pulses'])
            # pulse period
            p_p = random.choice(params_config['pulse_period'])
            
            channel = random.choice(channels)
            
            params = dict(
                channel = channel,
                first_phase_amplitude = f_c,
                first_phase_duration = f_d,
                second_phase_amplitude = s_c,
                second_phase_duration = s_d,
                number_of_pulses = p_n,
                pulse_train_period = p_p,
            )
            if verbose:
                pprint(params)
            if not mock:
                stim.set_stimulation_parameters(
                    **params,
                )
            
            state.event_log.put({
                'system_time': time.perf_counter(),
                'type': 'trigger_stimulus',
                'params': params,
            })
            if not mock:
                stim.trigger_stimulus()
            
            # delay_range = [0.5, 1]
            delay = random.uniform(*delay_range)
            if verbose:
                print('waiting', delay)
            time.sleep(delay)
            
            state._not_paused.wait()
            if state.is_stopping():
                break

def spawn_random_stimulus_process(params_config, *, mock: bool, verbose: bool = False) -> State:
    state = State()
    
    spawn_process(_random_stimulus, state, params_config, mock=mock, verbose=verbose)
    
    return state

def main():
    import hjson
    with open('test_data/config.hjson', encoding='utf8') as f:
        data = hjson.load(f)
    params_config = data['stim_params']
    # state = State()
    # _random_stimulus(state)
    # state = spawn_random_stimulus_process(params_config, mock=True, verbose=True)
    # state = spawn_random_stimulus_process(params_config, mock=False, verbose=True)
    state = State()
    _random_stimulus(state, params_config, mock=False, verbose=True)
    # global stim
    # stim = Stimulator()
    # input('set params')
    # stim.set_stimulation_parameters(first_phase_amplitude=1, first_phase_duration=1, second_phase_amplitude=1, second_phase_duration=1)
    # input('stimulus')
    # stim.trigger_stimulus()
    # input('close')
    # stim.close()
    
    # input()
    # state.stop()
    
    # event_list = state.event_list()
    # pprint(event_list)

if __name__ == '__main__':
    main()
