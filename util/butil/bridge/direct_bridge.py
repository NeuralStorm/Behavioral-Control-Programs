

from pathlib import Path
import socket
import json
import os
import time

from ..event_source import Event, EventSource
from .data_bridge import ConnectionError, CHAN_MAPPING

def _to_bits(x, width):
    for _ in range(width):
        yield x & 1
        x >>= 1

class _EdgeDetector:
    def __init__(self):
        self._prev = None
    
    def proc(self, data):
        if self._prev is None:
            self._prev = data
            return
        for i, (prev, new) in enumerate(zip(self._prev, data)):
            if not prev and new: # rising edge
                yield i, True
            if not new and prev: # falling edge
                yield i, False
        self._prev = data

class DirectBridge(EventSource):
    def __init__(self):
        p_key = 'data_bridge_path'
        if p_key in os.environ:
            path = Path(os.environ[p_key])
            # assert path.exists()
        else:
            path = Path.home() / 'test/test_socket'
            if not path.exists():
                path = Path.home() / 'tasks/test/test_socket'
            if not path.exists():
                path = Path.home() / 'tasks/test/bridge_server_rs/test_socket'
        self._path = path
        
        # simulate analog joystick values based on digital events on channel 28-31 (PB12-PB15)
        self._analog_js_emu = True
        
        # self._digital_prev = None
        self._edge_dig = _EdgeDetector()
        self._edge_out = _EdgeDetector()
        
        self._soc = None
        
        self._buf = None
        
        self.robust = True
        self.custom_config: bytes | None = None
        
        # time.perf_counter value to reconnect at
        self._reconnect_after = 0
        self._count = 0
    
    def wait_for_start(self):
        return {'ts': 0}
    
    def connect(self):
        soc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        
        soc.setblocking(False)
        # soc.settimeout(0.0005)
        try:
            soc.connect(str(self._path))
        except (ConnectionRefusedError, FileNotFoundError) as e:
            print(f'data bridge error {e}')
            self._soc = None
            self._reconnect_after = time.perf_counter() + 1
            return
        
        try:
            if self.custom_config is not None:
                soc.sendall(self.custom_config)
            elif self.robust:
                # soc.sendall(b'''{"allow_drop": false, "buffer_size": 2000, "prefix_filter": ["h"]}\n''')
                soc.sendall(b'''{"allow_drop": false, "downsample_factor": 20, "buffer_size": 2000, "prefix_filter": ["h"]}\n''')
            else:
                soc.sendall(b'''{"allow_drop": true, "buffer_size": 10, "prefix_filter": ["h"]}\n''')
        except OSError as e:
            print(f'data bridge error {e}')
            if self.robust:
                raise
            self._soc = None
            self._reconnect_after = time.perf_counter() + 1
            return
        # print('connected')
        
        self._soc = soc
    
    def get_raw(self):
        if self._soc is None:
            x = b''
        else:
            try:
                x = self._soc.recv(4096)
                # x = self._soc.recv(128)
            except BlockingIOError:
                time.sleep(1/8000)
                return
            except OSError as e:
                print(f'data bridge error {e}')
                x = b''
        
        if not x:
            if self._soc is not None:
                try:
                    self._soc.close()
                except:
                    pass
                if self.robust:
                    raise ConnectionError()
            if time.perf_counter() > self._reconnect_after:
                self.connect()
            if self._soc is None and self.robust:
                raise ConnectionError()
            return
        
        if self._buf:
            x = self._buf + x
        
        parts = x.split(b'\n')
        
        self._buf = parts[-1]
        parts = parts[:-1]
        
        for part in parts:
            # print(part)
            part = part.removeprefix(b'h')
            # if part[0] != b'{'[0]:
            #     continue
            # msg = json.loads(part)
            # yield msg
            # yield part
            _count, digital, output, analog = part.split(b':')
            # parts = part.split(b':')
            digital = list(_to_bits(int(digital), 32))
            output = list(_to_bits(int(output), 32))
            analog = [int(x) for x in analog.split(b',')]
            yield self._count, digital, output, analog
            self._count += 1
    
    def get_data(self):
        # count = 0
        for count, digital, output, analog in self.get_raw():
            
            # ts = count / 4000
            ts = count / 200 # downsample of 20
            
            # message_type = msg.get('t')
            
            # if message_type == 'bridge':
                # msg['ts'] /= 4000
            for i, val_str in enumerate(analog):
                val = int(val_str)
                yield Event(
                    ts, Event.ANALOG,
                    value=val / (65000/5), # roughly 0-5 range
                    chan=i,
                )
            
            for i, is_high in enumerate(digital):
                # if self._analog_js_emu and 28 <= i <= 31:
                if self._analog_js_emu and i >= 2: # all but the two actual analog channels
                    # out_chan = i-28+3
                    # assert 3 <= out_chan <= 6
                    out_chan = i
                    if is_high:
                        yield Event(ts, Event.ANALOG, value=5, chan=out_chan)
                    else:
                        yield Event(ts, Event.ANALOG, value=0, chan=out_chan)
            
            for i, is_rising in self._edge_dig.proc(digital):
                chan = CHAN_MAPPING.get(i, i)
                if chan is None:
                    continue
                yield Event(ts, Event.EVENT, chan=chan, falling=not is_rising)
            for i, is_rising in self._edge_out.proc(output):
                # offset output channels by 1000
                i += 1000
                chan = CHAN_MAPPING.get(i, i)
                if chan is None:
                    continue
                yield Event(ts, Event.EVENT, chan=chan, falling=not is_rising)
            
            # event_data = digital+output
            # if self._digital_prev is not None:
            #     for i, (prev, new) in enumerate(zip(self._digital_prev, event_data)):
            #         if not prev and new: # rising edge
            #             chan = CHAN_MAPPING.get(i, i)
            #             if chan is None:
            #                 continue
            #             yield PlexonEvent(ts, PlexonEvent.EVENT, chan=chan)
            #         if not new and prev: # falling edge
            #             chan = CHAN_MAPPING.get(i, i)
            #             if chan is None:
            #                 continue
            #             yield PlexonEvent(ts, PlexonEvent.EVENT, chan=chan, falling=True)
            # self._digital_prev = digital
            # elif message_type == 'spike':
            #     yield PlexonEvent(msg['ts'], PlexonEvent.SPIKE, chan=msg['ch'], unit=0)
            # count += 1

