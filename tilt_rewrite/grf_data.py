
from typing import List, Dict, get_type_hints, Any, Literal, Tuple, Optional, Callable
import time
import csv
from collections import deque
from contextlib import ExitStack, AbstractContextManager, contextmanager
from itertools import count
from multiprocessing import Process, Event as PEvent, Queue
import atexit

RECORD_PROCESS_STOP_TIMEOUT = 30

def _spawn_process(func, *args, **kwargs) -> Process:
    proc = Process(target=func, args=args, kwargs=kwargs)
    proc.start()
    # atexit.register(lambda: proc.terminate())
    return proc

class LiveViewState:
    def __init__(self):
        self.enabled: bool = False
        
        self.queue = Queue(10)
        self.stopped = PEvent()
    
    def stop(self):
        if self.enabled:
            self.queue.put(None, block=False)
            self.stopped.wait(timeout=RECORD_PROCESS_STOP_TIMEOUT)

class RecordState:
    def __init__(self):
        # set to request the record process to stop 
        self.stopping = PEvent()
        # set when the record process completes
        self.stopped = PEvent()
        # set if recording process fails
        self.failed = PEvent()
        
        self.live = LiveViewState()
    
    def stop_recording(self):
        self.stopping.set()
        self.stopped.wait(timeout=RECORD_PROCESS_STOP_TIMEOUT)
        
        self.live.stop()

class LiveViewContext(AbstractContextManager):
    def __init__(self, state: RecordState):
        self.state: RecordState = state
    
    def __exit__(self, *exc):
        # if exc != (None, None, None):
        #     self.stop_event.failed.set()
        # print('debug wait for stop')
        # time.sleep(5)
        # self.stop_event.stopped.set()
        self.state.live.stopped.set()

class RecordEventContext(AbstractContextManager):
    def __init__(self, stop_event: RecordState):
        self.stop_event: RecordState = stop_event
    
    def __exit__(self, *exc):
        if exc != (None, None, None):
            self.stop_event.failed.set()
        # print('debug wait for stop')
        # time.sleep(5)
        self.stop_event.stopped.set()

def live_view(state: RecordState):
    #https://stackoverflow.com/questions/11874767/how-do-i-plot-in-real-time-in-a-while-loop-using-matplotlib/15724978#15724978
    
    import matplotlib.pyplot as plt
    
    @contextmanager
    def figure_context(*args, **kwargs):
        fig = plt.figure(*args, **kwargs)
        yield fig
        plt.close(fig)
    
    with ExitStack() as stack:
        stack.enter_context(LiveViewContext(state))
        i = 0
        collect_a: deque[float] = deque(maxlen=1250*10)
        collect_b: deque[float] = deque(maxlen=1250*10)
        
        fig_a = stack.enter_context(figure_context())
        fig_b = stack.enter_context(figure_context())
        
        # plt.axis([0, 10, 0, 1])
        # fig_a.axis([0, 10, 0, 1])
        # fig_b.axis([0, 10, 0, 1])
        
        while True:
            data = state.live.queue.get()
            if data is None:
                return
            # print('live', len(data), len(data[0]))
            collect_a.extend(data[0])
            collect_b.extend(data[1])
            
            e = i + len(data[0])
            s = e - len(collect_a)
            
            x_vals = list(range(s, e))
            
            plt.cla()
            plt.scatter(x_vals, collect_a)
            plt.pause(0.2)
            
            # fig_a.cla()
            # fig_a.scatter(x_vals, collect_a)
            # fig_a.pause(0.2)
            # plt.show()
            
            # fig_b.cla()
            # fig_b.scatter(x_vals, collect_b)
            # fig_b.pause(0.2)
            
            i += len(data[0])

def record_data(*,
        clock_source: str="", clock_rate: int,
        csv_path,
        state: RecordState,
        mock: bool,
        num_samples: Optional[int] = None,
    ):
    
    # samples per second
    # SAMPLE_RATE = 1250
    SAMPLE_RATE = clock_rate
    SAMPLE_BATCH_SIZE = SAMPLE_RATE
    
    csv_headers = [
        "Dev6/ai18", "Dev6/ai19", "Dev6/ai20", "Dev6/ai21", "Dev6/ai22","Dev6/ai23",
        "Dev6/ai32", "Dev6/ai33", "Dev6/ai34", "Dev6/ai35", "Dev6/ai36","Dev6/ai37","Dev6/ai38", "Dev6/ai39",
        "Dev6/ai48", "Dev6/ai49", "Dev6/ai50","Dev6/ai51",
        "Strobe", "Start", "Inclinometer", 'Timestamp',
    ]
    # csv_path = './loadcell_tilt.csv'
    # clock sourcs Dev6/PFI6
    with ExitStack() as stack:
        # add the record event context first so it will set the stopped
        # event after all other context __exit__ methods are called
        # 
        # this should happen before any failable operation so the failed event will
        # be set in the case of a failure
        stack.enter_context(RecordEventContext(state))
        
        if state.live.enabled:
            _spawn_process(live_view, state=state)
        
        if not mock:
            import nidaqmx # pylint: disable=import-error
            # pylint: disable=import-error
            from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
            
            task: Any = stack.enter_context(nidaqmx.Task())
            
            task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
            task.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
            # task.timing.cfg_samp_clk_timing(1000, source = "", sample_mode= AcquisitionType.CONTINUOUS, samps_per_chan = 1000)
            # set sample rate slightly higher than actual sample rate, not sure if that's needed
            # clock_source = "/Dev6/PFI6"
            # clock_source = ""
            task.timing.cfg_samp_clk_timing(SAMPLE_RATE, source=clock_source, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=SAMPLE_BATCH_SIZE)
            # task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev6/PFI8", trigger_edge=Edge.RISING)
        else:
            WAIT_INFINITELY = None
            class MockTask:
                def read(self, samples_per_channel, _timeout):
                    time.sleep(1)
                    row = [
                        # [1 for _ in range(SAMPLE_BATCH_SIZE)]
                        [i for i in range(SAMPLE_BATCH_SIZE)]
                        for _ in range(len(csv_headers) - 1)
                    ]
                    return row
            task = MockTask()
        
        csv_file = stack.enter_context(open(csv_path, 'w+', newline=''))
        writer = csv.writer(csv_file)
        writer.writerow(csv_headers)
        
        if not mock:
            task.start()
        
        sample_i = 0
        for row_i in count(0):
            if row_i == 0:
                # no timeout on first read to wait for start trigger
                # read_timeout = WAIT_INFINITELY
                # actually a timeout since start trigger isn't being used
                read_timeout = 20
            else:
                read_timeout = 10 # default in nidaq
            
            data = task.read(SAMPLE_BATCH_SIZE, read_timeout)
            
            if state.live.enabled:
                state.live.queue.put(data)
            
            for i in range(SAMPLE_BATCH_SIZE):
                def gen_row():
                    for chan in data:
                        yield chan[i]
                    yield sample_i / SAMPLE_RATE
                
                writer.writerow(gen_row())
                
                sample_i += 1
            
            if num_samples is not None and sample_i >= num_samples:
                break
            if state.stopping.is_set():
                break
