
from typing import Any, Optional
import csv
from pprint import pprint
from datetime import timedelta
import statistics
from collections import Counter
from itertools import groupby
from copy import deepcopy

class RaiseType:
    pass
Raise = RaiseType()

class EventNotFound(Exception):
    pass
class MoreThanOne(Exception):
    pass

def sgroup(data, key):
    return groupby(sorted(data, key=key), key=key)

def _group_trials_inner(data):
    # trials = []
    trial_events = None
    for x in data:
        if x['name'] == 'trial_start':
            # trials.append([])
            if trial_events:
                yield trial_events
            trial_events = []
        # if trials:
            # trials[-1].append(x)
        if trial_events is not None:
            trial_events.append(x)
    
    if trial_events:
        yield trial_events
    # return trials

def group_trials(
    events, *,
    filter_incomplete=True,
    game_only=True,
    filter_photodiode=False,
):
    def p(evt):
        name = evt.get('name')
        if game_only and name is None:
            return False
        if filter_photodiode and name in ['photodiode_changed', 'photodiode_on', 'photodiode_off']:
            return False
        return True
    
    events = (e for e in events if p(e))
    trials = _group_trials_inner(events)
    if filter_incomplete:
        trials = filter_incomplete_trials(trials)
    return trials

def find(events, name, *,
    after: Optional[float] = None,
    event_id = None,
):
    for e in events:
        if after is not None and not e['time_m'] > after:
            continue
        if event_id is not None and e.get('id') != event_id:
            continue
        if name is None or e.get('name') == name:
            yield e

def find_one(
    events, name: Optional[str] = None, *,
    ignore_extra: bool = False,
    default: Any = Raise,
    after: Optional[float] = None,
    event_id = None,
) -> Any:
    it = find(events, name, after=after, event_id=event_id)
    try:
        out = next(it)
    except StopIteration:
        if default is Raise:
            raise EventNotFound(f"not found {name}")
        return default
    if ignore_extra:
        return out
    try:
        next(it)
    except StopIteration:
        return out
    raise MoreThanOne(f"more than one {name}")

def find_id(events, event_id: Optional[int]):
    if event_id is None:
        return None
    return find_one(events, event_id=event_id)

def filter_incomplete_trials(trials):
    """filters incomplete trials, may be from game being stopped, program closing, etc"""
    for trial in trials:
        comp = find_one(trial, 'task_completed', ignore_extra=True, default=None)
        if comp is not None:
            yield trial

def row_from_trial(events, trial, *, trial_i, task_type: str, config):
    def _find(name):
        yield from find(trial, name)
    def _find_one(name, ignore_extra=False, default:Any=Raise):
        return find_one(trial, name, ignore_extra=ignore_extra, default=default)
    
    # pprint(trial)
    start = _find_one('trial_start')
    comp_event = _find_one('task_completed')
    comp = comp_event['info']
        # 'reward_duration': reward_duration, # Optional[float]
        # 'remote_pull_duration': remote_pull_duration, # float
        # 'pull_duration': pull_duration, # float
        # 'action_duration': action_duration,
        # 'success': reward_duration is not None, # bool
        # 'failure_reason': log_failure_reason[0], # Optional[str]
        # 'discrim': selected_image_key, # str
    
    js_enter = _find_one('joystick_zone_enter', ignore_extra=True, default=None)
    js_exit = _find_one('joystick_zone_exit', ignore_extra=True, default=None)
    def get_t(evt):
        if evt is None:
            return ''
        if 'plexon_ts' in evt['info']:
            return evt['info']['plexon_ts']
        return evt['time_m']
    
    # pprint(start)
    # pprint(comp)
    # print(js_enter)
    # print(js_exit)
    
    is_success = comp['reward_duration'] is not None
    reason = comp['failure_reason'] or ''
    
    time_in_homezone = 0
    pull_duration = 0
    if task_type == 'homezone_exit':
        time_in_homezone = comp['pull_duration']
    elif task_type == 'joystick_pull':
        pull_duration = comp['pull_duration']
        
        if reason == 'hand removed before cue':
            def get_cue_name():
                if comp['homezone_exit_event'] is None:
                    return False
                home_exit = find_one(events, event_id=comp['homezone_exit_event'])
                discrim = find_one(trial, 'discrim_shown', default=None)
                if discrim is None or home_exit['time_m'] < discrim['time_m']:
                    return 'discrim'
                else:
                    return 'go cue'
            
            def check_pull_after_early_exit():
                if comp['homezone_exit_event'] is None:
                    return False
                _home_exit = find_one(events, event_id=comp['homezone_exit_event'])
                _js_pull = find_one(events, 'joystick_pulled', ignore_extra=True, default=None, after=_home_exit['time_m'])
                
                if _js_pull is None:
                    return False
                
                time_diff = _js_pull['info']['time_ext'] - _home_exit['info']['time_ext']
                
                return time_diff < config['post_successful_pull_delay']
            
            cue_name = get_cue_name()
            if check_pull_after_early_exit():
                reason = f'joystick pulled before {cue_name}'
            else:
                reason = f'hand removed before {cue_name}'
    
    row = [
        trial_i+1,
        # start['info']['discrim'],
        comp['discrim'],
        is_success,
        reason,
        time_in_homezone,
        pull_duration,
        comp['reward_duration'] or 0,
        get_t(js_enter),
        get_t(js_exit),
        start['info']['discrim_delay'],
        start['info']['go_cue_delay'],
    ]
    
    return row

