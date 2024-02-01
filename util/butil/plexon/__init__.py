
import logging
from pathlib import Path
import os
from multiprocessing import Process, Queue as PQueue
from queue import Empty
import platform

from .common import PlexonError

from .plexdo import PlexDo
from .. import DigitalOutput

logger = logging.getLogger(__name__)

try:
    from .pyopxclient import PyOPXClientAPI, OPX_ERROR_NOERROR, SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, OTHER_TYPE
except ImportError:
    plexon_import_failed = True
else:
    plexon_import_failed = False

# This will be filled in later. Better to store these once rather than have to call the functions
# to get this information on every returned data block
source_numbers_types = {}
source_numbers_names = {}
source_numbers_rates = {}
source_numbers_voltage_scalers = {}

class PlexonEvent:
    ANALOG = 'analog'
    SPIKE = 'spike'
    EVENT = 'event'
    OTHER_EVENT = 'other_event'
    
    def __init__(self, ts, event_type, *,
        value: float = 0,
        chan: int = 0,
        unit: int = 0,
        falling: bool = False,
    ):
        self.ts: float = ts
        self.type: str = event_type
        self.value: float = value
        self.chan: int = chan
        self.unit: int = unit
        self.falling: bool = falling
    
    @property
    def rising(self) -> bool:
        return not self.falling

class Plexon:
    def __init__(self):
        assert not plexon_import_failed
        
        self.client = PyOPXClientAPI()
        
        # Connect to OmniPlex Server, check for success
        self.client.connect()
        if not self.client.connected:
            # print("Client isn't connected, exiting.\n")
            # print("Error code: {}\n".format(self.client.last_result))
            raise PlexonError("Client isn't connected, Error code: {}".format(self.client.last_result))
            # self.plexon = False
        
        # print("Connected to OmniPlex Server\n")
        # Get global parameters
        global_parameters = self.client.get_global_parameters()
        
        ##### Need to include information here about getting Digital signals ############
        for source_id in global_parameters.source_ids:
            source_name, _, _, _ = self.client.get_source_info(source_id)
            logger.info('source %s %s', source_name, source_id)
            if source_name == 'KBD':
                self.keyboard_event_source = source_id
            if source_name == 'AI':
                self.ai_source = source_id
            if source_name == 'Single-bit events':
                self.event_source = source_id
            if source_name == 'Other events':
                self.other_event_source = source_id
                # print ("Other event source is {}".format(self.other_event_source))
            
            ##### Need to include information here about getting Digital signals ############
            for index in range(global_parameters.num_sources):
                # Get general information on the source
                source_name, source_type, num_chans, linear_start_chan = self.client.get_source_info(global_parameters.source_ids[index])
                # Store information about the source types and names for later use.
                source_numbers_types[global_parameters.source_ids[index]] = source_type
                source_numbers_names[global_parameters.source_ids[index]] = source_name
                if source_name == 'AI':
                    logger.info("----- Source {} -----".format(global_parameters.source_ids[index]))
                    source_types = { SPIKE_TYPE: "Spike", EVENT_TYPE: "Event", CONTINUOUS_TYPE: "Continuous", OTHER_TYPE: "Other" }
                    logger.info("Name: {}, Type: {}, Channels: {}, Linear Start Channel: {}".format(source_name,
                                                                                    source_types[source_type],
                                                                                    num_chans,
                                                                                    linear_start_chan))
                if source_type == CONTINUOUS_TYPE and source_name == 'AI':
                    # Get information specific to a continuous source
                    _, rate, voltage_scaler = self.client.get_cont_source_info(source_name)
                    # Store information about the source rate and voltage scaler for later use.
                    source_numbers_rates[global_parameters.source_ids[index]] = rate
                    source_numbers_voltage_scalers[global_parameters.source_ids[index]] = voltage_scaler
                    logger.info("Digitization Rate: {}, Voltage Scaler: {}".format(rate, voltage_scaler))
    
    def wait_for_start(self):
        while True:
            new_data = self.client.get_new_data()
            for i in range(new_data.num_data_blocks):
                if new_data.source_num_or_type[i] == self.other_event_source and new_data.channel[i] == 2: # Start event timestamp is channel 2 in 'Other Events' source
                    return {
                        'ts': new_data.timestamp[i],
                    }
    
    def get_data(self):
        # self.client.opx_wait(5)
        new_data = self.client.get_new_data()
        
        for i in range(new_data.num_data_blocks):
            num_or_type = new_data.source_num_or_type[i]
            block_type = source_numbers_types[new_data.source_num_or_type[i]]
            source_name = source_numbers_names[new_data.source_num_or_type[i]]
            chan = new_data.channel[i]
            ts = new_data.timestamp[i]
            
            if block_type == CONTINUOUS_TYPE and source_name == 'AI':
                voltage_scaler = source_numbers_voltage_scalers[num_or_type]
                samples = new_data.waveform[i]
                samples = (s * voltage_scaler for s in samples)
                
                for val in samples:
                    yield PlexonEvent(ts, PlexonEvent.ANALOG, value=val, chan=chan)
            elif block_type == SPIKE_TYPE:
                unit = new_data.unit[i]
                yield PlexonEvent(ts, PlexonEvent.SPIKE, chan=chan, unit=unit)
            elif num_or_type == self.event_source:
                yield PlexonEvent(ts, PlexonEvent.EVENT, chan=chan)
            elif num_or_type == self.other_event_source:
                if chan == 1:
                    continue
                yield PlexonEvent(ts, PlexonEvent.OTHER_EVENT, chan=chan)

class _PlexonProcess(Process):
    def __init__(self):
        self._queue = PQueue()
        super().__init__(daemon=True)
    
    def run(self):
        plexon = Plexon()
        
        while True:
            plexon.client.opx_wait(1)
            data = list(plexon.get_data())
            if not data:
                continue
            self._queue.put(data)
    
    def get_data(self):
        try:
            data = self._queue.get(block=False)
        except Empty:
            return []
        return data

class PlexonProxy:
    def __init__(self):
        assert not plexon_import_failed
        
        self._proc = _PlexonProcess()
        self._proc.start()
    
    def wait_for_start(self):
        while True:
            new_data = self._proc.get_data()
            for x in new_data:
                if x.type == x.OTHER_EVENT and x.chan == 2:
                    return {
                        'ts': x.ts
                    }
    
    def get_data(self):
        return self._proc.get_data()

class PlexonOutput(DigitalOutput):
    def __init__(self):
        self.reward_nidaq_bit = 17 # DO Channel
        self.plexdo = PlexDo()
    
    def water_on(self):
        if self.plexdo is not None:
            self.plexdo.bit_on(self.reward_nidaq_bit)
    
    def water_off(self):
        if self.plexdo is not None:
            self.plexdo.bit_off(self.reward_nidaq_bit)
