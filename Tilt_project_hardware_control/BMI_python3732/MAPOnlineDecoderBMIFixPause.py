#MAP System Online Decoder
#from pyplexdo import PyPlexDO, DODigitalOutputInfo
from pyplexclientts import PyPlexClientTSAPI, PL_SingleWFType, PL_ExtEventType
import time
import numpy
from decimal import Decimal
from collections import Counter
import json
import copy
#TODO: CSV for channels. Include post time window of event. Need to save population response (dict? key as event_count) from an event  so that they are all saved.
class PSTH: ###Initiate PSTH with desired parameters, creates unit_dict which has wanted units and will catch timestamps from plexon.
    def __init__(self, channel_dict, pre_time, post_time, bin_size):
        self.pre_time = pre_time
        self.post_time = post_time
        self.bin_size = bin_size
        self.total_bins = int((post_time) / bin_size)           # Post time bins, used by decoder
        self.channel_dict = copy.deepcopy(channel_dict)         # Current days channel dictionary, used to create template for the next day
        self.json_template_channel_dict = {}                    # Loaded Channel Dictionary, used by decoder
        self.total_channel_dict = copy.deepcopy(channel_dict)   # Copy of channel_dict, channels / units from loaded Channel Dict will be added to this.
                                                                # total_channel_dict is used to gather spikes from only neurons that we are interested in.
        self.unit_dict = {}                             # Dict of dicts, takes channels / units from channel_dict and creates a place to store timestamps.
        self.total_unit_dict = {}                       # Not currently used, similar to unit_dict, but uses the complete set of channels / units from current and decoder day.
        self.pop_total_response = {}                    # 
        self.json_template_pop_total_response = {}
        self.psth_templates = {}
        self.pop_current_response = []
        self.json_template_pop_current_response = []
        self.event_ts_list = []
        self.event_number_list = []
        self.decoder_list = []
        self.decoder_times = []
        self.total_units = 0
        self.json_template_unit_dict_nonints = {}
        self.json_template_unit_dict = {}
        self.json_template_total_units = 0
        self.event_count = 0
        self.current_ts = 0
        
        self.responses = 0 ### testing number of responses
        # print('channel_dict', self.channel_dict)
        for chan, unit_list in self.channel_dict.items():
            if chan not in self.unit_dict.keys():
                self.unit_dict[chan] = {}
            for unit in unit_list:
                self.unit_dict[chan][unit] = []
                self.total_units = self.total_units + 1

        self.unit_dict_template = copy.deepcopy(self.unit_dict)
        # print('unit_dict', self.unit_dict) 
    ###### build_unit will be used to gather timestamps from plexon and add them to the unit_dict which will be used to compare psth formats, etc.
    def build_unit(self, tmp_channel, tmp_unit, tmp_timestamp):
        if tmp_channel in self.channel_dict.keys() and tmp_unit in self.channel_dict[tmp_channel]:
            self.unit_dict[tmp_channel][tmp_unit].append(Decimal(tmp_timestamp).quantize(Decimal('1.0000')))
        if tmp_channel in self.json_template_channel_dict.keys() and tmp_unit in self.json_template_channel_dict[tmp_channel]:
            self.json_template_unit_dict[tmp_channel][tmp_unit].append(Decimal(tmp_timestamp).quantize(Decimal('1.0000')))

    def event(self, event_ts, event_unit):
        #Need to check that it's not a duplicate event...
        if (event_ts - self.current_ts) > 1:
            print('event def')
            self.event_count = self.event_count + 1                             #Total count of events (number of events that occurred)
            self.current_ts = event_ts                                          #Timestamp of the current event
            self.current_event = event_unit                                     #Event number of the current event
            self.event_ts_list.append(event_ts)                                 #List of timestamps
            self.event_number_list.append(event_unit)                           #List of event number
            return True
        else:
            return False


    def psth(self, json_template, baseline_recording):
        ### Create relative response from population on given trial
        ### Relative response dimensions:
        ### unit:total bins #population: units * total bins
        #OK to call unit_event_response here since we don't need to save it, data is saved to pop_event_response
        if json_template == True:
            pop_trial_response = []
            self.index = 0
            #self.population_response = numpy.zeros(shape=(1, (self.total_units * self.total_bins))) #Create a pop_response template to be filled by bins from neurons
            self.population_response = []
            for chan in self.unit_dict:
                for unit in self.unit_dict[chan]:
                    unit_ts = numpy.asarray(self.unit_dict[chan][unit], dtype = 'float')
                    trial_ts = self.current_ts
                    offset_ts = unit_ts - trial_ts
                    offset_ts = [Decimal(x).quantize(Decimal('1.0000')) for x in offset_ts]
                    self.binned_response = numpy.histogram(numpy.asarray(offset_ts, dtype='float'), self.total_bins, range = (0, self.post_time))[0]
                    self.population_response.extend(self.binned_response)
                    #self.population_response[(self.total_bins*self.index):(self.total_bins*(self.index+1))] = self.binned_response   #### These values will give the total bins (currently: 5) for each neuron (unit)
                    pop_trial_response = [x for x in self.population_response]
                    self.index = self.index + 1
                    if self.index == self.total_units:
                        if self.current_event not in self.pop_total_response.keys():
                            self.pop_total_response[self.current_event] = pop_trial_response
                        else:
                            self.pop_total_response[self.current_event].extend(pop_trial_response)
                        self.pop_current_response = pop_trial_response

            self.unit_dict = copy.deepcopy(self.unit_dict_template) #Reset unit_dict to save computational time later
        else: #Decoding psth
            json_pop_trial_response = []
            self.json_index = 0
            #self.json_population_response = numpy.zeros(shape=(1, (self.total_units * self.total_bins))) #Create a pop_response template to be filled by bins from neurons
            self.json_population_response = []
            for chan in self.json_template_unit_dict:
                for unit in self.json_template_unit_dict[chan]:
                    unit_ts = numpy.asarray(self.json_template_unit_dict[chan][unit], dtype = 'float')
                    trial_ts = self.current_ts
                    offset_ts = unit_ts - trial_ts
                    offset_ts = [Decimal(x).quantize(Decimal('1.0000')) for x in offset_ts]
                    self.json_template_binned_response = numpy.histogram(numpy.asarray(offset_ts, dtype='float'), self.total_bins, range = (0, self.post_time))[0]
                    self.json_population_response.extend(self.json_template_binned_response)
                    #self.json_population_response[(self.total_bins*self.json_index):(self.total_bins*(self.json_index+1))] = self.json_template_binned_response   #### These values will give the total bins (currently: 5) for each neuron (unit)
                    json_pop_trial_response = [x for x in self.json_population_response]
                    self.json_index = self.json_index + 1
                    if self.json_index == self.json_template_total_units:
                        if self.current_event not in self.json_template_pop_total_response.keys():
                            self.json_template_pop_total_response[self.current_event] = json_pop_trial_response
                        else:
                            self.json_template_pop_total_response[self.current_event].extend(json_pop_trial_response)
                        self.json_template_pop_current_response = json_pop_trial_response

            self.json_template_unit_dict = copy.deepcopy(self.json_template_unit_dict_template) #Reset unit_dict to save computational time later

    def psthtemplate(self): #Reshape into PSTH format Trials x (Neurons x Bins) Used at the end of all trials.
        #Counts the events
        self.event_number_count = Counter()
        for num in self.event_number_list:
            self.event_number_count[num] += 1

        for event in self.pop_total_response.keys():
            self.psth_templates[event] = numpy.reshape(self.pop_total_response[event],(self.event_number_count[event], self.total_units*self.total_bins))
            self.psth_templates[event] = self.psth_templates[event].sum(axis = 0) / self.event_number_count[event]
            self.psth_templates[event] = [x for x in self.psth_templates[event]]
    
    def decode(self):
        tic = time.time()
        for i in self.loaded_psth_templates.keys():
            for j in range(self.json_template_total_units*self.total_bins):
                # try:
                self.euclidean_dists[i][j] = (self.json_template_pop_current_response[j] - self.loaded_psth_templates[i][j])**2 #**0.5 , moved square root to the end.
                # except:
                #     print('bin', self.binned_response)
                #     print('pop bin', self.json_population_response)
                #     print('i', i)
                #     print('j', j)
                #     print('length pop_current_response', len(self.json_template_pop_current_response))
                #     print('json_temp pop current resp', self.json_template_pop_current_response)
                #     print('pop resp', self.json_population_response)
                #     print('length loaded template i:',len(self.loaded_psth_templates[i]))
                #     print('psth temps', self.loaded_psth_templates[i])
                #     break

            self.sum_euclidean_dists[i] = (sum(self.euclidean_dists[i]))**0.5 #Moved square root to here. from inside loop above.
        decoder_key = int(min(self.sum_euclidean_dists.keys(), key= (lambda k: self.sum_euclidean_dists[k])))
        self.decoder_list.append(decoder_key)
        toc = time.time() - tic
        self.decoder_times.append(toc)
        print(self.sum_euclidean_dists)
        print(decoder_key)
        #print('decoder key:', decoder_key)
        #print('min dist:', self.sum_euclidean_dists[decoder_key])
        if decoder_key == self.current_event:
            print('decoder correct')
            return True
        else:
            print('decoder incorrect')
            return False

    def savetemplate(self):
        json_event_number_dict = {'ActualEvents':self.event_number_list}
        json_decode_number_dict = {'PredictedEvents':self.decoder_list}
        json_channel_dict = {'ChannelDict':self.channel_dict}
        jsondata = {}
        jsondata.update(self.psth_templates)
        jsondata.update(json_event_number_dict) #Tilt list Actual
        jsondata.update(json_decode_number_dict) #Tilt list Predicted
        jsondata.update(json_channel_dict)
        #jsondata.update() #Something else?
        name = input('What would you like to name the template file:')
        with open(name +'.txt', 'w') as outfile:
            json.dump(jsondata, outfile)
    
    def loadtemplate(self):
        name = input('What template file would you like to open: ')
        with open(name + '.txt') as infile:
            data = json.load(infile)
        self.loaded_template = data
        self.loaded_psth_templates = {}
        self.euclidean_dists = {}
        self.sum_euclidean_dists = {}
        self.loaded_json_event_number_dict = {}
        self.loaded_json_decode_number_dict = {}
        self.loaded_json_chan_dict = {}
        for i in data.keys():
            if i.isnumeric():
                temp_psth_template = {i:data[i]}
                self.loaded_psth_templates.update(temp_psth_template)

            else:
                if i == 'ActualEvents':
                    self.loaded_json_event_number_dict = {i:data[i]}
                elif i == 'PredictedEvents':
                    self.loaded_json_decode_number_dict = {i:data[i]}
                elif i == 'ChannelDict':
                    loaded_json_chan_dict = {i:data[i]}
                    for j in loaded_json_chan_dict.keys():
                        self.loaded_json_chan_dict = data[j]
                        #print('loaded_json_chan_dict',self.loaded_json_chan_dict)
        
        for chan, unit_list in self.loaded_json_chan_dict.items():
            new_chan = int(chan)
            new_chan_unit_list = {new_chan:unit_list}
            self.json_template_channel_dict.update(new_chan_unit_list)

        # print('json_template_channel_dict', self.json_template_channel_dict)

        for chan, unit_list in self.loaded_json_chan_dict.items():
            if chan not in self.json_template_unit_dict_nonints.keys():
                self.json_template_unit_dict_nonints[chan] = {}
            for unit in unit_list:
                self.json_template_unit_dict_nonints[chan][unit] = []
                self.json_template_total_units = self.json_template_total_units + 1
        for i,j in self.json_template_unit_dict_nonints.items():
            new_i = int(i)
            new_ij = {new_i:j}
            self.json_template_unit_dict.update(new_ij)

        # print('json_template_unit_dict', self.json_template_unit_dict)
        for chan, unit_list in self.unit_dict.items():
            if chan not in self.total_unit_dict.keys():
                self.total_unit_dict[chan] = {}
            for unit in unit_list:
                self.total_unit_dict[chan][unit] = []

        for chan, unit_list in self.json_template_unit_dict.items():
            if chan not in self.total_unit_dict.keys():
                self.total_unit_dict[chan] = {}
            for unit in unit_list:
                if unit not in self.total_unit_dict[chan].keys():
                    self.total_unit_dict[chan][unit] = []
        # print('total unit dict', self.total_unit_dict)
        # Prepare Euclidean dist matrix
        for i in data.keys():
            if i.isnumeric():
                zero = numpy.zeros((self.json_template_total_units*self.total_bins,), dtype = int)
                zero_matrix = [x for x in zero]
                self.euclidean_dists[i] = zero_matrix
                self.sum_euclidean_dists[i] = []
        self.json_template_unit_dict_template = copy.deepcopy(self.json_template_unit_dict)
        # print('json_template_unit_dict_template', self.json_template_unit_dict_template)

        for chan, unit_list in self.json_template_channel_dict.items():
            if chan not in self.total_channel_dict.keys():
                self.total_channel_dict.update({chan:self.json_template_channel_dict[chan]})
            for unit in unit_list:
                if unit not in self.total_channel_dict[chan]:
                    self.total_channel_dict[chan].append(unit)

        # print('total_channel_dict', self.total_channel_dict)
    def Test(self, baseline):
        print('test')
        print('event list:', self.event_number_list)
        if baseline == False:
            print('decoder list:', self.decoder_list)
        # print('population total response:', self.pop_total_response)
        # print('psth templates', self.psth_templates)
        return self.psth_templates, self.pop_total_response



