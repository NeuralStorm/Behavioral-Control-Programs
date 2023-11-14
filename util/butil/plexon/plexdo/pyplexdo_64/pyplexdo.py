# PyPlexDO.py - Python wrapper for Plexon digital output API for controlling the digital
#               output functionality of "E" series NIDAQ cards
#
# (c) 2022 Plexon, Inc., Dallas, Texas
#  www.plexon.com
#
# This software is provided as-is, without any warranty.
# You are free to modify or share this file, provided that the above 
# copyright notice is kept intact.
#
# General notes:
#
# Unless otherwise noted, functions return 0 if successful, -1 if error. Typical errors
# are passing an out of range device number (must be in the range 1..16), bit number
# (1..n), or line number (1..n), or calling a function before
# plexdo_get_digital_output_info and plexdo_do_init_device have been called to
# initialize PlexDO and the desired NIDAQ device.
#
# In parameters to plexdo functions, bit and line numbers start at one. Bit and line
# numbers on Plexon breakout boxes also start at one. However, NI hardware and NI-
# supplied breakout boxes use zero-based numbering, so that plexdo output bit 1
# corresponds to NIDAQ digital output DIO0 and plexdo output line 1 corresponds to
# NIDAQ counter GPCTR_0.
#
# See the sample code PyPlexDOExample1.py for examples of how to use
# the functions defined in this API.

from pathlib import Path

from ctypes import *
from collections import namedtuple
from enum import Enum
_dll_path = Path(__file__).parent / 'plexdodll64.dll'
_dll = WinDLL(str(_dll_path))

# define line modes
class LINEMODE(Enum):
    PULSE_GEN = 0
    CLOCK_GEN = 1

# Initialization and query functions
def plexdo_get_digital_output_info():
    """
    Query function which returns info on available (and supported) digital NI
    output devices.

    Usage:
        info = plexdo_get_digital_output_info()

    Args:
        None

    Returns:
        info -- a namedtuple comprising the following elements:
            num_do_cards - the number of connected cards with DO capability
            device_numbers - a list of each card's device number
            number_of_digital_output_bits - a list of how many bits each card has
            number_of_digital_output_lines- a list of how many lines each card has
    """

    num_do_cards = c_int()
    device_numbers = (c_uint*16)()
    number_of_digital_output_bits = (c_uint*16)()
    number_of_digital_output_lines = (c_uint*16)()

    try:
        _dll.DOGetDigitalOutputInfo(device_numbers, number_of_digital_output_bits, number_of_digital_output_lines, byref(num_do_cards))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    num_do_cards = num_do_cards.value

    if num_do_cards != -1:
        device_numbers = list(device_numbers)[:num_do_cards]
        number_of_digital_output_bits = list(number_of_digital_output_bits)[:num_do_cards]
        number_of_digital_output_lines = list(number_of_digital_output_lines)[:num_do_cards]
    else:
        device_numbers = []
        number_of_digital_output_bits = []
        number_of_digital_output_lines = []

    digital_output_info = namedtuple("digital_output_info", ["num_do_cards", "device_numbers", "number_of_digital_output_bits", "number_of_digital_output_lines"])
    info = digital_output_info(num_do_cards=num_do_cards, device_numbers=device_numbers, number_of_digital_output_bits=number_of_digital_output_bits, number_of_digital_output_lines=number_of_digital_output_lines)
    return info


