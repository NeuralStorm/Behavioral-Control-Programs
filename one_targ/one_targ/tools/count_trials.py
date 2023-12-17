"""calculates trial counts and other info from center out output file

each "trial_correct" is considered a correct trial
each "trial_incorrect" is considered an incorrect trial

the position of the trial is based on the most recent position event (e.g. top_left)
"""

import sys
import json
from collections import Counter
from pprint import pprint

def print_counter(counts, *, indent=2):
    for k in sorted(counts):
        v = counts[k]
        print(' '*indent, k, ': ', v, sep='')

def main():
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
    
    events = data['events']
    
    cur_pos = 'no_position'
    
    correct_counts = Counter()
    incorrect_counts = Counter()
    
    event_counts = Counter()
    
    for e in events:
        if 'type' in e:
            continue
        name = e['name']
        
        event_counts[name] += 1
        
        if name in ['top_left', 'top_left', 'bottom_right', 'bottom_left']:
            cur_pos = name
        
        if name == 'trial_incorrect':
            incorrect_counts[cur_pos] += 1
        if name == 'trial_correct':
            correct_counts[cur_pos] += 1
    
    print('event counts')
    # pprint(event_counts)
    print_counter(event_counts)
    print()
    
    print(f"correct (total: {sum(correct_counts.values(), start=0)})")
    print_counter(correct_counts)
    print()
    
    print(f"incorrect (total: {sum(incorrect_counts.values(), start=0)})")
    print_counter(incorrect_counts)
    print()

if __name__ == '__main__':
    main()
