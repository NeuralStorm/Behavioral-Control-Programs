import numpy as np
import tables
import matplotlib.pyplot as plt

data_path = 'C:/Users/scientist/Documents/Preeya/data/'
day_to_analyze = '0802'
monk = 'haun'

import glob
files = glob.glob(data_path+monk+'*'+day_to_analyze+'*'+'_data.hdf')


def run_analysis():
	for fl in files: 
		hdf = tables.open_file(fl)
		state = [str(st) for st in hdf.root.task[:]['state']]

		ix = np.nonzero(np.array(state)=="b'reward'")[0]
		ix2 = []
		for i, j in enumerate(ix):
			if j-ix[i-1] > 1:
				ix2.append(j)
		print(fl+'........')
		print('number of reward: '+ str(len(ix2)))

def plot_cursor(hdf):
	state = hdf.root.task[:]['state']

	state_i = ''
	states = []

	for  i in range(len(state)):
	    if state[i] != state_i:
	        states.append([state[i], i])
	        state_i = state[i]
	states = np.vstack((states))

	ix = np.nonzero(states[:, 0]==b'reward')[0]

	# which ix is trial 15? 
	trl_15_rew = ix[15]
	cent_ix = trl_15_rew - 4
	cent_ix2 = trl_15_rew - 3

	# now, which is the center hold start? 
	hdf_row = states[cent_ix, 1]
	hdf_row2 = states[cent_ix2, 1]

	# cursors
	cursors = hdf.root.task[:]['cursor']


	for i in range(10):
	    plt.plot(cursor[:, i, 0], cursor[:, i, 1])


	for i in range(10):
	    plt.plot(cursor[int(hdf_row):int(hdf_row2), i, 0], cursor[int(hdf_row):int(hdf_row2), i, 1], 'k-')

	f, ax = plt.subplots()
	for i in range(10):
	    ax.plot(cursor[int(hdf_row):int(hdf_row2), i, 0])