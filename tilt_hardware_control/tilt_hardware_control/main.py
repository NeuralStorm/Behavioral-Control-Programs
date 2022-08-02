"""
"""

from typing import List, Dict, get_type_hints, Any, Literal, Tuple, Optional, Callable
import time
from contextlib import ExitStack
from threading import Thread
from multiprocessing import Process
from queue import Queue, Empty as QEmpty
import sys
import os
import atexit
import functools
import traceback
import argparse
from pprint import pprint
from copy import copy, deepcopy
import json
from pathlib import Path
import random

import hjson

from psth_tilt import PsthTiltPlatform
from util import hash_file
from util_multiprocess import spawn_process
from util_nidaq import line_wait
from psth_new import EuclClassifier, build_template_file
from stimulation import spawn_random_stimulus_process, State as StimState, TiltStimulation

from grf_data import record_data, RecordState

NIDAQ_CLOCK_PINS: Dict[str, str] = {
    'internal': '',
    'external': '/Dev6/PFI6',
}

def generate_tilt_sequence(num_tilts):
    #No event 2 and 4 for early training
    #because they are the fast tilts and animals take longer to get used to them
    
    assert num_tilts % 4 == 0, "num tilts must be divisable by 4"
    n = num_tilts // 4
    
    tilt_list = [
        *(['slow_left']*n),
        *(['fast_left']*n),
        *(['slow_right']*n),
        *(['fast_right']*n),
    ]
    random.shuffle(tilt_list)
    return tilt_list

class RecordFailure(Exception):
    pass
class StimFailure(Exception):
    pass

# None if unitialized, False if not recording
_recording_check_event: Any = {'_': None, 'stim': None}
def check_recording():
    """raises an exception if the recording or stimulation processes has failed"""
    _check_stim()
    
    e = _recording_check_event['_']
    assert e is not None
    if e is False:
        return
    if e.is_set():
        raise RecordFailure()

def _check_stim():
    stim = _recording_check_event['stim']
    assert stim is not None
    if stim is False:
        return
    if stim.is_set():
        raise StimFailure()

def spawn_thread(func, *args, **kwargs) -> Thread:
    thread = Thread(target=func, args=args, kwargs=kwargs)
    thread.daemon = True
    thread.start()
    return thread

def _error_record_data(*args, **kwargs):
    try:
        return record_data(*args, **kwargs)
    except:
        print("record data process failed")
        traceback.print_exc()
        raise

