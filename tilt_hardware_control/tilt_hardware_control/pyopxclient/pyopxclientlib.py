# pyopxclientlib.py - Low level wrapper functions for accessing data from the OmniPlex Server software.
#
# (c) 2019 Plexon, Inc., Dallas, Texas
# www.plexon.com
#
# This software is provided as-is, without any warranty.
# You are free to modify or share this file, provided that the above
# copyright notice is kept intact.

from ctypes import Structure, c_int32, c_double, c_uint8, c_uint32, c_uint16, c_int16, WinDLL, byref, c_char, c_int, c_uint, c_byte, c_ulonglong, c_ulong, c_bool, c_float
import os
import platform
from collections import namedtuple

# Temporary, TODO
TS64 = 1

# Source and channel types
SPIKE_TYPE = 1
EVENT_TYPE = 4
CONTINUOUS_TYPE = 5
OTHER_TYPE = 6

# Maximum number of sources
MAX_SOURCES = 256

# Maximum number of channels per source
MAX_CHANS_PER_SOURCE = 512

# Maximum number of AuxAI channels
MAX_AUXAI_CHANS = 64

# Channel numbers are relative to one of the four channel types
CHANNEL_FORMAT_LINEAR = 1

# Channel numbers are relative to the channel's source
CHANNEL_FORMAT_SOURCE_RELATIVE = 2

# Size of the WaveForm array (sample data array) in the OPX_DataBlock structure
MAX_WF_LENGTH = 56

# Values for the OPXSystemType parameter returned by OPX_GetGlobalPars;
# identifies the main neural data acquisition device(s); currently,
# these values are mutually exclusive.

# Indicates that no valid topology is loaded in Server
OPXSYSTEM_INVALID = 0
# OmniPlex system using a TestADC (artificial data) device
OPXSYSTEM_TESTADC = 1
# OmniPlex-A system:
OPXSYSTEM_AD64 = 2
# OmniPlex-D system, using either DigiAmp or MiniDigi
OPXSYSTEM_DIGIAMP = 4
# OmniPlex-D system, using Digital Headstage Processor (DHP)
OPXSYSTEM_DHSDIGIAMP = 8

# Values returned by OPX_GetOPXSystemStatus
OPX_DAQ_STOPPED = 1
OPX_DAQ_STARTED = 2
OPX_RECORDING = 3
OPX_RECORDING_PAUSED = 4

# Named tuple to organize information returned from PyOPXClient.get_global_parameters()
GlobalParameters = namedtuple('GlobalParameters', 'opx_system_type, opx_software_version, opx_sdk_version, num_sources, source_ids, num_spike_chans, num_cont_chans, num_event_chans, num_other_chans, timestamp_frequency, client_sample_rate_limit, bits_per_sample, minimize_client_latency')
# Named tuple to organize information returned from PyOPXClient.get_get_cont_source_chan_filter_info_by_number/name
FilterInfo = namedtuple('FilterInfo', 'hpf_enabled, hpf_filter_type, hpf_num_poles, hpf_freq, lpf_enabled, lpf_filter_type, lpf_num_poles, lpf_freq, pli_filter_enabled, pli_filter_freq, num_harmonics, adaptive_harmonics')
# Named tuple to organize information returned from PyOPXClient.get_new_data()
NewData = namedtuple('NewData', 'num_data_blocks, source_num_or_type, timestamp, channel, unit, number_of_blocks_per_waveform, block_number_for_waveform, waveform')
# Named tuple to organize information returned from PyOPXClient.get_new_timestamps()
NewTimestamps = namedtuple('NewTimestamps', 'num_timestamps, timestamp, source_num_or_type, channel, unit')

# TODO
# - Conversion from string/bytes/UTF is functional but sloppy

# Converts byte array to string. Do nothing if it's not a byte array.
# Added this function because Python3 by default treats c_char arrays as bytes
# instead of a string like Python 2 does.
def byte_array_to_string(barray, encoding = "utf-8"):
    if type(barray) is bytes:
        tmp = barray.decode(encoding)
        return tmp
    else:
        return barray

# Structure returned by OPX_GetGlobalParams
class OPX_GlobalParams(Structure):
    _fields_ = [("OPXSystemType", c_int32),           # A hardware-specific OPXSTSTEM_* value (see 4 values above)
                ("OPXSoftwareVersion", c_int32),      # Version of OmniPlex being used, e.g. 1151 = version 1.15.1
                ("OPXSDKVersion", c_int32),           # Version of the Native Client API being used
                ("numSources", c_int32),              # Total number of sources available to client
                ("sourceIds", c_int32 * MAX_SOURCES), # An array of source numbers, e.g. [4,1,3,6,10,11,...]
                ("numSpikeChans", c_int32),           # Total number of channels of SPIKE_TYPE
                ("numContChans", c_int32),            # Total number of channels of CONTINUOUS_TYPE
                ("numEventChans", c_int32),           # Total number of channels of EVENT_TYPE
                ("numOtherChans", c_int32),           # Total number of channels of OTHER_TYPE
                ("timestampFrequency", c_double),     # Frequency of timestamp "ticks"; currently either 40000 or 1000000,i.e. one tick = either 25 microseconds or 1 microsecond
                ("clientSampleRateLimit", c_double),  # Server only sends continuous data to clients if the sample rate is this frequency or less; by default, 1000 Hz
                ("bitsPerSample", c_int32),           # Typically either 12 or 16 bits, as set in Server options
                ("minimizeClientLatency", c_int32),   # Nonzero if Server "Minimize Client Latency" option is enabled
                ("reserved", c_uint8 * 1024)]         # Reserved for future use


