
import sys
from pathlib import Path
import argparse
import traceback

import plotnine

import pandas as pd
import numpy as np

from plotnine import (
    ggplot,
    aes,
    after_stat,
    geom_histogram,
    geom_bar,
    geom_rect,
    geom_point,
    facet_wrap,
    facet_grid,
    coord_flip,
    scale_y_continuous,
    scale_x_continuous,
    scale_y_sqrt,
    scale_y_log10,
    scale_fill_manual,
    scale_x_discrete,
    scale_y_discrete,
    scale_y_continuous,
    theme_bw,
    theme_xkcd,
    theme_dark,
    theme_void,
    
)

from plotnine.data import diamonds
from mizani.formatters import percent_format

from MonkeyImages_Joystick_Conf import InfoView

import json

from collections import Counter
import statistics
from itertools import groupby

def sgroup(data, key):
    return groupby(sorted(data, key=key), key=key)

def get_end_info(event_log):
    events = [e for e in event_log if e['name'] == 'task_completed']
    
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

def get_info_text(end_info, event_log):
    out = []
    
    ad = end_info['action_duration']
    out.append("duration")
    out.append(f"  min-max: {ad['min']:.3f}-{ad['max']:.3f}")
    out.append(f"  mean: {ad['mean']:.3f} stdev: {ad['stdev']:.3f}")
    for discrim, dad in end_info['discrim_action_duration'].items():
        out.append(f"  {discrim} correct/pulls/count: {dad['correct_count']}/{dad['pull_count']}/{dad['count']}")
        out.append(f"    min-max: {dad['min']:.3f}-{dad['max']:.3f}")
        out.append(f"    mean: {dad['mean']:.3f} stdev: {dad['stdev']:.3f}")
    
    out.append(f"trials: {end_info['count']}")
    out.append("")
    errors = end_info['errors']
    if errors:
        error_col_width = max(len(e) for e in errors)
        for error, error_info in errors.items():
            count = error_info['count']
            perc = error_info['percent']
            out.append(f"{error.rjust(error_col_width)} {count:>2} {perc*100:.1f}%")
        out.append("")
    
    return "\n".join(out)

# with open('output/TIP_1_001_20220726_001733_Joystick_events.json') as f:
# with open('output/TIP_1_001_20220726_001733_Joystick_events.json') as f:

def gen_histogram(event_log, output_path):
    # with open(input_path, encoding='utf8', newline='\n') as f:
    #     data = json.load(f)

    # event_log = data['events']

    end_info = get_end_info(event_log)

    hist_lengths, hist_errors = InfoView.gen_histogram(event_log, h_range=(0, 10))

    info_text = get_info_text(end_info, event_log)

    # print(hist_lengths)
    # print(end_info)
    # print(info_text)

    test = {
        # 'carat': [1,2,3,3,3],
        # 'y': [1, 1, 1, 2, 3],
        
        # 'xmin': [1  ,1  ,1  ,2  ,3  ],
        # 'xmax': [1.9,1.9,1.9,2.9,3.9],
        # 'ymin': [0  ,1  ,2  ,2  ,2  ],
        # 'ymax': [0.9,1.9,2.9,2.9,2.9],
        'xmin': [],
        'xmax': [],
        'ymin': [],
        'ymax': [],
        
        # 'carat': [1],
        # 'fill': [1,1,1,255255],
        # 'fill': ['FFFFFF', 'FFFFFF', 'FFFFFF', 'FFFFFA'],
        # 'fill': ['S', 'S', 'S', 'F', 'S'],
        'fill': [],
    }

    y_breaks = []
    y_labels = []

    y_pos = 0

    for (r_start, r_end), trials in sorted(hist_lengths.items(), key=lambda x: x[0][0], reverse=True):
        label = f"{r_start:.3f}-{r_end:.3f}"
        y_labels.append(label)
        y_breaks.append(y_pos + 0.45)
        
        x_pos = 1
        for trial in trials:
            test['xmin'].append(x_pos)
            test['xmax'].append(x_pos + 0.9)
            test['ymin'].append(y_pos)
            test['ymax'].append(y_pos + 0.9)
            
            test['fill'].append('S' if trial else 'F')
            
            x_pos += 1
        
        y_pos += 1

    max_trials = max(len(ts) for ts in hist_lengths.values())

    fig = (
        # ggplot(diamonds, aes(x='carat'))
        # ggplot(pd.DataFrame(test), aes(x='carat'))
        ggplot(pd.DataFrame(test))
        # + theme_dark()
        # + theme_void()
        # + plotnine.themes.themeable.strip_margin(0)
        + plotnine.theme(dpi=96*2)
        # + plotnine.theme(strip_margin=0, axis_ticks_pad=0, panel_spacing=0, plot_margin=0)
        + plotnine.theme(plot_title=plotnine.element_text(ha='left', size=8, family='monospace'))
        # + geom_histogram()
        # + scale_fill_manual(values=["#000000", "#E69F00", "#56B4E9", "#009E73", "#F0E442"])
        # + scale_fill_manual(breaks=['FFFFFF', 'FFFFFA'], values=["#000000", "#E69F00"])
        # + scale_fill_manual(breaks=['FFFFFA','FFFFFF'], values=["#000000", "#E69F00"])
        + scale_fill_manual(breaks=['S','F'], values=["#55DD55", "#DD5555"], guide=False)
        
        # + scale_x_discrete(breaks=[0,1,2], limits=[0,1,2], labels=['a', 'b', 'c', 'd'])
        # + scale_y_discrete(breaks=[0.45, 1.45, 2.45], limits=[0,1,2,3], labels=['a', 'b', 'c'])
        # + scale_y_discrete(limits=[0,1,2,3], labels=['a', 'b', 'c', 'd'])
        # + scale_y_continuous(limits=[0,1,2,3,4], labels=['a', 'b', 'c', 'd', 'e'])
        + scale_y_continuous(
            breaks=y_breaks, labels=y_labels, limits=[0, max(y_pos, 20)],
            minor_breaks=[],
        )
        + scale_x_continuous(limits=[1, max(max_trials, 50)])
        
        + plotnine.ggtitle(info_text)
        
        # + coord_flip()
        # + geom_bar(aes(x='carat', fill='fill'))
        # + geom_bar(aes(x='carat', color='fill'))
        # + geom_point(aes(x='carat', y='y', color='fill'))
        + geom_rect(aes(xmin='xmin', xmax='xmax', ymin='ymin', ymax='ymax', fill='fill'))
    )

    fig.save(filename = output_path, verbose=False)
    # print(output_path)

def gen_from_file(input_path, output_path):
    with open(input_path, encoding='utf8', newline='\n') as f:
        data = json.load(f)

    event_log = data['events']
    
    gen_histogram(event_log, output_path)

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--overwrite', action='store_true',
        help="overwrite existing data files instead of skipping them")
    
    parser.add_argument('--skip-failed', action='store_true')
    
    parser.add_argument('input', nargs='+', type=Path,
        help='input events json files')
    
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    
    for input_path in args.input:
        output_path = input_path.parent / f"{input_path.stem}_histogram.png"
        
        if output_path.is_file() and not args.overwrite:
            continue
        
        try:
            gen_histogram(input_path, output_path)
        except:
            if not args.skip_failed:
                raise
            traceback.print_exc()
            print("exception ocurred processing file", input_path)
            with open(output_path, 'w') as _f:
                pass

if __name__ == '__main__':
    main()
