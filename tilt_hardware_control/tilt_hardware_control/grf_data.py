
from typing import List, Dict, get_type_hints, Any, Literal, Tuple, Optional, Callable
import os
import time
import csv
import json
from collections import deque
from contextlib import ExitStack, AbstractContextManager, contextmanager
from itertools import count
from multiprocessing import Process, Event as PEvent, Queue, Value, Lock
from queue import Empty, Full
import atexit

from util_multiprocess import DigitalLine, AnalogChannel, spawn_process

RECORD_PROCESS_STOP_TIMEOUT = 30

# pos = row, col
GRAPHS: Dict[str, Dict[str, Any]] = {
    'force_x': {
        'pos': (0, 0),
        'title': "strain guage 1",
    },
    'force_y': {
        'pos': (0, 1),
        'title': "strain guage 2",
    },
    'force_z': {
        'pos': (0, 2),
        'title': "strain guage 3",
    },
    'torque_x': {
        'pos': (1, 0),
        'title': "strain guage 4",
    },
    'torque_y': {
        'pos': (1, 1),
        'title': "strain guage 5",
    },
    'torque_z': {
        'pos': (1, 2),
        'title': "strain guage 6",
    },
    'strobe': {
        'pos': (2, 0),
        'title': 'Tilt active(r)/midpoint(g)',
        'y_max': 1.5,
    },
    'misc': {
        'pos': (2, 1),
        'title': 'Stim',
        'y_max': 1.5,
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
        'nidaq': 'Dev6/ai18',
        'csv': "sensor1_s1",
        'analog_channel': "sensor1_s1",
        'cal': 'rhl_s1',
        'graph': 'force_x',
        'color': (255, 0, 0),
    },
    { # rhl_fy
        'nidaq': 'Dev6/ai19',
        'csv': "sensor1_s2",
        'analog_channel': "sensor1_s2",
        'cal': 'rhl_s2',
        'graph': 'force_y',
        'color': (255, 0, 0),
    },
    { # rhl_fz
        'nidaq': 'Dev6/ai20',
        'csv': "sensor1_s3",
        'analog_channel': "sensor1_s3",
        'cal': 'rhl_s3',
        'graph': 'force_z',
        'color': (255, 0, 0),
    },
    { # rhl_tx
        'nidaq': 'Dev6/ai21',
        'csv': "sensor1_s4",
        'analog_channel': "sensor1_s4",
        'cal': 'rhl_s4',
        'graph': 'torque_x',
        'color': (255, 0, 0),
    },
    { # rhl_ty
        'nidaq': 'Dev6/ai22',
        'csv': "sensor1_s5",
        'analog_channel': "sensor1_s5",
        'cal': 'rhl_s5',
        'graph': 'torque_y',
        'color': (255, 0, 0),
    },
    { # rhl_tz
        'nidaq': 'Dev6/ai23',
        'csv': "sensor1_s6",
        'analog_channel': "sensor1_s6",
        'cal': 'rhl_s6',
        'graph': 'torque_z',
        'color': (255, 0, 0),
    },
    { # lhl_fx
        'nidaq': 'Dev6/ai32',
        'csv': "sensor2_s1",
        'analog_channel': "sensor2_s1",
        'cal': 'lhl_s1',
        'graph': 'force_x',
        'color': (0, 255, 0),
    },
    { # lhl_fy
        'nidaq': 'Dev6/ai33',
        'csv': "sensor2_s2",
        'analog_channel': "sensor2_s2",
        'cal': 'lhl_s2',
        'graph': 'force_y',
        'color': (0, 255, 0),
    },
    { # lhl_fz
        'nidaq': 'Dev6/ai34',
        'csv': "sensor2_s3",
        'analog_channel': "sensor2_s3",
        'cal': 'lhl_s3',
        'graph': 'force_z',
        'color': (0, 255, 0),
    },
    { # lhl_tx
        'nidaq': 'Dev6/ai35',
        'csv': "sensor2_s4",
        'analog_channel': "sensor2_s4",
        'cal': 'lhl_s4',
        'graph': 'torque_x',
        'color': (0, 255, 0),
    },
    { # lhl_ty
        'nidaq': 'Dev6/ai36',
        'csv': "sensor2_s5",
        'analog_channel': "sensor2_s5",
        'cal': 'lhl_s5',
        'graph': 'torque_y',
        'color': (0, 255, 0),
    },
    { #lhl_tz
        'nidaq': 'Dev6/ai37',
        'csv': "sensor2_s6",
        'analog_channel': "sensor2_s6",
        'cal': 'lhl_s6',
        'graph': 'torque_z',
        'color': (0, 255, 0),
    },
    { # fl_fx
        'nidaq': 'Dev6/ai38',
        'csv': "sensor3_s1",
        'analog_channel': "sensor3_s1",
        'cal': 'fl_s1',
        'graph': 'force_x',
        'color': (0, 0, 255),
    },
    { # fl_fy
        'nidaq': 'Dev6/ai39',
        'csv': "sensor3_s2",
        'analog_channel': "sensor3_s2",
        'cal': 'fl_s2',
        'graph': 'force_y',
        'color': (0, 0, 255),
    },
    { # fl_fz
        'nidaq': 'Dev6/ai48',
        'csv': "sensor3_s3",
        'analog_channel': "sensor3_s3",
        'cal': 'fl_s3',
        'graph': 'force_z',
        'color': (0, 0, 255),
    },
    { # fl_tx
        'nidaq': 'Dev6/ai49',
        'csv': "sensor3_s4",
        'analog_channel': "sensor3_s4",
        'cal': 'fl_s4',
        'graph': 'torque_x',
        'color': (0, 0, 255),
    },
    { # fl_ty
        'nidaq': 'Dev6/ai50',
        'csv': "sensor3_s5",
        'analog_channel': "sensor3_s5",
        'cal': 'fl_s5',
        'graph': 'torque_y',
        'color': (0, 0, 255),
    },
    { # fl_tz
        'nidaq': 'Dev6/ai51',
        'csv': "sensor3_s6",
        'analog_channel': "sensor3_s6",
        'cal': 'fl_s6',
        'graph': 'torque_z',
        'color': (0, 0, 255),
    },
    {
        'nidaq': 'Dev6/ai8',
        'analog_channel': 'strobe',
        'csv': "Strobe",
        'cal': 'Strobe',
        'graph': 'strobe',
    },
    {
        'nidaq': 'Dev6/ai9',
        'analog_channel': "start",
        'csv': "Start",
        'cal': 'Start',
        'graph': 'strobe',
        'color': (0, 255, 255),
    },
    {
        'nidaq': 'Dev6/ai10',
        'analog_channel': "inclinometer",
        'csv': "Inclinometer",
        'cal': 'Inclinometer',
        'graph': 'inclinometer',
    },
    {
        # 'nidaq_digital': 'Dev6/port2/line3',
        # 'nidaq': 'Dev6/port2/line3',
        # 'nidaq_digital': 'Dev6/port0/line3',
        'nidaq_digital': 'Dev6/port0/line0',
        # 'nidaq_digital': 'Dev6/port0/line0:7',
        'digital_line': 'tilt_active',
        'analog_channel': "tilt_active",
        'downsample_mode': 'max',
        'csv': "strobe_digital",
        'graph': 'strobe',
        'color': (255, 0, 0),
    },
    {
        # 'nidaq_digital': 'Dev6/port0/line4',
        'nidaq_digital': 'Dev6/port0/line1',
        'analog_channel': 'tilt_midpoint',
        'downsample_mode': 'max',
        'csv': "tilt_midpoint",
        'graph': 'strobe',
        'color': (0, 255, 0),
    },
    # {
    #     'nidaq_digital': 'Dev6/port0/line0',
    #     'analog_channel': 'tilt_active_new',
    #     'digital_line': 'tilt_active_new',
    #     'downsample_mode': 'max',
    #     'csv': "tilt_active_new",
    #     'graph': 'start',
    #     'color': (255, 0, 0),
    # },
    # {
    #     'nidaq_digital': 'Dev6/port0/line1',
    #     'analog_channel': 'tilt_midpoint_new',
    #     'downsample_mode': 'max',
    #     'csv': "tilt_midpoint_new",
    #     'graph': 'start',
    #     'color': (0, 255, 0),
    # },
    {
        'nidaq_digital': 'Dev6/port0/line5',
        'analog_channel': 'stim',
        'downsample_mode': 'max',
        'csv': "stim",
        # 'graph': 'strobe',
        'graph': 'misc',
        'color': (255, 255, 0),
    },
    # {
    #     # 'nidaq_digital': 'Dev6/port2/line3',
    #     # 'nidaq': 'Dev6/port2/line3',
    #     'nidaq_digital': 'Dev6/port0/line4',
    #     # 'nidaq_digital': 'Dev6/port0/line0:7',
    #     # 'digital_line': 'tilt_active',
    #     # 'analog_channel': "tilt_active",
    #     # 'csv': "start_digital",
    #     # 'graph': 'start',
    #     # 'color': (255, 0, 0),
    # },
    # {
    #     'csv': 'Timestamp',
    #     'cal': 'Timestamp',
    #     'synthetic': True,
    # },
]