# Structure returned by OPX_GetNewData and OPX_GetNewDataEx
class OPX_DataBlock(Structure):
    _fields_ = [("SourceNumOrType", c_uint8),           # Source number or source type: SPIKE_TYPE, EVENT_TYPE or CONTINUOUS TYPE
                ("reserved1", c_uint8),
                ("reserved2", c_uint8),
                ("UpperTS", c_uint8),                   # Upper 8 bits of the 40-bit timestamp
                ("TimeStamp", c_uint32),                # Lower 32 bits of the 40-bit timestamp
                ("Channel", c_uint16),                  # Channel number within one of the four source-type ranges
                ("Unit", c_uint16),                     # Unit (0 = unsorted, 1 = a, 2 = b, etc), or strobed event value
                ("reserved3", c_uint8),
                ("NumberOfBlocksPerWaveform", c_uint8), # For spikes longer than one block
                ("BlockNumberForWaveform", c_uint8),    # For spikes longer than one block
                ("NumberOfDataWords", c_uint8),         # Number of shorts (2-byte integers) that follow this header
                ("WaveForm", c_int16 * MAX_WF_LENGTH)]  # The spike waveform or a series of continuous data samples

class OPX_FilterInfo(Structure):
    _fields_ = [("m_bEnabledHPF", c_bool),
                ("m_filterTypeHPF", c_int32),
                ("m_numPolesHPF", c_int32),
                ("m_freqHPF", c_float),
                ("m_bEnabledLPF", c_bool),
                ("m_filtereTypeLFP", c_int32),
                ("m_numPolesLFP", c_int32),
                ("m_freqLFP", c_float),
                ("m_bEnabledPLIFilter", c_bool),
                ("m_freqPLIFilter", c_int32),
                ("m_numHarmonics", c_int32),
                ("m_bAdaptiveHarmonics", c_bool),
                ("m_reserved", c_ulong)] # Using c_ulong for Windows DWORD type

