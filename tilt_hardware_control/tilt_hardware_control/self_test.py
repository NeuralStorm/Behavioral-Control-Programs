
import sys
import time
from contextlib import ExitStack

def test_clock_speed():
    import nidaqmx # pylint: disable=import-error
    # pylint: disable=import-error
    from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
    
    SAMPLE_RATE = 1250
    SAMPLE_BATCH_SIZE = SAMPLE_RATE
    clock_source = '/Dev6/PFI6'
    
    read_timeout = 2
    
    num_iterations = 3
    
    with ExitStack() as stack:
        task = stack.enter_context(nidaqmx.Task())
        
        task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
        task.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
        
        task.timing.cfg_samp_clk_timing(SAMPLE_RATE, source=clock_source, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=SAMPLE_BATCH_SIZE)
        
        start_time = time.perf_counter()
        for i in range(num_iterations):
            data = task.read(SAMPLE_BATCH_SIZE, read_timeout)
            
            for i in range(SAMPLE_BATCH_SIZE):
                for chan in data:
                    chan[i]
        
        end_time = time.perf_counter()
        
        elapsed = end_time - start_time
        print("ellapsed", elapsed)

def test_tilts():
    import nidaqmx # pylint: disable=import-error
    # pylint: disable=import-error
    from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
    
    from motor_control import MotorControl
    
    tilt_types = [
        ('a', 1, 9,  'Slow Counter Clockwise',),
        ('b', 2, 11, 'Fast Counter Clockwise',),
        ('c', 3, 12, 'Slow Clockwise'        ,),
        ('d', 4, 14, 'Fast Clockwise'        ,),
    ]
    
    with ExitStack() as stack:
        motor = MotorControl()
        stack.enter_context(motor)
        
        for tilt_type in tilt_types:
            print("tilt", tilt_type)
            
            with nidaqmx.Task() as task:
                sample_rate = 1000
                batch_size = 3000
                read_timeout = 4
                task.timing.cfg_samp_clk_timing(
                    sample_rate,
                    source='',
                    sample_mode=AcquisitionType.CONTINUOUS,
                    samps_per_chan=batch_size,
                )
                task.ai_channels.add_ai_voltage_chan("Dev6/ai8")
                
                motor.tilt(tilt_type[0])
                time.sleep(1.75)
                motor.tilt('stop')
                
                data = task.read(batch_size, read_timeout)
                
                assert len(data) == 1
                strobe = data[0]
                print("strobe max", max(strobe))
                assert strobe[0] < 4
                assert strobe[-1] < 4
                assert any(x > 4 for x in strobe)
            
            input('press enter to continue')
        
        motor.close()

def main():
    try:
        cmd = sys.argv[1]
    except IndexError:
        cmd = None
    
    if cmd == 'clock':
        test_clock_speed()
    else:
        test_tilts()

if __name__ == '__main__':
    main()