class LiveViewState:
    def __init__(self):
        self.enabled: bool = False
        
        self.queue = Queue(1000)
        # self.timing_queue = Queue(1000)
        self.stopping = PEvent()
        self.stopped = PEvent()
        
        self.calibrated: bool = False
        # bias file to use for calibration
        self.bias_file: Optional[str] = None
    
    def stop(self):
        if self.enabled:
            # self.queue.put(None, block=False)
            self.stopping.set()
            self.stopped.wait(timeout=RECORD_PROCESS_STOP_TIMEOUT)

class RecordState:
    def __init__(self):
        # set to request the record process to stop 
        self.stopping = PEvent()
        # set when the record process completes
        self.stopped = PEvent()
        # set if recording process fails
        self.failed = PEvent()
        
        self.chan_lock = Lock()
        
        d_line_keys = [x['digital_line'] for x in HEADERS if 'digital_line' in x]
        self.digital_lines = {
            # 'tilt_active': DigitalLine(),
            k: DigitalLine()
            for k in d_line_keys
        }
        
        ac_keys = [x['analog_channel'] for x in HEADERS if 'analog_channel' in x]
        self.analog_channels = {
            k: AnalogChannel(max_len=30000, lock=self.chan_lock)
            for k in ac_keys
        }
        
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
        update_hz: int,
        calibrate: Optional[Tuple[int, str]],
    ):
    
    from pyqtgraph.Qt import QtGui, QtCore
    import numpy as np
    import pyqtgraph as pg
    from pyqtgraph.ptime import time as ptime
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
        
        # live_headers = [h for h in HEADERS if not h.get('synthetic')]
        live_headers = [h for h in HEADERS if 'graph' in h]
        for h in live_headers:
            assert 'analog_channel' in h
        
        # how many time to recieve data between each render
        # samples_per_render: int = sample_rate // update_hz
        time_per_render: float = 1 / update_hz
        src_sample_rate = sample_rate
        
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
            
            bias_column_mapping = [
                (h['csv'], h['cal'])
                for h in HEADERS
                if 'cal' in h and h['csv'].startswith('sensor')
            ]
            # bias_column_mapping_ = [
            #     ('Dev6/ai18', 'rhl_fx'), ('Dev6/ai19', 'rhl_fy'), ('Dev6/ai20', 'rhl_fz'),
            #     ('Dev6/ai21', 'rhl_tx'), ('Dev6/ai22', 'rhl_ty'), ('Dev6/ai23', 'rhl_tz'),
            #     ('Dev6/ai32', 'lhl_fx'), ('Dev6/ai33', 'lhl_fy'), ('Dev6/ai34', 'lhl_fz'),
            #     ('Dev6/ai35', 'lhl_tx'), ('Dev6/ai36', 'lhl_ty'), ('Dev6/ai37', 'lhl_tz'),
            #     ('Dev6/ai38', 'fl_fx'), ('Dev6/ai39', 'fl_fy'), ('Dev6/ai48', 'fl_fz'),
            #     ('Dev6/ai49', 'fl_tx'), ('Dev6/ai50', 'fl_ty'), ('Dev6/ai51', 'fl_tz'),
            # ]
            # assert bias_column_mapping == bias_column_mapping_
            
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
        timing_label = layout.addLabel('')
        
        queue_len = sample_rate*seconds#*(downsample_factor if downsample_factor is not None else 1)
        collectors: List[deque[float]] = [deque(maxlen=queue_len) for _ in live_headers]
        initial = [0 for _ in range(queue_len)]
        for c in collectors:
            c.extend(initial)
        x_axis_data = [i/sample_rate for i in range(queue_len, 0, -1)]
        
        plots = {}
        for graph_name, graph_info in GRAPHS.items():
            row, col = graph_info['pos']
            title = graph_info.get('title', graph_name)
            plot = layout.addPlot(row=row+1, col=col, title=title)
            
            y_max = graph_info.get('y_max')
            view_box = plot.getViewBox()
            if y_max:
                view_box.disableAutoRange(axis=ViewBox.YAxis)
                view_box.setRange(yRange=(0, y_max))
            
            view_box.disableAutoRange(axis=ViewBox.XAxis)
            # view_box.setRange(xRange=(0, sample_rate*seconds))
            view_box.setRange(xRange=(0, seconds))
            view_box.invertX(True)
            
            plots[graph_name] = plot
        
        def get_curve(i):
            h = live_headers[i]
            assert 'graph' in h
            color = h.get('color', (255, 255, 255))
            plot = plots[h['graph']]
            curve = plot.plot(pen=color)
            curve.setData(x=x_axis_data, y=initial)
            return curve
        
        curves: List[PlotDataItem] = [get_curve(i) for i in range(len(live_headers))]
        
        # _samples_since_last_render = [0]
        # number of samples to ignore in future collections of samples
        # _downsample_overflow = [0]
        _last_render_time = [time.perf_counter()]
        
        timing_window: Any = deque(maxlen=src_sample_rate*2)
        batch_latency_ms = [0]
        
        def update():
            if state.live.stopping.is_set():
                app.quit()
                return
            # for _ in range(20):
            #     try:
            #         data = state.live.timing_queue.get(block=False)
            #     except Empty:
            #         break
            #     timing_window.append(data['proc'])
            #     _samples_since_last_render[0] += 1
            # get data from queue up to 20 times per callback
            for _ in range(20):
                try:
                    data = state.live.queue.get(block=False)
                except Empty:
                    pass
                else:
                    # if data is None:
                    #     app.quit()
                    #     return
                    if 'proc_time' in data:
                        timing_window.append(data['proc_time'])
                    if 'batch_size' in data:
                        batch_latency_ms[0] = round(data['batch_size'] / src_sample_rate * 1000)
            
            
            
            # if _samples_since_last_render[0] < samples_per_render:
            #     return
            # else:
            #     _samples_since_last_render[0] = 0
            now = time.perf_counter()
            # print(now - _last_render_time[0], '<', time_per_render)
            if (now - _last_render_time[0]) < time_per_render:
                return
            _last_render_time[0] = now
            # import random
            # if random.random() > 0.001:
            #     return
            
            # for i, h in enumerate(live_headers):
            #     if 'analog_channel' in h:
            #         collectors[i].clear()
            #         data = state.analog_channels[h['analog_channel']].read()
            #         collectors[i].extend([0 for _ in range(queue_len-len(data))])
            #         collectors[i].extend(data[-queue_len:])
            
            if timing_window:
                t_avg = sum(timing_window) / len(timing_window)
                t_max = max(timing_window)
                queue_pressure = state.live.queue.qsize()
                # t_avg, t_max, queue_pressure = 0, 0, 0
                text = f"{t_avg*1000:.3f}({t_max*1000:.3f})ms|{queue_pressure:<3}" \
                f"|{batch_latency_ms[0]:<3}"
                # timing_label.setText(text)
                # timing_label.setText('aaa')
                # timing_label.item.setHtml(text)
                # timing_label.text = 'aaa'
                from pyqtgraph import getConfigOption
                from pyqtgraph import functions as fn
                # print(getConfigOption('foreground'))
                # print(fn.mkColor('d'))
                # print(fn.mkColor(getConfigOption('foreground')).name())
                color_name = fn.mkColor(getConfigOption('foreground')).name()
                # timing_label.item.setHtml(f'<span style="color:{color_name}">aaa</span>')
                timing_label.item.setHtml(f'<span style="color:{color_name}">{text}</span>')
                # timing_label.updateMin()
                # timing_label.resizeEvent(None)
                # timing_label.updateGeometry()
            
            def apply_cal():
                data = np.array(collectors, dtype=float)
                data = data.swapaxes(0, 1)
                
                data = {
                    'np': data,
                    'column_names': [x['cal'] for x in live_headers],
                }
                
                apply_bias(data, bias)
                apply_best_voltage(data, hw_conf)
                cop = calc_all_cop(data, hw_conf)
                
                out_data = data['np'].swapaxes(0, 1)
                for i, (curve, header) in enumerate(zip(curves, live_headers)):
                    if header['csv'] == 'Strobe':
                        curve.setData(cop['cop_x'])
                    elif header['csv'] == 'Start':
                        curve.setData(cop['cop_y'])
                    else:
                        curve.setData(out_data[i])
            
            if calibrate is not None:
                apply_cal()
            else:
                for i, (meta, curve) in enumerate(zip(live_headers, curves)):
                    data = state.analog_channels[meta['analog_channel']].read()
                    downsample_mode = meta.get('downsample_mode', 'first')
                    if downsample_factor is not None:
                        if downsample_mode == 'first':
                            data = [data[x] for x in range(0, min(len(data), src_sample_rate*seconds), downsample_factor)]
                        elif downsample_mode == 'max':
                            data = [max(data[x:x+downsample_factor]) for x in range(0, min(len(data), src_sample_rate*seconds), downsample_factor)]
                        else:
                            raise ValueError(f'invalid downsample mode {downsample_mode}')
                        # print(downsample_factor)
                    if len(data) < queue_len:
                        data = [0 for _ in range(queue_len-len(data))] + data
                    # curve.setData(y=collectors[i], x=x_axis_data)
                    curve.setData(y=data, x=x_axis_data)
            
            app.processEvents()
        
        timer = QtCore.QTimer()
        timer.timeout.connect(update)
        timer.setInterval(1)
        timer.start(0)
        
        app.exec_()

