
import math
from collections import Counter
import statistics
from itertools import groupby

import tkinter as tk
from tkinter.font import Font
from PIL import Image, ImageTk

def _screenshot_region(x: int, y: int, w: int, h: int) -> Image.Image:
    import pyscreenshot as ImageGrab
    # x //= 2
    # y //= 2
    
    bbox = (x, y, x+w, y+h)
    
    # img = ImageGrab.grab(bbox=bbox, backend='grim')
    img = ImageGrab.grab(bbox=bbox)
    assert isinstance(img, Image.Image)
    return img

def screenshot_widgets(widgets, path):
    if not widgets:
        return
    
    # for widget in widgets:
    #     print('-')
    #     print(' ', widget.winfo_rooty())
    #     print(' ', widget.winfo_y())
    
    x_min = min(x.winfo_rootx() for x in widgets)
    x_max = max(x.winfo_rootx() + x.winfo_width() for x in widgets)
    y_min = min(x.winfo_rooty() for x in widgets)
    y_max = max(x.winfo_rooty() + x.winfo_height() for x in widgets)
    
    # print(x_min, x_max, y_min, y_max)
    
    img = _screenshot_region(x_min, y_min, x_max-x_min, y_max-y_min)
    img.save(path, 'PNG')

def screenshot_widget(widget, path):
    # x = widget.winfo_rootx() + widget.winfo_x()
    # y = widget.winfo_rooty() + widget.winfo_y()
    # x //= 2
    # y //= 2
    x = widget.winfo_rootx()
    y = widget.winfo_rooty()
    
    w = widget.winfo_width()
    h = widget.winfo_height()
    # x_ = x + widget.winfo_width()
    # y_ = y + widget.winfo_height()
    
    # bbox = (x, y, x_, y_)
    # print(bbox)
    # (4916, 3910, 5760, 4254)
    # 2604,1890 572x401
    
    img = _screenshot_region(x, y, w, h)
    # img = ImageGrab.grab(bbox=bbox, backend='grim')
    
    # img = ImageGrab.grab(backend='grim')
    img.save(path, 'PNG')

def sgroup(data, key):
    return groupby(sorted(data, key=key), key=key)

