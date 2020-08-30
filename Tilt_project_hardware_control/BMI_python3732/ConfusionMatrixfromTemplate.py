# Confusion Matrix and Accuracy


from sklearn.metrics import confusion_matrix
from MAPOnlineDecoderBMIFixPause import *

name = input('What template file would you like to open: ')
with open(name + '.txt') as infile:
    data = json.load(infile)
loaded_template = data
loaded_psth_templates = {}
euclidean_dists = {}
sum_euclidean_dists = {}
loaded_json_event_number_dict = {}
loaded_json_decode_number_dict = {}
loaded_json_chan_dict = {}
for i in data.keys():
    if i.isnumeric():
        temp_psth_template = {i:data[i]}
        loaded_psth_templates.update(temp_psth_template)

    else:
        if i == 'ActualEvents':
            loaded_json_event_number_dict = {i:data[i]}
        elif i == 'PredictedEvents':
            loaded_json_decode_number_dict = {i:data[i]}
        elif i == 'ChannelDict':
            loaded_json_chan_dict = {i:data[i]}
            for j in loaded_json_chan_dict.keys():
                loaded_json_chan_dict = data[j]

event_number_list = loaded_json_event_number_dict['ActualEvents']
decode_number_list = loaded_json_decode_number_dict['PredictedEvents']

print('actual events:y axis, predicted events:x axis')
confusion_matrix_calc = confusion_matrix(event_number_list,decode_number_list)
print(confusion_matrix_calc)
correct_trials = 0
for i in range(0,len(confusion_matrix_calc)):
    correct_trials = correct_trials + confusion_matrix_calc[i][i]
decoder_accuracy = correct_trials / len(event_number_list)
print(('Accuracy = {} / {} = {}').format(correct_trials, len(event_number_list), decoder_accuracy))