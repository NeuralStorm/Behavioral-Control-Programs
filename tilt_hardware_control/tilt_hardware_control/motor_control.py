
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
        
        """
        tilt type is signaled using the first 3 bits of the array for each tilt type
        the first 3 bits are connected to inputs 3, 4, 5 on the motor controller
        e.g. the array [1,1,0,1,0,0,0,0] would have inputs 3 and 4 high and input 5 low
        
        the fourth bit is connected to input 6 (speculative)
        
        a tilt is started by setting bits 3,4,5 to one of a set of specific sequences defined
        in the SI programmer script
        
        a tilt is stopped by bringing input 6 low (speculative)
        """
        
        # variable name / number / sham number / label in SI5 file
        self.tilt_types = {
            'stop': [0,0,0,0,0,0,0,0],
            # tilt1 / 1 / 9 / tilt6
            # Slow Counter Clockwise
            'a': [0,0,0,1,0,0,0,0],
            # tilt3 / 2 / 11 / tilt4
            # Fast Counter Clockwise
            'b': [0,1,0,1,0,0,0,0],
            # tilt4 / 3 / 12 / tilt3
            # Slow Clockwise
            'c': [0,0,1,1,0,0,0,0],
            # tilt6 / 4 / 14 / tilt1
            # Fast Clockwise
            'd': [0,1,1,1,0,0,0,0],
            'reward': [1,0,0,0,0,0,0,0],
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
