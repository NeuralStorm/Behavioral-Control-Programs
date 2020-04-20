import numpy
import time
import random
import PyDAQmx
import tkinter as tk
from PyDAQmx import Task
from PyDAQmx.DAQmxFunctions import *
from PyDAQmx.DAQmxConstants import *
from pyplexdo import PyPlexDO, DODigitalOutputInfo
from pyopxclient import PyOPXClientAPI, OPX_ERROR_NOERROR, SPIKE_TYPE, CONTINUOUS_TYPE, EVENT_TYPE, OTHER_TYPE
from pyopxclient import OPXSYSTEM_INVALID, OPXSYSTEM_TESTADC, OPXSYSTEM_AD64, OPXSYSTEM_DIGIAMP, OPXSYSTEM_DHSDIGIAMP
import winsound
import threading
import math
import os
from PIL import Image, ImageTk
   
class MultiChannelAnalogInput():
    """Class to create a multi-channel analog input
    
    Usage: AI = MultiChannelInput(physicalChannel)
        physicalChannel: a string or a list of strings
    optional parameter: limit: tuple or list of tuples, the AI limit values
                        reset: Boolean
    Methods:
        read(name), return the value of the input name
        readAll(), return a dictionary  name:value
    """
    def __init__(self,physicalChannel, limit = None, reset = False):
        if type(physicalChannel) == type(""):
            self.physicalChannel = [physicalChannel]
        else:
            self.physicalChannel  =physicalChannel
        self.numberOfChannel = physicalChannel.__len__()
        if limit is None:
            self.limit = dict([(name, (-10.0,10.0)) for name in self.physicalChannel])
        elif type(limit) == tuple:
            self.limit = dict([(name, limit) for name in self.physicalChannel])
        else:
            self.limit = dict([(name, limit[i]) for  i,name in enumerate(self.physicalChannel)])           
        if reset:
            DAQmxResetDevice(physicalChannel[0].split('/')[0] )
    def configure(self):
        # Create one task handle per Channel
        taskHandles = dict([(name,TaskHandle(0)) for name in self.physicalChannel])
        for name in self.physicalChannel:
            DAQmxCreateTask("",byref(taskHandles[name]))
            DAQmxCreateAIVoltageChan(taskHandles[name],name,"",DAQmx_Val_Diff,
                                     self.limit[name][0],self.limit[name][1],
                                     DAQmx_Val_Volts,None)
        self.taskHandles = taskHandles
    def readAll(self):
        return dict([(name,self.read(name)) for name in self.physicalChannel])
    def read(self,name = None):
        if name is None:
            name = self.physicalChannel[0]
        taskHandle = self.taskHandles[name]                    
        DAQmxStartTask(taskHandle)
        data = numpy.zeros((1,), dtype=numpy.float64)
#        data = AI_data_type()
        read = int32()
        DAQmxReadAnalogF64(taskHandle,1,10.0,DAQmx_Val_GroupByChannel,data,1,byref(read),None)
        DAQmxStopTask(taskHandle)
        return data[0]

# Handy strings to have associated to their respective types
system_types = { OPXSYSTEM_INVALID: "Invalid System", OPXSYSTEM_TESTADC: "Test ADC", OPXSYSTEM_AD64: "OPX-A", OPXSYSTEM_DIGIAMP: "OPX-D", OPXSYSTEM_DHSDIGIAMP: "OPX-DHP" }
source_types = { SPIKE_TYPE: "Spike", EVENT_TYPE: "Event", CONTINUOUS_TYPE: "Continuous", OTHER_TYPE: "Other" }

# This will be filled in later. Better to store these once rather than have to call the functions
# to get this information on every returned data block
source_numbers_types = {}
source_numbers_names = {}
source_numbers_rates = {}
source_numbers_voltage_scalers = {}

# To avoid overwhelming the console output, set the maximum number of data
# blocks to print information about
max_block_output = 1

# To avoid overwhelming the console output, set the maximum number of continuous
# samples or waveform samples to output
max_samples_output = 1

# Poll time in seconds
poll_time_s = 0.250

def RewardClass(*args): #Duration is the input of how long the animal will press
    counter = 0
    Ranges = []
    if len(args)%2 == 1:
        input("Odd number of args. This might cause errors. Press Enter to continue")
    for arg in args:
        counter = counter + 1
        peak = math.trunc((counter + 1) / 2)
        if counter%2 == 1:
            print('This arg is a peak {} center: {}'.format(peak,arg))
            arg_center = arg
        else:
            print('This arg is a peak {} width: {}'.format(peak,arg))
            arg_width = arg
            low = arg_center - arg_width
            high = arg_center + arg_width
            print('The range for interval {} is {} to {}'.format(peak,low,high))
            Ranges.append(low)
            Ranges.append(arg_center)
            Ranges.append(high)
    return Ranges
