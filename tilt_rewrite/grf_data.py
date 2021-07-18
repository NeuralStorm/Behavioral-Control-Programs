
from typing import List, Dict, get_type_hints, Any, Literal, Tuple, Optional, Callable
import os
import time
import csv
from collections import deque
from contextlib import ExitStack, AbstractContextManager, contextmanager
from itertools import count
from multiprocessing import Process, Event as PEvent, Queue
from queue import Empty, Full
import atexit

RECORD_PROCESS_STOP_TIMEOUT = 30

# pos = row, col
GRAPHS: Dict[str, Dict[str, Any]] = {
    'force_x': {
        'pos': (0, 0),
        'title': "force x",
    },
    'force_y': {
        'pos': (0, 1),
    },
    'force_z': {
        'pos': (0, 2),
    },
    'torque_x': {
        'pos': (1, 0),
    },
    'torque_y': {
        'pos': (1, 1),
    },
    'torque_z': {
        'pos': (1, 2),
    },
    'strobe': {
        'pos': (2, 0),
        'title': 'Start of tilt from motor',
        'y_max': 6,
    },
    'start': {
        'pos': (2, 1),
        'y_max': 6,
    },
    'inclinometer': {
        'pos': (2, 2),
    },
}

# rhl = red
# lhl = green
# fl = blue
# cal indicates column name for calibration
HEADERS: List[Dict[str, Any]] = [
    { # rhl_fx
        'csv': "Dev6/ai18",
        'cal': 'rhl_fx',
        'graph': 'force_x',
        'color': (255, 0, 0),
    },
    { # rhl_fy
        'csv': "Dev6/ai19",
        'cal': 'rhl_fy',
        'graph': 'force_y',
        'color': (255, 0, 0),
    },
    { # rhl_fz
        'csv': "Dev6/ai20",
        'cal': 'rhl_fz',
        'graph': 'force_z',
        'color': (255, 0, 0),
    },
    { # rhl_tx
        'csv': "Dev6/ai21",
        'cal': 'rhl_tx',
        'graph': 'torque_x',
        'color': (255, 0, 0),
    },
    { # rhl_ty
        'csv': "Dev6/ai22",
        'cal': 'rhl_ty',
        'graph': 'torque_y',
        'color': (255, 0, 0),
    },
    { # rhl_tz
        'csv': "Dev6/ai23",
        'cal': 'rhl_tz',
        'graph': 'torque_z',
        'color': (255, 0, 0),
    },
    { # lhl_fx
        'csv': "Dev6/ai32",
        'cal': 'lhl_fx',
        'graph': 'force_x',
        'color': (0, 255, 0),
    },
    { # lhl_fy
        'csv': "Dev6/ai33",
        'cal': 'lhl_fy',
        'graph': 'force_y',
        'color': (0, 255, 0),
    },
    { # lhl_fz
        'csv': "Dev6/ai34",
        'cal': 'lhl_fz',
        'graph': 'force_z',
        'color': (0, 255, 0),
    },
    { # lhl_tx
        'csv': "Dev6/ai35",
        'cal': 'lhl_tx',
        'graph': 'torque_x',
        'color': (0, 255, 0),
    },
    { # lhl_ty
        'csv': "Dev6/ai36",
        'cal': 'lhl_ty',
        'graph': 'torque_y',
        'color': (0, 255, 0),
    },
    { #lhl_tz
        'csv': "Dev6/ai37",
        'cal': 'lhl_tz',
        'graph': 'torque_z',
        'color': (0, 255, 0),
    },
    { # fl_fx
        'csv': "Dev6/ai38",
        'cal': 'fl_fx',
        'graph': 'force_x',
        'color': (0, 0, 255),
    },
    { # fl_fy
        'csv': "Dev6/ai39",
        'cal': 'fl_fy',
        'graph': 'force_y',
        'color': (0, 0, 255),
    },
    { # fl_fz
        'csv': "Dev6/ai48",
        'cal': 'fl_fz',
        'graph': 'force_z',
        'color': (0, 0, 255),
    },
    { # fl_tx
        'csv': "Dev6/ai49",
        'cal': 'fl_tx',
        'graph': 'torque_x',
        'color': (0, 0, 255),
    },
    { # fl_ty
        'csv': "Dev6/ai50",
        'cal': 'fl_ty',
        'graph': 'torque_y',
        'color': (0, 0, 255),
    },
    { # fl_tz
        'csv': "Dev6/ai51",
        'cal': 'fl_tz',
        'graph': 'torque_z',
        'color': (0, 0, 255),
    },
    {
        'csv': "Strobe",
        'cal': 'Strobe',
        'graph': 'strobe',
    },
    {
        'csv': "Start",
        'cal': 'Start',
        'graph': 'start',
    },
    {
        'csv': "Inclinometer",
        'cal': 'Inclinometer',
        'graph': 'inclinometer',
    },
    {
        'csv': 'Timestamp',
        'cal': 'Timestamp',
        'synthetic': True,
    },
]

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
        
        self.calibrated: bool = False
        # bias file to use for calibration
        self.bias_file: Optional[str] = None
    
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