class PyOPXClient:
    """
    PyOPXClient wraps functions in the C++ OmniPlex Native Client API. All functions (except for close_client()) return
    a result code along with the requested data.
    
    By default the class initializes expecting the OPXClient.dll or OPXClient64.dll files to be in a folder called
    'bin' in the current working directory. It also initializes with a maximum data structures return count of 100000.
    Both can be replaced with custom values.
    """
    
    def __init__(self, opxclient_dll_path = 'bin', max_opx_data = 100000):
        self.platform = platform.architecture()[0]
        self.max_opx_data = max_opx_data
        self.opx_dll_path = os.path.abspath(opxclient_dll_path)
        
        # Used in get_new_data()
        self.data_blocks = (OPX_DataBlock * self.max_opx_data)()

        # Used in get_new_timestamps()
        self.num_timestamps = (c_int)(self.max_opx_data)
        self.timestamp = (c_double * self.max_opx_data)(0)
        self.source_num_or_type = (c_byte * self.max_opx_data)(0)
        self.channel = (c_uint16 * self.max_opx_data)(0)
        self.unit = (c_uint16 * self.max_opx_data)(0)
        
        if self.platform == '32bit':
            self.opx_dll_file = os.path.join(self.opx_dll_path, 'OPXClient.dll')
        else:
            self.opx_dll_file = os.path.join(self.opx_dll_path, 'OPXClient64.dll')

        try:
            self.opxclient_dll = WinDLL(self.opx_dll_file)
        except (WindowsError):
            print("Error: Can't load OPX Client DLL at: " + self.opx_dll_path)

    def init_client(self):
        """
        Connects the client program to OmniPlex Server.
        Call this function once, before calling any other client function.

        Args:
            None
        
        Returns:
            OPX_ERROR_NOERROR if success
        """
        return self.opxclient_dll.OPX_InitClient()

    def close_client(self):
        """
        Disconnects the client program from OmniPlex Server.
        
        Args:
            None
        
        Returns:
            None
        """
        self.opxclient_dll.OPX_CloseClient()

    def get_global_parameters(self):
        """
        Returns basic info on sources and system parameters.

        Args:
            None

        Returns:
            result - OPX_ERROR_NOERROR on success
            GlobalParameters - named tuple loaded with elements of the OPX_GlobalParameters class/structure
        """
        g = OPX_GlobalParams()
        result = self.opxclient_dll.OPX_GetGlobalParameters(byref(g))
        
        return result, GlobalParameters(opx_system_type = g.OPXSystemType,
                                        opx_software_version = g.OPXSoftwareVersion, 
                                        opx_sdk_version = g.OPXSDKVersion,
                                        num_sources = g.numSources, 
                                        source_ids = tuple(g.sourceIds[0:g.numSources]), 
                                        num_spike_chans = g.numSpikeChans, 
                                        num_cont_chans = g.numContChans, 
                                        num_event_chans = g.numEventChans, 
                                        num_other_chans = g.numOtherChans, 
                                        timestamp_frequency = g.timestampFrequency, 
                                        client_sample_rate_limit = g.clientSampleRateLimit,
                                        bits_per_sample = g.bitsPerSample,
                                        minimize_client_latency = g.minimizeClientLatency)

    def get_source_info_by_number(self, source_num):
        """
        Given a source number, returns basic info about that source.
        
        Args:
            source_num - Number of the source whose info is being requested

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_name - string containing the source name
            source_type - one of the values SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE
            num_chans - number of channels in the source
            linear_start_chan - starting channel number for the source, within the linear array of channels of the specified type
        """
        source_name = (c_char * 256)()
        source_type = c_int(0)
        num_chans = c_int(0)
        linear_start_chan = c_int(0)
        result = self.opxclient_dll.OPX_GetSourceInfoByNumber(c_int(source_num), byref(source_name), byref(source_type), byref(num_chans), byref(linear_start_chan))
        tmp_source_name = byte_array_to_string(source_name.value)
        return result, tmp_source_name, source_type.value, num_chans.value, linear_start_chan.value

    def get_source_info_by_name(self, source_name):
        """
        Given a source name, returns basic info about that source.
        
        Args:
            source_name - String containing the source name of the source whose info is being requested

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_number - Source number
            source_type - One of the values SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE
            num_chans - Number of channels in the source
            linear_start_chan - starting channel number for the source, within the linear array of channels of the specified type
        """
        source_num = c_int(0)
        source_type = c_int(0)
        num_chans = c_int(0)
        linear_start_chan = c_int(0)
        result = self.opxclient_dll.OPX_GetSourceInfoByName(source_name.encode("utf-8"), byref(source_num), byref(source_type), byref(num_chans), byref(linear_start_chan))
        return result, source_num.value, source_type.value, num_chans.value, linear_start_chan.value

    def get_spike_source_info_by_number(self, source_num):
        """
        Given a spike source number, returns info specific to a spike source.

        Args:
            source_num - Number of the spike source whose info is being requested

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_name - string containing the source name
            rate - sample rate of the spike source
            voltage_scaler - value which converts integer spike waveform values to volts
            trodality - 1 = single electrode, 2 = stereotrode, 4 = tetrode
            pts_per_waveform - number of points in each spike waveform
            pre_thresh_pts - number of waveform points before the threshold crossing
        """
        source_name = (c_char * 256)()
        rate = c_double(0)
        voltage_scaler = c_double(0)
        trodality = c_int(0)
        pts_per_waveform = c_int(0)
        pre_thresh_pts = c_int(0)
        result = self.opxclient_dll.OPX_GetSpikeSourceInfoByNumber(c_int(source_num), byref(source_name), byref(rate), byref(voltage_scaler), byref(trodality), byref(pts_per_waveform), byref(pre_thresh_pts))
        tmp_source_name = byte_array_to_string(source_name.value)
        return result, tmp_source_name, rate.value, voltage_scaler.value, trodality.value, pts_per_waveform.value, pre_thresh_pts.value
    
    def get_spike_source_info_by_name(self, source_name):
        """
        Given a spike source number, returns info specific to a spike source.

        Args:
            source_name - String containing the spike source name of the source whose info is being requested

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_number - source number
            rate - sample rate of the spike source
            voltage_scaler - value which converts integer spike waveform values to volts
            trodality - 1 = single electrode, 2 = stereotrode, 4 = tetrode
            pts_per_waveform - number of points in each spike waveform
            pre_thresh_pts - number of waveform points before the threshold crossing
        """
        source_num = c_int(0)
        rate = c_double(0)
        voltage_scaler = c_double(0)
        trodality = c_int(0)
        pts_per_waveform = c_int(0)
        pre_thresh_pts = c_int(0)
        result = self.opxclient_dll.OPX_GetSpikeSourceInfoByName(source_name.encode("utf-8"), byref(source_num), byref(rate), byref(voltage_scaler), byref(trodality), byref(pts_per_waveform), byref(pre_thresh_pts))
        return result, source_num.value, rate.value, voltage_scaler.value, trodality.value, pts_per_waveform.value, pre_thresh_pts.value

    def get_cont_source_info_by_number(self, source_num):
        """
        Given a continuous source, returns continuous-source specific info.

        Args:
            source_num - Number of the continuous source whose info is being requested
        
        Returns:
            result - OPX_ERROR_NOERROR on success
            rate - sample rate of the continuous source
            voltage_scaler - value which converts integer continuous sample values to volts
        """
        source_name = (c_char * 256)()
        rate = c_double(0)
        voltage_scaler = c_double(0)
        result = self.opxclient_dll.OPX_GetContSourceInfoByNumber(c_int(source_num), byref(source_name), byref(rate), byref(voltage_scaler))
        tmp_source_name = byte_array_to_string(source_name.value)
        return result, tmp_source_name, rate.value, voltage_scaler.value

    def get_cont_source_info_by_name(self, source_name):
        """
        Given a continuous source, returns continuous-source specific info.

        Args:
            source_name - String containing the continuous source name of the source whose info is being requested

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_num - source number
            rate - sample rate of the continuous source
            voltage_scaler - value which converts integer continuous sample values to volts
        """
        source_num = c_int(0)
        rate = c_double(0)
        voltage_scaler = c_double(0)
        result = self.opxclient_dll.OPX_GetContSourceInfoByName(source_name.encode("utf-8"), byref(source_num), byref(rate), byref(voltage_scaler))
        return result, source_num.value, rate.value, voltage_scaler.value

    def get_source_chan_info_by_number(self, source_num, source_chan):
        """
        Given a source number and source-relative channel number, returns info for that source channel.
        
        Args:
            source_num - Source number whose info is being requested
            source_chan - Source-relative channel number

        Returns:
            result - OPX_ERROR_NOERROR on success
            chan_name - String containing the channel name
            rate - sample rate of the continuous source
            voltage_scaler - value which converts integer continuous sample values to volts   
            enabled - 1 if channel is enabled, 0 if disabled         
        """
        chan_name = (c_char * 256)()
        rate = c_double(0)
        voltage_scaler = c_double(0)
        enabled = c_int(0)
        result = self.opxclient_dll.OPX_GetSourceChanInfoByNumber(c_int(source_num), c_int(source_chan), byref(chan_name), byref(rate), byref(voltage_scaler), byref(enabled))
        tmp_chan_name = byte_array_to_string(chan_name.value)
        return result, tmp_chan_name, rate.value, voltage_scaler.value, enabled.value

    def get_source_chan_info_by_name(self, source_name, source_chan):
        """
        Given a source name and source-relative channel number, returns info for that source channel.abs
        
        Args:
            source_name - String containing the source's name
            source_chan - Source-relative channel number

        Returns:
            result - OPX_ERROR_NOERROR on success
            chan_name - String containing the channel name
            rate - sample rate of the continuous source
            voltage_scaler - value which converts integer continuous sample values to volts   
            enabled - 1 if channel is enabled, 0 is disabled           
        """
        chan_name = (c_char * 256)()
        rate = c_double(0)
        voltage_scaler = c_double(0)
        enabled = c_int(0)
        result = self.opxclient_dll.OPX_GetSourceChanInfoByName(source_name.encode("utf-8"), c_int(source_chan), byref(chan_name), byref(rate), byref(voltage_scaler), byref(enabled))
        tmp_chan_name = byte_array_to_string(chan_name.value)
        return result, tmp_chan_name, rate.value, voltage_scaler.value, enabled.value

    def get_linear_chan_info(self, linear_chan_type, chan):
        """
        Given a channel type and channel number within that type, returns info for that channel.

        Args:
            linear_chan_type - SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE
            chan - channel number within the channel type

        Returns:
            result - OPX_ERROR_NOERROR on success
            chan_name - String containing the channel name
            rate - sample rate of the continuous source
            voltage_scaler - value which converts integer continuous sample values to volts   
            enabled - 1 if channel is enabled, 0 is disabled
        """
        chan_name = (c_char * 256)()
        rate = c_double(0)
        voltage_scaler = c_double(0)
        enabled = c_int(0)
        result = self.opxclient_dll.OPX_GetLinearChanInfo(c_int(linear_chan_type), c_int(chan), byref(chan_name), byref(rate), byref(voltage_scaler), byref(enabled))
        tmp_chan_name = byte_array_to_string(chan_name.value)
        return result, tmp_chan_name, rate.value, voltage_scaler.value, enabled.value

    def get_cont_source_chan_filter_info_by_number(self, source_num, source_chan):
        """
        Given a source number and channel number within that source, return digital filter info for that source channel.

        Args:
            source_num - Source number whose info is being requested
            source_chan - Source-relative channel number

        Returns:
            result - OPX_ERROR_NOERROR on success
            FilterInfo - named tuple loaded with elements of the OPX_FilterInfo class/structure
        """
        f = OPX_FilterInfo()
        result = self.opxclient_dll.OPX_GetContSourceChanFilterInfoByNumber(c_int(source_num), c_int(source_chan), byref(f))

        FilterInfo = namedtuple('FilterInfo', 'hpf_enabled, hpf_filter_type, hpf_num_poles, hpf_freq, lpf_enabled, lpf_filter_type, lpf_num_poles, lpf_freq, pli_filter_enabled, pli_filter_freq, num_harmonics, adaptive_harmonics')
        return result, FilterInfo(hpf_enabled = f.m_bEnabledHPF,
                                    hpf_filter_type = f.m_filterTypeHPF,
                                    hpf_num_poles = f.m_numPolesHPF,
                                    hpf_freq = f.m_freqHPF,
                                    lpf_enabled = f.m_bEnabledLPF,
                                    lpf_filter_type = f.m_filterTypeLPF,
                                    lpf_num_poles = f.m_numPolesLPF,
                                    lpf_freq = f.m_freqLPF,
                                    pli_filter_enabled = f.m_bEnabledPLIFilter,
                                    pli_filter_freq = f.m_freqPLIFilter,
                                    num_harmonics = f.m_numHarmonics,
                                    adaptive_harmonics = f.m_bAdaptiveHarmonics)
    
    def get_cont_source_chan_filter_info_by_name(self, source_name, source_chan):
        """
        Given a source name and channel number within that source, return digital filter info for that source channel.

        Args:
            source_name - Source name whose info is being requested
            source_chan - Source-relative channel number

        Returns:
            result - OPX_ERROR_NOERROR on success
            FilterInfo - named tuple loaded with elements of the OPX_FilterInfo class/structure
        """
        f = OPX_FilterInfo()
        result = self.opxclient_dll.OPX_GetContSourceChanFilterInfoByName(source_name.encode("utf-8"), c_int(source_chan), byref(f))

        FilterInfo = namedtuple('FilterInfo', 'hpf_enabled, hpf_filter_type, hpf_num_poles, hpf_freq, lpf_enabled, lpf_filter_type, lpf_num_poles, lpf_freq, pli_filter_enabled, pli_filter_freq, num_harmonics, adaptive_harmonics')
        return result, FilterInfo(hpf_enabled = f.m_bEnabledHPF,
                                    hpf_filter_type = f.m_filterTypeHPF,
                                    hpf_num_poles = f.m_numPolesHPF,
                                    hpf_freq = f.m_freqHPF,
                                    lpf_enabled = f.m_bEnabledLPF,
                                    lpf_filter_type = f.m_filterTypeLPF,
                                    lpf_num_poles = f.m_numPolesLPF,
                                    lpf_freq = f.m_freqLPF,
                                    pli_filter_enabled = f.m_bEnabledPLIFilter,
                                    pli_filter_freq = f.m_freqPLIFilter,
                                    num_harmonics = f.m_numHarmonics,
                                    adaptive_harmonics = f.m_bAdaptiveHarmonics)

    def get_cont_linear_chan_filter_info(self, chan):
        """
        Given a continuous channel number, return digital filter info for that source channel.

        Args:
            source_name - Source name whose info is being requested
            source_chan - Source-relative channel number

        Returns:
            result - OPX_ERROR_NOERROR on success
            FilterInfo - named tuple loaded with elements of the OPX_FilterInfo class/structure
        """
        f = OPX_FilterInfo()
        result = self.opxclient_dll.OPX_GetContLinearCHanFilterInfo(c_int(chan), byref(f))

        FilterInfo = namedtuple('FilterInfo', 'hpf_enabled, hpf_filter_type, hpf_num_poles, hpf_freq, lpf_enabled, lpf_filter_type, lpf_num_poles, lpf_freq, pli_filter_enabled, pli_filter_freq, num_harmonics, adaptive_harmonics')
        return result, FilterInfo(hpf_enabled = f.m_bEnabledHPF,
                                    hpf_filter_type = f.m_filterTypeHPF,
                                    hpf_num_poles = f.m_numPolesHPF,
                                    hpf_freq = f.m_freqHPF,
                                    lpf_enabled = f.m_bEnabledLPF,
                                    lpf_filter_type = f.m_filterTypeLPF,
                                    lpf_num_poles = f.m_numPolesLPF,
                                    lpf_freq = f.m_freqLPF,
                                    pli_filter_enabled = f.m_bEnabledPLIFilter,
                                    pli_filter_freq = f.m_freqPLIFilter,
                                    num_harmonics = f.m_numHarmonics,
                                    adaptive_harmonics = f.m_bAdaptiveHarmonics)

    def get_source_voltage_scalers_by_number(self, source_num):
        """
        Given a source number, fills in a tuple of voltage scaling values. If the source does not support per-channel 
        scaling, all the values will be the same. If the source does not support gain changes, this function only 
        needs to be called once. If the source does support gain changes, the function get_last_gain_change_time(). 
        can determine when gains have changed.

        Args:
            source_num - source number

        Returns:
            result - OPX_ERROR_NOERROR on success
            scales - tuple of voltage scaling values 
        """
        scalers = (c_double * MAX_CHANS_PER_SOURCE)()
        result = self.opxclient_dll.OPX_GetSourceVoltageScalersByNumber(c_int(source_num), byref(scalers))
        return result, tuple(scalers)

    def get_source_voltage_scalers_by_name(self, source_name):
        """
        Given a source name, fills in a tuple of voltage scaling values. If the source does not support per-channel 
        scaling, all the values will be the same. If the source does not support gain changes, this function only 
        needs to be called once. If the source does support gain changes, the function get_last_gain_change_time(). 
        can determine when gains have changed.

        Args:
            source_name - string containing the source's name, e.g. "FP"

        Returns:
            result - OPX_ERROR_NOERROR on success
            scales - tuple of voltage scaling values 
        """
        scalers = (c_double * MAX_CHANS_PER_SOURCE)()
        result = self.opxclient_dll.OPX_GetSourceVoltageScalersByName(source_name.encode("utf-8"), byref(scalers))
        return result, tuple(scalers)

    def exclude_source_by_number(self, source_num):
        """
        Exclude the given source from the data sent to this client.

        Args:
            source_num - Number of the source to be excluded

        Returns:
            OPX_ERROR_NOERROR on success
        """
        result = self.opxclient_dll.OPX_ExcludeSourceByNumber(c_int(source_num))
        return result
    
    def exclude_source_by_name(self, source_name):
        """
        Exclude the given source from the data sent to this client.

        Args:
            source_name - Name of the source to be excluded

        Returns:
            OPX_ERROR_NOERROR on success
        """
        result = self.opxclient_dll.OPX_ExcludeSourceByName(source_name.encode("utf-8"))
        return result

    def exclude_all_sources_of_type(self, source_type):
        """
        Exclude all sources of the given type from the data sent to this client.abs
        
        Args:
            source_type - SPIKE_TYPE, CONTINUOUS_TYPE, or EVENT_TYPE
        
        Returns:
            OPX_ERROR_NOERROR on success
        """
        result = self.opxclient_dll.OPX_ExcludeAllSourcesOfType(c_int(source_type))
        return result
        
    def include_source_by_number(self, source_num):
        """
        Include the given source from the data sent to this client.

        Args:
            source_num - Number of the source to be included

        Returns:
            OPX_ERROR_NOERROR on success        
        """
        result = self.opxclient_dll.OPX_IncludeSourceByNumber(c_int(source_num))
        return result
    
    def include_source_by_name(self, source_name):
        """
        Include the given source from the data sent to this client.

        Args:
            source_name - Name of the source to be included

        Returns:
            OPX_ERROR_NOERROR on success        
        """
        result = self.opxclient_dll.OPX_IncludeSourceByName(source_name.encode("utf-8"))
        return result
        
    def include_all_sources_of_type(self, source_type):
        """
        Include all sources of the given type from the data sent to this client.abs
        
        Args:
            source_type - SPIKE_TYPE, CONTINUOUS_TYPE, or EVENT_TYPE
        
        Returns:
            OPX_ERROR_NOERROR on success        
        """
        result = self.opxclient_dll.OPX_IncludeAllSourcesOfType(c_int(source_type))
        return result

    def get_new_data(self):
        """
        Get a batch of online client data.

        Args:
            None

        Returns:
            result - OPX_ERROR_NOERROR on success
            NewData - named tuple loaded with data:
                .num_data_blocks - number of data blocks returned; is number of elements in all other returned data
                .source_num_or_type - source number or type of data block
                .upper_ts - spike, continuous, and event timestamps (upper 8 bits)
                .timestamp - spike, continuous, and event timestamps (lower 32 bits)
                .channel - channel numbers for each block timestamp
                .unit - units (0 = unsorted, 1 = Unit A, 2 = Unit B, etc) for spike timestamps, or a strobed event word value for a strobed event timestamp
                .number_of_blocks_per_waveform - how many blocks an individual spike waveform is spread across (for long waveforms)
                .block_number_for_waveform - block number of multiple-block spike waveform
                .waveform - spike or continuous waveform data

        Note: the OPX_SetDataFormat function determines whether source types or source numbers
        appear in source_num_or_type; by default, source numbers are returned
        """
        num_data_blocks = c_int(self.max_opx_data)
        
        result = self.opxclient_dll.OPX_GetNewData(byref(num_data_blocks), byref(self.data_blocks))
        
        source_num_or_type = [self.data_blocks[n].SourceNumOrType for n in range(num_data_blocks.value)]
        timestamp = [self.get_64_bit_double_timestamp_from_data_block(self.data_blocks[n]) for n in range(num_data_blocks.value)]
        channel = [self.data_blocks[n].Channel for n in range(num_data_blocks.value)]
        unit = [self.data_blocks[n].Unit for n in range(num_data_blocks.value)]
        number_of_blocks_per_waveform = [self.data_blocks[n].NumberOfBlocksPerWaveform for n in range(num_data_blocks.value)]
        block_number_for_waveform = [self.data_blocks[n].BlockNumberForWaveform for n in range(num_data_blocks.value)]
        waveform = [tuple(self.data_blocks[n].WaveForm[0:self.data_blocks[n].NumberOfDataWords]) for n in range(num_data_blocks.value)]

        return result, NewData(num_data_blocks = num_data_blocks.value,
                                source_num_or_type = source_num_or_type,
                                timestamp = timestamp,
                                channel = channel,
                                unit = unit,
                                number_of_blocks_per_waveform = number_of_blocks_per_waveform,
                                block_number_for_waveform = block_number_for_waveform,
                                waveform = waveform)

    def get_new_data_ex(self):
        """
        Get a back of online client data. Similar to get_new_data(), but returns extra information.

        Args:
            None

        Returns:
            A tuple with [0] as OPX_ERROR_NOERROR on success, and each member of the OPX_DataBlock structure
            as documented above (returned tuple index [1] through [9]), with the exception of "reserved" members.

            Additionally,

            num_spikes_read - The number of data blocks of type SPIKE_TYPE
            num_cont_read - The number of data blocks of type CONTINUOUS_TYPE
            num_events_read - The number of data blocks of type EVENT_TYPE
            num_other_read - The number of data blocks of type OTHER_TYPE
            min_timestamp - The smallest timestamp
            max_timestamp - The largest timestamp

        Note: the OPX_SetDataFormat function determines whether source types or source numbers
        appear in source_num_or_type; by default, source numbers are returned 
        """
        num_data_blocks = c_int(self.max_opx_data)
        
        num_spikes_read = c_int()
        num_cont_read = c_int()
        num_events_read = c_int()
        num_other_read = c_int()
        min_timestamp = c_double()
        max_timestamp = c_double()
        
        result = self.opxclient_dll.OPX_GetNewDataEx(byref(num_data_blocks), byref(self.data_blocks), byref(num_spikes_read), byref(num_cont_read), byref(num_events_read), byref(num_other_read), byref(min_timestamp), byref(max_timestamp))
        
        source_num_or_type = [self.data_blocks[n].SourceNumOrType for n in range(num_data_blocks.value)]
        upper_ts = [self.data_blocks[n].UpperTS for n in range(num_data_blocks.value)]
        timestamp = [self.data_blocks[n].TimeStamp for n in range(num_data_blocks.value)]
        channel = [self.data_blocks[n].Channel for n in range(num_data_blocks.value)]
        unit = [self.data_blocks[n].Unit for n in range(num_data_blocks.value)]
        number_of_blocks_per_waveform = [self.data_blocks[n].NumberOfBlocksPerWaveform for n in range(num_data_blocks.value)]
        block_number_for_waveform = [self.data_blocks[n].BlockNumberForWaveform for n in range(num_data_blocks.value)]
        waveform = [tuple(self.data_blocks[n].WaveForm) for n in range(num_data_blocks.value)]
        
        return result, num_data_blocks.value, source_num_or_type, upper_ts, timestamp, channel, unit, number_of_blocks_per_waveform, block_number_for_waveform, waveform, num_spikes_read.value, num_cont_read.value, num_events_read.value, num_other_read.value, min_timestamp.value, max_timestamp.value
    
    def get_new_timestamps(self):
        """
        Get a batch of online client data; no spike waveforms or continuous data are returned.

        Args:
            None

        Returns:
            result - OPX_ERROR_NOERROR on success
            NewData - named tuple loaded with data:
                .num_timestamps - the number of timestamps returned
                .timestamp - spike and event timestamps
                .source_num_or_type - source numers or source types (SPIKE_TYPE or EVENT_TYPE) for each timestamp
                .channel - channel numbers for each timestamp
                .unit - units (0 = unsorted, 1 = Unit A, 2 = Unit B, etc) for spike timestamps, or a strobed event word value for a strobed event timestamp

        Note: the OPX_SetDataFormat function determines whether source types or source numbers
        appear in source_num_or_type; by default, source numbers are returned 
        """
        num_timestamps = (c_int)(self.max_opx_data)
        
        result = self.opxclient_dll.OPX_GetNewTimestamps(byref(num_timestamps), byref(self.timestamp), byref(self.source_num_or_type), byref(self.channel), byref(self.unit))

        return result, NewTimestamps(num_timestamps = num_timestamps.value,
                                        timestamp = [self.timestamp[n] for n in range(self.num_timestamps.value)],
                                        source_num_or_type = [self.source_num_or_type[n] for n in range(self.num_timestamps.value)],
                                        channel = [self.channel[n] for n in range(self.num_timestamps.value)],
                                        unit = [self.unit[n] for n in range(self.num_timestamps.value)])
    
    def set_data_format(self, data_format):
        """
        Sets the format for the data returned. Data can be formatted in terms of source number and source-relative
        channel, or source type and source-type-relative channel. The default is source numbers.

        Args:
            data_format - FORMAT_SOURCE_TYPE_RELATIVE or FORMAT_SOURCE_NUMBER_RELATIVE

        Returns:
            result - OPX_ERROR_NOERROR on success
        """
        result = self.opxclient_dll.OPX_SetDataFormat(c_int(data_format))
        return result

    def send_client_data_words(self, data_words):
        """
        Sends one or more 16-bit data words to OmniPlex Server. See the C Client API documentation for more
        information on this function, its usage, and its limitations.

        Args:
            data_words - Python list of data words

        Returns:
            result = OPX_ERROR_NOERROR on success
        """
        c_data_words = (c_int16 * len(data_words))(*data_words)
        num_data_words = c_int32(len(data_words))

        result = self.opxclient_dll.OPX_SendClientDataWords(c_data_words, num_data_words)
        return result

    def get_64_bit_int_timestamp_from_data_block(self, data_block):
        """
        Extract a 64-bit integer timestamp (in units of ticks) from the 40-bit integer timestamp in an OPX_DataBlock.

        None of the functions in the pyopxclientlib module return an OPX_DataBlock class/structure. This is included
        only for the sake of completion.

        Args:
            data_block - Instance of OPX_DataBlock class

        Returns:
            64-bit integer timestamp in units of tics
        """
        func = self.opxclient_dll.OPX_Get64BitIntTimestampFromDataBlock
        func.restype = c_ulonglong
        return func(byref(data_block))

    def make_64_bit_int_timestamp_from_upper_lower(self, timestamp_lower, timestamp_upper):
        """
        Combine the lower 32 bits and upper 8 bits of a 40-bit integer timestamp into a 64-bit integer timestamp (in units of ticks).

        Args:
            timestamp_lower - lower 32 bits of the 40-bit timestamp
            timestamp_upper - upper 8 bits of the 40-bit timestamp

        Returns:
            64-bit integer timestamp in units of tics
        """
        func = self.opxclient_dll.OPX_Make64BitIntTimestampFromUpperLower
        func.restype = c_ulonglong
        return func(c_uint32(timestamp_lower), c_uint8(timestamp_upper))

    def get_64_bit_double_timestamp_from_data_block(self, data_block):
        """
        Extract a 64-bit double precision floating point timestamp (in units of seconds) from the 40-bit integer timestamp in an OPX_DataBlock.

        None of the functions in the pyopxclientlib module return an OPX_DataBlock class/structure. This is included
        only for the sake of completion.

        Args:
            data_block - Instance of OPX_DataBlock class

        Returns:
            64-bit double precision floating point timestamp in units of seconds
        """
        func = self.opxclient_dll.OPX_Get64BitDoubleTimestampFromDataBlock
        func.restype = c_double
        return func(byref(data_block))
    
    def make_64_bit_double_timestamp_from_upper_lower(self, timestamp_lower, timestamp_upper):
        """
        Combine the lower 32 bits and upper 8 bits of a 40-bit integer timestamp into a 64-bit double precision floating point timestamp (in units of seconds).

        Args:
            timestamp_lower - lower 32 bits of the 40-bit timestamp
            timestamp_upper - upper 8 bits of the 40-bit timestamp

        Returns:
            64-bit double precision floating point timestamp in units of seconds
        """
        func = self.opxclient_dll.OPX_Make64BitDoubleTimestampFromUpperLower
        func.restype = c_double
        return func(c_uint32(timestamp_lower), c_uint8(timestamp_upper))

    def get_wait_handle(self):
        """
        Get a handle to be used when waiting for new data (see OPX_WaitForNewData). A client should only call this function once, not every time it calls OPX_WaitForNewData.

        Args:
            None
        
        Returns:
            Wait handle value
        """
        return self.opxclient_dll.OPX_GetWaitHandle()
        
    def wait_for_new_data(self, wait_handle, timeout):
        """
        Wait for new client data.  The client will block (wait) without using CPU time until either new data is available, or the specified timeout elapses.

        Args:
            wait_handle - Wait handle value
            timeout - Timeout interval in milliseconds

        Returns:
            OPX_ERROR_NOERROR on success
        """
        return self.opxclient_dll.OPX_WaitForNewData(c_uint32(wait_handle), c_uint32(timeout))

    def get_opx_system_status(self):
        """
        Get the current status of the OmniPlex system.

        Args:
            None
        
        Returns:
            Status of OPX_DAQ_STOPPED, OPX_DAQ_STARTED, OPX_RECORDING, or OPX_RECORDING_PAUSED
        """
        return self.opxclient_dll.OPX_GetOPXSystemStatus()

    def wait_for_opx_daq_ready(self, timeout_msecs):
        """
        Wait for OmniPlex data acquisition to begin, or for a specified timeout interval to elapse.  Note that this
        is not the same as waiting for new data to become available after data acquisition has started.

        Args:
            timeout_msecs - timeout interval in milliseconds

        Returns:
            OPX_ERROR_NOERROR on success
        """
        return self.opxclient_dll.OPX_WaitForOPXDAQReady(c_uint32(timeout_msecs))

    def clear_data(self, timeout_msecs):
        """
        Reads and discards client data, until no more data is immediately available, or until a specified timeout interval elapses.
        This is useful when a client needs to avoid processing a potentially large "backlog" of data, for example, at startup 
        or if it desires to only occasionally read a "sample" of the incoming data.

        Args:
            timeout_msecs - timeout interval in milliseconds

        Returns:
            OPX_ERROR_NOERROR on success
        """
        return self.opxclient_dll.OPX_ClearData(c_uint32(timeout_msecs))

    def get_last_parameter_update_time(self):
        """
        Get the OmniPlex time when any client-accessible OmniPlex parameter was updated.  Clients can use this function to
        determine whether a parameter has changed since the previous time they called the function.

        Args:
            None

        Returns:
            Time in seconds of the most recent parameter update
        """
        func = self.opxclient_dll.OPX_GetLastParameterUpdateTime
        func.restype = c_double
        return func()

    def get_last_gain_change_time(self):
        """
        Get the OmniPlex time when any source or channel gain changed.  Clients can use this function to
        determine whether gain values have changed since the previous time they called the function.

        Args:
            None

        Returns:
            Time in seconds of the most recent gain change
        """
        func = self.opxclient_dll.OPX_GetLastGainChangeTime
        func.restype = c_double
        return func()

    def get_last_wait_event_time(self):
        """
        Get the OmniPlex time when new client data was most recently available. Clients can use this function to determine whether
        new client data was made available since the previous time they called the function. However, for lowest latency, clients should use the 
        wait_for_new_data() function.
        
        Args:
            None
        
        Returns:
            Time in seconds of when new client data was most recently made available
        """
        func = self.opxclient_dll.OPX_GetLastWaitEventTime
        func.restype = c_double
        return func()

    def get_local_machine_time(self):
        """
        Returns the current machine time (Windows time).  Note that machine time is not the same as acquisition time ("timestamp time").

        Args:
            None

        Returns:
            Time in seconds of the current machine time
        """
        func = self.opxclient_dll.OPX_GetLocalMachineTime
        func.restype = c_double
        return func()

    def source_name_to_source_number(self, source_name):
        """
        Convert a source name to the equivalent source number.

        Args:
            source_name - Source name string

        Returns:
            Source number that corresponds to the provided source name
        """
        return self.opxclient_dll.OPX_SourceNameToSourceNumber(source_name.encode("utf-8"))

    def source_number_to_source_name(self, source_number):
        """
        Convert a source number to the equivalent source name.

        Args:
            source_number - Source number

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_name - Source name that corresponds to the provided source number
        """
        source_name = (c_char * 256)()
        result = self.opxclient_dll.OPX_SourceNumberToSourceName(c_uint32(source_number), byref(source_name))
        return result, source_name.value

    def source_chan_to_linear_chan_and_type(self, source_num, source_chan):
        """
        Convert a source number and source-relative channel number to a source type and a channel number within one of the linear channel number ranges.

        Args:
            source_num - Source number
            source_chan - Channel number within the specific source

        Returns:
            result - OPX_ERROR_NOERROR on success
            linear_chan_type - channel type (SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE)
            linear_chan - channel number within the channel range of the returned channel type
        """
        linear_chan_type = c_int32()
        linear_chan = c_int32()
        result = self.opxclient_dll.OPX_SourceChanToLinearChanAndType(c_uint32(source_num), c_int32(source_chan), byref(linear_chan_type), byref(linear_chan))
        return result, linear_chan_type.value, linear_chan.value

    def source_chan_to_linear_chan_and_type_by_name(self, source_name, source_chan):
        """
        Similar to source_chan_to_linear_chan_and_type(), but the source is specified by name rather than by number.

        Args:
            source_name - Source name
            source_chan - Channel number within the specific source

        Returns:
            result - OPX_ERROR_NOERROR on success
            linear_chan_type - channel type (SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE)
            linear_chan - channel number within the channel range of the returned channel type
        """
        linear_chan_type = c_int32()
        linear_chan = c_int32()
        result = self.opxclient_dll.OPX_SourceChanToLinearChanAndTypeByName(source_name.encode("utf-8"), c_int32(source_chan), byref(linear_chan_type), byref(linear_chan))
        return result, linear_chan_type.value, linear_chan.value

    def linear_chan_and_type_to_source_chan(self, linear_chan_type, linear_chan):
        """
        Convert a channel type and channel number within that channel type's channel range into the equivalent source number, source name, and source-relative channel.

        Args:
            linear_chan_type - channel type (SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, or OTHER_TYPE)
            linear_chan - channel number within the channel range of the specified channel type

        Returns:
            result - OPX_ERROR_NOERROR on success
            source_num - Source number
            source_name - Source name
            source_chan - Source-relative channel number
        """
        source_num = c_int32()
        source_name = (c_char * 256)()
        source_chan = c_int32()
        result = self.opxclient_dll.OPX_LinearChanAndTypeToSourceChan(c_int32(linear_chan_type), c_int32(linear_chan), byref(source_num), byref(source_name), byref(source_chan))
        tmp_source_name = byte_array_to_string(source_name.value)
        return result, source_num.value, tmp_source_name, source_chan.value

