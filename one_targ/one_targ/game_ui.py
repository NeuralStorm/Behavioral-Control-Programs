
from typing import Optional, Any
import sys
import os
from math import pi, sin, cos
import random
import time
from pathlib import Path

def get_pos() -> tuple[int, int, int , int] | None:
    # -1920,0<-1920x1086
    # ^ x pos
    #       ^ y pos
    #          ^ width
    #               ^ height
    try:
        s = os.environ['pos']
    except KeyError:
        return None
    
    pos, size = s.split('<-')
    px, py = pos.split(',')
    px = int(px)
    py = int(py)
    sx, sy = size.split('x')
    sx = int(sx)
    sy = int(sy)
    
    return (px, py, sx, sy)

from kivy.config import Config as KivyConfig
_pos = get_pos()
if _pos is not None:
    KivyConfig.set('graphics', 'position', 'custom')
    KivyConfig.set('graphics', 'left', _pos[0])
    KivyConfig.set('graphics', 'top', _pos[1])
    KivyConfig.set('graphics', 'width', _pos[2])
    KivyConfig.set('graphics', 'height', _pos[3])

from kivy.app import App
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, ListProperty, StringProperty, BooleanProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock

from .config import Config

# these values get set in main
config: Config
game_state: Any

class Splash(Widget):
    def init(self, *args):
        self.args = args

class BackgroundOverlay:
    def __init__(self, color, *, window=Window):
        self.window = window
        self.original_color = window.clearcolor
        self.color = color
    
    def __enter__(self):
        self.original_color = self.window.clearcolor
        self.window.clearcolor = self.color
    
    def __exit__(self, *exc):
        self.window.clearcolor = self.original_color

class TargetOverlay:
    def __init__(self, target, color):
        self.target = target
        self._starting_color = target.color
        self.color = color
    
    def __enter__(self):
        self._starting_color = self.target.color
        self.target.set_color(self.color)
    
    def __exit__(self, *exc):
        self.target.set_color(self._starting_color)

class Target(Widget):
    
    color = [1, 1, 1, 1]
    _color = ListProperty([0,0,0,0])
    _rectangle_color = ListProperty([0,0,0,0])
    _triangle_color = ListProperty([0,0,0,0])
    triangle_points = ListProperty([500, 500, 510, 510, 490, 510])
    shape = 'circle'
    hidden = True
    
    def set_color(self, color):
        self.color = color
        self._update()
    
    def overlay(self, color):
        return TargetOverlay(self, color)
    
    def show(self):
        self.hidden = False
        self._update()
    
    def hide(self):
        self.hidden = True
        self._update()
    
    def _update(self):
        if self.shape == 'circle':
            self._color = self._get_color('circle')
        elif self.shape == 'square':
            self._rectangle_color = self._get_color('square')
        elif self.shape == 'triangle':
            self._triangle_color = self._get_color('triangle')
    
    def _get_color(self, shape):
        if self.hidden:
            return (0, 0, 0, 0)
        if self.shape != shape:
            return (0, 0, 0, 0)
        
        return self.color
    
    def set_size(self, size):
        self.size = size
    
    def move_px(self, pos):
        x, y = pos
        self.center = int(x), int(y)
        
        x, y = self.center
        hs = self.size[0] / 2 # half of size
        self.triangle_points = [
            x, y + hs,
            x - hs, y - hs,
            x + hs, y - hs,
        ]
    
    def point_is_within(self, pos):
        t_x, t_y = self.center
        c_x, c_y = pos
        
        shape = self.shape
        hs = self.size[0] / 2
        if shape == 'circle':
            d = ((t_x - c_x)**2 + (t_y - c_y)**2)**0.5
            return d <= hs
        elif shape == 'square':
            return abs(c_x - t_x) <= hs and abs(c_y - t_y) <= hs
        elif shape == 'triangle':
            # if not in bounding rectangle return false
            if not (abs(c_x - t_x) <= hs and abs(c_y - t_y) <= hs):
                return False
            
            # distance (y) from top of triangle
            from_top = t_y - c_y + hs
            # percent of width that is filled at y
            perc = from_top / (hs*2)
            # distance (x) touch can be from center while still being in triangle at y
            ok_dx = perc * hs
            if abs(t_x - c_x) > ok_dx:
                return False
            
            return True
        else:
            raise ValueError()

class PhotoMarker(Widget):
    color = ListProperty((0, 0, 0, 0))
    photo_marker = ObjectProperty(None)
    
    def on(self):
        self.color = 1, 1, 1, 1
    
    def off(self):
        self.color = 0, 0, 0, 1
    
    def set_color(self, r, g, b):
        _, _, _, a = self.color
        self.color = r, g, b, a
    
    def show(self):
        r, g, b, _ = self.color
        self.color = r, g, b, 1
    
    def hide(self):
        r, g, b, _ = self.color
        self.color = r, g, b, 0
    
    def reposition(self, root):
        # self.top = root.height
        self.top = root.top
        # self.right = root.width
        # self.bottom = root.y
        self.left = root.x

