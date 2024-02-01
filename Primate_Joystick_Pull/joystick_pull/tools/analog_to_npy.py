
import argparse
from pathlib import Path
from contextlib import ExitStack
from struct import Struct
from base64 import b85decode

from butil import EventReader

def parse_args():
    parser = argparse.ArgumentParser(description='')
    
    parser.add_argument('input', type=Path,
        help="path to input .json.gz file")
    parser.add_argument('--channel',
        help="channel name")
    parser.add_argument('--output', type=Path,
        help="path to output npy file")
    
    parser.add_argument('--rate', type=float,
        help="sample rate of analog signal")
    
    args = parser.parse_args()
    return args

def print_info(input_path: Path):
    channels = set()
    with EventReader(path=input_path) as reader:
        for rec in reader.read_records():
            if rec.get('type') == 'analog':
                channels.add(rec['channel'])
    
    print('\n'.join(channels))

def make_npy(input_path: Path, channel: str, npy_path: Path, rate_override=None):
    sample_chunks = []
    unpacker = Struct('<d')
    with EventReader(path=input_path) as reader:
        for rec in reader.read_records():
            if rec.get('type') == 'analog' and rec['channel'] == channel:
                chunk_samples = []
                for s in unpacker.iter_unpack(b85decode(rec['samples'])):
                    x, = s
                    chunk_samples.append(x)
                sample_chunks.append((rec['ts'], chunk_samples))
    
    if rate_override is None:
        rates = []
        for i in range(0, len(sample_chunks)-1):
            a_ts, a_samples = sample_chunks[i]
            b_ts, b_samples = sample_chunks[i+1]
            elapsed = b_ts - a_ts
            n = len(a_samples)
            # print(n, elapsed, a_ts)
            # print(n/elapsed)
            rates.append(n/elapsed)
        
        if len(rates) > 1:
            del rates[0]
        if len(rates) > 1:
            del rates[-1]
        
        rate = sum(rates) / len(rates)
    else:
        rate = rate_override
    print(f'rate: {rate}')
    step = 1 / rate
    
    out = []
    for chunk_ts, samples in sample_chunks:
        t = chunk_ts
        for x in samples:
            out.append([t, x])
            t += step
    
    # print(out)
    
    import numpy as np
    arr = np.array(out)
    np.save(npy_path, arr, allow_pickle=False)

def main():
    args = parse_args()
    
    if args.channel is None: # print info
        print_info(args.input)
        return
    
    assert args.channel is not None
    assert args.output is not None
    make_npy(args.input, args.channel, args.output, rate_override=args.rate)

if __name__ == '__main__':
    main()
