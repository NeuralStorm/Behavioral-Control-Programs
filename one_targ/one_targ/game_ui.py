
from typing import Optional, Any, Tuple
import sys
import os
from math import pi, sin, cos
import random
import time
from pathlib import Path
import gc

import pygame
from pygame._sdl2 import Window, Texture, Renderer

from .config import Config

class BackgroundOverlay:
    def __init__(self, color, *, window):
        self.window = window
        self.original_color = window.background_color
        self.color = color
    
    def __enter__(self):
        self.original_color = self.window.background_color
        self.window.background_color = self.color
    
    def __exit__(self, *exc):
        self.window.background_color = self.original_color

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

class PyGameTarget:
    def __init__(self):
        self.color = [0, 0, 0]
        
        self.center = 0, 0
        self.abs_pos = 0, 0
        self.size = 0
        self.shape = 'circle'
        self.hidden = True
        self.show_time = 0
    
    def set_color(self, color: tuple[int, int, int]):
        self.color = color
    
    def overlay(self, color):
        return TargetOverlay(self, color)
    
    def show(self):
        self.show_time = time.perf_counter()
        self.hidden = False
    
    def hide(self):
        self.hidden = True
    
    def render(self, screen, center_pos):
        if self.hidden:
            return
        
        cx, cy = center_pos
        rx, ry = self.center
        x = cx + rx
        y = cy + ry
        self.abs_pos = x, y
        
        s = self.size
        r = self.size / 2
        if self.shape == 'circle':
            pygame.draw.circle(screen, self.color, (x, y), r)
        elif self.shape == 'square':
            pygame.draw.rect(screen, self.color, (x-r, y-r, s, s))
        elif self.shape == 'triangle':
            points = [
                (x, y - r),
                (x-r, y+r),
                (x+r, y+r),
            ]
            pygame.draw.polygon(screen, self.color, points)
    
    def set_size(self, size):
        self.size = size
    
    def move_px(self, pos):
        self.center = pos
    
    def point_is_within(self, pos):
        t_x, t_y = pos
        c_x, c_y = self.abs_pos
        
        shape = self.shape
        hs = self.size / 2
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

class GameRenderer:
    def __init__(self, config: Config):
        self.periph_pos = 0, 0
        self.trial_counter = 0
        self.cursor_px = {}
        
        self.background_color = (0,0,0)
        
        self.center_target = PyGameTarget()
        self.periph_target = PyGameTarget()
        
        self.photodiode_flash_duration = config.photodiode_flash_duration
        self._photodiode_off_time = None
        
        px_per_cm = config.px_per_cm
        self.px_per_cm = px_per_cm
        cent_rad = config.center_target_radius
        self.nudge = config.nudge
        
        self.center_target.set_size(2*cent_rad*px_per_cm)
        self.center_target.set_color((255,255,0))
        nx, ny = self.nudge
        self.center_target.move_px((nx*px_per_cm, ny*px_per_cm))
        
        self.periph_target.set_color(config.periph_target_color)
        self.periph_target.shape = config.periph_target_shape
        self.periph_target.set_size(2*config.periph_target_radius*px_per_cm)
    
    def overlay(self, color):
        return BackgroundOverlay(color, window=self)
    
    def flash_marker(self, duration):
        if self.photodiode_flash_duration is not None:
            self._photodiode_off_time = time.perf_counter() + duration
    
    def move_periph(self, x: float, y: float):
        nx, ny = self.nudge
        x = (x+nx) * self.px_per_cm
        y = (y+ny) * self.px_per_cm
        self.periph_target.move_px((x, y))
    
    def target_touched(self, target, *, no_drag_in=True):
        for _, (start_pos, pos, show_time) in self.cursor_px.items():
            if show_time < target.show_time:
                continue
            if no_drag_in and not target.point_is_within(start_pos):
                continue
            if target.point_is_within(pos):
                return True
        return False
    
    def render(self, screen):
        now = time.perf_counter()
        w = screen.get_width()
        h = screen.get_height()
        
        center = w / 2, h / 2
        
        screen.fill(self.background_color)
        
        if self.photodiode_flash_duration is not None:
            if self._photodiode_off_time is not None:
                if now > self._photodiode_off_time:
                    self._photodiode_off_time = None
            if self._photodiode_off_time is not None:
                pygame.draw.rect(screen, (255,255,255), (0, 0, 100, 100))
            else:
                pygame.draw.rect(screen, (0,0,0), (0, 0, 100, 100))
        
        self.center_target.render(screen, center)
        self.periph_target.render(screen, center)

class MultiWindow:
    def __init__(self, *,
            title='-',
            fullscreen_position: Tuple[Tuple[int, int], Tuple[int, int]] | None = None):
        
        window = Window(title)
        window.resizable = True
        
        render = Renderer(window, vsync=False)
        
        surface = pygame.Surface(window.size)
        
        texture = Texture.from_surface(render, surface)
        
        window.show()
        
        self.window = window
        self._render = render
        self.surface = surface
        self._texture = texture
        
        self._size = window.size
        self._fullscreen_position = fullscreen_position
        self._fs_restore = window.position, window.size
        self.fullscreen = False
        
        if fullscreen_position is not None:
            self.toggle_fullscreen
    
    def destroy(self):
        # SIGSEGV was caused when render was cleaned up after window.destroy()
        # this makes it get cleaned up beforehand
        # it's very important no references to self._render are held externally
        # this is almost certainly very fragile and relies on the specifics of cpython's GC
        del self._texture
        gc.collect()
        assert len(gc.get_referrers(self._render)) == 1
        del self._render
        gc.collect()
        
        self.window.destroy()
    
    def toggle_fullscreen(self):
        if not self.fullscreen:
            if self._fullscreen_position is not None:
                self.window.borderless = True
                self._fs_restore = self.window.position, self.window.size
                pos, size = self._fullscreen_position
                self.window.position = pos
                self.window.size = size
            else:
                self.window.set_fullscreen()
            self.fullscreen = True
        else:
            if self._fullscreen_position is not None:
                self.window.position, self.window.size = self._fs_restore
                self.window.borderless = False
            else:
                self.window.set_windowed()
            self.fullscreen = False
    
    def _resize(self):
        del self._texture
        del self.surface
        self.surface = pygame.Surface(self.window.size)
        self._texture = Texture.from_surface(self._render, self.surface)
        self._size = self.window.size
    
    def present(self):
        if self._size != self.window.size:
            # print('resize')
            # self._size = self.window.size
            self._resize()
        
        self._texture.update(self.surface)
        self._texture.draw()
        self._render.present()
