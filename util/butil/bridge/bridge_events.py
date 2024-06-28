
import os
from pathlib import Path
import socket
import json

class BridgeEventOutput:
    def __init__(self):
        p_key = 'data_bridge_input_path'
        if p_key in os.environ:
            path = Path(os.environ[p_key])
            # assert path.exists()
        else:
            path = Path.home() / 'test/input_socket'
            if not path.exists():
                path = Path.home() / 'tasks/test/input_socket'
            if not path.exists():
                path = Path.home() / 'tasks/test/bridge_server_rs/input_socket'
        self._path: Path = path
        
        inp_soc = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        inp_soc.settimeout(1)
        inp_soc.connect(str(self._path))
        self._inp_soc: socket.socket = inp_soc
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        self._inp_soc.close()
    
    def send_event(self, event: str, meta=None):
        assert '\n' not in event
        assert ' ' not in event
        if meta is not None:
            out = f"e{event} {json.dumps(meta)}\n"
        else:
            out = f"e{event} {{}}\n"
        self._inp_soc.sendall(out.encode())
