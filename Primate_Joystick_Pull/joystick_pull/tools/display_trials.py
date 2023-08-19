
import os
import argparse
from pathlib import Path

from butil import EventReader
from .output_gen.gen_csv import group_trials, find_one

def get_disp_data(trials):
    for events in trials:
        comp = find_one(events, 'task_completed', default=None)
        success = comp is not None and comp['info']['success']
        
        if comp is not None:
            fail_reason = comp['info']['failure_reason']
        else:
            fail_reason = None
        
        s = events[0]['time_m']
        e = events[-1]['time_m']
        d = e - s
        
        out = []
        for e in events:
            rel_time = e['time_m'] - s
            perc = rel_time / d
            
            out.append({
                **e,
                'rel_time': rel_time,
                'perc': perc,
                'trial_dur': d,
                'success': success,
                'fail_reason': fail_reason,
            })
        
        yield out

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--success', action='store_true',
        help="only show successful trials")
    parser.add_argument('input', type=Path)
    
    return parser.parse_args()

def main():
    width, _ = os.get_terminal_size()
    args = parse_args()
    
    with EventReader(path=args.input) as reader:
        data = reader.read_records()
        trials = group_trials(data, filter_incomplete=False)
        
        trials = get_disp_data(trials)
        max_d = 20
        
        section_count = width
        for trial_i, trial in enumerate(trials):
            success = trial[0]['success']
            if args.success and not success:
                continue
            
            c = '-' if success else '+'
            trial_info_str = f"{trial_i} "
            fr = trial[0]['fail_reason']
            if fr is not None:
                trial_info_str += f"{fr} "
            header_width = width - len(trial_info_str)
            print(trial_info_str, end='')
            if trial[0]['trial_dur'] > max_d:
                print(c*header_width, sep='')
            else:
                print(f'{c} '*(header_width//2), sep='')
            
            for e in trial:
                rel_time = e['rel_time']
                perc = rel_time / max(max_d, e['trial_dur'])
                section = round(perc*section_count)
                
                if e['name'] == 'trial_start':
                    disp_time = f"({e['time_m']:.4f})"
                else:
                    disp_time = f"{e['rel_time']:.4f}"
                
                if perc <= 0.5:
                    print(f"{' '*section}|{e['name']} {disp_time}")
                else:
                    part = f"{e['name']} {disp_time}"
                    print(f"{' '*(section-len(part)-1)}{part}|")

if __name__ == '__main__':
    main()
