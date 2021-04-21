"""
"""

from typing import List, Dict, get_type_hints, Any, Literal, Tuple, Optional, Callable
import time
from random import randint
from contextlib import ExitStack, AbstractContextManager, contextmanager
import csv
from itertools import count
from threading import Thread
from multiprocessing import Process, Event as PEvent
from queue import Queue, Empty as QEmpty
import sys
import atexit
import functools
import traceback
import argparse
from pprint import pprint
from copy import deepcopy
import json
from pathlib import Path

import hjson

import numpy as np

from psth_tilt import PsthTiltPlatform, SpikeWaitTimeout
from motor_control import MotorControl
from util import hash_file

from grf_data import record_data, RecordState

DEBUG_CONFIG = {
    # 'motor_control': False,
    'mock': False,
}
# RECORD_PROCESS_STOP_TIMEOUT = 30

NIDAQ_CLOCK_PINS: Dict[str, str] = {
    'internal': '',
    'external': '/Dev6/PFI6',
}

# start Dev4/port2/line1 True
# stop  Dev4/port2/line2 False
def line_wait(line: str, value):
    waiter = LineWait(line)
    waiter.wait(value)
    waiter.end()

class LineWait:
    def __init__(self, line: str):
        import nidaqmx # pylint: disable=import-error
        from nidaqmx.constants import LineGrouping # pylint: disable=import-error
        
        self.task = nidaqmx.Task()
        self.task.di_channels.add_di_chan(line, line_grouping = LineGrouping.CHAN_PER_LINE)
        self.task.start()
    
    def wait(self, value):
        while True:
            data = self.task.read(number_of_samples_per_channel = 1)
            if data == [value]:
                return
    
    def end(self):
        self.task.stop()

# record stop line "Dev4/port2/line6"
class LineReader:
    def __init__(self, line: str):
        import nidaqmx # pylint: disable=import-error
        from nidaqmx.constants import LineGrouping # pylint: disable=import-error
        
        task = nidaqmx.Task()
        task.di_channels.add_di_chan(line, line_grouping=LineGrouping.CHAN_PER_LINE)
        task.start()
        self.task = task
    
    def read_bool(self) -> bool:
        value = self.task.read(number_of_samples_per_channel=1)
        return bool(value[0])
    
    def __enter__(self):
        self.task.__enter__()
        return self
    
    def __exit__(self, *exc):
        return self.task.__exit__(*exc)

class TiltPlatform(AbstractContextManager):
    def __init__(self, *, mock: bool = False, delay_range: Tuple[float, float]):
        
        self.delay_range = delay_range
        
        self.motor = MotorControl(mock = mock)
    
    def __exit__(self, *exc):
        self.close()
    
    def stop(self):
        self.motor.tilt('stop')
    
    def close(self):
        self.motor.close()
    
    def tilt(self, tilt_type, water=False):
        water_duration = 0.15
        tilt_duration = 1.75
        
        try:
            tilt_name = {1: 'a', 2: 'b', 3: 'c', 4: 'd'}[tilt_type]
        except KeyError:
            raise ValueError("Invalid tilt type {}".format(tilt_type))
        
        self.motor.tilt(tilt_name)
        time.sleep(tilt_duration)
        self.motor.tilt('stop')
        
        if water:
            self.motor.tilt('wateron')
            time.sleep(water_duration)
            self.motor.tilt('stop')
        
        # delay = ((randint(1,100))/100)+1.5
        import random
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)

def generate_tilt_sequence(num_tilts):
    #No event 2 and 4 for early training
    #because they are the fast tilts and animals take longer to get used to them
    
    assert num_tilts % 4 == 0, "num tilts must be divisable by 4"
    n = num_tilts // 4
    
    a = [1]*n
    a.extend([2]*n)
    a.extend([3]*n)
    a.extend([4]*n)
    np.random.shuffle(a)
    return a

class RecordFailure(Exception):
    pass

# None if  unitialized, False if not recording
_recording_check_event = {'_': None}
def check_recording():
    """raises an exception if recording has failed"""
    e = _recording_check_event['_']
    assert e is not None
    if e is False:
        return
    if e.is_set():
        raise RecordFailure()

def spawn_thread(func, *args, **kwargs) -> Thread:
    thread = Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