def plexdo_get_device_string(device_number: int):
    """
    Returns an identifying string for the given NI device number, 
    e.g. "PCI-6071E", or None (i.e., NoneType) if no 
    identifying string can be found.

    Usage:
        device_string = plexdo_get_device_string(device_number)
    
    Args:
        device_number - the relevant card's device number

    Returns:
        device_string - a string containing the device name
    """

    retval = c_int()
    device_string = (c_char*16)()

    try:
        _dll.DOGetDeviceString(c_uint(device_number), device_string, byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        

    if retval.value == 0:
        return device_string.value.decode("utf-8")
    else:
        return None

def plexdo_init_device(device_number: int, is_used_by_MAP: bool =False):
    """
    This function must be called before any digital output is 
    attempted on the specified device. All of the specified device's
    digital bits and lines will be set to 0.
    
    Usage:
        retval = plexdo_init_device(device_number, is_used_by_MAP)

    Args:
        device_number - the relevant card's device number
        is_used_by_MAP - this boolean indicates whether or not the MAP
                         is sharing the specified device, in which case 
                         output line 0 is not available for digital output.
                         Defaults to False (i.e., the default assumption
                         is that the MAP is NOT sharing this device)
    
    Returns:
        retval - 0 for successful initialization
                 nonzero value for failed initialization
    """
    retval = c_int()
    
    try:
        _dll.DOInitDevice(c_uint(device_number), c_uint(is_used_by_MAP), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
    
    return retval.value


def plexdo_release_devices():
    """
    This function closes connections to all devices.

    Usage:
        plexdo_release_devices()
    
    Args:
        None
    
    Returns:
        No output returned
    """

    try:
        _dll.DOReleaseDevices()
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)


# Digital output bit functions
def plexdo_clear_all_bits(device_number: int):
    """
    This function resets all digital output bits to 0 for the specified device. The
    bits are sequentially set to 0 as quickly as possible.

    Usage:
        retval = plexdo_clear_all_bits(device_number)
    
    Args:
        device_number - the relevant card's device number
    
    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOClearAllBits(c_uint(device_number), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)

    return retval.value


def plexdo_set_bit(device_number: int, bit_number: int):
    """
    This function sets a single digital output bit to 1.

    Usage:
        retval = plexdo_set_bit(device_number, bit_number)
    
    Args:
        device_number - the relevant card's device number
        bit_number - the bit to be set
                     Note: bit_numbers are 1-based; "Bit 1" corresponds to DIO0 on most NI devices.
    
    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOSetBit(c_uint(device_number), c_uint(bit_number), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)

    return retval.value


def plexdo_clear_bit(device_number: int, bit_number: int):
    """
    This function clears the specified digital output bit to 0.

    Usage:
        retval = plexdo_clear_bit(device_number, bit_number)
    
    Args:
        device_number - the relevant card's device number
        bit_number - the bit to be set
                     Note: bit_numbers are 1-based; "Bit 1" corresponds to DIO0 on most NI devices.
    
    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOClearBit(c_uint(device_number), c_uint(bit_number), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)

    return retval.value


def plexdo_pulse_bit(device_number: int, bit_number: int, duration: int):
    """
    This function pulses a single bit from LOW to HIGH (i.e., 0 to 1) for
    approximately the specified duration (in milliseconds). The pulse will
    be at least as long as specified, but the exact length and the variance 
    of the length will depend on Windows system activity. If the duration is
    0, the bit is pulsed for as short a time as possible; this time will depend
    on system activity and the speed of the system processor.

    Usage:
        retval = plexdo_pulse_bit(device_number, bit_number, duration)

    Args:
        device_number - the relevant card's device number
        bit_number - the bit to be set
                     Note: bit_numbers are 1-based; "Bit 1" corresponds to DIO0 on most NI devices.
        duration - the desired pulse duration in milliseconds

    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOPulseBit(c_uint(device_number), c_uint(bit_number), c_uint(duration), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
    
    return retval.value


def plexdo_set_word(device_number: int, low_bit_number: int, high_bit_number: int, value: int):
    """
    This function sets a contiguous range of digital output bits to the 
    specified value. Only the lowest number (high_bit_number - low_bit_number + 1)
    bits of value are used. The specified bits are set sequentially as quickly
    as possible.

    Usage:
        retval = plexdo_set_word(device_number, low_bit_number, high_bit_number, value)
    
    Args:
        device_number - the relevant card's device number
        low_bit_number - the lowest bit in the contiguous range
        high_bit_number - the highest bit in the contiguous range
        value - the value to which all bits in the contiguous 
                range are to be set

    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOSetWord(c_uint(device_number), c_uint(low_bit_number), c_uint(high_bit_number), c_uint(value), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)

    return retval.value


# Digital output line functions
def plexdo_set_line_mode(device_number: int, line_number: int, mode: LINEMODE):
    """
    This function specifies whether an output line is to be used for
    pulse generation or clock generation. These modes are defined in
    the LINEMODE enum included with this package:
        LINEMODE.PULSE_GEN = 0
        LINEMODE.CLOCK_GEN = 1
    Note: The default mode for all lines is PULSE_GEN.

    Usage:
        retval = plexdo_set_line_mode(device_number, line_number, mode)
    
    Args:
        device_number - the relevant card's device number
        line_number - the line number whose mode is to be set
                      Note: line_number is 1-based; "Line 1" corresponds to GPCTR_0 on E series NI devices.
        mode - the desired mode
             - pulse generation - LINEMODE.PULSE_GEN or 0
             - clock generation - LINEMODE.CLOCK_GEN or 1

    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOSetLineMode(c_uint(device_number), c_uint(line_number), c_uint(mode.value if isinstance(mode,LINEMODE) else mode), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)

    return retval.value


def plexdo_set_pulse_duration(device_number: int, line_number: int, pulse_duration: int):
    """
    This function should be called after plexdo_set_line_mode is 
    used to set a line to pulse generation mode, and before calling
    plexdo_output_pulse on that line. Otherwise, a default 1 msec pulse
    will be output. To reiterate, the line must have been set to pulse 
    generation mode by a previous call to plexdo_set_line_mode.

    Usage:
        retval = plexdo_set_pulse_duration(device_number, line_number, pulse_duration)
    
    Args:
        device_number - the relevant card's device number
        line_number - the line number whose pulse duration is to be set
        pulse_duration - the pulse duration in microseconds
    
    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOSetPulseDuration(c_uint(device_number), c_uint(line_number), c_uint(pulse_duration), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    return retval.value


def plexdo_output_pulse(device_number: int, line_number: int):
    """
    This function outputs a single pulse on the specified line. The
    duration is as specified by a previous call to plexdo_set_pulse_duration.
    If plexdo_set_pulse_duration has not been called previously, a default
    pulse width of 1 msec is used.

    Usage:
        retval = plexdo_output_pulse(device_number, line_number)

    Args:
        device_number - the relevant card's device number
        line_number - the line number from which a pulse is to be issued

    Returns:
        retval - 0 for success
                 non-0 for failure
    """

    retval = c_int()

    try:
        _dll.DOOutputPulse(c_uint(device_number), c_uint(line_number), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    return retval.value


def plexdo_set_clock_params(device_number: int, line_number: int, microsecs_high: int, microsecs_low: int):
    """
    This function specifies a clock output signal in terms of the length of 
    the HIGH and LOW times of a single clock cycle. The minimum value 
    permitted is 1 microsecond for both the HIGH time and the LOW time
    (i.e., corresponding to a clock frequency of 500 kHz). The maximum value
    permitted is 0.5 seconds (i.e., corresponding to a clock frequency of 
    1 Hz). Note that this clock is free-running with respect to the MAP clock.

    Usage:
        retval = plexdo_set_clock_params(device_number, line_number, microsecs_high, microsecs_low)
    
    Args:
        device_number - the relevant card's device number
        line_number - the line number for which clock parameters 
                                    are to be set
        microsecs_high - the duration (in microseconds) of the HIGH 
                                    phase of the clock output signal cycle
        microsecs_low - the duration (in microseconds) of the LOW 
                        phase of the clock output signal cycle

    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOSetClockParams(c_uint(device_number), c_uint(line_number), c_uint(microsecs_high), c_uint(microsecs_low), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    return retval.value


def plexdo_start_clock(device_number: int, line_number: int):
    """
    This function starts the clock output on the specified line. The 
    clock's frequency and duty cycle should have been specified in a 
    previous call to plexdo_set_clock_params. If plexdo_set_clock_params
    was not called previously, a default clock with frequency = 1 kHz
    and duty cycle = 50% is output.

    Usage:
        retval = plexdo_start_clock(device_number, line_number)
    
    Args:
        device_number - the relevant card's device number
        line_number - the line number for which the clock output is to be started

    Returns:
        retval - 0 for success
                                    non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOStartClock(c_uint(device_number), c_uint(line_number), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    return retval.value


def plexdo_stop_clock(device_number: int, line_number: int):
    """
    This function stops the clock output on the specified line.

    Usage:
        retval = plexdo_stop_clock(device_number, line_number)
    
    Args:
        device_number - the relevant card's device number
        line_number - the line number for which the clock output is to be stopped

    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOStopClock(c_uint(device_number), c_uint(line_number), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    return retval.value


# Utility functions
def plexdo_sleep(millisecs: int):
    """
    This function sleeps for the specified time before returning. 
    It provides better timing accuracy than Win32's Sleep() function, 
    but it should be noted that the accuracy can vary depending on system
    activity. For precision pulse output, a digital output line and the 
    functions plexdo_set_pulse_duration and plexdo_output_pulse should be used
    rather than timing individual pulses with plexdo_sleep.

    Usage:
        retval = plexdo_sleep(millisecs)

    Args:
        millisecs - duration in milliseconds

    Returns:
        retval - 0 for success
                 non-0 for failure
    """
    retval = c_int()

    try:
        _dll.DOSleep(c_uint(millisecs), byref(retval))
    except:
        error_message = "Something went wrong calling functions in plexdodll64.dll."
        print(error_message)
        
    return retval.value