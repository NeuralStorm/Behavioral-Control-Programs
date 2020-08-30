# example2.py
# Demonstrates how to connect to OmniPlex Server and repeatedly get 
# event data. The loop uses Keyboard Event 8 as a trigger to stop
# collecting data and exit.
#
# (c) 2018 Plexon, Inc., Dallas, Texas
# www.plexon.com - support@plexon.com

from pyplexclientts import PyPlexClientTSAPI, PL_ExtEventType
import time

if __name__ == '__main__':
    # Create instance of API class
    client = PyPlexClientTSAPI()

    # Connect to OmniPlex Server
    client.init_client()

    running = True

    # It's best to pause briefly after initializing the client
    time.sleep(1)

    while(running):
        # Get accumulated timestamps
        res = client.get_ts()
        
        # Print information on acquired events
        for t in res:
            if t.Type == PL_ExtEventType:
                print(('Ts: {}s Channel: {}').format(t.TimeStamp, t.Channel))
                
                # If Keyoard Event 8 is detected, stop the client
                if t.Channel == 108:
                    running = False
        
        # Pause briefly to let more data accumulate
        time.sleep(.25)
    
    # Close the connection
    client.close_client()