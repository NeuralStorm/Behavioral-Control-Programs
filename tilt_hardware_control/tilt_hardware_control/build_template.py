
import argparse
from pathlib import Path

from psth_new import build_template_file

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('--meta', type=Path,
        help='input meta file')
    parser.add_argument('--events', type=Path,
        help='input events file')
    parser.add_argument('--template-out', type=Path,
        help='output path for generated template file')
    
    parser.add_argument('--post-time', type=int,
        help='post time for template generation (ms)')
    parser.add_argument('--bin-size', type=int,
        help='bin size for template generation (ms)')
    
    parser.add_argument('--overwrite', action='store_true',
        help='overwrite output file if it already exists')
    
    args = parser.parse_args()
    
    return args

def main():
    args = parse_args()
    
    if not args.overwrite:
        assert not args.template_out.exists()
    
    # print(args)
    
    build_template_file(
        args.meta, args.events, args.template_out,
        post_time = args.post_time,
        bin_size = args.bin_size,
    )

if __name__ == '__main__':
    main()
