
import sys
from pathlib import Path

from pyplexdo import PyPlexDO

def init_plex_do() -> PyPlexDO:
    
    ## Setup for Plexon DO
    compatible_devices = ['PXI-6224', 'PXI-6259']
    path = Path(__file__).parent / 'pyplexdo/bin'
    plex_do = PyPlexDO(plexdo_dll_path=str(path))
    doinfo = plex_do.get_digital_output_info()
    device_number = None
    device_strings = []
    for k in range(doinfo.num_devices):
        dev_string = plex_do.get_device_string(doinfo.device_numbers[k])
        device_strings.append(dev_string)
        if dev_string in compatible_devices:
            device_number = doinfo.device_numbers[k]
    if device_number == None:
        print("No compatible devices found. Exiting.")
        print("Found devices", device_strings)
        sys.exit(1)
    else:
        print("{} found as device {}".format(plex_do.get_device_string(device_number), device_number))
    res = plex_do.init_device(device_number)
    if res != 0:
        print("Couldn't initialize device. Exiting.")
        sys.exit(1)
    plex_do.clear_all_bits(device_number)
    
    return plex_do