def print_errors(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            traceback.print_exc()
            raise
    
    return wrapper

def _error_record_data(*args, **kwargs):
    try:
        return record_data(*args, **kwargs)
    except:
        print("record data process failed")
        traceback.print_exc()
        raise

def spawn_process(func, *args, **kwargs) -> Process:
    proc = Process(target=func, args=args, kwargs=kwargs)
    proc.start()
    atexit.register(lambda: proc.terminate())
    return proc

def run_non_psth_loop(platform: TiltPlatform, tilt_sequence, *, num_tilts):
    assert num_tilts == len(tilt_sequence)
    i = 0
    while True:
        try:
            while True:
                check_recording()
                
                # check at start of loop in case of keyboard interrupt
                if i >= num_tilts:
                    break
                
                print(f"tilt {i+1}/{num_tilts}")
                platform.tilt(tilt_sequence[i])
                
                i += 1
        except KeyboardInterrupt:
            platform.stop()
            i += 1
            try:
                input("\nPausing... (Hit ENTER to continue, ctrl-c again to quit.)")
            except KeyboardInterrupt:
                break
            continue
        
        break

def run_psth_loop(platform: PsthTiltPlatform, tilt_sequence, *,
    sham: bool, retry_failed: bool,
    output_extra: Dict[str, Any],
    before_platform_close: Callable[[PsthTiltPlatform], None],
):
    
    input_file_list = []
    if platform.template_in_path is not None:
        input_file_list.append(Path(platform.template_in_path))
    
    input_files = {}
    for fpath in input_file_list:
        input_files[fpath.name] = hash_file(fpath)
    
    # psth = platform.psth
    if sham:
        with open(platform.template_in_path) as f:
            template_in = json.load(f)
        tilt_sequence = []
        sham_decodes = []
        sham_delays = []
        
        for tilt in template_in['tilts']:
            tilt_sequence.append(tilt['tilt_type'])
            p_tilt_type = tilt['predicted_tilt_type']
            if p_tilt_type is None:
                p_tilt_type = tilt['tilt_type']
            sham_decodes.append(p_tilt_type)
            sham_delays.append(tilt['delay'])
    
    input_queue: 'Queue[str]' = Queue(1)
    def input_thread():
        while True:
            cmd = input(">")
            input_queue.put(cmd)
            input_queue.put("")
            input_queue.join()
    
    spawn_thread(input_thread)
    
    tilt_records: List[Dict[str, Any]] = []
    # tilts will be added to below before being written to json
    platform.psth.output_extra['tilts'] = tilt_records
    platform.psth.output_extra['baseline'] = platform.baseline_recording
    platform.psth.output_extra['input_files'] = input_files
    platform.psth.output_extra['output_files'] = {}
    platform.psth.output_extra.update(output_extra)
    
    def get_cmd():
        try:
            _cmd: str = input_queue.get_nowait()
        except QEmpty:
            pass
        else:
            input_queue.task_done()
            print("Press enter to resume; q, enter to stop")
            cmd = input("paused>")
            # if cmd == 'q':
            #     break
            input_queue.get()
            input_queue.task_done()
            return cmd
    
    def do_tilt(tilt_type, i, sham_i, retry=None):
        check_recording()
        if sham:
            sham_result = tilt_type == sham_decodes[sham_i]
        else:
            sham_result = None
        
        if retry is not None:
            delay = retry['delay']
        elif sham:
            delay = sham_delays[sham_i]
        else:
            delay = None
        
        try:
            tilt_rec = platform.tilt(tilt_type, sham_result=sham_result, delay=delay)
        except SpikeWaitTimeout as e:
            tilt_rec = e.tilt_rec
            tilt_rec['spike_wait_timeout'] = True
            tilt_records.append(tilt_rec)
            raise
        tilt_rec['i'] = i
        tilt_rec['retry'] = retry
        # pprint(tilt_rec, sort_dicts=False)
        # pprint(tilt_rec)
        tilt_records.append(tilt_rec)
        # put data into psth class often so data will get saved in the case of a crash
        platform.psth.output_extra['tilts'] = tilt_records
        return tilt_rec
    
    def run_tilts():
        for i, tilt_type in enumerate(tilt_sequence):
            print(f'tilt {i}/{len(tilt_sequence)}')
            do_tilt(tilt_type, i, i)
            
            if get_cmd() == 'q':
                return
        
        out_i = i
        
        if retry_failed:
            failed_tilts = [
                deepcopy(x)
                for x in tilt_records
                if x['decoder_result_source'] == 'no_spikes'
            ]
        else:
            failed_tilts = None
        
        while failed_tilts:
            for tilt in failed_tilts:
                out_i += 1
                
                i = tilt['i']
                tilt_type = tilt['tilt_type']
                
                retry_tilt = do_tilt(tilt_type, out_i, i, retry=tilt)
                
                if retry_tilt['decoder_result_source'] != 'no_spikes':
                    tilt['retry_success'] = True
                
                if get_cmd() == 'q':
                    return
            
            failed_tilts = [x for x in failed_tilts if not x.get('retry_success')]
    
    run_tilts()
    
    before_platform_close(platform)
    
    platform.close()
    psthclass = platform.psth
    
    if not platform.baseline_recording and not sham:
        # pylint: disable=import-error
        from sklearn.metrics import confusion_matrix
        
        print('actual events:y axis, predicted events:x axis')
        confusion_matrix_calc = confusion_matrix(psthclass.event_number_list,psthclass.decoder_list)
        print(confusion_matrix_calc)
        correct_trials = 0
        for i in range(0,len(confusion_matrix_calc)):
            correct_trials = correct_trials + confusion_matrix_calc[i][i]
        decoder_accuracy = correct_trials / len(psthclass.event_number_list)
        print(('Accuracy = {} / {} = {}').format(correct_trials, len(psthclass.event_number_list), decoder_accuracy))
        print('Stop Plexon Recording.')
    
    for tilt in tilt_records:
        for warning in tilt['warnings']:
            print(warning)
    print()
    if any(x['decoder_result_source'] == 'no_spikes' for x in tilt_records):
        num_failures = len([x['decoder_result_source'] == 'no_spikes' for x in tilt_records])
        print(f"{num_failures} tilts failed due to no spikes occuring, THIS SHOULD NOT HAPPEN. TELL DR MOXON")

class Config:
    channels: Optional[Dict[int, List[int]]]
    # "open_loop" or "closed_loop"
    mode: Literal['open_loop', 'closed_loop', 'bias']
    
    # clock source and rate for grf data collection
    # external = downsampled plexon clock, PFI6
    # internal = internal nidaq clock
    clock_source: Literal['external', 'internal']
    clock_rate: int
    
    num_tilts: int
    # time range to wait between tilts
    delay_range: Tuple[float, float]
    
    # None if mode == open_loop
    baseline: Optional[bool]
    sham: Optional[bool]
    reward: Optional[bool]
    
    # full deserialized json from the config file
    raw: Any

def load_config(path: Path, labels_path: Optional[Path]) -> Config:
    with open(path) as f:
        data = hjson.load(f)
    
    config = Config()
    config.raw = data
    
    mode = data['mode']
    assert mode in ['open_loop', 'closed_loop', 'bias']
    config.mode = mode
    
    config.clock_source = data['clock_source']
    assert config.clock_source in ['external', 'internal']
    config.clock_rate = data['clock_rate']
    assert type(config.clock_rate) == int
    
    assert len(data['delay_range']) == 2
    config.delay_range = (data['delay_range'][0], data['delay_range'][1])
    assert len(config.delay_range) == 2
    
    config.num_tilts = data['num_tilts']
    assert type(config.num_tilts) == int
    
    if mode == 'open_loop':
        config.baseline = None
        config.sham = None
        config.reward = None
        config.channels = None
    elif mode == 'closed_loop':
        config.baseline = data['baseline']
        config.sham = data['sham']
        config.reward = data['reward']
        assert type(config.baseline) == bool
        assert type(config.sham) == bool
        assert type(config.reward) == bool
        
        if labels_path is not None:
            with open(labels_path) as f:
                labels_data = hjson.load(f)
        else:
            labels_data = data
        channels = {
            int(k): v
            for k, v in labels_data['channels'].items()
        }
        # assert isinstance(channels, get_type_hints(Config)['channels'])
        config.channels = channels
    else:
        assert False
    
    return config

def parse_args_config():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('config',
        help='config file')
    parser.add_argument('--labels', required=False,
        help='labels file')
    
    parser.add_argument('--bias',
        help='overrides the mode in the config file with `bias` and the --loadcell-out'\
            'params with the provided value')
    parser.add_argument('--monitor', action='store_true',
        help="overrides the mode in the config file with `monitor`")
    
    parser.add_argument('--no-start-pulse', action='store_true',
        help='do not wait for plexon start pulse or enter press, skips initial 3 second wait')
    parser.add_argument('--loadcell-out', default='./loadcell_tilt.csv',
        help='file to write loadcell csv data to (default ./loadcell_tilt.csv)')
    parser.add_argument('--no-record', action='store_true',
        help='skip recording loadcell data')
    parser.add_argument('--live', action='store_true',
        help='show real time data')
    parser.add_argument('--live-secs', type=int, default=5,
        help='number of seconds to keep data for in live view (5)')
    
    parser.add_argument('--template-out',
        help='output path for generated template')
    parser.add_argument('--template-in',
        help='input path for template')
    
    parser.add_argument('--no-spike-wait', action='store_true',
        help=argparse.SUPPRESS)
    parser.add_argument('--fixed-spike-wait', action='store_true',
        help=argparse.SUPPRESS)
    parser.add_argument('--retry', action='store_true',
        help=argparse.SUPPRESS)
    parser.add_argument('--mock', action='store_true',
        help=argparse.SUPPRESS)
    parser.add_argument('--dbg-motor-control', action='store_true',
        help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    return args

def bias_main(config: Config, loadcell_out: str, mock: bool):
    record_events = RecordState()
    clock_source = NIDAQ_CLOCK_PINS[config.clock_source]
    
    record_data(
        clock_source = clock_source,
        clock_rate = config.clock_rate,
        csv_path = loadcell_out,
        state = record_events,
        mock = mock,
        num_samples = 5000,
    )
    
    record_events.stop_recording()

def main():
    args = parse_args_config()
    config = load_config(args.config, args.labels)
    print(config.channels)
    
    args_record = dict(vars(args))
    dev_flags = [
        'dbg_motor_control',
        'mock',
        'no_spike_wait',
        'fixed_spike_wait',
        'retry',
    ]
    for flag in dev_flags:
        if not args_record[flag]:
            del args_record[flag]
    
    mock = args.mock
    
    if args.bias is not None:
        config.mode = 'bias'
        args.loadcell_out = args.bias
    if args.monitor:
        config.mode = 'monitor'
    
    if not args.dbg_motor_control:
        DEBUG_CONFIG['motor_control'] = True
    if mock:
        DEBUG_CONFIG['mock'] = True
    
    if config.mode == 'bias':
        return bias_main(config, args.loadcell_out, args.mock)
    
    # mode = 'normal' if args.non_psth else 'psth'
    if config.mode == 'open_loop':
        mode = 'normal'
    elif config.mode == 'closed_loop':
        mode = 'psth'
    elif config.mode == 'monitor':
        mode = 'monitor'
    else:
        raise ValueError(f"invalid mode {config.mode}")
    
    assert mode in ['psth', 'normal', 'monitor']
    
    tilt_sequence = generate_tilt_sequence(config.num_tilts)
    
    clock_source = NIDAQ_CLOCK_PINS[config.clock_source]
    
    if not args.no_record:
        record_stop_event = RecordState()
        if args.live:
            record_stop_event.live.enabled = True
        _recording_check_event['_'] = record_stop_event.failed
        spawn_process(
            _error_record_data, clock_source=clock_source,
            clock_rate=config.clock_rate, csv_path=args.loadcell_out,
            state=record_stop_event, mock=args.mock,
            live_view_seconds=args.live_secs,
        )
    else:
        _recording_check_event['_'] = False
        record_stop_event = None
    
    if mode == 'monitor':
        input('press enter to exit')
        record_stop_event.stop_recording()
        return
    
    assert mode in ['psth', 'normal']
    
    if not args.no_start_pulse and not args.mock:
        print("waiting for plexon start pulse")
        line_wait("Dev4/port2/line1", True)
        
        input("Press enter to start")
        print("Waiting 3 seconds ?")
        time.sleep(3) # ?
    
    if mode == 'psth': # closed loop
        print("running psth")
        baseline_recording = config.baseline
        
        output_extra = {
            'config': config.raw,
            'args': args_record,
        }
        
        def before_platform_close(platform):
            # if the platform is already closed the psth will have written
            # its output and it's too late to add the file hash
            if platform.closed:
                return
            if record_stop_event is not None:
                # stop the recording process so we can calculate the hash of the recorded file
                print("waiting for recording to stop (platform)")
                record_stop_event.stop_recording()
                
                fpath = Path(args.loadcell_out)
                grf_file_hash = hash_file(fpath)
                
                platform.psth.output_extra['output_files'][fpath.name] = grf_file_hash
        
        # also create a context manager so before_platform_close will still be run
        # if an error occures
        @contextmanager
        def platform_close_context(platform):
            try:
                yield
            finally:
                before_platform_close(platform)
        
        with PsthTiltPlatform(
            baseline_recording = baseline_recording,
            save_template = bool(args.template_out),
            template_output_path = args.template_out,
            template_in_path = args.template_in,
            channel_dict = config.channels,
            mock = mock,
            reward_enabled = config.reward,
        ) as platform:
            if args.no_spike_wait:
                assert not args.fixed_spike_wait
                platform.fixed_spike_wait_time = 0.2
                platform.fixed_spike_wait_timeout = 1.5
            if args.fixed_spike_wait:
                assert not args.no_spike_wait
                platform.fixed_spike_wait = True
            platform.delay_range = config.delay_range
            with platform_close_context(platform):
                run_psth_loop(
                    platform, tilt_sequence,
                    sham=config.sham, retry_failed=args.retry,
                    output_extra=output_extra,
                    before_platform_close = before_platform_close,
                )
    elif mode == 'normal': # open loop
        print("running non psth")
        with TiltPlatform(mock=mock, delay_range=config.delay_range) as platform:
            run_non_psth_loop(platform, tilt_sequence, num_tilts=config.num_tilts)
    else:
        raise ValueError("Invalid mode")
    
    if record_stop_event is not None:
        print("waiting for recording to stop")
        record_stop_event.stop_recording()
    
    check_recording()

if __name__ == '__main__':
    main()