def record_data(*,
        clock_source: str="", clock_rate: int,
        csv_path,
        state: RecordState,
        mock: bool,
        num_samples: Optional[int] = None,
        live_view_seconds: int = 10,
        output_meta: Optional[Dict[str, Any]] = None,
    ):
    
    # samples per second
    # SAMPLE_RATE = 1250
    # SAMPLE_RATE = clock_rate
    # SAMPLE_BATCH_SIZE = SAMPLE_RATE
    # SAMPLE_BATCH_SIZE = 1000
    sample_batch_size = 1
    nidaq_buffer_size = clock_rate
    
    assert sample_batch_size > 0
    
    _digital_line_cache = {k: False for k in state.digital_lines}
    def set_digital_line(line: str, val: bool):
        if _digital_line_cache[line] != val:
            _digital_line_cache[line] = val
            if val:
                state.digital_lines[line].set_true()
            else:
                state.digital_lines[line].set_false()
    
    csv_headers = [x['csv'] for x in HEADERS if 'csv' in x]
    def get_channels():
        for h in HEADERS:
            if 'csv' not in h:
                continue
            # ensure header is a digital or analog channel but not both
            assert ('nidaq' in h) ^ ('nidaq_digital' in h)
            if 'nidaq' in h:
                yield {
                    'type': 'analog',
                    'line': h['nidaq'],
                    'header': h['csv'],
                }
            else:
                yield {
                    'type': 'digital',
                    'line': h['nidaq_digital'],
                    'header': h['csv'],
                }
    channels = list(get_channels())
    # csv_path = './loadcell_tilt.csv'
    # clock sourcs Dev6/PFI6
    with ExitStack() as stack:
        # add the record event context first so it will set the stopped
        # event after all other context __exit__ methods are called
        # 
        # this should happen before any failable operation so the failed event will
        # be set in the case of a failure
        stack.enter_context(RecordEventContext(state))
        
        nidaq_channels = [x for x in HEADERS if 'nidaq' in x]
        digital_channels = [x for x in HEADERS if 'nidaq_digital' in x]
        assert len(nidaq_channels) + len(digital_channels) == len(channels)
        
        if state.live.enabled:
            if state.live.calibrated:
                assert state.live.bias_file is not None
                cal: Any = (1, state.live.bias_file)
            else:
                cal = None
            
            spawn_process(_live_view,
                state=state,
                sample_rate=clock_rate,
                downsample_to=100,
                # downsample_to=None,
                seconds=live_view_seconds,
                # update_hz=0.25,
                update_hz=4,
                # update_hz=1000,
                calibrate=cal,
            )
        
        if not mock:
            import nidaqmx # pylint: disable=import-error
            # pylint: disable=import-error
            from nidaqmx.constants import LineGrouping, Edge, AcquisitionType, WAIT_INFINITELY
            
            task: Any = stack.enter_context(nidaqmx.Task())
            digital_task: Any = stack.enter_context(nidaqmx.Task())
            
            # task.ai_channels.add_ai_voltage_chan("Dev6/ai18:23,Dev6/ai32:39,Dev6/ai48:51")
            # task.ai_channels.add_ai_voltage_chan("Dev6/ai8:10")
            for h in nidaq_channels:
                task.ai_channels.add_ai_voltage_chan(h['nidaq'])
            for h in digital_channels:
                digital_task.di_channels.add_di_chan(h['nidaq_digital'], line_grouping = LineGrouping.CHAN_PER_LINE)
            
            # task.timing.cfg_samp_clk_timing(1000, source = "", sample_mode= AcquisitionType.CONTINUOUS, samps_per_chan = 1000)
            # set sample rate slightly higher than actual sample rate, not sure if that's needed
            # clock_source = "/Dev6/PFI6"
            # clock_source = ""
            # samps_per_chan determines buffer size with CONTINUOUS sample_mode
            task.timing.cfg_samp_clk_timing(clock_rate, source=clock_source, sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=nidaq_buffer_size)
            
            # NOTE: CONTINUOUS sample mode only works with port 0
            digital_task.timing.cfg_samp_clk_timing(clock_rate, source='ai/SampleClock', sample_mode=AcquisitionType.CONTINUOUS, samps_per_chan=nidaq_buffer_size)
            
            # task.triggers.start_trigger.cfg_dig_edge_start_trig("/Dev6/PFI8", trigger_edge=Edge.RISING)
        else:
            WAIT_INFINITELY = None
            class MockTask:
                def __init__(self, *, digital: bool = False):
                    self.i = 0
                    self.digital = digital
                    if digital:
                        hz = 0.5
                        self._step = 1/clock_rate * hz
                    else:
                        self._step = 0.0001
                    
                    class InStream:
                        avail_samp_per_chan = 1
                    self.in_stream = InStream()
                
                def start(self):
                    pass
                
                def count(self):
                    i = self.i
                    self.i += self._step
                    if self.i > 1:
                        self.i = 0
                    return i
                
                def read(self, samples_per_channel, _timeout):
                    time.sleep(samples_per_channel/clock_rate)
                    from random import randrange
                    val = self.count()
                    def gen_samples(meta, col_i):
                        if self.digital:
                            return [val > 0.5 for _ in range(samples_per_channel)]
                            # return [True for _ in range(samples_per_channel)]
                        return [self.count()+(col_i/3) for _ in range(samples_per_channel)]
                    if self.digital:
                        row = [
                            # [1 for _ in range(SAMPLE_BATCH_SIZE)]
                            # [i for i in range(SAMPLE_BATCH_SIZE)]
                            # [self.count()+(j/3) for _ in range(samples_per_channel)]
                            gen_samples(meta, i)
                            for i, meta in enumerate(digital_channels)
                        ]
                    else:
                        row = [
                            # [1 for _ in range(SAMPLE_BATCH_SIZE)]
                            # [i for i in range(SAMPLE_BATCH_SIZE)]
                            # [self.count()+(j/3) for _ in range(samples_per_channel)]
                            gen_samples(meta, j)
                            for meta, j in zip(nidaq_channels, range(len(nidaq_channels)))
                        ]
                    # emulated nidaqmx behavior with one channel
                    if len(row) == 1:
                        row = row[0]
                    return row
            task = MockTask()
            digital_task = MockTask(digital=True)
        
        if csv_path is not None:
            csv_file = stack.enter_context(open(csv_path, 'w+', newline='', encoding='utf8'))
            writer = csv.writer(csv_file)
            
            if output_meta is not None:
                # write metadata
                writer.writerow(['v', '1'])
                writer.writerow([json.dumps(output_meta, indent=2)])
            
            writer.writerow(csv_headers + ['Timestamp'])
        
        task.start()
        digital_task.start()
        
        sample_i = 0
        for batch_i in count(0):
            if batch_i == 0:
                # no timeout on first read to wait for start trigger
                # read_timeout = WAIT_INFINITELY
                # actually a timeout since start trigger isn't being used
                # short timeout for first sample so an error happens quickly if
                # plexon is not collecting data (required to enable the 40khz clock)
                read_timeout = 1
            else:
                read_timeout = 10 # default in nidaqmx
            
            # print(task.in_stream.avail_samp_per_chan)
            # sample_batch_size = 1000
            sample_batch_size = task.in_stream.avail_samp_per_chan or 1
            data = task.read(sample_batch_size, read_timeout)
            # digital_batch_size = 
            digital_data = digital_task.read(sample_batch_size, read_timeout)
            # digital_data = [False]
            # print(len(data))
            # continue
            timer_start = time.perf_counter()
            
            # if there is only one channel nidaqmx returns [ch1] in stead of [[ch1], [ch2]]
            # convert the data into a consistant format regardless of channel count
            if type(data[0]) is not list:
                assert len(nidaq_channels) == 1
                data = [data]
            else:
                assert len(nidaq_channels) != 1
            if type(digital_data[0]) is not list:
                assert len(digital_channels) == 1
                digital_data = [digital_data]
            else:
                assert len(digital_channels) != 1
            
            # if state.live.enabled:
            #     try:
            #         state.live.queue.put(data, block=False)
            #     except Full:
            #         print("live view queue full, data is being discarded (will still be written to csv)")
            
            # import util_multiprocess
            with state.chan_lock:
                for meta, chan in zip(nidaq_channels, data):
                    if 'digital_line' in meta:
                        val = chan[-1]
                        val = val > 2.2
                        assert type(val) == bool
                        set_digital_line(meta['digital_line'], val)
                    if 'analog_channel' in meta:
                        # assert len(chan) == 1
                        val = chan[0]
                        assert type(val) == float
                        ch = state.analog_channels[meta['analog_channel']]
                        # with ch._lock:
                        for x in chan:
                            ch._write_sample(x)
                        # state.analog_channels[meta['analog_channel']].write_sample(val)
                for meta, chan in zip(digital_channels, digital_data):
                    if 'digital_line' in meta:
                        val = chan[-1]
                        assert type(val) == bool
                        set_digital_line(meta['digital_line'], val)
                    if 'analog_channel' in meta:
                        # assert len(chan) == 1
                        # val = 1.0 if chan[0] else 0.0
                        # assert type(val) == float
                        ch = state.analog_channels[meta['analog_channel']]
                        for x in chan:
                            ch._write_sample(1.0 if x else 0.0)
                        # state.analog_channels[meta['analog_channel']].write_sample(val)
            
            
            for i in range(sample_batch_size):
                def gen_row():
                    # indexes for analog and digital channels
                    a_i = 0
                    d_i = 0
                    for c in channels:
                        if c['type'] == 'analog':
                            x = data[a_i][i]
                            yield x
                            a_i += 1
                        elif c['type'] == 'digital':
                            x = digital_data[d_i][i]
                            yield 1 if x else 0
                            d_i += 1
                        else:
                            assert False
                    
                    assert a_i == len(data)
                    assert d_i == len(digital_data)
                    
                    # for meta, chan in zip(nidaq_channels, data):
                    #     if 'csv' in meta:
                    #         val = chan[i]
                    #         if type(val) == bool:
                    #             yield 1 if val else 0
                    #         else:
                    #             yield val
                    yield sample_i / clock_rate
                
                if csv_path is not None:
                    writer.writerow(gen_row())
                
                sample_i += 1
            
            timer_end = time.perf_counter()
            # print(timer_end - timer_start)
            if state.live.enabled:
                try:
                    state.live.queue.put({
                        'proc_time': timer_end - timer_start,
                        'batch_size': sample_batch_size,
                    }, block=False)
                except Full:
                    # print("timing queue full")
                    pass
            
            if num_samples is not None and sample_i >= num_samples:
                break
            if state.stopping.is_set():
                break
