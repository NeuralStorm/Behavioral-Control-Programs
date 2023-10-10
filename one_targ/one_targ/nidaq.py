
from typing import List
import time
import threading

def build_event_types(dev: str):
    out = {
        'center_show': {
            'nidaq_pin': f'/{dev}/port0/line0',
            'plexon_channel': 17,
        },
        'center_touch': {
            'nidaq_pin': f'/{dev}/port0/line1',
            'plexon_channel': 18,
        },
        'center_hide': {
            'nidaq_pin': f'/{dev}/port0/line2',
            'plexon_channel': 19,
        },
        'periph_show': {
            'nidaq_pin': f'/{dev}/port0/line3',
            'plexon_channel': 20,
        },
        'periph_touch': {
            'nidaq_pin': f'/{dev}/port0/line4',
            'plexon_channel': 21,
        },
        'periph_hide': {
            'nidaq_pin': f'/{dev}/port0/line5',
            'plexon_channel': 22,
        },
        'top_left': {
            'nidaq_pin': f'/{dev}/port0/line6',
            'plexon_channel': 23,
        },
        'top_right': {
            'nidaq_pin': f'/{dev}/port0/line7',
            'plexon_channel': 24,
        },
        'bottom_left': {
            'nidaq_pin': f'/{dev}/port1/line0',
            'plexon_channel': 25,
        },
        'bottom_right': {
            'nidaq_pin': f'/{dev}/port1/line1',
            'plexon_channel': 26,
        },
        'trial_correct': {
            'nidaq_pin': f'/{dev}/port1/line2',
            'plexon_channel': 27,
        },
        'trial_incorrect': {
            'nidaq_pin': f'/{dev}/port1/line3',
            'plexon_channel': 28,
        },
    }
    return out

class Nidaq:
    def __init__(self, pins: List[str]):
        import nidaqmx
        from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
        from nidaqmx.constants import RegenerationMode
        self.pins = pins
        self.tasks = [nidaqmx.Task() for _ in pins]
        
        for pin, task in zip(pins, self.tasks):
            task.do_channels.add_do_chan(pin, line_grouping = LineGrouping.CHAN_PER_LINE)
    
    def start(self):
        for task in self.tasks:
            task.start()
    
    def stop(self):
        for task in self.tasks:
            task.stop()
    
    def pulse_pin(self, pin):
        idx = self.pins.index(pin)
        def pulse_end():
            self.tasks[idx].write(True)
            time.sleep(0.004) # 4ms wait
            self.tasks[idx].write(False)
        thread = threading.Thread(target=pulse_end)
        thread.start()
