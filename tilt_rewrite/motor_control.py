
class MotorControl:
    def __init__(self, *, port: int = 0, mock: bool = False):
        self.mock: bool = mock
        
        if mock:
            self.task = None
        else:
            import nidaqmx
            task = nidaqmx.Task()
            task.do_channels.add_do_chan(f"/Dev4/port{port}/line0:7")
            
            task.start()
            
            self.task = task
        
        # variable name / number / sham number
        self.tilt_types = {
            'stop': [0,0,0,0,0,0,0,0],
            # tilt1 / 1 / 9
            'a': [1,0,0,1,0,0,0,0],
            # tilt3 / 2 / 11
            'b': [1,1,0,1,0,0,0,0],
            # tilt4 / 3 / 12
            'c': [0,0,1,1,0,0,0,0],
            # tilt6 / 4 / 14
            'd': [0,1,1,1,0,0,0,0],
            'reward': [0,0,1,1,0,0,0,0],
            'punish': [0,0,1,0,0,0,0,0],
            'wateron': [0,0,0,0,1,0,0,0],
        }
        
        self.tilt('stop')
    
    def close(self):
        self.tilt('stop')
        if not self.mock:
            self.task.stop()
    
    def _print_mock_debug(self, data):
        for k, v in self.tilt_types.items():
            if v == data:
                print(f"mock tilt {k}")
                return
        
        print(f"mock tilt {data}")
    
    def send_raw_tilt(self, data):
        assert len(data) == 8
        for x in data:
            assert x in [0, 1]
        
        if not self.mock:
            self.task.write(data)
        else:
            self._print_mock_debug(data)
    
    def tilt(self, tilt_type: str):
        data = self.tilt_types[tilt_type]
        
        self.send_raw_tilt(data)