# Error codes returned by API functions

# No error.
OPX_ERROR_NOERROR = 0

# One of the client data pools that OmniPlex uses to communicate with clients
# was not found.  Check to make sure that OmniPlex Server is running.
OPX_ERROR_NODATAPOOL1 = -1
OPX_ERROR_NODATAPOOL2 = -2

# An attempt to allocate memory failed.
OPX_ERROR_NOMEM = -3

# A bad channel type / source type was passed to an API function.  Valid types are
# SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, and OTHER_TYPE.
OPX_ERROR_BADCHANTYPE = -4

# An invalid source number was passed to an API function.  Make sure that you are
# passing a source number obtained by a call to OPX_GetGlobalParameters.  Note that
# source numbers do not necessarily start at 1 or form a contiguous range of
# source numbers.
OPX_ERROR_BADSOURCENUM = -5

# An invalid data format was passed to an API function.  Valid formats are
# FORMAT_SOURCE_TYPE_RELATIVE and FORMAT_SOURCE_NUMBER_RELATIVE.
OPX_ERROR_BADDATAFORMAT = -6

# A null (zero) parameter was passed to an API function which does not allow a
# null value for that parameter.
OPX_ERROR_NULLPARAMETER = -7

# The requested mapping, for example, between a source name and a source number,
# could not be performed, possibly because one or more parameters were invalid.
OPX_ERROR_MAPPINGFAILED = -8

# The client failed to initialize.  Either OPX_InitClient was not called before
# any other client API function, or it was called but returned an error code.
# Attempts to call API functions after a failed initialization will return this error.
OPX_INIT_FAILED = -9

# The wait handle could not be opened.  Make sure that OmniPlex Server is running.
OPX_ERROR_NOWAITHANDLE = -10

# The specified timeout interval elapsed/expired.
OPX_ERROR_TIMEOUT = -11

# OPX_ClearData returned before it was able to clear all the available data.
OPX_ERROR_NOTCLEARED = -12

# The data buffer was not large enough to return all the available data. Call the function again to
# read the remaining data. Poll for data more frequently, or increase the buffer size to prevent this error.
OPX_ERROR_NOT_ALL_DATA_WAS_RETURNED = -13

# The data buffer could not be allocated, possible because the requested size was too large.
OPX_ERROR_BUFFER_ALLOC_FAILED = -14

# OPX_SendClientDataWords was unable to open the CinePlex device client., which is used for sending words to Server.
OPX_ERROR_OPEN_DLL_FAILED = -15

OPX_ERROR_UNKNOWN = -255
