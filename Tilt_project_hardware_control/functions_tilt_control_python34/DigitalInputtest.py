import definitions 
from definitions import *


with nidaqmx.Task() as task:
    channel = "Dev4/port2/line7"
    print(channel)
    task.di_channels.add_di_chan(channel, line_grouping = LineGrouping.CHAN_PER_LINE)
    task.read(number_of_samples_per_channel=1)
    print(task.read(number_of_samples_per_channel=1))
    input('running')

    running = True
    while running:
        ex = task.read(number_of_samples_per_channel=1)
        print(ex)
        if ex == True or ex == [True]:
            running = False

    print('done')
            
