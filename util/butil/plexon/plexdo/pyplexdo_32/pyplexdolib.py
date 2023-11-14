# (c) 2016 Plexon, Inc., Dallas, Texas
# www.plexon.com
#
# Authors: Alex Cheng, Chris Heydrick (chris@plexon.com)

# TODO: remove all the unnecessary "self."
# TODO: update function documentation to indicate what the return values are
# TODO: Python 3 support and refactor. This will be the first public release

from pathlib import Path
from ctypes import c_uint, byref, CDLL, c_char
import os
from collections import namedtuple

# for do_set_line_mode()
PULSE_GEN = 0
CLOCK_GEN = 1

DODigitalOutputInfo = namedtuple('DODigitalOutputInfo', ['num_devices', 'device_numbers', 'num_bits', 'num_lines'])

class PyPlexDO:
    '''
    Plexon digital output API for controlling the digital output functionality of "E" series NIDAQ cards.  Python
    wrapper for the C Client API.  Note: Almost all functions will return a 0 indicating successful execution of
    the function or a -1 indicating the opposite unless specified otherwise
    '''
    def __init__(self, plexdo_dll_path='bin'):
        '''
        Upon initialization, the class will look for the dll in the bin path.  If the dll cannot be found the
        initialization will fail.  By default, the class will look for the bin folder but you can specify the
        location of the dll as the parameter

        Input:
            plexdo_dll_path - directory path containing the dlls

        Returns:
            prints an error message in the console

        '''
        dll_path = Path(__file__).parent / 'PlexDO.dll'
        dll_path = dll_path.resolve()
        # self.plexdo_dll_path = os.path.abspath(plexdo_dll_path)
        # self.plexdo_dll_file = os.path.join(self.plexdo_dll_path, 'PlexDO.dll')

        try:
            # self.plexdoclient_dll = CDLL(self.plexdo_dll_file)
            self.plexdoclient_dll = CDLL(str(dll_path))
        except (WindowsError):
            print(f"Error: Can't load PlexDO.dll at: {dll_path}")
            raise

    def get_digital_output_info(self):
        '''
        Query function which returns info on available (and supported) digital NI output devices. Return value is
        the number of supported NI devices which were found. This function returns a named tuple containing device
        info.

        Input:
            none
        Returns:
            A named tuple called DODigitalOutputInfo with these attributes:
                num_devices - number of DO capable cards
                device_numbers - NI device numbers of these devices
                num_bits - the number of digital output bits on each device
                num_lines - the number of digital output lines on each device

        Note: Returns -1 in num_devices field if NIDAQ is not installed. Arrays are set to size of 16 to emphasize the NI limit of 16
        devices.
        '''
        device_numbers = (c_uint * 16)()
        num_bits = (c_uint * 16)()
        num_lines = (c_uint * 16)()

        num_devices = self.plexdoclient_dll.DOGetDigitalOutputInfo(device_numbers, num_bits, num_lines)

        return DODigitalOutputInfo(num_devices=num_devices, device_numbers=device_numbers, num_bits=num_bits,
                                   num_lines=num_lines)

    def get_device_string(self, device_number):
        '''
        Returns an identifying string for the given NI device number, e.g. "PCI-6071E"

        Input:
            device_number - the NI device number for the device

        Returns:
            device_string - a string containing the identifying model number for the NI card

        If an error occurs a -1 will be returned
        '''
        self.device_number = c_uint(device_number)
        device_string = (c_char * 64)()
        result = self.plexdoclient_dll.DOGetDeviceString(self.device_number, byref(device_string))
        if result != 0:
            return result
        else:
            return device_string.value.decode('ascii')

    def init_device(self, device_number, is_used_by_map = False):
        '''
        Must be called before any digital output is attempted on the specified device. All digital output bits and
        lines will be set to 0. is_used_by_map = True indicates that the MAP is sharing this device, in which case
        output line 0 is not be available for digital output.

        Input:
            device_number - the NI device number for the device
            is_used_by_map - determines whether a MAP system is sharing the device.  False = not sharing, True = sharing. By
            default set to False.

        Returns:
            An integer that indicates whether initializing the device was successful.  0 = success, -1 = fail
        '''
        self.device_number = c_uint(device_number)
        self.is_used_by_map = c_uint(is_used_by_map)
        return self.plexdoclient_dll.DOInitDevice(self.device_number, self.is_used_by_map)

    def clear_all_bits(self, device_number):
        '''
        Resets all digital output bits to 0 on the given device. The bits are sequentially set to 0 as quickly as
        possible.

        Input:
            device_number - the NI device number for the device

        Returns:
            An integer that indicates whether all the bits are clear.  0 = success, -1 = fail
        '''
        self.device_number = c_uint(device_number)
        return self.plexdoclient_dll.DOClearAllBits(self.device_number)

    def set_bit(self, device_number, bit_number):
        '''
        Sets a single digital output bit to 1.

        Input:
            device_number - the NI device number for the device
            bit_number - the bit number of the NI device

        Returns:
            An integer that indicates whether the bit was set.
        '''
        self.device_number = c_uint(device_number)
        self.bit_number = c_uint(bit_number)
        return self.plexdoclient_dll.DOSetBit(self.device_number, self.bit_number)

    def clear_bit(self, device_number, bit_number):
        '''
        Clears a single digital output bit to 0.

        Input:
            device_number - the NI device number for the device
            bit_number - the bit number of the NI device

        Returns:
            An integer that indicates whether the bit was cleared or not
        '''
        self.device_number = c_uint(device_number)
        self.bit_number = c_uint(bit_number)
        return self.plexdoclient_dll.DOClearBit(self.device_number, self.bit_number)

    def pulse_bit(self, device_number, bit_number, duration):
        '''
        Pulses a single bit from low to high (0 to 1) for approximately the specified duration (in milliseconds).
        The pulse will be at least as long as specified, but the exact length and the variance of the length will
        depend on Windows system activity. If duration is 0, the bit is pulsed for as short a time as possible; this
        time will depend on system activity and the speed of the system processor.

        Input:
            device_number - the NI device number for the device
            bit_number - the bit number of the NI device
            duration - the specified duration of the pulse

        Returns:
            an integer that indicates whether the pulse was successful or not
        '''
        self.device_number = c_uint(device_number)
        self.bit_number = c_uint(bit_number)
        self.duration = c_uint(duration)
        return self.plexdoclient_dll.DOPulseBit(self.device_number, self.bit_number, self.duration)

    def set_word(self, device_number, lowbit_number, highbit_number, value):
        '''
        Sets a contiguous range of digital output bits to the specified value. Only the lowest (highbit_number -
        lowbit_number + 1) bits of value are used. The specified bits are set sequentially as quickly as possible.

        Input:
            device_number - the NI device number for the device
            lowbit_number - the lowest bit number
            highbit_number - the highest bit number
            value - value the bits will be set to

        Returns:
            an integer that indicates whether the word was set
        '''
        self.device_number = c_uint(device_number)
        self.lowbit_number = c_uint(lowbit_number)
        self.highbit_number = c_uint(highbit_number)
        self.value = c_uint(value)
        return self.plexdoclient_dll.DOSetWord(self.device_number, self.lowbit_number, self.highbit_number, self.value)

    def set_line_mode(self, device_number, line_number, mode):
        '''
        Defines whether an output line is to be used for clock generation or pulse generation.  mode is either
        PULSE_GEN or CLOCK_GEN. The default mode for all lines is PULSE_GEN.  line_number is 1-based: line 1
        corresponds to GPCTR_0 on E series NI devices.

        Input:
            device_number - the NI device number for the device
            line_number - the number corresponding to the line for the device
            mode - Either PULSE_GEN or CLOCK_GEN

        Returns:
            an integer that indicates whether the line mode has been set
        '''
        self.device_number = c_uint(device_number)
        self.line_number = c_uint(line_number)
        self.mode = c_uint(mode)
        return self.plexdoclient_dll.DOSetLineMode(self.device_number, self.line_number, self.mode)

    def set_pulse_duration(self, device_number, line_number, pulse_duration):
        '''
        When set_line_mode() is used to set a line to pulse generation mode, this function should be called before
        calling output_pulse() on that line; otherwise, a default 1 msec pulse will be output. pulse_duration is
        the length of the pulse in microseconds. The line must have been set to pulse generation mode by a previous
        call to set_line_mode().

        Input:
            device_number - the NI device number for the device
            line_number - the number corresponding to the line for the deivce
            pulse_duration - the length of the pulse in microseconds

        Returns:
            an integer indicating success or failure
        '''
        self.device_number = c_uint(device_number)
        self.line_number = c_uint(line_number)
        self.pulse_duration = c_uint(pulse_duration)
        return self.plexdoclient_dll.DOSetPulseDuration(self.device_number, self.line_number, self.pulse_duration)

    def output_pulse(self, device_number, line_number):
        '''
        Outputs a single pulse on the specified line.  Duration is as specified by a previous call to
        set_pulse_duration(). If set_pulse_duration() has not been called previously, a default pulse width of 1
        msec is used.

        Input:
            device_number - the NI device number for the device
            line_number - the number corresponding to the line for the device

        Returns:
            an integer indicating success or failure
        '''
        self.device_number = c_uint(device_number)
        self.line_number = c_uint(line_number)
        return self.plexdoclient_dll.DOOutputPulse(self.device_number, self.line_number)

    def set_clock_params(self, device_number, line_number, microsecs_high, microsecs_low):
        '''
        Specifies a clock output signal in terms of the length of the high and low times of a single clock cycle.
        Minimum value is 1 microsecond for both high and low times (i.e. clock frequency of 500 kHz), maximum value
        is 0.5 second (1 Hz). Note that this clock is free-running with respect to the MAP clock.

        Input:
            device_number - the NI device number for the device
            line number - the number corresponding to the line for the device
            microsecs_high - length of high times of a single clock cycle
            microsecs_low - length of the low times of a single clock cycle

        Returns:
            an integer indicating success or failure
        '''
        self.device_number = c_uint(device_number)
        self.line_number = c_uint(line_number)
        self.microsecs_high = c_uint(microsecs_high)
        self.microsecs_low = c_uint(microsecs_low)
        return self.plexdoclient_dll.DOSetClockParams(self.device_number, self.line_number, self.microsecs_high,
                                                      self.microsecs_low)

    def start_clock(self, device_number, line_number):
        '''
        Starts the clock output on the specified line. Frequency and duty cycle are as specified by a
        previous call to set_clock_params(). If set_clock_params() has not been called previously, a default clock
        with frequency = 1 kHz and duty cycle = 50% is output.

        Input:
            device_number - the NI device number for the device
            line_number - the number corresponding to the line for the device

        Returns:
            an integer indicating success or failure
        '''
        self.device_number = c_uint(device_number)
        self.line_number = c_uint(line_number)
        return self.plexdoclient_dll.DOStartClock(self.device_number, self.line_number)

    def stop_clock(self, device_number, line_number):
        '''
        Stops the clock output on the specified line. See start_clock()

        Input:
            device_number - the NI device number for the device
            line_number - the number corresponding to the line for the device

        Returns:
            an integer indicating success or failure
        '''
        self.device_number = c_uint(device_number)
        self.line_number = c_uint(line_number)
        return self.plexdoclient_dll.DOStopClock(self.device_number, self.line_number)

    def sleep(self, millisecs):
        '''
        Sleeps for the specified time (in milliseconds) before returning. Better timing accuracy than the Win32
        Sleep() function, but note that accuracy can vary, depending on system activity.  For precision pulse
        output, a digital output line and the functions set_pulse_duration() and output_pulse() should be used,
        rather than timing individual pulses using do_sleep.

        Input:
            millisecs - the length of time the device will be put to sleep

        Returns:
            an integer indicating success or failure
        '''
        self.millisecs = c_uint(millisecs)
        return self.plexdoclient_dll.DOSleep(millisecs)
