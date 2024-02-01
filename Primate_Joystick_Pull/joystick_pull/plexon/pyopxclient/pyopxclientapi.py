# pyopxclientapi.py - High level functions for accessing data from the OPX server
#
# (c) 2018 Plexon, Inc., Dallas, Texas
# www.plexon.com
#
# This software is provided as-is, without any warranty.
# You are free to modify or share this file, provided that the above
# copyright notice is kept intact.

from collections import namedtuple
from .pyopxclientlib import PyOPXClient, OPX_ERROR_NOERROR
import time
from pathlib import Path

class PyOPXClientAPI:
    """
    The PyOPXClientAPI class contains functions that can acquire data from OmniPlex Server.  The data grabbed can
    then be analyzed and processed further by the user.

    Args:
        opxclient_dll_path - folder path containing the dll files.  The folder should contain the 32 bit dll
        file if you have a 32 bit machine or the 64 bit dll file if you have a 64 bit machine

        max_opx_data - the maximum number of data blocks that can be retrieved in one query to OmniPlex Server. Setting
        this too high may result in too much memory being consumed by the client. Only change the default value if you're 
        polling so infrequently that you're always getting the maximum number returned

    Returns:
        Initializes the class object's private global variables.  See list below on the description of the
        variables.  If the dll files are not in the folder path, an error message will be returned

    Class Vars:
        self.opx_client - object to the PyOPXClient class that wraps OPXClient.dll
        self.connected - true when connected to OmniPlex, false when not
        self._wait_handle - contains the _wait_handle for the OPX server, used by opx_wait(), considered private
        self.last_result - contains the return code of the last run function
    """
    def __init__(self, *, max_opx_data = 100000):
        bin_path = Path(__file__).parent / 'bin'
        opxclient_dll_path = str(bin_path)
        
        self.opx_client = PyOPXClient(opxclient_dll_path, max_opx_data)
        
        self.connected = False
        self._wait_handle = None
        self.last_result = 0
    
    def connect(self):
        """
        Initializes connection to the server. If the connection is successful, self.connected will be set to True

            Args:
                None
            Returns:
                None
        """
        self.last_result = self.opx_client.init_client()
        if self.last_result == OPX_ERROR_NOERROR:
            self.connected = True
    
    def disconnect(self):
        """
        Terminates connection with the server. Sets self.connected to False.
        Note - this method does not update self.last_result!

        Args:
            None

        Returns:
            None
        """
        self.opx_client.close_client()
        self.connected = False

    def get_global_parameters(self):
        """
        Gets the OmniPlex system parameters.

        Args:
            None

        Returns:
            global_parameters - A named tuple, with fields defined below
        """
        result, global_parameters = self.opx_client.get_global_parameters()
        self.last_result = result

        return global_parameters

    def opx_wait(self, timeout):
        """
        Wait for new client data. The client will block (wait) until new data is available, or the timeout has
        elapsed.

        Args:
            timeout - timeout interval in milliseconds

        Returns:
            None
        """
        if self._wait_handle == None:
            self._wait_handle = self.opx_client.get_wait_handle()

        if self._wait_handle != None:
            self.last_result = self.opx_client.wait_for_new_data(self._wait_handle, timeout)

    def clear_data(self, timeout):
        """
        Reads and discards client data, until no more data is immediately available, or until a specified interval
        elapses. This is useful when a client needs to avoid processing a potentially large "backlog" of data, for example, at startup 
        or if it desires to only occasionally read a "sample" of the incoming data.

        Args:
            timeout - timeout inverval in milliseconds

        Returns:
            None
        """
        self.last_result = self.opx_client.clear_data(timeout)

    def get_new_data(self, timestamps_only = False):
        """
        Get a batch of online client data.

        Args:
            timestamps_only - If False, returns spike and event information along with spike waveforms and continuous data
                              If True, returns spike and event information only
        
        Returns:
            new_data - Named tuple loaded with data:

                If timestamps_only == False:
                    new_data - named tuple loaded with data:
                    .num_data_blocks - number of data blocks returned; is number of elements in all other returned data
                    .source_num_or_type - source number or type of data block
                    .timestamp - spike, continuous, and event timestamps in seconds
                    .channel - channel numbers for each block
                    .unit - units (0 = unsorted, 1 = Unit A, 2 = Unit B, etc) for spike timestamps, or a strobed event word value for a strobed event timestamp
                    .number_of_blocks_per_waveform - how many blocks an individual spike waveform is spread across (for long waveforms)
                    .block_number_for_waveform - block number of multiple-block spike waveform
                    .waveform - spike or continuous waveform data

                If timestamps_only == True:
                    new_data - named tuple loaded with data:
                    .num_timestamps - the number of timestamps returned
                    .timestamp - spike and event timestamps
                    .source_num_or_type - source numers or source types (SPIKE_TYPE or EVENT_TYPE) for each timestamp
                    .channel - channel numbers for each timestamp
                    .unit - units (0 = unsorted, 1 = Unit A, 2 = Unit B, etc) for spike timestamps, or a strobed event word value for a strobed event timestamp

        Note: the PyOPXClientAPI.set_data_format() function determines whether source types or source numbers appear in source_num_or_type; by default, source numbers are returned    
        """
        if timestamps_only:
            result, new_data = self.opx_client.get_new_timestamps()
        else:
            result, new_data = self.opx_client.get_new_data()
            
        self.last_result = result
        return new_data

    def get_source_info(self, source_name_or_number):
        """
        Given a source number or name, return basic info about that source
        
        Args:
            source_name_or_number - name or number of source
        
        Returns:
            _source_name_or_number - name of source if called by number, number of source if called by name
            source_type - one of the values SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE
            num_chans - number of channels in the source
            linear_start_chan - starting channel number for the source, within the linear array of channels of the specified type
        """

        if type(source_name_or_number) is str:
            self.last_result, _source_name_or_number, source_type, num_chans, linear_start_chan = self.opx_client.get_source_info_by_name(source_name_or_number)
        
        if type(source_name_or_number) is int:
            self.last_result, _source_name_or_number, source_type, num_chans, linear_start_chan = self.opx_client.get_source_info_by_number(source_name_or_number)

        return _source_name_or_number, source_type, num_chans, linear_start_chan

    def get_spike_source_info(self, source_name_or_number):
        """
        Given a spike source number or name, return specific info about the spike source

        Args:
            source_name_or_number - name or number of spike source

        Returns:
            _source_name_or_number - name of source if called by number, number of source if called by name
            rate - digitization rate of spike source
            voltage_scaler - value which converts integer spike waveform values to volts
            trodality - 1 = single electrode, 2 = stereotrode, 4 = tetrode
            pts_per_waveform - number of points in each spike waveform
            pre_thresh_pts - number of waveform points before the threshold crossing
        """

        if type(source_name_or_number) is str:
            print("SENDING IN {} WHICH IS TYPE {} TO get_spike_source_info_by_name".format(source_name_or_number, type(source_name_or_number)))
            self.last_result, _source_name_or_number, rate, voltage_scaler, trodality, pts_per_waveform, pre_thresh_pts = self.opx_client.get_spike_source_info_by_name(source_name_or_number)
        
        if type(source_name_or_number) is int:
            self.last_result, _source_name_or_number, rate, voltage_scaler, trodality, pts_per_waveform, pre_thresh_pts  = self.opx_client.get_spike_source_info_by_number(source_name_or_number)

        return _source_name_or_number, rate, voltage_scaler, trodality, pts_per_waveform, pre_thresh_pts

    def get_cont_source_info(self, source_name_or_number):
        """
        Given a continuous source, returns specific info about the continuous source

        Args:
            source_name_or_number - name or number of continuous source

        Returns:
            _source_name_or_number - name of source if called by number, number of source if called by name
            rate - digitization rate of continuous source
            voltage_scaler - value which converts integer continuous sample values to volts
        """

        if type(source_name_or_number) is str:
            self.last_result, _source_name_or_number, rate, voltage_scaler = self.opx_client.get_cont_source_info_by_name(source_name_or_number)

        if type(source_name_or_number) is int:
            self.last_result, _source_name_or_number, rate, voltage_scaler = self.opx_client.get_cont_source_info_by_number(source_name_or_number)

        return _source_name_or_number, rate, voltage_scaler

    def exclude_source(self, source_name_or_number):
        """
        Excludes the given source from the data sent to this client.

        Args:
            source_name_or_number - name or number of continuous source

        Returns:
            None
        """

        if type(source_name_or_number) is str:
            self.last_result = self.opx_client.exclude_source_by_name(source_name_or_number)

        if type(source_name_or_number) is int:
            self.last_result = self.opx_client.exclude_source_by_number(source_name_or_number)

    def include_source(self, source_name_or_number):
        """
        Includes the given source with the data sent to this client.
        By default all sources are included. Only call this to re-include something specifically excluded.

        Args:
            source_name_or_number - name or number of continuous source

        Returns:
            None
        """

        if type(source_name_or_number) is str:
            self.last_result = self.opx_client.include_source_by_name(source_name_or_number)

        if type(source_name_or_number) is int:
            self.last_result = self.opx_client.include_source_by_number(source_name_or_number)