def run_psth_loop(platform: PsthTiltPlatform, tilt_sequence, *,
    yoked: bool, retry_failed: bool,
    output_extra: Dict[str, Any],
    template_in_path: Optional[str],
    stim_state: Optional[StimState],
):
    sham = yoked
    
    input_file_list = []
    if template_in_path is not None:
        input_file_list.append(Path(template_in_path))
    
    for fpath in input_file_list:
        output_extra['input_files'][fpath.name] = hash_file(fpath)
    
    if sham:
        assert template_in_path is not None
        with open(template_in_path, encoding='utf8') as f:
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
            input("")
            input_queue.put(time.perf_counter())
            input_queue.join()
    
    spawn_thread(input_thread)
    
    output_extra['baseline'] = platform.baseline_recording
    # tilt_records will be added to below before being written to json
    tilt_records: List[Dict[str, Any]] = []
    output_extra['tilts'] = tilt_records
    
    def get_cmd():
        try:
            pause_time: str = input_queue.get_nowait()
        except QEmpty:
            return None
        else:
            return pause_time
    
    tilt_counter = [0]
    
    def run_tilt_list(tilt_commands):
        # reverse tilt list so we can .pop() the next tilt
        tilt_commands = list(reversed(tilt_commands))
        
        while tilt_commands:
            tilt = tilt_commands.pop()
            
            tilt_name = tilt['tilt_name']
            retry_i = tilt.get('i')
            tilt_i = tilt_counter[0]
            tilt_counter[0] += 1
            
            check_recording()
            tilt_rec = platform.tilt(
                tilt_name = tilt_name,
                yoked_prediction = tilt.get('sham_prediction'),
                delay = tilt.get('delay'),
            )
            
            tilt_rec['i'] = tilt_i
            if retry_i is not None:
                tilt_rec['retry_of'] = retry_i
            
            pause_time = get_cmd()
            if pause_time is not None:
                if stim_state is not None:
                    stim_state.pause()
                
                tilt_rec['paused'] = True
                tilt_rec['pause_time'] = pause_time
                retry_tilt = deepcopy(tilt)
                retry_tilt['i'] = tilt_i
                tilt_commands.append(retry_tilt)
                
                print("Press enter to resume; or type a command and press enter")
                print("Commands:")
                print("  q: stops the program")
                print("  pop: skips the next tilt (first use will skip re-run of paused tilt")
                print("  n <text>: add a note to the record of the tilt")
                while True:
                    cmd = input("paused>")
                    check_recording()
                    if cmd == 'q':
                        tilt_rec['warnings'].append('manual quit')
                        yield tilt_rec
                        return
                    elif cmd == 'pop':
                        try:
                            tilt_commands.pop()
                        except IndexError:
                            print("no remaining tilts")
                    elif cmd.startswith('n '):
                        notes = tilt_rec.get('notes', [])
                        notes.append(cmd[2:])
                        tilt_rec['notes'] = notes
                    elif cmd == '':
                        break
                    else:
                        print(f"unknown command `{cmd}`")
                # allow pause input_thread to resume
                input_queue.task_done()
                if stim_state is not None:
                    stim_state.unpause()
            
            if tilt_rec['decoder_result_source'] == 'no_spikes':
                tilt_rec['failed'] = True
            
            # don't retry twice if a pause happened
            if not tilt_rec.get('paused') and tilt_rec.get('failed'):
                retry_tilt = deepcopy(tilt)
                retry_tilt['i'] = tilt_i
                if retry_failed:
                    tilt_commands.insert(0, retry_tilt)
            
            yield tilt_rec
    
    def run_tilts():
        tilt_commands = []
        for i, tilt_name in enumerate(tilt_sequence):
            tilt_command = {
                'tilt_name': tilt_name,
            }
            if sham:
                tilt_command.update({
                    'sham_prediction': sham_decodes[i],
                    'delay': sham_delays[i],
                })
            tilt_commands.append(tilt_command)
        
        for tilt_rec in run_tilt_list(tilt_commands):
            tilt_records.append(tilt_rec)
            if tilt_rec['warnings']:
                for warning in tilt_rec['warnings']:
                    print('WARNING:', warning)
    
    run_tilts()
    
    if not platform.baseline_recording and not sham:
        # pylint: disable=import-error,import-outside-toplevel
        from sklearn.metrics import confusion_matrix
        
        actual = []
        predicted = []
        for rec in tilt_records:
            if rec['predicted_tilt_type'] is not None:
                actual.append(rec['tilt_name'])
                predicted.append(rec['predicted_tilt_type'])
        
        print('actual events:y axis, predicted events:x axis')
        confusion_matrix_calc = confusion_matrix(actual, predicted)
        print(confusion_matrix_calc)
        correct_trials = 0
        for i, _ in enumerate(confusion_matrix_calc):
            correct_trials = correct_trials + confusion_matrix_calc[i][i]
        decoder_accuracy = correct_trials / len(actual)
        print(f"Accuracy = {correct_trials} / {len(actual)} = {decoder_accuracy}")
    
    for tilt in tilt_records:
        for warning in tilt['warnings']:
            print(warning)
    print()
    if any(x['decoder_result_source'] == 'no_spikes' for x in tilt_records):
        num_failures = len([x['decoder_result_source'] == 'no_spikes' for x in tilt_records])
        print(f"{num_failures} tilts failed due to no spikes occuring, THIS SHOULD NOT HAPPEN. TELL DR MOXON")

