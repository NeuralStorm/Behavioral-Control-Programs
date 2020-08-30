import definitions
from definitions import *
from nidaqmx.constants import *


with nidaqmx.Task() as task:
    task.di_channels.add_di_chan("Dev4/port2/line5", line_grouping = LineGrouping.CHAN_PER_LINE)
##    task.timing.ref_clk_src = "Dev4/port2/line7"
##    task.timing.ref_clk_rate = 40000    
##    task.timing.cfg_samp_clk_timing(1000, sample_mode = AcquisitionType.CONTINUOUS)

    wait_start = True
    
    
    while wait_start:
        tic = time.time()
        ex = task.read(number_of_samples_per_channel=1)
        if ex == True or ex == [True]:
            starttime = time.time()
            wait_start = False
    print(tic)
    print(starttime)