class InfoView:
    def __init__(self, root, *, monkey_images=None):
        self.monkey_images = monkey_images
        _orig_root = root
        self.window = tk.Toplevel(root)
        root = self.window
        root.geometry('800x600')
        root.bind('<Key>', self.key_handler)
        
        font = Font(family='consolas', size=15)
        self.label = tk.Label(root, text = '-', justify=tk.LEFT, font=font)
        self.label.pack(side=tk.TOP, anchor=tk.NW)
        
        self.rows = []
    
    def key_handler(self, event):
        if self.monkey_images is not None:
            self.monkey_images.KeyPress(event)
    
    @staticmethod
    def gen_histogram(events, *, h_range = None):
        if h_range is None:
            h_min = min(x['info']['action_duration'] for x in events)
            h_max = max(x['info']['action_duration'] for x in events)
            h_range = h_min, h_max
        
        def get_bin_ranges():
            start, end = h_range
            step = 0.5
            
            ws = start # window start
            we = start # window end
            while ws < end:
                ws = we
                if ws < 0.9 - 0.00001:
                    we = ws + 0.1
                elif ws < 1.1 - 0.00001:
                    we = ws + 0.2
                elif ws < 1.5 - 0.00001:
                    we = ws + 0.4
                else:
                    we = ws + step
                yield ws, we
        bins = {
            k: []
            for k in get_bin_ranges()
        }
        errors = Counter()
        
        for e in events:
            a_d = e['info']['action_duration']
            if a_d == 0 and e['info']['failure_reason'] is not None:
                errors[e['info']['failure_reason']] += 1
                continue
            for (bin_s, bin_e), bin_events in bins.items():
                if bin_s <= a_d < bin_e:
                    bin_events.append(e['info']['success'])
                    break
        
        # bins = {(start:float, end:float): [success:bool,...],...}
        # errors = {errors:str: error_count:int}
        return bins, errors
    
    @staticmethod
    def print_histogram(events):
        bins, errors = InfoView.gen_histogram(events)
        
        if errors:
            print('-'*20)
            error_col_width = max(len(e) for e in errors)
            for error, count in errors.items():
                print(f"{error.rjust(error_col_width)} {count}")
        
        for i, ((bin_s, bin_e), bin_events) in enumerate(bins.items()):
            if i%4==0:
                print('-'*20)
            events_str = "".join('O' if e else 'X' for e in bin_events)
            print(f"{bin_s:>5.1f}-{bin_e:<5.1f} {events_str}")
    
    @staticmethod
    def calc_end_info(events):
        n = len(events)
        def perc(count):
            if n == 0:
                return 0
            return count/n
        
        error_counts = Counter()
        for e in events:
            reason = e['info']['failure_reason']
            if reason is None:
                continue
            error_counts[reason] += 1
        error_info = {
            reason: {'count': c, 'percent': perc(c)}
            for reason, c in error_counts.items()
        }
        
        correct = [e for e in events if e['info']['success']]
        correct_n = len(correct)
        
        pull_durations = [e['info']['action_duration'] for e in events]
        pull_durations = [x for x in pull_durations if x != 0]
        
        def get_discrim_durations():
            for discrim, d_events in sgroup(events, lambda x: x['info']['discrim']):
                d_events = list(d_events)
                d_correct = [e for e in d_events if e['info']['success']]
                pull_durations = [
                    e['info']['action_duration']
                    for e in d_events
                ]
                count = len(pull_durations)
                pull_durations = [x for x in pull_durations if x != 0]
                out = {
                    'count': count, # number of times discrim appeared
                    'pull_count': len(pull_durations), # number of pulls in response to discrim
                    'correct_count': len(d_correct),
                    'min': min(pull_durations, default=0),
                    'max': max(pull_durations, default=0),
                    'mean': statistics.mean(pull_durations) if pull_durations else 0,
                    'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
                }
                yield discrim, out
        
        info = {
            'count': n,
            'correct_count': len(correct),
            'percent_correct': perc(correct_n),
            'action_duration': {
                'min': min(pull_durations, default=0),
                'max': max(pull_durations, default=0),
                'mean': statistics.mean(pull_durations) if pull_durations else 0,
                'stdev': statistics.pstdev(pull_durations) if pull_durations else 0,
            },
            'discrim_action_duration': dict(get_discrim_durations()),
            'errors': error_info,
        }
        
        return info
    
    def update_info(self, event_log):
        end_info = self.calc_end_info(event_log)
        
        out = []
        
        ad = end_info['action_duration']
        out.append("duration")
        out.append(f"  min-max: {ad['min']:.3f}-{ad['max']:.3f}")
        out.append(f"  mean: {ad['mean']:.3f} stdev: {ad['stdev']:.3f}")
        for discrim, dad in end_info['discrim_action_duration'].items():
            out.append(f"  {discrim} correct/pulls/count: {dad['correct_count']}/{dad['pull_count']}/{dad['count']}")
            out.append(f"    min-max: {dad['min']:.3f}-{dad['max']:.3f}")
            out.append(f"    mean: {dad['mean']:.3f} stdev: {dad['stdev']:.3f}")
        
        out.append(f"trials: {end_info['count']}")
        out.append("")
        errors = end_info['errors']
        if errors:
            error_col_width = max(len(e) for e in errors)
            for error, error_info in errors.items():
                count = error_info['count']
                perc = error_info['percent']
                out.append(f"{error.rjust(error_col_width)} {count:>2} {perc*100:.1f}%")
            out.append("")
        
        print("\n".join(out))
        self.label['text'] = "\n".join(out)
        # import pdb;pdb.set_trace()
        
        h_min = math.floor(ad['min'])
        h_max = math.ceil(ad['max'])
        bins, errors = self.gen_histogram(event_log, h_range=(h_min, h_max))
        
        for row in self.rows:
            row.destroy()
        self.rows = []
        
        for (start, end), results in bins.items():
            frame = tk.Frame(self.window,
                # width = canvas_x, height = canvas_y,
                height = 5,
                bd = 0, bg='yellow',
                highlightthickness=0,)
            frame.pack(side = tk.TOP, anchor='nw', fill='x')
            font = Font(size=15)
            label = tk.Label(frame, text = f"{start:.2f}-{end:.2f}", justify=tk.LEFT, font=font,
                width=10, bg='#F0B000')
            label.pack(side=tk.LEFT, anchor=tk.NW, expand=False)
            
            canvas = tk.Canvas(frame,
                # width = canvas_x, height = canvas_y,
                height=0,
                # background = '#D0D0D0',
                background = 'black',
                bd = 0, relief = tk.FLAT,
                highlightthickness=0,)
            canvas.pack(side = tk.LEFT, expand=True, fill='both')
            
            x = 0
            for res in results:
                canvas.create_rectangle(x, 0, x+10, 100,
                    fill='green' if res else 'red')
                x += 12
            
            self.rows.append(frame)

