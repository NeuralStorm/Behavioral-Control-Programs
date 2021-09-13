
"""
"""

import serial
#import csv
import time
import datetime
#import multiprocessing as mp
#mp.set_start_method('spawn', force=True)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import tables

class Data(tables.IsDescription):
    time = tables.Float32Col()
    time_abs = tables.Float32Col()
    acc = tables.Float32Col(shape=(3,))
    gyr = tables.Float32Col(shape=(3,))

def record_data(filename, port = 'COM12'):
    h5file = tables.open_file(filename + '_acc.hdf', mode='w', title = 'NHP acc data')
    h5_table = h5file.create_table('/', 'acc', Data, '')
    h5_table_row = h5_table.row

    my_serial = serial.Serial(port=port, baudrate=115200)
    print('Connecting Arduino.')
    cont = True
    t0 = time.time()
    while cont: 
        my_serial.flush()
        data = my_serial.readline()
        split_data = str(data).split(',')
        #print(split_data)
        if len(split_data) > 8:
            try:
                acc = np.array([float(split_data[6]), float(split_data[7]), float(split_data[8]), ])
                gyr = np.array([float(split_data[1]), float(split_data[2]), float(split_data[3]), ])
                time_abs = time.time();
                tmp = time_abs - t0;

                h5_table_row['acc'] = acc
                h5_table_row['gyr'] = gyr
                h5_table_row['time_abs'] = time_abs
                h5_table_row['time'] = tmp;
                h5_table_row.append()
            except: 
                pass
                print('skipping2')
        else:
            print('skipping: ')
        time.sleep(.001)
        #if time.time() - t0 > 20:
        #    cont = False

if __name__ == '__main__':
    import sys
    print(sys.argv)
    fname = sys.argv[1]
    record_data(fname)

