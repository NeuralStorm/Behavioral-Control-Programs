
from typing import Optional
import json
import csv
from copy import copy
from pprint import pprint
from pathlib import Path
import argparse
import sys
import os
from contextlib import ExitStack

from butil import EventReader
from ..output_gen.gen_csv import group_trials, find, find_one, find_id

def get_trial_details(events: list, plx_offset: Optional[float]=None):
    if plx_offset is None:
        plx_start = find_one(events, 'plexon_recording_start')
        plx_offset = plx_start['info']['time_ext']
    else:
        plx_offset = plx_offset
    
    for trial in group_trials(events):
        trial_e          = find_one(trial, 'trial_start')
        task_complete    = find_one(trial, 'task_completed')
        homezone_enter   = find_one(trial, 'homezone_enter', ignore_extra=True, default=None)
        
        joystick_pull    = find_id(trial, task_complete['info']['js_pull_event'])
        joystick_release = find_id(trial, task_complete['info']['js_release_event'])
        homezone_exit    = find_id(trial, task_complete['info'].get('homezone_exit_event'))
        
        jsz_after = None
        if homezone_exit is not None:
            jsz_after = homezone_exit['time_m']
        jsz_enter = find_one(trial, 'joystick_zone_enter', after=jsz_after, ignore_extra=True, default=None)
        jsz_exit  = find_one(trial, 'joystick_zone_exit' , after=jsz_after, ignore_extra=True, default=None)
        
        discrim = find_one(trial, 'discrim_shown' , default=None)
        go_cue  = find_one(trial, 'go_cue_shown'  , default=None)
        water   = find_one(trial, 'water_dispense', default=None)
        
        # try to handle older data without homezone exit event id
        if 'homezone_exit_event' not in task_complete['info'] and go_cue is not None:
            assert homezone_exit is None
            homezone_exit = find_one(trial, 'homezone_exit', after=go_cue['time_m'], ignore_extra=True, default=None)
        
        out = {
            'trial_event': trial_e,
            'task': task_complete,
            'joystick_pull': joystick_pull,
            'joystick_released': joystick_release,
            'homezone_enter': homezone_enter,
            'homezone_exit': homezone_exit,
            'jsz_enter': jsz_enter,
            'jsz_exit': jsz_exit,
            'discrim': discrim,
            'go_cue': go_cue,
            'water_dispense': water,
        }
        
        # find reference to estimate plexon time based on
        def find_ref():
            for e in trial:
                if 'time_ext' in e['info']:
                    return e
            return None
        ref_event = find_ref()
        
        def add_est(rec):
            if rec is None:
                return None
            if ref_event is None:
                return rec
            rec = copy(rec)
            d = rec['time_m'] - ref_event['time_m']
            rec['_estimated_plx_time'] = ref_event['info']['time_ext'] + d
            return rec
        
        # estimate plexon time
        for k, v in out.items():
            if v is None:
                continue
            out[k] = add_est(v)
        
        # add consistent _ts key that is always the best timestamp
        for k, v in out.items():
            if v is None:
                continue
            def get_ts():
                if 'time_ext' in v['info']:
                    return v['info']['time_ext']
                if '_estimated_plx_time' in v:
                    return v['_estimated_plx_time']
                return None
            ts = get_ts()
            if ts is not None:
                v['_ts'] = ts
        
        if plx_offset != 0.0:
            for k, v in out.items():
                if v is not None and '_ts' in v:
                    # plx offset is the offset to apply to the plx timestamps so subtract here
                    v['_ts'] -= plx_offset
        
        yield {
            'events': out,
        }