class GameFrame(tk.Frame):
    def __init__(self, parent, *,
        layout_debug: bool,
        hide_buttons: bool,
    ):
        self.parent = parent
        tk.Frame.__init__(self, parent)
        
        self._hide_buttons = hide_buttons
        
        self._layout_debug = layout_debug
        bgc = self._bgc
        
        ###Adjust width and height to fit monitor### bd is for if you want a border
        self.frame1 = tk.Frame(parent,
            # width = canvas_x, height = canvas_y,
            bd = 0, bg=bgc('yellow'),
            highlightthickness=0,)
        self.frame1.pack(side = tk.BOTTOM, expand=True, fill=tk.BOTH)
        self.cv1 = tk.Canvas(self.frame1,
            # width = canvas_x, height = canvas_y,
            background = bgc('#F0B000'), bd = 0, relief = tk.FLAT,
            highlightthickness=0,)
        self.cv1.pack(side = tk.BOTTOM, expand=True, fill=tk.BOTH)
        # self.cv1.grid(column=0, row=0, columnspan=2, rowspan=2, sticky='nsew')
        # self.frame1.columnconfigure(0, weight=1)
        # self.frame1.columnconfigure(1, weight=1)
        # self.frame1.rowconfigure(0, weight=1)
        # self.frame1.rowconfigure(1, weight=1)
        
        btn_frame = tk.Frame(parent,
            # width = canvas_x, height = canvas_y,
            # height=0 if hide_buttons else 100,
            bd = 0, bg=bgc('green'),
            highlightthickness=0)
        # btn_frame.pack_propagate(False)
        btn_frame.pack(side = tk.TOP, expand=False, fill=tk.BOTH)
        self._button_frame = btn_frame
        
        pos = 'top_left'
        # pos = 'bottom_right'
        # top left
        # pm_parent = self._button_frame
        # pm_side = tk.LEFT
        # bottom right
        if pos == 'top_left':
            # pm_parent = self.frame1
            pm_parent = self._button_frame
        elif pos == 'bottom_right':
            pm_parent = parent
        else:
            assert False
        # pm_side = tk.BOTTOM
        
        self.photo_marker = tk.Canvas(pm_parent,
            height=100, width=100,
            background='#000000',
            bd=0, relief=tk.FLAT,
            highlightthickness=0,
        )
        if pos == 'top_left':
            self.photo_marker.pack(side=tk.LEFT, expand=False)
        elif pos == 'bottom_right':
            self.photo_marker.place(x=0, y=-100, rely=1)
        else:
            assert False
        # self.photo_marker.grid(column=0, row=1)
    
    def _bgc(self, color: str) -> str:
        return color if self._layout_debug else 'black'
    
    def add_button(self, text, cmd):
        if self._hide_buttons:
            return
        b = tk.Button(
            # self.root, text = text,
            self._button_frame, text = text,
            height = 5,
            # width = 6,
            command = cmd,
            background = self._bgc('lightgreen'), foreground='grey',
            bd=1,
            relief = tk.FLAT,
            highlightthickness=1,
            highlightcolor='grey',
            highlightbackground='grey',
        )
        b.pack(side = tk.LEFT)
        # b.pack(side = tk.LEFT, fill=tk.BOTH)
    
    def set_marker_level(self, level):
        # self.photo_marker.create_rectangle(0, 0, 100, 100, fill='white')
        component = f"{round(level*255):2<0x}"
        color = '#' + component*3
        self.photo_marker.create_rectangle(0, 0, 100, 100, fill=color)
