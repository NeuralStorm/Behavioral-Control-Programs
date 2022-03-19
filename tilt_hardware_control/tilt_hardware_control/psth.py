#MAP System Online Decoder
#from pyplexdo import PyPlexDO, DODigitalOutputInfo
import time
import numpy
from decimal import Decimal
from collections import Counter, defaultdict
import json
import copy
#TODO: CSV for channels. Include post time window of event. Need to save population response (dict? key as event_count) from an event  so that they are all saved.
class PSTH: ###Initiate PSTH with desired parameters, creates unit_dict which has wanted units and will catch timestamps from plexon.
    def __init__(self, channel_dict, pre_time, post_time, bin_size, *, event_num_mapping=None):
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
        self.current_ts = -1000
        self.current_ts_by_channel = defaultdict(lambda: 0)
        
        self.event_num_mapping = event_num_mapping
        
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
        
        self.output_extra = {
            'event_num_mapping': event_num_mapping,
        }
    
    ###### build_unit will be used to gather timestamps from plexon and add them to the unit_dict which will be used to compare psth formats, etc.
    def build_unit(self, tmp_channel, tmp_unit, tmp_timestamp):
        if tmp_channel not in self.total_channel_dict or tmp_unit not in self.total_channel_dict[tmp_channel]:
            return
        
        relevent = False
        if tmp_channel in self.channel_dict.keys() and tmp_unit in self.channel_dict[tmp_channel]:
            self.unit_dict[tmp_channel][tmp_unit].append(Decimal(tmp_timestamp).quantize(Decimal('1.0000')))
            relevent = True
        if tmp_channel in self.json_template_channel_dict.keys() and tmp_unit in self.json_template_channel_dict[tmp_channel]:
            self.json_template_unit_dict[tmp_channel][tmp_unit].append(Decimal(tmp_timestamp).quantize(Decimal('1.0000')))
            relevent = True
        
        return relevent

    def event(self, event_ts, event_unit):
        #Need to check that it's not a duplicate event...
        # print("event_ts", event_ts, self.current_ts)
        # if (event_ts - self.current_ts) > 1:
        if self.event_num_mapping is not None:
            event_unit = self.event_num_mapping[event_unit]
        
        if (event_ts - self.current_ts) > 1:
            # print('event def')
            self.event_count = self.event_count + 1                             #Total count of events (number of events that occurred)
            self.current_ts = event_ts                                          #Timestamp of the current event
            # self.current_ts_by_channel[event_unit] = event_ts
            self.current_event = event_unit                                     #Event number of the current event
            # event_number_list is set in psth since event is sometimes called when psth is not
            # event_ts_list isn't effected since it doesn't appear to be used
            self.event_ts_list.append(event_ts)                                 #List of timestamps
            # self.event_number_list.append(event_unit)                           #List of event number
            return True
        else:
            print("duplicate event ignored")
            return False


    def psth(self, json_template, baseline_recording):
        assert self.current_event is not None
        if json_template == True:
            self.event_number_list.append(self.current_event)
        
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
                    self.json_template_binned_response = numpy.histogram(numpy.asarray(offset_ts, dtype='float'), self.total_bins, range = (-self.pre_time, self.post_time))[0]
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
        
        # self.current_event = None

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
        # print(self.sum_euclidean_dists)
        # print(decoder_key)
        #print('decoder key:', decoder_key)
        #print('min dist:', self.sum_euclidean_dists[decoder_key])
        if decoder_key == self.current_event:
            # print('decoder correct')
            return True
        else:
            # print('decoder incorrect')
            return False

    def savetemplate(self, output_path):
        json_event_number_dict = {'ActualEvents':self.event_number_list}
        json_decode_number_dict = {'PredictedEvents':self.decoder_list}
        json_channel_dict = {'ChannelDict':self.channel_dict}
        jsondata = {}
        jsondata.update(self.psth_templates)
        jsondata.update(json_event_number_dict) #Tilt list Actual
        jsondata.update(json_decode_number_dict) #Tilt list Predicted
        jsondata.update(json_channel_dict)
        
        jsondata.update(self.output_extra)
        
        #jsondata.update() #Something else?
        # name = input('What would you like to name the template file:')
        # with open(name +'.txt', 'w') as outfile:
        with open(output_path, 'w') as outfile:
            json.dump(jsondata, outfile, indent=2)
    
    def loadtemplate(self, input_path, *, event_num_mapping=None):
        if event_num_mapping is None:
            event_num_mapping = self.event_num_mapping
        
        def map_events(data):
            if event_num_mapping is not None:
                data = [event_num_mapping[x] for x in  data]
            return data
        
        # name = input('What template file would you like to open: ')
        # with open(name + '.txt') as infile:
        with open(input_path) as infile:
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
                if event_num_mapping is not None:
                    out_key = str(event_num_mapping[int(i)])
                
                self.loaded_psth_templates[out_key] = data[i]
                # temp_psth_template = {i:data[i]}
                # self.loaded_psth_templates.update(temp_psth_template)

            else:
                if i == 'ActualEvents':
                    self.loaded_json_event_number_dict = {i:map_events(data[i])}
                elif i == 'PredictedEvents':
                    self.loaded_json_decode_number_dict = {i:map_events(data[i])}
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
                if event_num_mapping is not None:
                    out_key = str(event_num_mapping[int(i)])
                zero = numpy.zeros((self.json_template_total_units*self.total_bins,), dtype = int)
                zero_matrix = [x for x in zero]
                self.euclidean_dists[out_key] = zero_matrix
                self.sum_euclidean_dists[out_key] = []
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

