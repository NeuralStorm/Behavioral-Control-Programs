
from typing import Literal
import platform

from .pyplexdo_32 import PyPlexDO

from .. import PlexonError

class Wrapper64:
    def __init__(self):
        from .pyplexdo_64 import pyplexdo
        self._pyplexdo = pyplexdo
    
    def get_digital_output_info(self):
        return self._pyplexdo.plexdo_get_digital_output_info()
    def get_device_string(self, device_number: int):
        return self._pyplexdo.plexdo_get_device_string(device_number)
    def init_device(self, device_number: int):
        return self._pyplexdo.plexdo_init_device(device_number)
    def clear_all_bits(self, device_number: int):
        return self._pyplexdo.plexdo_clear_all_bits(device_number)
    def set_bit(self, device_number: int, bit_number: int):
        return self._pyplexdo.plexdo_set_bit(device_number, bit_number)
    def clear_bit(self, device_number: int, bit_number: int):
        return self._pyplexdo.plexdo_clear_bit(device_number, bit_number)

class PlexDo:
    def __init__(self):
        self._obj_32: PyPlexDO | Wrapper64
        is_32 = platform.architecture()[0] == '32bit'
        if is_32:
            self._obj_32 = PyPlexDO()
        else:
            self._obj_32 = Wrapper64()
        self.device_number: Literal[1] = 1 # seems to be the result of mystery init anyway
    
    def mystery_init(self):
        """replicates old init behavior
        https://github.com/NeuralStorm/Behavioral-Control-Programs/blob/fbc7332c3151f55f9b2c8a719c3dfe164df7a1d5/Primate_Joystick_Pull/MonkeyImages_Joystick_Conf.py#L98
        """
        compatible_devices = ['PXI-6224', 'PXI-6259']
        self_plexdo = self._obj_32
        doinfo = self_plexdo.get_digital_output_info()
        self.device_number = 1
        for k in range(doinfo.num_devices):
            if self_plexdo.get_device_string(doinfo.device_numbers[k]) in compatible_devices:
                device_number = doinfo.device_numbers[k]
        if device_number == None:
            print("No compatible devices found. Exiting.")
            # sys.exit(1)
            raise PlexonError()
        else:
            print("{} found as device {}".format(self_plexdo.get_device_string(device_number), device_number))
        res = self_plexdo.init_device(device_number)
        if res != 0:
            print("Couldn't initialize device. Exiting.")
            # sys.exit(1)
            raise PlexonError()
        self_plexdo.clear_all_bits(device_number)
    
    def bit_on(self, bit: int):
        self._obj_32.set_bit(self.device_number, bit)
    
    def bit_off(self, bit: int):
        self._obj_32.clear_bit(self.device_number, bit)
