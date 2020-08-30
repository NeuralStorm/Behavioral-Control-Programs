# example1.py
# Demonstrates how to connect to OmniPlex Server and get data once.
#
# (c) 2018 Plexon, Inc., Dallas, Texas
# www.plexon.com - support@plexon.com

from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType
import time

if __name__ == '__main__':
    # Create instance of API class
    client = PyPlexClientTSAPI()

    # Connect to OmniPlex Server
    client.init_client()

    # Wait half a second for data to accumulate
    time.sleep(.5)

    # Get accumulated timestamps
    res = client.get_ts()

    # Print information on every gathered spike timestamp
    for t in res:
        if t.Type == PL_SingleWFType:
            print(('Ts: {}s Ch: {} Unit: {}').format(t.TimeStamp, t.Channel, t.Unit))
    
    # Close the connection
    client.close_client()