def start_recording(state: RecordState, args, config: 'Config'):
    clock_source = NIDAQ_CLOCK_PINS[config.clock_source]
    
    record_stop_event = state
    _recording_check_event['_'] = state.failed
    
    if args.live:
        record_stop_event.live.enabled = True
        assert not args.live_cal, "can not use both --live and --live-cal at the same time"
        
    if args.live_cal:
        record_stop_event.live.enabled = True
        record_stop_event.live.calibrated = True
        
        live_bias_str = args.live_bias
        assert live_bias_str is not None, "--live-bias is required when --live-cal is present"
        live_bias = Path(live_bias_str)
        if live_bias.exists():
            record_stop_event.live.bias_file = live_bias_str
        else:
            matches = list(live_bias.glob(f"*/{live_bias_str}"))
            assert len(matches) != 0, "no files matching bias file pattern found"
            if len(matches) > 1:
                print(f"warning: multiple bias files match pattern, using {matches[0]}")
            record_stop_event.live.bias_file = str(matches[0])
    
    if args.loadcell_out is not None and not args.overwrite:
        assert not Path(args.loadcell_out).exists(), f"output file {args.loadcell_out} already exists"
    
    # record_output_extra = {
    #     **output_extra,
    # }
    spawn_process(
        record_data, clock_source=clock_source,
        clock_rate=config.clock_rate, csv_path=args.loadcell_out,
        state=record_stop_event, mock=args.mock,
        live_view_seconds=args.live_secs,
        # output_meta=record_output_extra,
        output_meta=None,
    )
    # wait after starting recording to make sure there is enough time
    # before a tilt to cover an analysis window
    # only needed if recording data
    if args.loadcell_out is not None:
        time.sleep(config.after_tilt_delay + config.delay_range[0])

class Config:
    channels: Optional[Dict[int, List[int]]]
    # "open_loop" or "closed_loop"
    mode: Literal['open_loop', 'closed_loop', 'bias', 'stim', 'monitor']
    
    # clock source and rate for grf data collection
    # external = downsampled plexon clock, PFI6
    # internal = internal nidaq clock
    clock_source: Literal['external', 'internal']
    clock_rate: int
    
    num_tilts: int
    tilt_sequence: Optional[List[str]]
    sequence_repeat: int
    sequence_shuffle: bool
    
    # time range to wait between tilts
    delay_range: Tuple[float, float]
    # time after tilt completes before water reward
    after_tilt_delay: float
    
    reward: bool
    water_duration: float
    
    stim_params: Optional[Dict[str, Any]]
    
    # None if mode == open_loop
    baseline: Optional[bool]
    yoked: Optional[bool]
    
    plexon_lib: Optional[Literal['plex', 'opx']]
    
    # full deserialized json from the config file
    raw: Any

def load_config(path: Path, labels_path: Optional[Path]) -> Config:
    with open(path, encoding='utf8') as f:
        data = hjson.load(f)
    
    config = Config()
    config.raw = data
    
    mode = data['mode']
    # assert mode in ['open_loop', 'closed_loop', 'stim', 'bias']
    config.mode = mode
    
    config.clock_source = data['clock_source']
    assert config.clock_source in ['external', 'internal']
    config.clock_rate = data['clock_rate']
    assert type(config.clock_rate) == int
    
    assert len(data['delay_range']) == 2
    config.delay_range = (data['delay_range'][0], data['delay_range'][1])
    assert len(config.delay_range) == 2
    config.after_tilt_delay = data['after_tilt_delay']
    assert type(config.after_tilt_delay) == int
    
    config.tilt_sequence = data['tilt_sequence']
    if config.tilt_sequence is not None:
        assert type(config.tilt_sequence) == list
        assert all(type(x) == str for x in config.tilt_sequence)
        data['num_tilts'] = len(config.tilt_sequence)
        config.sequence_repeat = data['sequence_repeat']
        assert type(config.sequence_repeat) == int
        assert config.sequence_repeat >= 1
        config.sequence_shuffle = data['sequence_shuffle']
        assert type(config.sequence_shuffle) == bool
    else:
        config.sequence_repeat = None
        config.sequence_shuffle = False
    
    config.num_tilts = data['num_tilts']
    assert type(config.num_tilts) == int
    
    config.reward = data['reward']
    config.water_duration = data['water_duration']
    assert type(config.reward) == bool
    assert type(config.water_duration) in [int, float]
    
    if data['stim_enabled']:
        config.stim_params = data['stim_params']
        assert config.stim_params is not None
    else:
        config.stim_params = None
    
    if mode == 'open_loop':
        config.baseline = None
        config.yoked = None
        config.channels = None
        config.plexon_lib = None
    elif mode == 'closed_loop':
        config.baseline = data['baseline']
        config.yoked = data['yoked']
        config.plexon_lib = data.get('plexon_lib', 'opx')
        assert type(config.baseline) == bool
        assert type(config.yoked) == bool
        assert config.plexon_lib in ['plex', 'opx']
        
        if labels_path is not None:
            with open(labels_path, encoding='utf8') as f:
                labels_data = hjson.load(f)
        else:
            labels_data = data
        channels = {
            int(k): v
            for k, v in labels_data['channels'].items()
        }
        config.channels = channels
    elif mode in ['bias', 'stim', 'monitor']:
        pass
    else:
        raise ValueError(f"Invalid mode `{mode}`")
    
    return config