def main():
    import sys
    with open(sys.argv[1]) as f:
        data = json.load(f)
    
    template_in = sys.argv[2]
    try:
        baseline = data['baseline']
    except KeyError:
        arg = sys.argv[3]
        if arg == 'baseline':
            baseline = True
        elif arg == 'nonbaseline':
            baseline = False
        else:
            raise ValueError()
    
    pre_time = 0.0
    post_time = 0.200
    bin_size = 0.020
    event_num_mapping = {
        1: 1, 2: 2, 3: 3, 4: 4,
        9: 1, 11: 2, 12: 3, 14: 4,
    }
    psth = PSTH(
        data['ChannelDict'],
        pre_time, post_time, bin_size,
        event_num_mapping=event_num_mapping,
    )
    if template_in:
        assert not baseline
        psth.loadtemplate(template_in)
    
    correct = 0
    total = 0
    # correct values from actual run
    actual_correct = 0
    mismatched_perdictions = 0
    
    for tilt in data['tilts']:
        print("tilt", tilt['i'])
        found_event = False
        collected_ts = False
        for event in tilt['events']:
            if event['type'] == 'spike':
                relevent = psth.build_unit(event['channel'], event['unit'], event['time'])
                if relevent:
                    collected_ts = True
            elif event['type'] == 'tilt':
                if event['channel'] == 257 and not found_event:
                    psth.event(event['time'], event['unit'])
                    found_event = True
        
        got_response = found_event and collected_ts
        assert tilt['got_response'] == got_response
        
        if got_response:
            psth.psth(True, baseline)
            if not baseline:
                psth.psth(False, baseline)
        
        if not baseline:
            if got_response:
                decode_result = psth.decode()
                predicted_tilt_type = psth.decoder_list[-1]
                print("  decode_result", decode_result, predicted_tilt_type)
                print("  actl", tilt['tilt_type'])
                actual_prediction = tilt['predicted_tilt_type']
                print("  pred", predicted_tilt_type, actual_prediction)
                # assert predicted_tilt_type == actual_prediction
                
                total += 1
                if predicted_tilt_type == tilt['tilt_type']:
                    correct += 1
                if actual_prediction == tilt['tilt_type']:
                    actual_correct += 1
                if actual_prediction != predicted_tilt_type:
                    mismatched_perdictions += 1
            else:
                print("  no spikes")
    
    print(f"rerun  {correct}/{total} {correct/total*100:.2f}%")
    print(f"actual {actual_correct}/{total} {actual_correct/total*100:.2f}%")
    print(f"mismatched {mismatched_perdictions}")

if __name__ == '__main__':
    main()