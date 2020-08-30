#Clock Timing NIDAQMX

import nidaqmx
import time

with nidaqmx.Task() as taskAI, nidaqmx.Task() as taskClkExport:
    acquisition_time = 10
    rateAI=50000
    t=time.localtime()
    file_path_2 = r'C:/Users/moxon/Desktop/{}_{}_{}_{}_{}_{}'.format(t.tm_year, t.tm_mon,t.tm_mday,t.tm_hour,t.tm_min,t.tm_sec)
    
    # configure analog input task
    #for i in range(16):
    #    taskAI.ai_channels.add_ai_voltage_chan("PXI1Slot2/ai{}".format(i))
    #taskAI.ai_channels.add_ai_voltage_chan("Dev4/ai1")
    taskAI.ai_channels.add_ai_voltage_chan("Dev4/ai1")
    #taskAI.in_stream.configure_logging(file_path_2,
                                  #nidaqmx.constants.LoggingMode.LOG,
                                  #'myGroupName',
                                  #nidaqmx.constants.LoggingOperation.OPEN_OR_CREATE)
    taskAI.timing.cfg_samp_clk_timing(rate=rateAI,
                                 sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS,
                                 samps_per_chan=2048)

    # configure clock exporting task
    taskClkExport.do_channels.add_do_chan("Dev4/port2/line7")
    taskClkExport.export_signals.export_signal(signal_id=nidaqmx.constants.Signal.SAMPLE_CLOCK,
                                           output_terminal="PXI1Slot2/port2/line7")

    print('start')
    taskClkExport.start()
    taskAI.start()

    print('running...')
    time.sleep(10)

    print('stop')
    taskAI.stop()
    taskClkExport.stop()
