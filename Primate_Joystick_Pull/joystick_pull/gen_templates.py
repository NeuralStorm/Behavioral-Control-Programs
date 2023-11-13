
from typing import Any
import argparse
from pathlib import Path
import json
import sys
import os
from contextlib import ExitStack

import behavioral_classifiers
from butil import EventReader
from .tools.time_sync import get_event_times

from .config import GameConfig

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

_RED = '\033[91m'
_ENDC = '\033[0m'
def print_error(err):
    if sys.platform == "win32":
        os.system('color')
    if not isinstance(err, str):
        err = str(err)
    err = _RED + err + _ENDC
    eprint(err)

"""
event is the event in trial details
event class is the classification event found in real time
aliases (optional) is a set that specifies other strings that can be used instead of the key
"""
event_classes = {
    'joystick_pull': {
        'event': 'joystick_pull',
        'event_class': 'joystick_pull',
        'aliases': {'tpullstart'},
    },
    'discrim': {
        'event': 'discrim',
        'event_class': 'discrim_shown',
        'aliases': {'tdiscrim'},
    },
    'go_cue': {
        'event': 'go_cue',
        'event_class': 'go_cue_shown',
        'aliases': {'tgocue'},
    },
}

def parse_args(args):
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--events', required=True, type=Path,
        help=".json.gz file")
    parser.add_argument('--event-class', required=True,
        help="e.g. joystick_pull")
    parser.add_argument('--template-out', type=Path,
        help="")
    parser.add_argument('--info-out', type=Path,
        help="debug info output path")
    parser.add_argument('--labels', type=Path,
        help="json labels file")
    parser.add_argument('--post-time', type=int, default=200,
        help="window size after event in ms")
    parser.add_argument('--bin-size', type=int, default=20,
        help="bin size in ms")
    
    return parser.parse_args(args=args)

def gen_templates_main(stack, args_list=None):
    args = parse_args(args_list)
    
    debug_info = {}
    # end info written is added last for readability of output file
    end_debug_info = {}
    ts_info = []
    debug_info['ts'] = ts_info
    
    def write_debug_info():
        debug_info.update(end_debug_info)
        if args.info_out is not None:
            with open(args.info_out, 'w', encoding='utf8', newline='\n') as f:
                json.dump(debug_info, f, indent=2)
    stack.callback(write_debug_info)
    
    event_class = None
    try:
        event_class = event_classes[args.event_class]
    except KeyError:
        for v in event_classes.values():
            if args.event_class in v.get('aliases', set()):
                event_class = v
                break
    if event_class is None:
        print_error(f'unknown event class {args.event_class}')
        sys.exit(1)
    
    events = []
    with EventReader(path=args.events) as reader:
        for record in reader.read_records():
            name = record.get('name')
            if name is None:
                continue
            events.append(record)
    data = get_event_times.get_trial_details(events, plx_offset=0)
    data = list(data)
    end_debug_info['trial_details'] = data
    end_debug_info['events'] = events
    
    def get_ts():
        for rec in data:
            dbg: Any = {}
            ts_info.append(dbg)
            try:
                if rec['events']['task'] is None:
                    dbg['error'] = 'no task'
                    continue
                succ = rec['events']['task']['info']['success']
                task_id = rec['events']['task']['id']
            except KeyError as e:
                dbg['error'] = f"key error {e}"
                continue
            dbg['task_id'] = task_id
            dbg['success'] = succ
            
            cue = rec['events']['task']['info']['discrim']
            dbg['cue'] = cue
            
            event = rec['events'][event_class['event']]
            if event is None or '_ts' not in event:
                dbg['error'] = f"no timestamp for task {task_id}"
                print_error(f"no timestamp for task {task_id}")
                continue
            ts = event['_ts']
            dbg['ts'] = ts
            
            if not succ:
                dbg['error'] = "not success"
                continue
            
            yield cue, ts
    
    ts = list(get_ts())
    debug_info['event_timestamps'] = ts
    # eprint('events', ts)
    eprint('event count', len(ts))
    
    if args.labels is None:
        labels = None
    else:
        with open(args.labels) as f:
            labels = json.load(f)['channels']
    
    if args.template_out is not None:
        debug_info['templates'] = behavioral_classifiers.eucl_classifier.build_templates_from_new_events_file(
            ts_list = ts,
            events_path = args.events,
            template_path = args.template_out,
            event_class = event_class['event_class'],
            post_time = args.post_time,
            bin_size = args.bin_size,
            labels = labels,
        )

def main():
    with ExitStack() as stack:
        gen_templates_main(stack)

if __name__ == '__main__':
    main()
