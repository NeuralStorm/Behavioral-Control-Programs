# __init__.py - Module setup for PyOPXClient
#
# (c) 2019 Plexon, Inc., Dallas, Texas
# www.plexon.com
#
# This software is provided as-is, without any warranty.
# You are free to modify or share this file, provided that the above
# copyright notice is kept intact.

#__init__.py serves three purposes:
#   1) Let's Python know that the .py files in this directory are importable modules.
#   2) Sets up classes and functions in the pyopxclientlib and pyopxclientapi modules to be easy to
#      access. For example, without importing the opx_connect function from pyopxclientapi in
#      __init__.py, you would have to import pyopxclient in your script like this:
#           from PyOPXClient.pyopxclientapi import opx_connect
#      instead of like this:
#           from PyOPXClient import opx_connect
#      It's a minor convenience, but improves readability.
#   3) Explicitly states which classes and functions in pyopxclient are meant to be public
#      parts of the API.

from .pyopxclientlib import PyOPXClient, OPX_GlobalParams, OPX_DataBlock, OPX_FilterInfo
from .pyopxclientlib import SPIKE_TYPE, EVENT_TYPE, CONTINUOUS_TYPE, OTHER_TYPE
from .pyopxclientlib import MAX_WF_LENGTH
from .pyopxclientlib import OPXSYSTEM_INVALID, OPXSYSTEM_TESTADC, OPXSYSTEM_AD64, OPXSYSTEM_DIGIAMP, OPXSYSTEM_DHSDIGIAMP
from .pyopxclientlib import OPX_DAQ_STOPPED, OPX_DAQ_STARTED, OPX_RECORDING, OPX_RECORDING_PAUSED
from .pyopxclientlib import OPX_ERROR_NOERROR, OPX_ERROR_NODATAPOOL1, OPX_ERROR_NODATAPOOL2, OPX_ERROR_NOMEM, OPX_ERROR_BADCHANTYPE, OPX_ERROR_BADSOURCENUM
from .pyopxclientlib import OPX_ERROR_BADDATAFORMAT, OPX_ERROR_NULLPARAMETER, OPX_ERROR_MAPPINGFAILED, OPX_INIT_FAILED, OPX_ERROR_NOWAITHANDLE, OPX_ERROR_TIMEOUT
from .pyopxclientlib import OPX_ERROR_NOTCLEARED, OPX_ERROR_NOT_ALL_DATA_WAS_RETURNED, OPX_ERROR_BUFFER_ALLOC_FAILED, OPX_ERROR_OPEN_DLL_FAILED, OPX_ERROR_UNKNOWN

from .pyopxclientapi import PyOPXClientAPI

__author__ = ['Chris Heydrick (chris@plexon.com)', 'Jennifer Mickel (jennifera@plexon.com)']

__version__ = '1.3.0'
# 5/30/2019 CLH
# Version 1.2.0 exclusively functions with Python 3.
# 8/8/2019 CLH
# Gridmon and Strobe Monitor GUI examples added.