def _live_view(
        *, state: RecordState, sample_rate: int, downsample_to: Optional[int],
        seconds: int,
        calibrate: Optional[Tuple[int, str]],
    ):
    
    from pyqtgraph.Qt import QtGui, QtCore
    import numpy as np
    import pyqtgraph as pg
    from pyqtgraph.ptime import time
    from pyqtgraph import PlotDataItem
    from pyqtgraph.graphicsItems.ViewBox import ViewBox
    # https://github.com/pyqtgraph/pyqtgraph/blob/master/examples/GraphicsLayout.py
    
    # data will be downsampled to this value
    # downsample_to: Optional[int] = 100
    # (hw version, bias path)
    # bp = '<grf_python>/test_data/CSM016/bias_20191120.csv'
    # calibrate: Optional[Tuple[int, str]] = (1, bp)
    # calibrate = None
    
    @contextmanager
    def app_closer(app):
        try:
            yield
        finally:
            app.quit()
    
    with ExitStack() as stack:
        stack.enter_context(LiveViewContext(state))
        
        live_headers = [h for h in HEADERS if not h.get('synthetic')]
        
        if downsample_to is not None:
            assert sample_rate % downsample_to == 0, "sample rate must be evenly divisible by downsampled rate"
            downsample_factor: Optional[int] = sample_rate // downsample_to
            sample_rate = downsample_to
        else:
            downsample_factor = None
    
        if calibrate is not None:
            import importlib.util
            import sys
            
            hw_version, bias_path = calibrate
            
            # adding the grf_python folder to path risks breaking stuff
            # but it should only break the live view process at worst
            
            # note that tilt_rewrites util will shadow grf_python's
            
            grf_python_path = os.environ['grf_python_path']
            
            sys.path.append(grf_python_path)
            
            from load_table import apply_bias, apply_best_voltage, load_bias
            from cop import calc_all_cop, add_cop_columns
            from hardware_config import HardwareConfig
            import numpy as np
            
            bias_column_mapping = [
                (h['csv'], h['cal'])
                for h in HEADERS
                if 'cal' in h and h['csv'].startswith('Dev6/')
            ]
            bias_column_mapping_ = [
                ('Dev6/ai18', 'rhl_fx'), ('Dev6/ai19', 'rhl_fy'), ('Dev6/ai20', 'rhl_fz'),
                ('Dev6/ai21', 'rhl_tx'), ('Dev6/ai22', 'rhl_ty'), ('Dev6/ai23', 'rhl_tz'),
                ('Dev6/ai32', 'lhl_fx'), ('Dev6/ai33', 'lhl_fy'), ('Dev6/ai34', 'lhl_fz'),
                ('Dev6/ai35', 'lhl_tx'), ('Dev6/ai36', 'lhl_ty'), ('Dev6/ai37', 'lhl_tz'),
                ('Dev6/ai38', 'fl_fx'), ('Dev6/ai39', 'fl_fy'), ('Dev6/ai48', 'fl_fz'),
                ('Dev6/ai49', 'fl_tx'), ('Dev6/ai50', 'fl_ty'), ('Dev6/ai51', 'fl_tz'),
            ]
            assert bias_column_mapping == bias_column_mapping_
            
            bias = load_bias(bias_path, column_mapping=bias_column_mapping)
            
            hw_conf = HardwareConfig(1)
            
            # data = {
            #     'np': np.array([[1.0 for _ in live_headers] for _ in range(10)]),
            #     'column_names': [x['cal'] for x in live_headers],
            # }
            # print(bias)
            # apply_bias(data, bias)
            # apply_best_voltage(data, hw_conf)
            # print(data)
            # cop = calc_all_cop(data, hw_conf)
            # print(cop)
        
        app = pg.mkQApp("Data")
        stack.enter_context(app_closer(app))
        
        view = pg.GraphicsView()
        layout = pg.GraphicsLayout(border=(100,100,100))
        
        view.setCentralItem(layout)
        view.show()
        view.setWindowTitle('data')
        view.resize(800,600)
        
        layout.addLabel('red=rhl green=lhl blue=fl')
        
        collectors: List[deque[float]] = [deque(maxlen=sample_rate*seconds) for _ in live_headers]
        
        plots = {}
        for graph_name, graph_info in GRAPHS.items():
            row, col = graph_info['pos']
            title = graph_info.get('title', graph_name)
            plot = layout.addPlot(row=row+1, col=col, title=title)
            
            y_max = graph_info.get('y_max')
            if y_max:
                view_box = plot.getViewBox()
                view_box.disableAutoRange(axis=ViewBox.YAxis)
                view_box.setRange(yRange=(0, y_max))
            
            plots[graph_name] = plot
        
        def get_curve(i):
            h = live_headers[i]
            if 'graph' not in h:
                # curves.append(None)
                # continue
                return None
            color = h.get('color', (255, 255, 255))
            plot = plots[h['graph']]
            curve = plot.plot(pen=color)
            return curve
        
        curves: List[PlotDataItem] = [get_curve(i) for i in range(len(live_headers))]
        
        def update():
            try:
                data = state.live.queue.get(block=False)
            except Empty:
                return
            
            if data is None:
                app.quit()
                return
            
            for i, h in enumerate(live_headers):
                # skip timestamp column since it isn't actually in the collected data
                if h['csv'] == 'Timestamp':
                    continue
                
                if downsample_factor is None:
                    collectors[i].extend(data[i])
                else:
                    downsampled = (data[i][x] for x in range(0, len(data[i]), downsample_factor))
                    collectors[i].extend(downsampled)
            
            def apply_cal():
                data = np.array(collectors, dtype=float)
                data = data.swapaxes(0, 1)
                
                data = {
                    'np': data,
                    'column_names': [x['cal'] for x in live_headers],
                }
                
                apply_bias(data, bias)
                apply_best_voltage(data, hw_conf)
                
                out_data = data['np'].swapaxes(0, 1)
                for i, curve in enumerate(curves):
                    if curve is not None:
                        curve.setData(out_data[i])
            
            if calibrate is not None:
                apply_cal()
            else:
                for i, curve in enumerate(curves):
                    if curve is not None:
                        curve.setData(collectors[i])
            
            app.processEvents()
        
        timer = QtCore.QTimer()
        timer.timeout.connect(update)
        timer.start(0)
        
        app.exec_()

def record_data(*,
        clock_source: str="", clock_rate: int,
        csv_path,
        state: RecordState,
        mock: bool,
        num_samples: Optional[int] = None,
        live_view_seconds: int = 10,
    ):
    
    # samples per second
    # SAMPLE_RATE = 1250
    SAMPLE_RATE = clock_rate
    SAMPLE_BATCH_SIZE = SAMPLE_RATE
    
    csv_headers = [x['csv'] for x in HEADERS]
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
            if state.live.calibrated:
                assert state.live.bias_file is not None
                cal: Any = (1, state.live.bias_file)
            else:
                cal = None
            
            _spawn_process(_live_view,
                state=state,
                sample_rate=clock_rate,
                downsample_to=100,
                seconds=live_view_seconds,
                calibrate=cal,
            )
        
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
                    from random import randrange
                    row = [
                        # [1 for _ in range(SAMPLE_BATCH_SIZE)]
                        # [i for i in range(SAMPLE_BATCH_SIZE)]
                        [i*j for i in range(SAMPLE_BATCH_SIZE)]
                        for j in range(len(csv_headers) - 1)
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
                try:
                    state.live.queue.put(data, block=False)
                except Full:
                    print("live view queue full, data is being discarded (will still be written to csv)")
            
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
