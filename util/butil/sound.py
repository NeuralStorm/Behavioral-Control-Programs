
from typing import Any
from os import PathLike
from pathlib import Path

try:
    import winsound
except ImportError:
    winsound = None # type: ignore

try:
    import pygame
except ImportError:
    pygame = None # type: ignore

class SoundProvider:
    def play_file(self, path: PathLike):
        raise NotImplementedError()
    
    def stop(self):
        pass

class Silent(SoundProvider):
    def play_file(self, path):
        pass

class PygameSound(SoundProvider):
    def __init__(self):
        import pygame
        self._pygame = pygame
        pygame.mixer.init()
        
        self.sounds = {}
    
    def play_file(self, path):
        p = Path(path)
        try:
            sound = self.sounds[p]
        except KeyError:
            sound = self._pygame.mixer.Sound(file=p)
            self.sounds[p] = sound
        
        sound.play()
    
    def stop(self):
        self._pygame.mixer.stop()

class WinSound(SoundProvider):
    def __init__(self):
        import winsound
        self._winsound: Any = winsound
    
    def play_file(self, path):
        winsound = self._winsound
        p = Path(path)
        winsound.PlaySound(
                str(p),
                winsound.SND_FILENAME + winsound.SND_ASYNC + winsound.SND_NOWAIT,
        )
    
    def stop(self):
        winsound = self._winsound
        winsound.PlaySound(None, winsound.SND_PURGE)

def get_sound_provider(*, disable = False) -> SoundProvider:
    if disable:
        return Silent()
    
    try:
        import pygame
    except ImportError:
        pass
    else:
        return PygameSound()
    
    try:
        import winsound
    except ImportError:
        pass
    else:
        return WinSound()
    
    raise ValueError()
