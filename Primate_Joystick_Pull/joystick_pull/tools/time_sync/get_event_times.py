
from typing import Optional, Dict, Any
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

def isolate_recording_start(events, target_idx):
    found = True
    idx = 0
    
    out = []
    for evt in events:
        if evt['name'] != 'plexon_recording_start':
            out.append(evt)
        else:
            if target_idx == idx:
                found = True
                out.append(evt)
            idx += 1
    
    assert found
    return out

def get_trial_details(
    events: list, plx_offset: Optional[float]=None,
    pd_times: Dict[int, float] = {},
    estimate: bool = False,
):
    config_loaded = find_one(events, 'config_loaded')
    is_joystick = config_loaded['info']['config']['task_type'] == 'joystick_pull'
    if not is_joystick:
        assert config_loaded['info']['config']['task_type'] == 'homezone_exit'
    post_successful_pull_delay = config_loaded['info']['config']['post_successful_pull_delay']
    
    
    if plx_offset is None:
        plx_start = find_one(events, 'plexon_recording_start')
        plx_offset = plx_start['info']['time_ext']
    else:
        plx_offset = plx_offset
    
    for trial in group_trials(events, filter_incomplete=False):
        trial_end = find_one(trial, 'trial_end', ignore_extra=True, default=None)
        game_stop = find_one(trial, 'game_stop', ignore_extra=True, default=None)
        if game_stop is not None:
            yield {'_partial': True, 'errortrial': 'S'}
            continue
        elif trial_end is None:
            yield {'_partial': True, 'errortrial': 'X'}
            continue
        
        trial_e          = find_one(trial, 'trial_start')
        task_complete    = find_one(trial, 'task_completed')
        success = task_complete['info']['success']
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
        
        class_attem = find_one(trial, 'classification_attempted', default=None)
        
        def prep_pd(event):
            try:
                edge_time = pd_times[event['id']]
            except KeyError:
                pd_on = find_one(trial, 'photodiode_on', after=event['time_m'], ignore_extra=True, default=None)
                if pd_on is None:
                    return None
                
                out = {
                    'id': event['id'],
                    'name': event['info']['name'],
                    't': pd_on['info']['edge_ts'],
                    '_debug': {
                        'local_event_time': event['time_m'],
                        'local_pd_time': pd_on['time_m'],
                        'external_pd_time': pd_on['info']['time_ext'],
                        'edge_time': pd_on['info']['edge_ts'],
                    },
                }
                return out
                
                assert False
            
            out = {
                'id': event['id'],
                'name': event['info']['name'],
                't': edge_time,
            }
            return out
        trial_pds_ = (prep_pd(x) for x in trial if x['name'] == 'photodiode_expected')
        trial_pds: list[Any] = [x for x in trial_pds_ if x is not None]
        def get_pd_time(name, *, first=False, last=False):
            def gen():
                for pd in trial_pds:
                    if pd['name'] == name:
                        yield pd
            pds = list(gen())
            if not pds:
                return None
            if first:
                return pds[0]
            if last:
                return pds[-1]
            assert len(pds) == 1
            return pds[0]
        def get_pd_t(*args, **kwargs):
            x = get_pd_time(*args, **kwargs)
            return x['t'] if x is not None else None
        
        def add_pd_time(event, name):
            if event is None:
                return
            pd_time = get_pd_time(name)
            if pd_time is None:
                return
            event['_pd_time'] = pd_time['t']
        add_pd_time(discrim, 'discrim_shown')
        add_pd_time(go_cue, 'go_cue_shown')
        
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
            'classification_attempted': class_attem,
        }
        
        # find reference to estimate plexon time based on
        def find_ref():
            if not estimate:
                return None
            for e in trial:
                if 'time_ext' in e['info']:
                    return e
            for e in events:
                if 'time_ext' in e['info']:
                    return e
            return None
        ref_event = find_ref()
        
        def add_est(rec):
            if not estimate:
                return copy(rec)
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
        
        def add_ts(events):
            # add consistent _ts key that is always the best timestamp
            for k, v in events.items():
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
        add_ts(out)
        
        if plx_offset != 0.0:
            for k, v in out.items():
                if v is not None and '_ts' in v:
                    # plx offset is the offset to apply to the plx timestamps so subtract here
                    v['_ts'] -= plx_offset
        
        for k, v in out.items():
            if v is not None and '_pd_time' in v:
                v['_ts'] = v['_pd_time']
        
        def get_ts(evt):
            if isinstance(evt, str):
                evt = out[evt]
            if evt is None or '_ts' not in evt:
                return None
            return evt['_ts']
        
        def get_treward():
            if not success:
                return None
            if is_joystick:
                t = get_ts('joystick_released')
            else: # homezone exit
                t = get_ts('go_cue')
            if t is None:
                return None
            return t + post_successful_pull_delay
        
        timing_vars = {
            'tclock': get_ts('trial_event'),
            'tstart': get_pd_t('prep_diamond', first=True),
            'tdiscrim': get_ts('discrim'),
            'tgocue': get_ts('go_cue'),
            'tpullstart': get_ts('joystick_pull'),
            'tpullstop': get_ts('joystick_released'),
            'treward': get_treward(),
            'terror': get_pd_t('punish'),
        }
        
        yield {
            'events': out,
            'photodiode': trial_pds,
            'timing_vars': timing_vars,
            'errortrial': '0' if success else '1',
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
        
        out_f = stack.enter_context(open(out_path, 'w', newline='\n', encoding='utf8'))
        
        dialect = csv.excel if os.environ.get('no_tsv') else csv.excel_tab
        writer = csv.writer(out_f, dialect=dialect)
        header = next(reader)
        # header += [
        #     'homezone_enter_ts',
        #     'DiscrimDisplay',
        #     'GoCue_Display',
        #     'ExitHomeZone',
        #     'JoystickPull',
        #     'JoystickRelease',
        #     'water_dispense',
        #     'joystick_zone_enter',
        #     'joystick_zone_exit',
        # ]
        timing_var_names = []
        for trial in trial_details:
            if 'timing_vars' in trial:
                timing_var_names = list(trial['timing_vars'].keys())
                break
        header = copy(timing_var_names)
        header.append('errortrial')
        
        writer.writerow(header)
        rows = list(reader)
        n = len(trial_details)
        # for row, trial in zip(rows[:n-1], trial_details):
        for trial in trial_details:
            
            # trial = trial['events']
            # def get_ts(k):
            #     x = trial[k]
            #     if x is None:
            #         return None
            #     if '_ts' in x:
            #         return x['_ts']
            #     return None
            # ts = [
            #     get_ts('homezone_enter'),
            #     get_ts('discrim'),
            #     get_ts('go_cue'),
            #     get_ts('homezone_exit'),
            #     get_ts('joystick_pull'),
            #     get_ts('joystick_released'),
            #     get_ts('water_dispense'),
            #     get_ts('jsz_enter'),
            #     get_ts('jsz_exit'),
            # ]
            if trial.get('_partial'):
                ts = [None for k in timing_var_names]
            else:
                ts = [trial['timing_vars'][k] for k in timing_var_names]
            ts.append(trial['errortrial'])
            # writer.writerow(row + ts)
            writer.writerow(ts)
        
        # for row in rows[n-1:]:
        #     writer.writerow(row)

def build_event_info_csv(trial_details, out_path):
    with open(out_path, 'w', newline='\n', encoding='utf8') as out_f:
        dialect = csv.excel if os.environ.get('no_tsv') else csv.excel_tab
        writer = csv.writer(out_f, dialect=dialect)
        writer.writerow(['EventLabel', 'EventTimestamp', 'Index'])
        i = 0
        for trial in trial_details:
            if trial.get('_partial'):
                continue
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

def build_event_file_csv(
    trial_details, out_path, *,
    skip_failed: bool = True,
    key_format: str,
):
    def get_keys(trial):
        cue = trial['events']['task']['info']['discrim']
        success = trial['events']['task']['info']['success']
        if not success and skip_failed:
            return
        tv = trial['timing_vars']
        for k, ts in tv.items():
            if ts is None:
                continue
            key_vars = {
                'event_class': k,
                'cue': cue,
                'success': 's' if success else 'f',
            }
            out_k = key_format.format(**key_vars)
            yield out_k, ts
    
    trials_by_key = {}
    for trial in trial_details:
        if trial.get('_partial'):
            continue
        
        keys = get_keys(trial)
        for key, ts in keys:
            if key not in trials_by_key:
                trials_by_key[key] = []
            trials_by_key[key].append(ts)
    
    with open(out_path, 'w', newline='\n', encoding='utf8') as out_f:
        dialect = csv.excel if os.environ.get('no_tsv') else csv.excel_tab
        writer = csv.writer(out_f, dialect=dialect)
        
        def get_idx(xs, i):
            try:
                return xs[i]
            except IndexError:
                return None
        keys = sorted(trials_by_key)
        max_len = max(len(x) for x in trials_by_key.values())
        writer.writerow(keys)
        for i in range(max_len):
            row = [get_idx(trials_by_key[k], i) for k in keys]
            writer.writerow(row)

def run_for_paths(
    events_path, csv_out, event_info_path=None, *,
    event_file_path=None,
    plx_offset: Optional[float] = None, trial_details_path=None,
    pd_times_path: Optional[Path] = None,
    estimate: bool = False,
    ignore_photodiode: bool = False,
    key_format: str,
    include_failed: bool = False,
    permissive: bool = False,
    recording_start_idx: Optional[int] = None,
):
    input_path = events_path
    out_events = []
    with ExitStack() as stack:
        reader = stack.enter_context(EventReader(path=input_path))
        
        for record in reader.read_records():
            rtype = record.get('type')
            match rtype:
                case None:
                    pass
                case _:
                    continue
            name = record['name']
            if ignore_photodiode and name in ['photodiode_on', 'photodiode_off']:
                continue
            out_events.append(record)
    
    if recording_start_idx is not None:
        out_events = isolate_recording_start(out_events, recording_start_idx)
    
    pd_times = {}
    if pd_times_path is not None:
        with open(pd_times_path) as f:
            data = json.load(f)
            assert data['relative_to_recording_start'] is True
            pd_times = {int(k): v for k, v in data['times'].items()}
    
    events = out_events
    
    if permissive:
        from ..output_gen.gen_csv import permissive_events
        events = permissive_events(events)
    
    # print("event types", {e['name'] for e in events})
    
    trial_details = list(get_trial_details(events, plx_offset=plx_offset, pd_times=pd_times, estimate=estimate))
    
    if trial_details_path is not None:
        with open(trial_details_path, 'w', newline='\n', encoding='utf8') as f:
            json.dump(trial_details, f, indent=2)
    
    if csv_out is not None:
        build_csv(events, trial_details, csv_out)
    if event_info_path is not None:
        build_event_info_csv(trial_details, event_info_path)
    if event_file_path is not None:
        build_event_file_csv(
            trial_details, event_file_path,
            key_format=key_format,
            skip_failed = not include_failed,
        )

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--events', required=True, type=Path,
        help='events .json.gz')
    parser.add_argument('--pd-times', type=Path,
        help='pd times json, maps photodiode_expected event ids to times')
    parser.add_argument('--csv-out', type=Path,
        help='by trial tsv output')
    parser.add_argument('--event-info', type=Path,
        help='event info tsv output')
    parser.add_argument('--event-file', type=Path,
        help='event file tsv output')
    parser.add_argument('--trial-details', type=Path,
        help='trial details json output')
    parser.add_argument('--offset', type=float,
        help='time to subtract from external timestamps in seconds')
    parser.add_argument('--estimate', action='store_true',
        help='estimate external timestamps based on internal game clock')
    parser.add_argument('--ignore-photodiode', action='store_true',
        help='ignore photodiode events in the events file')
    parser.add_argument('--group-by', default='{event_class}',
        help='key format string used for event file')
    parser.add_argument('--include-failed', action='store_true',
        help='include failed trials in event file')
    parser.add_argument('--permissive', action='store_true',
        help='attempt to fill in data in older formats')
    parser.add_argument('--recording-start', type=int,
        help='which recording start to use')
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    path = args.events
    csv_out = args.csv_out
    event_info = args.event_info
    
    run_for_paths(
        path, csv_out, event_info,
        event_file_path=args.event_file,
        plx_offset=args.offset, trial_details_path=args.trial_details,
        pd_times_path = args.pd_times,
        estimate=args.estimate,
        key_format=args.group_by,
        include_failed=args.include_failed,
        permissive=args.permissive,
        recording_start_idx=args.recording_start,
    )

if __name__ == '__main__':
    main()