def gen_trial_rows(events):
    config_event = find_one(events, 'config_loaded', ignore_extra=True)
    
    trials = group_trials(events)
    
    for trial_i, trial in enumerate(trials):
        new_config_event = list(find(trial, 'config_loaded'))
        if new_config_event:
            config_event = new_config_event[-1]
        try:
            row = row_from_trial(
                events,
                trial,
                trial_i = trial_i,
                task_type = config_event['info']['config']['task_type'],
                config = config_event['info']['config']
            )
        except EventNotFound as e:
            print("trial", trial_i, e)
            # continue
            raise
        
        yield row

def get_end_info(events):
    events = [e for e in events if e['name'] == 'task_completed']
    
    n = len(events)
    def perc(count):
        if n == 0:
            return 0
        return count/n
    
    error_counts = Counter()
    for e in events:
        reason = e['info']['failure_reason']
        if reason is None:
            continue
        error_counts[reason] += 1
    error_info = {
        reason: {'count': c, 'percent': perc(c)}
        for reason, c in error_counts.items()
    }
    
    correct = [e for e in events if e['info']['success']]
    correct_n = len(correct)
    
    pull_durations = [e['info']['action_duration'] for e in events]
    pull_durations = [x for x in pull_durations if x != 0]
    
    def get_discrim_durations():
        for discrim, d_events in sgroup(events, lambda x: x['info']['discrim']):
            d_events = list(d_events)
            d_correct = [e for e in d_events if e['info']['success']]
            pull_durations = [
                e['info']['action_duration']
                for e in d_events
            ]
            count = len(pull_durations)
            pull_durations = [x for x in pull_durations if x != 0]
            out = {
                'count': count, # number of times discrim appeared
                'pull_count': len(pull_durations), # number of pulls in response to discrim
                'correct_count': len(d_correct),
                'min': min(pull_durations, default=0),
                'max': max(pull_durations, default=0),
                'mean': statistics.mean(pull_durations) if pull_durations else 0,
                'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
            }
            yield discrim, out
    
    info = {
        'count': n,
        'correct_count': len(correct),
        'percent_correct': perc(correct_n),
        'action_duration': {
            'min': min(pull_durations, default=0),
            'max': max(pull_durations, default=0),
            'mean': statistics.mean(pull_durations) if pull_durations else 0,
            'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
        },
        'discrim_action_duration': dict(get_discrim_durations()),
        'errors': error_info,
    }
    
    return info

def permissive_events(events):
    out = []
    for e in events:
        name = e.get('name')
        if name is None:
            continue
        e = deepcopy(e)
        if name == 'config_loaded':
            # handle old config_loaded structure with only raw data
            if 'task_type' not in e['info']['config']:
                if e['info']['config']['Number of Events'][0] == '0':
                    e['info']['config']['task_type'] = 'homezone_exit'
                else:
                    e['info']['config']['task_type'] = 'joystick_pull'
            if 'post_successful_pull_delay' not in e['info']['config']:
                e['info']['config']['post_successful_pull_delay'] = 1.8
        
        out.append(e)
    
    return out

def gen_csv_rows(events, *, permissive=False):
    if permissive:
        events = permissive_events(events)
    yield [
        'trial',
        'discrim',
        'success',
        'failure reason',
        'time in homezone',
        'pull duration',
        'reward duration',
        'joystick_zone_enter',
        'joystick_zone_exit',
        'discrim_delay',
        'go_cue_delay',
    ]
    
    yield from gen_trial_rows(events)
    
    if not events:
        time_in_game = 0
    else:
        start_evt = find_one(events, 'game_start', ignore_extra=True, default=None)
        if start_evt is None:
            time_in_game = 0
        else:
            time_in_game = events[-1]['time_m'] - start_evt['time_m']
    time_in_game_str = str(timedelta(seconds=time_in_game))
    yield []
    
    end_info = get_end_info(events)
    dur = end_info['action_duration']
    yield [
        'count', end_info['count'],
        'percent_correct', end_info['percent_correct'],
        'time_in_game', time_in_game_str,
    ]
    yield [
        'min', dur['min'],
        'max', dur['max'],
        'mean', dur['mean'],
        'stdev', dur['stdev'],
    ]
    yield []
    
    yield ['discrim', 'correct', 'pulls', 'count', 'min', 'max', 'mean', 'stdev']
    for discrim, dad in end_info['discrim_action_duration'].items():
        yield [
            discrim, dad['correct_count'], dad['pull_count'], dad['count'],
            dad['min'], dad['max'], dad['mean'], dad['stdev'],
        ]
    yield []
    
    yield ['error', 'count', 'percent']
    for e, ei in end_info['errors'].items():
        yield [e, ei['count'], ei['percent']]

def write_csv(f, events, tsv_mode=False):
    if tsv_mode:
        dialect = csv.excel_tab
    else:
        dialect = csv.excel
    writer = csv.writer(f, dialect=dialect)
    
    for row in gen_csv_rows(events):
        writer.writerow(row)
