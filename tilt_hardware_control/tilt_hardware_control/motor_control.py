
import time

class MotorControl:
    def __init__(self, *, port: int = 1, mock: bool = False):
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
        
        the fourth bit is connected to input 6
        
        the inputs are marked as X3, X4, X5 and X6 in the manual and
        pinout and as simply 3, 4, 5 and 6 in the SI programmer software
        
        a tilt is started by setting bits 3,4,5 to one of a set of specific sequences defined
        in the SI programmer script
        
        a tilt is stopped by bringing input 6 low (speculative)
        
        the start of tilt is signaled by output 2 (Y2) being brought high for 2ms
        """
        
        # variable name / number / strobe number / label in SI5 file
        self.tilt_types = {
            # tilt1 / 1 / 9 / tilt6
            # Slow Counter Clockwise
            'slow_left': [0,0,0,1],
            # tilt3 / 2 / 11 / tilt4
            # Fast Counter Clockwise
            'fast_left': [0,1,0,1],
            # tilt4 / 3 / 12 / tilt3
            # Slow Clockwise
            'slow_right': [0,0,1,1],
            # tilt6 / 4 / 14 / tilt1
            # Fast Clockwise
            'fast_right': [0,1,1,1],
        }
        self._state = [0,0,0,0,0,0,0,0]
        
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
    
    def _update_output(self, data=None):
        if data is None:
            data = self._state
        
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
        if tilt_type == 'stop':
            self.stop()
            return
        self._state[0:4] = self.tilt_types[tilt_type][0:4]
        
        self._update_output()
    
    def tilt_return(self):
        """stop the current tilt and return to neutral"""
        self._state[0:2] = [1, 0]
        self._update_output()
    
    def tilt_punish(self):
        self._state[0:2] = [1, 1]
        self._update_output()
    
    def stop(self):
        for i in range(len(self._state)):
            self._state[i] = 0
        self._update_output()
    
    def water_on(self):
        self._state[4] = 1
        self._update_output()
    
    def water_off(self):
        self._state[4] = 0
        self._update_output()
    
    def water(self, duration: float):
        self.water_on()
        time.sleep(duration)
        self.water_off()