def build_csv(events, trial_details, out_path: Path):
    with ExitStack() as stack:
        def get_reader():
            if 'no_csv_gen' not in os.environ:
                try:
                    from joystick_pull.tools.output_gen import gen_csv
                except ImportError:
                    pass
                else:
                    return gen_csv.gen_csv_rows(events, permissive=True)
            
            return iter([[] for _ in trial_details])
        
        reader = get_reader()
        assert reader is not None
        
        out_f = stack.enter_context(open(out_path, 'w'))
        
        writer = csv.writer(out_f)
        header = next(reader)
        # header += [f'{event_class}_ts']
        header += ['homezone_enter_ts', 'DiscrimDisplay', 'GoCue_Display', 'ExitHomeZone', 'JoystickPull', 'JoystickRelease', 'water_dispense', 'joystick_zone_enter', 'joystick_zone_exit']
        writer.writerow(header)
        rows = list(reader)
        # print(len(rows), len(trial_details))
        n = len(trial_details)
        # print(n)
        for row, trial in zip(rows[:n-1], trial_details):
            trial = trial['events']
            def get_ts(k):
                x = trial[k]
                if x is None:
                    return None
                if '_ts' in x:
                    return x['_ts']
                return None
            ts = [
                get_ts('homezone_enter'),
                get_ts('discrim'),
                get_ts('go_cue'),
                get_ts('homezone_exit'),
                get_ts('joystick_pull'),
                get_ts('joystick_released'),
                get_ts('water_dispense'),
                get_ts('jsz_enter'),
                get_ts('jsz_exit'),
            ]
            writer.writerow(row + ts)
        
        for row in rows[n-1:]:
            writer.writerow(row)

def build_event_info_csv(trial_details, out_path):
    with open(out_path, 'w') as out_f:
        writer = csv.writer(out_f)
        writer.writerow(['EventLabel', 'EventTimestamp', 'Index'])
        i = 0
        for trial in trial_details:
            trial = trial['events']
            if trial['task'] is None:
                continue
            disc = trial['task']['info']['discrim']
            succ = trial['task']['info']['success']
            
            succ_s = 'Correct' if succ else 'Incorrect'
            
            events = [
                'homezone_enter',
                'discrim',
                'go_cue',
                'homezone_exit',
                'joystick_pull',
                'joystick_released',
                'water_dispense',
                'jsz_enter',
                'jsz_exit',
            ]
            for e in events:
                label = f"{disc}_{succ_s}_{e}"
                # print(label)
                if trial[e] is None:
                    continue
                if '_ts' not in trial[e]:
                    continue
                ts = trial[e]['_ts']
                writer.writerow([label, ts, i])
                i += 1

def run_for_paths(events_path, csv_out, event_info_path=None, *, plx_offset: Optional[float] = None, trial_details_path=None):
    input_path = events_path
    ignore_photodiode = True
    out_events = []
    with ExitStack() as stack:
        reader = stack.enter_context(EventReader(path=input_path))
        
        for record in reader.read_records():
            name = record.get('name')
            if name is None:
                continue
            if ignore_photodiode and name == 'photodiode_changed':
                continue
            out_events.append(record)
    
    events = out_events
    
    # print("event types", {e['name'] for e in events})
    
    trial_details = list(get_trial_details(events, plx_offset=plx_offset))
    
    if trial_details_path is not None:
        with open(trial_details_path, 'w') as f:
            json.dump(trial_details, f, indent=2)
    
    build_csv(events, trial_details, csv_out)
    if event_info_path is not None:
        build_event_info_csv(trial_details, event_info_path)

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--events', required=True, type=Path,
        help='events json')
    parser.add_argument('--csv-out', required=True, type=Path,
        help='csv output with added timestamps')
    parser.add_argument('--event-info',
        help='event info csv output')
    parser.add_argument('--trial-details',
        help='trial details json output')
    parser.add_argument('--offset', type=float,
        help='time to subtract from external timestamps in seconds')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    path = args.events
    csv_out = args.csv_out
    event_info = args.event_info
    
    run_for_paths(path, csv_out, event_info, plx_offset=args.offset, trial_details_path=args.trial_details)

if __name__ == '__main__':
    main()
