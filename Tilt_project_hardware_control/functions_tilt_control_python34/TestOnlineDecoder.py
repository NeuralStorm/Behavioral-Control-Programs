#Test Online Decoder Set up
from definitions import *

### TODO 


class PSTH: ###Initiate PSTH with desired parameters, creates unit_dict which has wanted units and will catch timestamps from plexon.
    def __init__(self, channel_dict, pre_time_start, pre_time_end, post_time_start, post_time_end, pre_total_bins, post_total_bins):
        self.pre_time = pre_time
        self.post_time = post_time 
        self.total_bins = total_bins
        self.channel_dict = channel_dict
        self.unit_dict = {}
        for chan, unit_list in self.channel_dict.items():
            print('chan {}'.format(chan))
            if chan not in self.unit_dict.keys():
                self.unit_dict[chan] = {}
            for unit in unit_list:
                self.unit_dict[chan][unit] = []
    ###### build_unit will be used to gather timestamps from plexon and add them to the unit_dict which will be used to compare psth formats, etc.
    def build_unit(self, tmp_channel, tmp_unit, tmp_timestamp):
        self.unit_dict[tmp_channel][tmp_unit].append(tmp_timestamp)
    

    
    ##### Creates PSTH for the event
    def psth(self, data, total_units, total_bins, pre_time, post_time):
        unit_event_response = dict()
        pop_event_response = dict()
        total_unit_length = total_units * total_bins
        start_indeces = [start for start in range(0, total_unit_length, total_bins)]
        end_indeces = [end + total_bins for end in start_indeces]
        unit_ranges = list(zip(start_indeces, end_indeces))
        for event in data['events']:
            event_trials = len(data['events'][event])
            population_response = numpy.empty(shape=(event_trials, (total_units * total_bins)))
            unit_event_response[event] = dict()
            for unit_index, unit in enumerate(data['neurons']):
                unit_start = unit_ranges[unit_index][0]
                unit_end = unit_ranges[unit_index][1]
                unit_ts = numpy.array(data['neurons'][unit])
                unit_response = numpy.empty(shape=(event_trials, total_bins))
                # Create relative response from population on given trial
                # Relative response dimensions:
                # unit: Trials x total bins population: Trials x (units * total bins)
                for trial_index, trial_ts in enumerate(data['events'][event]):
                    trial_ts = float(trial_ts)
                    offset_ts = unit_ts - trial_ts
                    binned_response = numpy.histogram(offset_ts, total_bins, 
                        range = (-abs(pre_time), post_time))[0]
                    unit_response[trial_index] = binned_response
                    population_response[trial_index, unit_start:unit_end] = binned_response
                unit_event_response[event][unit] = unit_response
            pop_event_response[event] = population_response
        return (pop_event_response, unit_event_response)
    
    def KBDTest(self):
        print(self.unit_dict)