class COGame(Widget):
    center = ObjectProperty()
    target = ObjectProperty()
    
    cursor_px = {}
    cursor_start_px = {}
    
    center_target = ObjectProperty()
    periph_target = ObjectProperty()
    
    photo_marker = ObjectProperty()
    
    trial_counter = NumericProperty(0)
    
    def on_touch_down(self, touch):
        self.cursor_start_px[touch.uid] = touch.x, touch.y
        
        self.cursor_px[touch.uid] = touch.x, touch.y

    def on_touch_move(self, touch):
        self.cursor_px[touch.uid] = touch.x, touch.y

    def on_touch_up(self, touch):
        try:
            del self.cursor_px[touch.uid]
        except KeyError:
            pass
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.plexon: bool = config.plexon_enabled
        
        self.update_callback: Optional[Any] = None
        
        self.px_per_cm = config.px_per_cm
        
        self.center_target_rad = config.center_target_radius
        self.periph_target_rad = config.periph_target_radius
        
        self.corner_dist = config.corner_dist
        
        self.peripheral_target_param = (
            config.periph_target_shape,
            config.periph_target_color,
        )
        
        self.nudge_x, self.nudge_y = config.nudge
        
        self.size = self.width, self.height
        self.center_target_position = 0, 0
        
        # late initialized
        self.reward1: Any = None
        self.reward2: Any = None
        
        # game state
        self.periph_rel = 0, 0
        
        self._photodiode_off_time: Optional[float] = None
    
    def init(self):
        self.center_target.set_size((2*self.center_target_rad*self.px_per_cm,)*2)
        self.center_target.set_color((1,1,0,1))
        
        shape, color = self.peripheral_target_param
        self.periph_target.set_color(color)
        self.periph_target.shape = shape
        self.periph_target.set_size((2*self.periph_target_rad*self.px_per_cm,)*2)
        
        try:
            pygame.mixer.init()
        except:
            pass
        self.reward1 = SoundLoader.load('reward1.wav')
        self.reward2 = SoundLoader.load('reward2.wav')
        
        Window.bind(on_resize=self.handle_window_resize)
        self.handle_reposition()
    
    def handle_window_resize(self, _root, width, height):
        self.size = (width, height)
        self.handle_reposition()
    
    def handle_reposition(self):
        self.photo_marker.reposition(self)
        width, height = self.size
        self.center_target_position = \
            width//2 + self.nudge_x*self.px_per_cm, \
            height//2 + self.nudge_y*self.px_per_cm
        self.center_target.move_px(self.center_target_position)
        
        x, y = self.periph_rel
        x += self.center_target.center[0]
        y += self.center_target.center[1]
        self.periph_target.move_px((x, y))
    
    def move_periph(self, x: float, y: float):
        x *= self.px_per_cm
        y *= self.px_per_cm
        self.periph_rel = x, y
        self.handle_reposition()
    
    def update(self, ts):
        now = time.perf_counter()
        
        if self._photodiode_off_time is not None and now >= self._photodiode_off_time:
            self.photo_marker.off()
            self._photodiode_off_time = None
        
        if self.update_callback is not None:
            self.update_callback()
    
    def flash_marker(self, duration: float):
        self.photo_marker.on()
        self._photodiode_off_time = time.perf_counter() + duration
    
    def run_big_rew_sound(self):
        self.reward1 = SoundLoader.load('reward1.wav')
        self.reward1.play()
    
    def target_touched(self, target, *, start=False):
        if start:
            cursor_px = self.cursor_start_px
        else:
            cursor_px = self.cursor_px
        for _, pos in cursor_px.items():
            if target.point_is_within(pos):
                return True
        return False

class Manager(ScreenManager):
    _splash = ObjectProperty(None)
    config = ObjectProperty()
    
    def __init__(self, config_path: Path, config: Config):
        super(Manager, self).__init__()
        self.current = 'splash_start'
        self.config = config
        
        if config.skip_start:
            self.start_co_game()
    
    def start_co_game(self):
        self.current = 'game_screen'
        game = self.ids['game']
        game.init()
        # global config
        
        # global game_state
        # game_state = GameState(config)
        game.update_callback = game_state.progress_gen
        game_state.co_game = game
        
        Clock.schedule_interval(game.update, 1.0 / 5000)

class COApp(App):
    def __init__(self, config_path: Path, config: Config):
        super(COApp, self).__init__()
        self._config_path = config_path
        self._config = config
    
    def build(self, **kwargs):
        return Manager(self._config_path, self._config)
