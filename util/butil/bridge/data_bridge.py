
from pathlib import Path
import socket
import json
import os
import time

from ..plexon import PlexonEvent

class ConnectionError(Exception):
    pass

CHAN_MAPPING = {
    8: 14, # enter homezone
    9: 11, # enter joystick zone
    # 2: 12, # exit zone
    12: None, # ensure zone exit channel is never sent
}

class DataBridge:
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
        # shows up as analog channels 3-6
        self._analog_js_emu = True
        
        self._digital_prev = None
        
        self._soc = None
        
        self._buf = None
        
        self.robust = True
        self.custom_config: bytes | None = None
        
        # time.perf_counter value to reconnect at
        self._reconnect_after = 0
    
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
                soc.sendall(b'''{"allow_drop": false, "buffer_size": 2000, "prefix_filter": ["b"]}\n''')
            else:
                soc.sendall(b'''{"allow_drop": true, "buffer_size": 10, "prefix_filter": ["b"]}\n''')
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
            part = part.removeprefix(b'b')
            if part[0] != b'{'[0]:
                continue
            msg = json.loads(part)
            yield msg
    
    def get_data(self):
        # while True:
            for msg in self.get_raw():
                
                message_type = msg.get('t')
                
                if message_type == 'bridge':
                    # msg['ts'] /= 4000
                    for i, val in enumerate(msg['a']):
                        yield PlexonEvent(
                            msg['ts'], PlexonEvent.ANALOG,
                            value=val / (65000/5), # roughly 0-5 range
                            chan=i,
                        )
                    
                    for i, is_high in enumerate(msg['d']):
                        if self._analog_js_emu and 28 <= i <= 31:
                            # out_chan = i-28+3
                            # assert 3 <= out_chan <= 6
                            out_chan = i
                            if is_high:
                                yield PlexonEvent(msg['ts'], PlexonEvent.ANALOG, value=5, chan=out_chan)
                            else:
                                yield PlexonEvent(msg['ts'], PlexonEvent.ANALOG, value=0, chan=out_chan)
                    
                    if self._digital_prev is None:
                        self._digital_prev = msg['d']
                    else:
                        for i, (prev, new) in enumerate(zip(self._digital_prev, msg['d'])):
                            if not prev and new: # rising edge
                                # if self._analog_js_emu and 28 <= i <= 31:
                                #     yield PlexonEvent(msg['ts'], PlexonEvent.ANALOG, value=5, chan=i-28+3)
                                
                                chan = CHAN_MAPPING.get(i, i)
                                if chan is None:
                                    continue
                                yield PlexonEvent(msg['ts'], PlexonEvent.EVENT, chan=chan)
                            if not new and prev: # falling edge
                                # if self._analog_js_emu and 28 <= i <= 31:
                                #     yield PlexonEvent(msg['ts'], PlexonEvent.ANALOG, value=0, chan=i-28+3)
                                
                                chan = CHAN_MAPPING.get(i, i)
                                if chan is None:
                                    continue
                                # chan *= -1
                                yield PlexonEvent(msg['ts'], PlexonEvent.EVENT, chan=chan, falling=True)
                        self._digital_prev = msg['d']
                elif message_type == 'spike':
                    yield PlexonEvent(msg['ts'], PlexonEvent.SPIKE, chan=msg['ch'], unit=0)