def run():
    # Initialize the API class
    client = PyOPXClientAPI()
    running = True

    # Connect to OmniPlex Server, check for success
    client.connect()
    if not client.connected:
        print("Client isn't connected, exiting.\n")
        print("Error code: {}\n".format(client.last_result))
        exit()

    print("Connected to OmniPlex Server\n")

    # Get global parameters
    global_parameters = client.get_global_parameters()

    #
    for source_id in global_parameters.source_ids:
        source_name, _, _, _ = client.get_source_info(source_id)
        if source_name == 'KBD': #Do something KBD
            keyboard_event_source = source_id
            


    # Print information on each source
    for index in range(global_parameters.num_sources):
        # Get general information on the source
        source_name, source_type, num_chans, linear_start_chan = client.get_source_info(global_parameters.source_ids[index])

        # Store information about the source types and names for later use.
        source_numbers_types[global_parameters.source_ids[index]] = source_type
        source_numbers_names[global_parameters.source_ids[index]] = source_name
        
        print("----- Source {} -----".format(global_parameters.source_ids[index]))
        print("Name: {}, Type: {}, Channels: {}, Linear Start Channel: {}".format(source_name,
                                                                            source_types[source_type],
                                                                            num_chans,
                                                                            linear_start_chan))
        if source_type == SPIKE_TYPE:
            # Get information specific to a spike source
            _, rate, voltage_scaler, trodality, pts_per_waveform, pre_thresh_pts = client.get_spike_source_info(source_name)
            
            # Store information about the source rate and voltage scaler for later use.
            source_numbers_rates[global_parameters.source_ids[index]] = rate
            source_numbers_voltage_scalers[global_parameters.source_ids[index]] = voltage_scaler

            print("Digitization Rate: {}, Voltage Scaler: {}, Trodality: {}, Points Per Waveform: {}, Pre-Threshold Points: {}".format(rate,
                                                                                                                                        voltage_scaler,
                                                                                                                                        trodality,
                                                                                                                                        pts_per_waveform,
                                                                                                                                        pre_thresh_pts))

        if source_type == CONTINUOUS_TYPE:
            # Get information specific to a continuous source
            _, rate, voltage_scaler = client.get_cont_source_info(source_name)
            
            # Store information about the source rate and voltage scaler for later use.
            source_numbers_rates[global_parameters.source_ids[index]] = rate
            source_numbers_voltage_scalers[global_parameters.source_ids[index]] = voltage_scaler

            print("Digitization Rate: {}, Voltage Scaler: {}".format(rate, voltage_scaler))

        print("\n")

    print("After starting, use CTRL-C or any OmniPlex keyboard event to quit...")
    input("\nPress Enter to start reading data...\n")

    running = True
 #################################################################
    try:
        while running == True:
            # Wait up to 1 second for new data to come in   //// Will Be Changed to deal with
            client.opx_wait(1000)

            # Get a new batch of client data, timestamps only (no waveform or A/D data)
            new_data = client.get_new_data()

            # Handle the unlikely case that there are fewer blocks returned than we want to output
            if new_data.num_data_blocks < max_block_output:
                num_blocks_to_output = new_data.num_data_blocks
            else:
                num_blocks_to_output = max_block_output

            # If a keyboard event is in the returned data
            for i in range(new_data.num_data_blocks):
                if new_data.source_num_or_type[i] == keyboard_event_source:
                        psthtest.KBDTest()
                        running = False

####################################################################

            #print("{} blocks read. Displaying info on first {} blocks; first {} samples of continuous/spike data.".format(new_data.num_data_blocks, num_blocks_to_output, max_samples_output))

            for i in range(num_blocks_to_output):
                # Output info
                tmp_source_number = new_data.source_num_or_type[i]                      #Ignore                              Just need to check that they are all Spike Data / Timestamps with an IF 
                tmp_channel = new_data.channel[i]                                       #IMPORTANT- Will Need this Channel
                tmp_source_name = source_numbers_names[tmp_source_number]               #Ignore
                tmp_voltage_scaler = source_numbers_voltage_scalers[tmp_source_number]  #Ignore
                tmp_timestamp = new_data.timestamp[i]                                   #IMPORTANT- This is the Timestamp Data that will be saved to the struct / class.
                tmp_unit = new_data.unit[i]                                             #IMPORTANT- Unit of the Channel
                tmp_rate = source_numbers_rates[tmp_source_number]                      #Ignore

                # Convert the samples from AD units to voltage using the voltage scaler
                tmp_samples = new_data.waveform[i][:max_samples_output]
                tmp_samples = [s * tmp_voltage_scaler for s in tmp_samples]
                # Construct a string with the samples for convenience
                tmp_samples_str = '{} ' * len(tmp_samples)
                tmp_samples_str = tmp_samples_str.format(*tmp_samples)
                if tmp_channel in channel_dict and tmp_unit in channel_dict[tmp_channel] and source_numbers_types[new_data.source_num_or_type[i]] == SPIKE_TYPE:
                    psthtest.build_unit(tmp_channel, tmp_unit, tmp_timestamp)
                    print("SRC:{} {} RATE:{} TS:{} CH:{} Unit:{} TS:{}".format(tmp_source_number, tmp_source_name, tmp_rate, tmp_timestamp, tmp_channel, tmp_unit, tmp_timestamp))
                    #

                    #if source_numbers_types[new_data.source_num_or_type[i]] == CONTINUOUS_TYPE:
                    #   print("SRC:{} {} RATE:{} TS:{} CH:{} WF:{}".format(tmp_source_number, tmp_source_name, tmp_rate, tmp_timestamp, tmp_channel, tmp_samples_str))

                if source_numbers_types[new_data.source_num_or_type[i]] == EVENT_TYPE and tmp_channel ==1: #Restrict this to Events that we want timestamps for in the code (EX:Event 1 good press)
                        print("SRC:{} {} TS:{} CH:{}".format(tmp_source_number, tmp_source_name, tmp_timestamp, tmp_channel))

                ###CLASS HERE ###


            # Pause execution, allowing time for more data to accumulate in OmniPlex Server
            time.sleep(poll_time_s)

    except KeyboardInterrupt:
        print("\nCTRL-C detected; stopping acquisition.")

    # Disconnect from OmniPlex Server
    client.disconnect()
