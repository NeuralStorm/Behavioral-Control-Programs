
class MotorControl:
    def __init__(self, *, port: int = 0, mock: bool = False):
        self.mock: bool = mock
        
        if mock:
            self.task = None
        else:
            import nidaqmx
            task = nidaqmx.Task()
            task.do_channels.add_do_chan(f"/Dev6/port{port}/line0:7")
            
            task.start()
            
            self.task = task
        
        # variable name / number / sham number
        self.tilt_types = {
            'stop': [0,0,0,0,0,0,0,0],
            # tilt1 / 1 / 9
            # Slow Counter Clockwise
            'a': [1,0,0,1,0,0,0,0],
            # tilt3 / 2 / 11
            # Fast Counter Clockwise
            'b': [1,1,0,1,0,0,0,0],
            # tilt4 / 3 / 12
            # Slow Clockwise
            'c': [0,0,1,1,0,0,0,0],
            # tilt6 / 4 / 14
            # Fast Clockwise
            'd': [0,1,1,1,0,0,0,0],
            'reward': [0,0,1,1,0,0,0,0],
            'punish': [0,0,1,0,0,0,0,0],
            'wateron': [0,0,0,0,1,0,0,0],
        }
        
        self.tilt('stop')
    
    def close(self):
        self.tilt('stop')
        if not self.mock:
            self.task.close()
    
    def _print_mock_debug(self, data):
        for k, v in self.tilt_types.items():
            if v == data:
                print(f"mock tilt {k}")
                return
        
        bin_str = "".join(reversed(f"{data[0]:0>8b}"))
        assert len(data) == 1
        print(f"mock tilt {bin_str}")
    
    def send_raw_tilt(self, data):
        assert len(data) == 8
        for x in data:
            assert x in [0, 1]
        
        num = 0
        for bit in reversed(data):
            num <<= 1
            num += bit
        data = [num]
        
        if not self.mock:
            self.task.write(data)
        else:
            self._print_mock_debug(data)
    
    def tilt(self, tilt_type: str):
        data = self.tilt_types[tilt_type]
        
        self.send_raw_tilt(data)
