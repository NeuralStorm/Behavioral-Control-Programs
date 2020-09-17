# pyplexclientts.py - Contains classes that wrap functions
# in PlexClient.dll for initializing clients and acquiring timestamp data
# from spike and event channels.
#
# History
# 3-15-2018 Created by CLH
# 7-16-2019 Updated by JAM
#
# (c) 2019 Plexon, Inc., Dallas, Texas
# www.plexon.com - support@plexon.com

from ctypes import Structure, WinDLL, byref
from ctypes import c_byte, c_short, c_ulong, c_ubyte, c_int
import os
from collections import namedtuple

PL_SingleWFType = 1
PL_StereotrodeWFType = 2
PL_TetrodeWFType = 3
PL_ExtEventType = 4
PL_ADDataType = 5

class PLEvent(Structure):
    """
    PLEvent wraps the PL_Event struct in plexon.h
    """
    _fields_ = [("Type", c_byte),
                ("NumberOfBlocksInRecord", c_byte),
                ("BlockNumberInRecord", c_byte),
                ("UpperTS", c_ubyte),
                ("TimeStamp", c_ulong),
                ("Channel", c_short),
                ("Unit", c_short),
                ("DataType", c_byte),
                ("NumberOfBlocksPerWaveform", c_byte),
                ("BlockNumberForWaveform", c_byte),
                ("NumberOfDataWords", c_byte)]

class PyPlexClientTSLib:
    def __init__(self, plexclient_dll_path = 'bin'):
        """
        PyPlexClientTSLib class wraps only the functions in plexclient.dll
        that connect to OmniPlex Server and collect spike and event timestamps.

        No spike waveform data, or continuous data is collected.

        The PyPlexClientTSAPI class uses PyPlexClientTSLib. It's not a good idea to use this
        class directly unless you're familiar with how the Plexon C client API works.

        Args:
            plexclient_dll_path - path where PlexClient.dll is location. The default value
                assumes the bin folder (with the .dll inside) is in your current working
                directory. Any file path passed is converted to an absolute path and checked
                to see if the .dll exists there.

        Returns:
            None
        """
        self.plexclient_dll_path = os.path.abspath(plexclient_dll_path)
        self.plexclient_dll_file = os.path.join(self.plexclient_dll_path, 'PlexClient.dll')

        try:
            self.plexclient_dll = WinDLL(self.plexclient_dll_file)
        except (WindowsError):
            print (f"Error: Can't load PlexClient.dll at: {self.plexclient_dll_path}")
            import platform
            if platform.architecture()[0] != '32bit':
                print ("Error: This API must be run with 32-bit Python.")


    def init_client(self):
        """
        Initializes connection to OmniPlex Server

        Args:
            None

        Returns:
            1 - connection to server successful
            0 - connection to server unsuccessful
        """
        self.result = c_int(0)
        self.result = self.plexclient_dll.PL_InitClient(c_int(1), None)
        return self.result

    def close_client(self):
        """
        Terminates connection to PlexClient Server

        Args:
            None

        Returns:
            None
        """
        self.plexclient_dll.PL_CloseClient()

    def get_timestamp_structures(self, max_opx_server_events, plevent_array):
        """
        Get recent timestamp structures

        Args:
            max_opx_server_events - c_int() class containing maximum number of timestamp structures to transfer
            plevent_array - array of PLEvent classes

        Returns:
            Modifies max_opx_server_events and events.

            max_opx_server_events - actual number of timestamp structures transferred
            plevent_array - copies the timestamp structures that was retrieved from the server
        """
        self.plexclient_dll.PL_GetTimeStampStructures(byref(max_opx_server_events), byref(plevent_array))

