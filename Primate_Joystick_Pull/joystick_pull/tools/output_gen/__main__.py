
import argparse
from pathlib import Path
from contextlib import ExitStack
import json
import traceback

from butil import EventReader
from . import gen_csv

def removeprefix(self: str, prefix: str, /) -> str:
    if self.startswith(prefix):
        return self[len(prefix):]
    else:
        return self[:]

def removesuffix(self: str, suffix: str, /) -> str:
    # suffix='' should not call self[:-0].
    if suffix and self.endswith(suffix):
        return self[:-len(suffix)]
    else:
        return self[:]


def parse_args():
    parser = argparse.ArgumentParser(prog='output_gen', description='')
    
    subparsers = parser.add_subparsers(
        title="action",
        metavar='action',
        dest='action',
        help='',
        required=True,
    )
    
    split_parser = subparsers.add_parser('gen',
        help="generate outputs from events file")
    split_parser.add_argument('--overwrite', action='store_true',
        help="regenerate existing output files")
    split_parser.add_argument('--skip-failed', action='store_true')
    split_parser.add_argument('--ignore-photodiode', action='store_true',
        help="discard photodiode events")
    split_parser.add_argument('--plots', action='store_true',
        help="enable histogram")
    split_parser.add_argument('input', nargs='+', type=Path,
        help='input events .json.bz files')
    
    args = parser.parse_args()
    return args

def gen_from_file(*,
    input_path: Path,
    ignore_photodiode: bool,
    overwrite: bool,
    plots: bool,
    ):
    # reader = EventReader(path=input_file)
    # out_events = []
    
    # stem = input_path.stem.removesuffix(".json").removesuffix('_new_events')
    stem = input_path.stem
    stem = removesuffix(stem, ".json")
    stem = removesuffix(stem, '_new_events')
    events_output_path = input_path.parent / f"{stem}_game_events.json"
    histogram_output_path = input_path.parent / f"{stem}_histogram.png"
    csv_output_path = input_path.parent / f"{stem}_trials.csv"
    
    
    if not overwrite:
        if any([
            events_output_path.exists(),
            histogram_output_path.exists(),
            csv_output_path.exists(),
        ]):
            return
        # assert not events_output_path.exists()
        # assert not histogram_output_path.exists()
        # assert not csv_output_path.exists()
    
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
    
    with open(events_output_path, 'w', encoding='utf8', newline='\n') as f:
        json.dump({'events': out_events}, f, indent=2)
    
    with open(csv_output_path, 'w', encoding='utf8', newline='\n') as f:
        gen_csv.write_csv(f, out_events)
    
    if plots:
        from . import gen_histogram
        gen_histogram.gen_histogram(out_events, histogram_output_path)

def main():
    args = parse_args()
    
    if args.action == 'gen':
        for input_path in args.input:
            try:
                gen_from_file(
                    input_path=input_path,
                    ignore_photodiode=args.ignore_photodiode,
                    overwrite=args.overwrite,
                    plots=args.plots,
                )
            except:
                if not args.skip_failed:
                    raise
                traceback.print_exc()
                print("exception ocurred processing file", input_path)
                
                # stem = input_path.stem.removesuffix(".json").removesuffix('_new_events')
                stem = input_path.stem
                stem = removesuffix(stem, ".json")
                stem = removesuffix(stem, '_new_events')
                output_path = input_path.parent / f"{stem}_trials.csv"
                with open(output_path, 'w') as _f:
                    pass

if __name__ == '__main__':
    main()
