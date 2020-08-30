PyPlexClientTS is a minimal Python wrapper for the Plexon C Client API. It only implements the functions in PlexClient.dll that connect to OmniPlex Server, collect spike and event timestamp data, and closes the connection to OmniPlex Server.

This API is made for Python 3.7.

pyplexclientts.py contains three classes. pyplexclienttslib is the class that directly implements some functions in PlexClient.dll using the ctypes module. pyplexclienttsapi is an API class that should be used to acquire the spike and event data.  The PLEvent class wraps a structure in plexon.h that is used by pyplexclienttslib.

Every client application should follow the same basic structure.

1) Connect to OmniPlex Server
2) Acquire data
3) Close the connection to OmniPlex Server

OmniPlex Server only holds a limited amount of data in a buffer that it makes available to clients. When this buffer fills up, the old data starts getting overwritten. When a client requests data, OmniPlex Server delivers all of the data that has been collected since the last time the client requested data (or when the client connected). The client should request data often enough to avoid missing data that was overwritten in the OmniPlex client buffer.

Here are some more tips and good practices:
- Pause execution for half a second after calling init_client(). Calling get_ts() too soon after init_client() causes problems. This is demonstrated in the example programs.

For example:

>> client = PyPlexClientTSAPI()
>> time.sleep(.5)
>> res = client.get_ts()

- Pause execution in between calls to get_ts(). Requesting new data too quickly causes problems. This is demonstrated in the example programs.

- In the PyPlexClientTSAPI class there is a variable called max_opx_server_events that is by default initialized to 100000. This number represents the maximum number of spike and event timestamps that OmniPlex Server will transfer to a client at one time. On a high channel count system (256+) this value might be too low, which will result in not all data being transferred to the client. If this is happening, increase this value during the class initialization. The only consequence is that the client will consume more memory.