def parse_args_config():
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument('--config')
    config_args = config_parser.parse_known_args()
    
    config_path = config_args[0].config
    
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--config', required=True,
        help='config file')
    parser.add_argument('--labels', required=False,
        help='labels file')
    
    parser.add_argument('--bias',
        help='overrides the mode in the config file with `bias` and the --loadcell-out'\
            'params with the provided value')
    parser.add_argument('--monitor', action='store_true',
        help="overrides the mode in the config file with `monitor`")
    
    parser.add_argument('--overwrite', action='store_true',
        help='overwrite existing output files')
    
    parser.add_argument('--no-start-pulse', action='store_true',
        help='do not wait for plexon start pulse or enter press, skips initial 3 second wait')
    parser.add_argument('--loadcell-out',
        help='file to write loadcell csv data to')
    parser.add_argument('--events-out',
        help='file to write event data to')
    parser.add_argument('--no-record', action='store_true',
        help='allow not recording loadcell data')
    parser.add_argument('--live', action='store_true',
        help='show real time data')
    parser.add_argument('--live-cal', action='store_true',
        help='show real time calibrated data')
    parser.add_argument('--live-bias',
        help='path to a bias file or glob pattern matching the bias file for live view')
    parser.add_argument('--live-secs', type=int, default=5,
        help='number of seconds to keep data for in live view (5)')
    
    parser.add_argument('--no-end-prompt', action='store_true',
        help='skip the user prompt after tilts are completed')
    
    parser.add_argument('--meta-out',
        help='output path for generated meta file')
    parser.add_argument('--template-in',
        help='input path for template')
    parser.add_argument('--template-out',
        help='output path for template')
    
    parser.add_argument('--retry', action='store_true',
        help=argparse.SUPPRESS)
    parser.add_argument('--mock', action='store_true',
        help=argparse.SUPPRESS)
    
    if config_path is not None:
        raw_args = copy(sys.argv[1:])
        with open(config_path, encoding='utf8') as f:
            config_data = hjson.load(f)
        
        if '-' in config_data:
            raw_args.extend(config_data['-'])
            del config_data['-']
        
        for k, v in config_data.items():
            if k.startswith('-'):
                raw_args.append(f"{k}")
                if v is not None:
                    raw_args.append(str(v))
    else:
        raw_args = None
    
    args = parser.parse_args(args=raw_args)
    
    # if args.loadcell_out is None and not args.no_record:
    #     parser.error("must specify --no-record if --loadcell-out is not set")
    
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
    
    def auto_path(path_str: Optional[str], postfix: str) -> Optional[str]:
        if path_str == "":
            return None
        if args.loadcell_out is None or path_str is not None:
            return path_str
        path = Path(args.loadcell_out)
        path = path.parent / f"{path.stem}{postfix}"
        return str(path)
    
    args.meta_out = auto_path(args.meta_out, "_meta.json")
    
    args.events_out = auto_path(args.events_out, "_events.json")
    
    if args.template_out is not None:
        assert args.meta_out is not None and args.events_out is not None, "Must output meta and events file to automatically generate a template."
    
    args_record = dict(vars(args))
    # hide unused dev flags
    dev_flags = [
        'mock',
        'retry',
        'no_end_prompt',
    ]
    for flag in dev_flags:
        if not args_record[flag]:
            del args_record[flag]
    
    mock = args.mock
    
    if args.bias is not None:
        config.mode = 'bias'
    if args.monitor:
        config.mode = 'monitor'
    
    if config.mode == 'bias':
        if not args.overwrite:
            assert not Path(args.bias).exists(), f"output file {args.bias} already exists"
        return bias_main(config, args.bias, args.mock)
    
    if config.mode == 'open_loop':
        mode = 'open_loop'
    elif config.mode == 'closed_loop':
        mode = 'closed_loop'
    elif config.mode == 'monitor':
        mode = 'monitor'
    elif config.mode in ['stim']:
        mode = config.mode
    else:
        raise ValueError(f"invalid mode {config.mode}")
    
    if config.stim_params is not None:
        raw_stim_mode = config.stim_params['mode']
        if raw_stim_mode in ['random', 'classifier']:
            stim_mode = raw_stim_mode
        else:
            raise ValueError(f"Invalid stim mode {raw_stim_mode}")
    else:
        stim_mode = None
    
    assert mode in ['closed_loop', 'open_loop', 'monitor', 'stim']
    
    if config.tilt_sequence is not None:
        tilt_sequence = config.tilt_sequence
        if config.sequence_repeat != 1:
            tilt_sequence = tilt_sequence * config.sequence_repeat
        if config.sequence_shuffle:
            tilt_sequence = random.sample(tilt_sequence, k=len(tilt_sequence))
    else:
        tilt_sequence = generate_tilt_sequence(config.num_tilts)
    
    output_extra = {
        'config': config.raw,
        'args': args_record,
        'input_files': {},
        'output_files': {},
        'tilt_sequence': tilt_sequence,
    }
    
    record_state = RecordState()
    start_recording(record_state, args, config)
    
    if mode == 'monitor':
        input('press enter to exit')
        record_state.stop_recording()
        return
    
    if mode == 'stim':
        if stim_mode != 'random':
            print(f'invalid stim mode {stim_mode}')
            return
        stim_state = spawn_random_stimulus_process(config.stim_params, mock=args.mock, verbose=os.environ.get('print_stim'))
        input('press enter to exit')
        stim_state.stop()
        record_state.stop_recording()
        return
    
    assert mode in ['closed_loop', 'open_loop']
    
    if args.meta_out is not None and not args.overwrite:
        assert not Path(args.meta_out).exists(), f"output file {args.meta_out} already exists"
    if args.events_out is not None and not args.overwrite:
        assert not Path(args.events_out).exists(), f"output file {args.events_out} already exists"
    if args.template_out is not None and not args.overwrite:
        assert not Path(args.template_out).exists(), f"output file {args.template_out} already exists"
    
    if not args.no_start_pulse and not args.mock:
        print("waiting for plexon start pulse")
        line_wait("Dev4/port2/line1", True)
        
        input("Press enter to start")
        print("Waiting 3 seconds ?")
        time.sleep(3) # ?
    
    post_time = 200
    bin_size = 20
    
    with ExitStack() as stack:
        
        if stim_mode == 'random':
            stim_state = spawn_random_stimulus_process(config.stim_params, mock=args.mock, verbose=os.environ.get('print_stim'))
            _recording_check_event['stim'] = stim_state.failed
            stim_handler = None
        elif stim_mode == 'classifier':
            stim_state = None
            _recording_check_event['stim'] = False
            stim_handler = TiltStimulation(
                stim_params = config.stim_params,
                tilt_types = set(tilt_sequence),
                mock = args.mock,
                verbose = os.environ.get('print_stim'),
            )
        else:
            stim_state = None
            stim_handler = None
            _recording_check_event['stim'] = False
        
        baseline_recording = config.baseline
        
        def before_platform_close():
            if args.loadcell_out is not None:
                fpath = Path(args.loadcell_out)
                grf_file_hash = hash_file(fpath)
                
                output_extra['output_files'][fpath.name] = grf_file_hash
        
        def after_platform_close():
            if args.events_out is not None:
                fpath = Path(args.events_out)
                file_hash = hash_file(fpath)
                output_extra['output_files'][fpath.name] = file_hash
            
            if args.meta_out is not None:
                with open(args.meta_out, 'w', encoding='utf8') as f:
                    json.dump(output_extra, f, indent=2)
            
            if args.template_out is not None:
                print("building templates...")
                build_template_file(
                    args.meta_out, args.events_out, args.template_out,
                    post_time = post_time,
                    bin_size = bin_size,
                )
                print("templates generated")
        
        def stop_recording():
            print("waiting for recording to stop")
            record_state.stop_recording()
        
        if mode == 'closed_loop':
            collect_events = True
        elif mode == 'open_loop':
            collect_events = False
        else:
            raise ValueError("Invalid mode")
        
        if mode == 'closed_loop':
            classifier: Optional[EuclClassifier] = EuclClassifier(
                post_time = post_time,
                bin_size = bin_size,
            )
            
            if not baseline_recording:
                assert args.template_in is not None
            if args.template_in is not None:
                with open(args.template_in, encoding='utf8') as f:
                    template_in = json.load(f)
                assert classifier.post_time == template_in['info']['post_time'], f"{classifier.post_time} {template_in['info']['post_time']}"
                assert classifier.bin_size == template_in['info']['bin_size'], f"{classifier.bin_size} {template_in['info']['bin_size']}"
                classifier.templates = template_in['templates']
                # events_path = template_in.get('events_path')
                # if events_path is not None:
                #     events_path = Path(events_path)
                #     if not events_path.is_absolute():
                #         events_path = Path(args.template_in).parent / events_path
                #     with open(events_path, encoding='utf8') as f:
                #         events_record = json.load(f)
                #     classifier.build_template_from_events(template_in['tilts'], events_record)
                # else:
                #     classifier.build_template_from_record(template_in['tilts'])
        else:
            classifier = None
            baseline_recording = True
        
        stack.callback(after_platform_close)
        
        # add stim callback after after_platform_close so the events are saved
        # to the output file before it is saved
        def stop_stim():
            if stim_state is not None:
                stim_state.stop()
                output_extra['stim_events'] = stim_state.event_list()
            elif stim_handler is not None:
                output_extra['stim_events'] = stim_handler.event_log
        stack.callback(stop_stim)
        
        platform = PsthTiltPlatform(
            baseline_recording = baseline_recording,
            channel_dict = config.channels,
            mock = mock,
            pyopx = config.plexon_lib == 'opx',
            after_tilt_delay = config.after_tilt_delay,
            collect_events = collect_events,
            reward_enabled = config.reward,
            water_duration = config.water_duration,
            post_time = post_time,
            delay_range = config.delay_range,
            classifier = classifier,
            tilt_duration = 1.5 if mock else None,
            record_state = record_state,
            stim_handler = stim_handler,
        )
        
        stack.enter_context(platform)
        stack.callback(before_platform_close)
        # add stop_recording to the exit stack after before_close_platform so the 
        # correct hash can be created for the grf recording
        stack.callback(stop_recording)
        
        if args.events_out is not None:
            events_file = stack.enter_context(open(args.events_out, 'w', encoding='utf8'))
            events_file.write('[\n')
            def finish_write_events():
                events_file.write('\n]\n')
            stack.callback(finish_write_events)
            _first_event = [True]
            def write_event(rec):
                if _first_event:
                    _first_event.clear()
                else:
                    events_file.write(',\n')
                json.dump(rec, events_file)
            platform.event_callback = write_event
        
        run_psth_loop(
            platform, tilt_sequence,
            yoked = config.yoked, retry_failed = args.retry,
            output_extra = output_extra,
            template_in_path = args.template_in,
            stim_state = stim_state,
        )
        if not args.no_end_prompt:
            input("press enter to stop recording and exit")
    
    check_recording()

if __name__ == '__main__':
    main()
