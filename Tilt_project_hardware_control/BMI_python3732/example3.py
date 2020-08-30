# example3.py
# Demonstrates how to connect to OmniPlex Server and get data 
# continuously until a condition is met.
#
# Information on spike channel 1 and all events will be
# printed to the console until Keyboard Event 8 is detected.
#
# (c) 2018 Plexon, Inc., Dallas, Texas
# www.plexon.com - support@plexon.com

from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType, PL_ExtEventType
import time

if __name__ == '__main__':
    # Create instance of API class
    client = PyPlexClientTSAPI()

    # Connect to OmniPlex Server
    client.init_client()

    running = True

    while running:
        # Wait half a second for data to accumulate
        time.sleep(.5)

        # Get accumulated timestamps
        res = client.get_ts()

        # Print information on the data returned
        for t in res:
            # Print information on spike channel 1
            if t.Type == PL_SingleWFType and t.Channel == 1:
                print(('Spike Ts: {}s\t Ch: {} Unit: {}').format(t.TimeStamp, t.Channel, t.Unit))

            # Print information on events
            if t.Type == PL_ExtEventType:
                print(('Event Ts: {}s Ch: {}').format(t.TimeStamp, t.Channel))

                # If Keyboard Event 8 (event channel 108) is found, stop the loop
                if t.Channel == 108:
                    running = False

    client.close_client()