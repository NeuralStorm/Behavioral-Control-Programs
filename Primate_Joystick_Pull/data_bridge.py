
from pathlib import Path
import socket
import json

from plexon import PlexonEvent

class ConnectionError(Exception):
    pass

CHAN_MAPPING = {
    0: 14, # enter homezone
    1: 11, # enter joystick zone
    # 2: 12, # exit zone
    12: None, # ensure zone exit channel is never sent
}

class DataBridge:
    def __init__(self):
        path = Path.home() / 'test/test_socket'
        if not path.exists():
            path = Path.home() / 'tasks/test/test_socket'
        
        self._digital_prev = None
        
        soc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        soc.setblocking(False)
        # soc.settimeout(0.0005)
        soc.connect(str(path))
        self._soc = soc
        
        self._buf = None
    
    def wait_for_start(self):
        return {'ts': 0}
    
    def water_on(self):
        # assert False
        pass
    
    def water_off(self):
        # assert False
        pass
    
    def get_data(self):
        while True:
            try:
                x = self._soc.recv(4096)
            except BlockingIOError:
                # time.sleep(1/4000)
                # continue
                break
            
            if not x:
                raise ConnectionError()
            
            if self._buf:
                x = self._buf + x
            
            parts = x.split(b'\n')
            self._buf = parts[-1]
            parts = parts[:-1]
            
            for part in parts:
                msg = json.loads(part)
                
                message_type = msg.get('t')
                
                if message_type == 'bridge':
                    for i, val in enumerate(msg['a']):
                        yield PlexonEvent(
                            msg['ts'], PlexonEvent.ANALOG,
                            value=val / (65000/5), # roughly 0-5 range
                            chan=i,
                        )
                    
                    if self._digital_prev is None:
                        self._digital_prev = msg['d']
                    else:
                        for i, (prev, new) in enumerate(zip(self._digital_prev, msg['d'])):
                            if not prev and new: # rising edge
                                chan = CHAN_MAPPING.get(i, i)
                                if chan is None:
                                    continue
                                yield PlexonEvent(msg['ts'], PlexonEvent.EVENT, chan=chan)
                            if not new and prev: # falling edge
                                chan = CHAN_MAPPING.get(i, i)
                                if chan is None:
                                    continue
                                chan *= -1
                                yield PlexonEvent(msg['ts'], PlexonEvent.EVENT, chan=chan)
                        self._digital_prev = msg['d']
                elif message_type == 'spike':
                    yield PlexonEvent(msg['ts'], PlexonEvent.SPIKE, chan=msg['ch'], unit=0)
