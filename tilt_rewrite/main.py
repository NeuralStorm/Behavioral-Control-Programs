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

DEBUG_CONFIG = {
    # 'motor_control': False,
    'mock': False,
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
        
        if DEBUG_CONFIG['motor_control']:
            self.motor = MotorControl(mock = mock)
        else:
            import PyDAQmx # pylint: disable=import-error
            from PyDAQmx import Task # pylint: disable=import-error
            self.task = Task()
            
            self.task.CreateDOChan("/Dev4/port0/line0:7","",PyDAQmx.DAQmx_Val_ChanForAllLines)
            self.task.StartTask()
            self.begin()
    
    def __exit__(self, *exc):
        self.close()
    
    def begin(self):
        assert not DEBUG_CONFIG['motor_control']
        import PyDAQmx # pylint: disable=import-error
        begin = np.array([0,0,0,0,0,0,0,0], dtype=np.uint8)
        self.task.WriteDigitalLines(1,1,10.0,PyDAQmx.DAQmx_Val_GroupByChannel,begin,None,None)
    
    def stop(self):
        if DEBUG_CONFIG['motor_control']:
            self.motor.tilt('stop')
        else:
            self.begin()
    
    def close(self):
        if DEBUG_CONFIG['motor_control']:
            self.motor.close()
        else:
            self.begin()
            self.task.StopTask()
    
    def tilt(self, tilt_type, water=False):
        water_duration = 0.15
        tilt_duration = 1.75
        
        try:
            tilt_name = {1: 'a', 2: 'b', 3: 'c', 4: 'd'}[tilt_type]
        except KeyError:
            raise ValueError("Invalid tilt type {}".format(tilt_type))
        
        self.motor.tilt(tilt_name)
        time.sleep(1) # should this be tilt duration?
        self.motor.tilt('stop')
        time.sleep(tilt_duration) # ???
        
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

class RecordEventContext(AbstractContextManager):
    def __init__(self, stop_event: Any):
        self.stop_event = stop_event
    
    def __exit__(self, *exc):
        # print('debug wait for stop')
        # time.sleep(5)
        self.stop_event['stopped'].set()

def record_data(*, clock_source: str="", clock_rate: int, csv_path, stop_event: Any, mock: bool):
    if not mock:
        import nidaqmx # pylint: disable=import-error
        # pylint: disable=import-error
        from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
    
    # samples per second
    # SAMPLE_RATE = 1250
    SAMPLE_RATE = clock_rate
    SAMPLE_BATCH_SIZE = SAMPLE_RATE
    
    csv_headers = [
        "Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22","Dev6/ai23",
        "Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36","Dev6/ai37","Dev6/ai38", "Dev6/ai39",
        "Dev6/ai48", "Dev6/ai49", "Dev6/ai50","Dev6/ai51",
        "Strobe", "Start", "Inclinometer", 'Timestamp',
    ]
    # csv_path = './loadcell_tilt.csv'
    # clock sourcs Dev6/PFI6
    with ExitStack() as stack:
        # add the record event context first so it will set the stopped
        # event after all other context __exit__methods are called
        stack.enter_context(RecordEventContext(stop_event))
        
        if not mock:
            task: Any = stack.enter_context(nidaqmx.Task())
            
            task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
            task.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
            # task.timing.cfg_samp_clk_timing(1000, source = "", sample_mode= AcquisitionType.CONTINUOUS, samps_per_chan = 1000)
            # set sample rate slightly higher than actual sample rate, not sure if that's needed
            # clock_source = "/Dev6/PFI6"
            # clock_source = ""
            task.timing.cfg_samp_clk_timing(SAMPLE_RATE, source=clock_source, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=SAMPLE_BATCH_SIZE)
            # task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev6/PFI8", trigger_edge=Edge.RISING)
        else:
            WAIT_INFINITELY = None
            class MockTask:
                def read(self, samples_per_channel, _timeout):
                    time.sleep(1)
                    row = [
                        [1 for _ in range(SAMPLE_BATCH_SIZE)]
                        for _ in range(len(csv_headers) - 1)
                    ]
                    return row
            task = MockTask()
        
        csv_file = stack.enter_context(open(csv_path, 'w+', newline=''))
        writer = csv.writer(csv_file)
        writer.writerow(csv_headers)
        
        if not mock:
            task.start()
        
        for row_i in count(0):
            if row_i == 0:
                # no timeout on first read to wait for start trigger
                read_timeout = WAIT_INFINITELY
            else:
                read_timeout = 10 # default in nidaq
            
            data = task.read(SAMPLE_BATCH_SIZE, read_timeout)
            
            for i in range(SAMPLE_BATCH_SIZE):
                def gen_row():
                    for chan in data:
                        yield chan[i]
                    yield row_i / SAMPLE_RATE
                
                writer.writerow(gen_row())
                
                row_i += 1
            
            if stop_event['stopping'].is_set():
                break

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
                # check at start of loop in case of keyboard interrupt
                if i >= num_tilts:
                    break
                
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
            print('tilt', i)
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
    channels: 'Dict[int, List[int]]'
    # "open_loop" or "closed_loop"
    mode: Literal['open_loop', 'closed_loop']
    
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

def load_config(path: Path, labels_path: Optional[Path]):
    with open(path) as f:
        data = hjson.load(f)
    
    config = Config()
    config.raw = data
    
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
    
    mode = data['mode']
    assert mode in ['open_loop', 'closed_loop']
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
        pass
    elif mode == 'closed_loop':
        config.baseline = data['baseline']
        config.sham = data['sham']
        config.reward = data['reward']
        assert type(config.baseline) == bool
        assert type(config.sham) == bool
        assert type(config.reward) == bool
    else:
        assert False
    
    return config

def parse_args_config():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('config',
        help='config file')
    parser.add_argument('--labels', required=False,
        help='labels file')
    
    parser.add_argument('--no-start-pulse', action='store_true',
        help='do not wait for plexon start pulse or enter press, skips initial 3 second wait')
    parser.add_argument('--loadcell-out', default='./loadcell_tilt.csv',
        help='file to write loadcell csv data to (default ./loadcell_tilt.csv)')
    parser.add_argument('--no-record', action='store_true',
        help='skip recording loadcell data')
    
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
    
    if not args.dbg_motor_control:
        DEBUG_CONFIG['motor_control'] = True
    if mock:
        DEBUG_CONFIG['mock'] = True
    
    # mode = 'normal' if args.non_psth else 'psth'
    if config.mode == 'open_loop':
        mode = 'normal'
    elif config.mode == 'closed_loop':
        mode = 'psth'
    else:
        raise ValueError(f"invalid mode {config.mode}")
    
    assert mode in ['psth', 'normal']
    
    tilt_sequence = generate_tilt_sequence(config.num_tilts)
    
    if config.clock_source == 'internal':
        clock_source = ''
    elif config.clock_source == 'external':
        clock_source = '/Dev6/PFI6'
    else:
        assert False
    if not args.no_record:
        record_stop_event = {
            'stopping': PEvent(),
            'stopped': PEvent(),
        }
        spawn_process(
            _error_record_data, clock_source=clock_source,
            clock_rate=config.clock_rate, csv_path=args.loadcell_out,
            stop_event=record_stop_event, mock=args.mock,
        )
    else:
        record_stop_event = None
    
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
            if platform.closed:
                return
            if record_stop_event is not None:
                record_stop_event['stopping'].set()
                print("waiting for recording to stop (platform)")
                record_stop_event['stopped'].wait(timeout=15)
                
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
        record_stop_event['stopping'].set()
        print("waiting for recording to stop")
        record_stop_event['stopped'].wait(timeout=15)

if __name__ == '__main__':
    main()
