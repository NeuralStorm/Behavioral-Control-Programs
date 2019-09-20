# Plexon Testing Cineplex Events
from definitions import *

class CineTest():
    def __init__(self, *args, **kwargs):
        ##Setup Plexon Server
        # Initialize the API class
        self.client = PyOPXClientAPI()
        # Connect to OmniPlex Server, check for success
        self.client.connect()
        if not self.client.connected:
            print("Client isn't connected, exiting.\n")
            print("Error code: {}\n".format(self.client.last_result))
            self.readyforplexon = False
            
        print("Connected to OmniPlex Server\n")
        # Get global parameters
        global_parameters = self.client.get_global_parameters()

        for source_id in global_parameters.source_ids:
            source_name, _, _, _ = self.client.get_source_info(source_id)
            if source_name == 'KBD':
                self.keyboard_event_source = source_id
            if source_name == 'AI':
                self.ai_source = source_id
        # Print information on each source

        ##### Need to include information here about getting Digital signals ############
        for index in range(global_parameters.num_sources):
            # Get general information on the source
            source_name, source_type, num_chans, linear_start_chan = self.client.get_source_info(global_parameters.source_ids[index])
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
                _, rate, voltage_scaler = self.client.get_cont_source_info(source_name)     
                # Store information about the source rate and voltage scaler for later use.
                source_numbers_rates[global_parameters.source_ids[index]] = rate
                source_numbers_voltage_scalers[global_parameters.source_ids[index]] = voltage_scaler
                print("Digitization Rate: {}, Voltage Scaler: {}".format(rate, voltage_scaler))
                
        ##Setup for Plexon DO
        compatible_devices = ['PXI-6224', 'PXI-6259']
        self.plexdo = PyPlexDO()
        doinfo = self.plexdo.get_digital_output_info()
        self.device_number = 1
        for k in range(doinfo.num_devices):
            if self.plexdo.get_device_string(doinfo.device_numbers[k]) in compatible_devices:
                device_number = doinfo.device_numbers[k]
        if device_number == None:
            print("No compatible devices found. Exiting.")
            sys.exit(1)
        else:
            print("{} found as device {}".format(self.plexdo.get_device_string(device_number), device_number))
        res = self.plexdo.init_device(device_number)
        if res != 0:
            print("Couldn't initialize device. Exiting.")
            sys.exit(1)
        self.plexdo.clear_all_bits(device_number)
        ##End Setup for Plexon DO

        self.Pedal = 0
        self.Pedal1 = 0 #Push / Forward
        self.Pedal2 = 0 #Right
        self.Pedal3 = 0 #Pull / Backwards
        self.Pedal4 = 0 #Left
        self.Area1_right = 5
        self.Area2_right = 6
        self.Area1_left = 7
        self.Area2_left = 8
        self.Area1_right_pres = False
        self.Area2_right_pres = False
        self.Area1_left_pres = False
        self.Area2_left_pres = False        
        
    def gathering_data_omni(self):
        new_data = self.client.get_new_data()
        if new_data.num_data_blocks < max_block_output:
            num_blocks_to_output = new_data.num_data_blocks
        else:
            num_blocks_to_output = max_block_output
        # If a keyboard event is in the returned data, perform action
        for i in range(new_data.num_data_blocks):
            try:
                if new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 1: #Alt 1
                    pass
                elif new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 2: #Alt 2
                    pass
                elif new_data.source_num_or_type[i] == self.keyboard_event_source and new_data.channel[i] == 8: #Alt 8
                    pass
            #For other new data find the AI channel 1 data for pedal
                if (source_numbers_types[new_data.source_num_or_type[i]] == 
                    CONTINUOUS_TYPE and (new_data.channel[i] == 1 or 
                                         new_data.channel[i] == 2 or 
                                         new_data.channel[i] == 3 or 
                                         new_data.channel[i] == 4 or 
                                         new_data.channel[i] == self.Area1_right or 
                                         new_data.channel[i] == self.Area2_right or 
                                         new_data.channel[i] == self.Area1_left or 
                                         new_data.channel[i] == self.Area2_left)):
                    # Output info
                    tmp_source_number = new_data.source_num_or_type[i]
                    tmp_channel = new_data.channel[i]
                    tmp_source_name = source_numbers_names[tmp_source_number]
                    tmp_voltage_scaler = source_numbers_voltage_scalers[tmp_source_number]
                    tmp_timestamp = new_data.timestamp[i]
                    tmp_unit = new_data.unit[i]
                    tmp_rate = source_numbers_rates[tmp_source_number]

                    # Convert the samples from AD units to voltage using the voltage scaler, use tmp_samples[0] because it could be a list. Should be fine.
                    tmp_samples = new_data.waveform[i][:max_samples_output]
                    tmp_samples = [s * tmp_voltage_scaler for s in tmp_samples]
                    if new_data.channel[i] == 1:
                        self.Pedal1 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal1)
                    elif new_data.channel[i] == 2:
                        self.Pedal2 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal2)
                    elif new_data.channel[i] == 3:
                        self.Pedal3 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal3)
                    elif new_data.channel[i] == 4:
                        self.Pedal4 = tmp_samples[0] # Assign Pedal from AI continuous
                        # Construct a string with the samples for convenience
                        tmp_samples_str = float(self.Pedal4)


                    #################################################################
                    elif new_data.channel[i] == (self.Area1_right):
                        if tmp_samples[0] >= 1:
                            if self.Area1_right_pres == False and tmp_samples[0] >= 1:
                                print('Area1_right_pres set to True')
                            self.Area1_right_pres = True
                        else:
                            if self.Area1_right_pres == True and tmp_samples[0] <= 1:
                                print('Area1_right_pres set to False')
                            self.Area1_right_pres = False
                            
                    elif new_data.channel[i] == (self.Area1_left):
                        if tmp_samples[0] >= 1:
                            if self.Area1_left_pres == False and tmp_samples[0] >= 1:
                                print('Area1_left_pres set to True')
                            self.Area1_left_pres = True
                        else:
                            if self.Area1_left_pres == True and tmp_samples[0] <= 1:
                                print('Area1_left_pres set to False')
                            self.Area1_left_pres = False

                    elif new_data.channel[i] == (self.Area2_right):
                        if tmp_samples[0] >= 1:
                            if self.Area2_right_pres == False and tmp_samples[0] >= 1:
                                print('Area2_right_pres set to True')
                            self.Area2_right_pres = True
                        else:
                            if self.Area2_right_pres == True and tmp_samples[0] <= 1:
                                print('Area2_right_pres set to False')
                            self.Area2_right_pres = False
                            
                    elif new_data.channel[i] == (self.Area2_left):
                        if tmp_samples[0] >= 1:
                            if self.Area2_left_pres == False and tmp_samples[0] >= 1:
                                print('Area2_left_pres set to True')
                            self.Area2_left_pres = True
                        else:
                            if self.Area2_left_pres == True and tmp_samples[0] <= 1:
                                print('Area2_left_pres set to False')
                            self.Area2_left_pres = False
                            
                    #print(self.Area2)
                    #print(self.Area1)
                    #time.sleep(0.1)
                    #print values that we want from AI
                    #if new_data.channel[i] == 1:
                        #print("SRC:{} {} TS:{} CH:{} WF:{}".format(tmp_source_number, tmp_source_name, tmp_timestamp, tmp_channel, tmp_samples_str))
                # This is for 2 events that come from Cineplex, might have to change channels depending on physical connections.
                # Waiting for Ryan to see if these should be event type or continuous

                    
            except KeyError:
                continue
    #end of gathering data

if __name__ == "__main__":
    Test = CineTest()
    while True:
        Test.gathering_data_omni()