################################################################
if __name__ == '__main__':
    ##Setup Plexon Server
    # Initialize the API class
    client = PyOPXClientAPI()
    # Connect to OmniPlex Server, check for success
    client.connect()
    if not client.connected:
        print("Client isn't connected, exiting.\n")
        print("Error code: {}\n".format(client.last_result))
        exit()
    print("Connected to OmniPlex Server\n")
    # Get global parameters
    global_parameters = client.get_global_parameters()
    # For this example, we'll treat DO channel 8 as if it's connected
    # to the OmniPlex strobe input
    strobe_channel = 9
    for source_id in global_parameters.source_ids:
        source_name, _, _, _ = client.get_source_info(source_id)
        if source_name == 'KBD':
            keyboard_event_source = source_id
        if source_name == 'AI':
            ai_source = source_id
    # Print information on each source
    for index in range(global_parameters.num_sources):
        # Get general information on the source
        source_name, source_type, num_chans, linear_start_chan = client.get_source_info(global_parameters.source_ids[index])
        # Store information about the source types and names for later use.
        source_numbers_types[global_parameters.source_ids[index]] = source_type
        source_numbers_names[global_parameters.source_ids[index]] = source_name
        if source_name == 'AI':
            print("----- Source {} -----".format(global_parameters.source_ids[index]))
            print("Name: {}, Type: {}, Channels: {}, Linear Start Channel: {}".format(source_name,
                                                                            source_types[source_type],
                                                                            num_chans,
                                                                            linear_start_chan))
        if source_type == CONTINUOUS_TYPE and source_name == 'AI':
            # Get information specific to a continuous source
            _, rate, voltage_scaler = client.get_cont_source_info(source_name)     
            # Store information about the source rate and voltage scaler for later use.
            source_numbers_rates[global_parameters.source_ids[index]] = rate
            source_numbers_voltage_scalers[global_parameters.source_ids[index]] = voltage_scaler
            print("Digitization Rate: {}, Voltage Scaler: {}".format(rate, voltage_scaler))   
    ##Setup for Plexon DO
    compatible_devices = ['PXI-6224', 'PXI-6259']
    plexdo = PyPlexDO()
    doinfo = plexdo.get_digital_output_info()
    device_number = None
    for i in range(doinfo.num_devices):
        if plexdo.get_device_string(doinfo.device_numbers[i]) in compatible_devices:
            device_number = doinfo.device_numbers[i]
    if device_number == None:
        print("No compatible devices found. Exiting.")
        sys.exit(1)
    else:
        print("{} found as device {}".format(plexdo.get_device_string(device_number), device_number))
    res = plexdo.init_device(device_number)
    if res != 0:
        print("Couldn't initialize device. Exiting.")
        sys.exit(1)
    plexdo.clear_all_bits(device_number)
    ##End Setup for Plexon DO
    ##Setup for Plexon Server
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
    max_block_output = 100

    # To avoid overwhelming the console output, set the maximum number of continuous
    # samples or waveform samples to output
    max_samples_output = 50

    channel_dict = {1: [0,1,2,3], 2: [0,1,2], 4:[0,1,2,3,4], 5: [0,1]} #New Format to compare Channel and Unit. 0 is unsorted

    pre_time_start = .200 #seconds (This value is negative or whatever you put, ex: put 0.200 for -200 ms)
    pre_time_end = 0 #seconds
    post_time_start = 0 #seconds
    post_time_end = .200 #seconds
    bin_size = 0.001 #seconds
    pre_total_bins = 200 #bins
    post_total_bins = 200 #bins

    
    # Poll time in seconds
    poll_time_s = .250
    psthtest = PSTH(channel_dict, pre_time, post_time, total_bins)
    print('run')
    ### Run Function
    run()

