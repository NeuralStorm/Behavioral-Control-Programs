
class DigitalOutput:
    def water_on(self):
        pass
    
    def water_off(self):
        pass
    
    def cineplex_start(self):
        pass
    
    def cineplex_stop(self):
        pass

def get_digital_output(mode: str):
    match mode:
        case 'plexdo':
            from .plexon import PlexonProxy, PlexonOutput
            return PlexonOutput()
        case 'bridge':
            from .bridge.output import BridgeOutput
            return BridgeOutput()
        case 'none':
            return DigitalOutput()
        case _:
            raise ValueError(f"Invalid digital output mode {mode}")