class PyPlexClientTSAPI:
    def __init__(self, plexclient_dll_path = 'bin', max_opx_server_events = 100000):
        """
        PyPlexClientTSAPI is a user-friendly API for collecting spike and event timestamps from OmniPlex Server.

        Args:
            plexclient_dll_path - path where PlexClient.dll is location. The default value
                assumes the bin folder (with the .dll inside) is in your current working
                directory. Any file path passed is converted to an absolute path and checked
                to see if the .dll exists there.
            max_opx_server_events - determines size of the PLEvent array.

        Returns:
            Initializes certain values that can be accessed by the class object
        """
        self.plexclient_dll_path = plexclient_dll_path
        self.max_opx_server_events = c_int(max_opx_server_events)
        self.initialized = False
        self.num_retreived_opx_server_events = None

        # DEBUG
        self.num_spike_blocks = 0
        self.num_event_blocks = 0
        self.num_continuous_blocks = 0

        # Create instance of PyPlexClientTSLib class
        self.plexclient = PyPlexClientTSLib(plexclient_dll_path = self.plexclient_dll_path)
        # Create array of PLEvent class
        self.plevent_array = (PLEvent * self.max_opx_server_events.value)()

    def init_client(self):
        result = self.plexclient.init_client()
        if result:
            self.initialized = True

    def close_client(self):
        self.plexclient.close_client()
        self.initialized = False

    def get_ts(self):
        """
        """
        # The number of retreived Server events (spike and event timestamps) is first set to the
        # maximum number of Server events we'll attempt to acquire. This value gets updated with the
        # actual number of Server events acquired.
        self.num_retreived_opx_server_events = c_int(self.max_opx_server_events.value)
        # Call the library function
        self.plexclient.get_timestamp_structures(self.num_retreived_opx_server_events, self.plevent_array)

        # The retreived Server events are now in plevent_array. This next code segment unpacks it into an
        # easier to use data structure
        spike_event_tuple = namedtuple('TimeStamps', ['Type', 'Channel', 'Unit', 'TimeStamp'])
        result = []

        # DEBUG
        self.num_spike_blocks = 0
        self.num_event_blocks = 0
        self.num_continuous_blocks = 0

        # Inspect every returned plevent_array element
        for i in range(self.num_retreived_opx_server_events.value):
            # If the element at this index is a spike timestamp
            if self.plevent_array[i].Type == PL_SingleWFType:
                # Convert the timestamp from tics to seconds
                converted_timestamp = self.timestamp_tics_to_seconds(self.plevent_array[i].UpperTS, self.plevent_array[i].TimeStamp)

                # Arrange spike's data into a named tuple
                tmp_spike = spike_event_tuple(Type=self.plevent_array[i].Type, Channel=self.plevent_array[i].Channel,
                            Unit=self.plevent_array[i].Unit, TimeStamp=converted_timestamp)

                # Append this spike 
                result.append(tmp_spike)
                self.num_spike_blocks += 1
            
            # If the element at this index is an event timestamp
            elif self.plevent_array[i].Type == PL_ExtEventType:
                converted_timestamp = self.timestamp_tics_to_seconds(self.plevent_array[i].UpperTS, self.plevent_array[i].TimeStamp)

                tmp_event = spike_event_tuple(Type=self.plevent_array[i].Type, Channel=self.plevent_array[i].Channel,
                            Unit=self.plevent_array[i].Unit, TimeStamp=converted_timestamp)

                result.append(tmp_event)
                self.num_event_blocks += 1

            elif self.plevent_array[i].Type == PL_ADDataType:
                self.num_continuous_blocks += 1
                
        return result

    def timestamp_tics_to_seconds(self, UpperTS, LowerTS, sampling_frequency=40000):
        """
            Combines the upper 8 bits and lower 32 bits of the 40 bit timestamp tic value by shifting the upper 8 bits
            to the left 32 times then combining it with the lower 32 bits. It then converts it to seconds using the
            given sampling frequency.  By default the sampling frequency is set to 40000 Hz

            Args:
                UpperTs - upper bits of the timestamp tic
                LowerTS - lower bits of the timestamp tic
                sampling_frequency - sampling frequency the timestamp was retrieved

            Returns:
                timestamp - the timestamp value in seconds
        """
        timestamp = UpperTS << 32
        timestamp = timestamp + LowerTS
        timestamp = float(timestamp / float(sampling_frequency))
        return timestamp