if __name__ =='__main__':
    # Create instance of API class
    # New Format to compare Channel and Unit. 0 is unsorted. Channels are Dict Keys, Units are in each list.
    channel_dict = {1: [1,2], 2: [1,2], 3: [1,2,3], 4: [1,2,3],
                6: [1,2], 7: [1,2,3,4], 8: [1,2,3,4],
                9: [1,2,3], 10: [1,2],
                13: [1,2,3], 14: [1,2,3,4], 15: [1,2,3], 16: [1,2,3],
                18: [1], 19: [1,2], 20: [1,2,3,4],
                25: [1,2,3], 26: [1], 27: [1], 28: [1],
                29: [1], 31: [1], 32: [1]}
    pre_time = 0.200 #seconds (This value is negative or whatever you put, ex: put 0.200 for -200 ms)
    post_time = 0.200 #seconds
    bin_size = 0.020 #seconds
    # pre_total_bins = 200 #bins
    # post_total_bins = 200 #bins
    wait_for_timestamps = False
    calculate_PSTH = False
    calc_psth = False
    foundevent = False
    collected_ts = False
    baseline_recording = True # True for Creating a baseline recording.
                               # False to Load a template
    psthclass = PSTH(channel_dict, pre_time, post_time, bin_size)
    
    if baseline_recording == False:
        psthclass.loadtemplate()
    
    ##Setup for Plexon DO
    # compatible_devices = ['PXI-6224', 'PXI-6259']
    # plexdo = PyPlexDO()
    # doinfo = plexdo.get_digital_output_info()
    # device_number = None
    # for i in range(doinfo.num_devices):
    #     if plexdo.get_device_string(doinfo.device_numbers[i]) in compatible_devices:
    #         device_number = doinfo.device_numbers[i]
    # if device_number == None:
    #     print("No compatible devices found. Exiting.")
    #     sys.exit(1)
    # else:
    #     print("{} found as device {}".format(plexdo.get_device_string(device_number), device_number))
    # res = plexdo.init_device(device_number)
    # if res != 0:
    #     print("Couldn't initialize device. Exiting.")
    #     sys.exit(1)
    # plexdo.clear_all_bits(device_number)
    ##End Setup for Plexon DO
    
    client = PyPlexClientTSAPI()

    # Connect to OmniPlex Server
    client.init_client()

    running = True
    print('running')
    running = True
    #timer_list = []
    try:
        while running:
            # Wait half a second for data to accumulate
            # if wait_for_timestamps:
            #     time.sleep(post_time)
            #     calculate_PSTH = True

            # else:
            #     time.sleep(.1)
            time.sleep(0.1)
            # Get accumulated timestamps
            res = client.get_ts()

            # Print information on the data returned
            
            for t in res:
                # Print information on spike channel 1
                if t.Type == PL_SingleWFType and t.Channel in psthclass.total_channel_dict.keys() and t.Unit in psthclass.total_channel_dict[t.Channel]:
                    psthclass.build_unit(t.Channel,t.Unit,t.TimeStamp)
                    if foundevent == True and t.TimeStamp >= (psthclass.current_ts + psthclass.post_time):
                        collected_ts = True


                # Print information on events
                if t.Type == PL_ExtEventType and foundevent == False:
                    print(('Event Ts: {}s Ch: {} Type: {}').format(t.TimeStamp, t.Channel, t.Type))
                    if t.Channel == 257: #Channel for Strobed Events.
                        psthclass.event(t.TimeStamp,t.Unit)
                        foundevent = True

            if calc_psth == False and collected_ts == True:
                psthclass.psth(True, baseline_recording)
                calc_psth = True
                if baseline_recording == False:
                    psthclass.psth(False, baseline_recording)

                if baseline_recording == False:
                    psthclass.decode()
                wait_for_timestamps = False
                calculate_PSTH = False
                foundevent = False
                calc_psth = False
                collected_ts = False
##            toc = time.time() - tic
##            print('toc: ',toc)
##            timer_list.append(toc)

                       

    except KeyboardInterrupt:
        running = False
        
    print('close')
    psthclass.psthtemplate()
    client.close_client()
    psthclass.savetemplate()
    x , y = psthclass.Test(baseline_recording)
    # print("timer_list: ", timer_list)