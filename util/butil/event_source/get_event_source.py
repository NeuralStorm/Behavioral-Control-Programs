
from typing import Tuple

from . import EventSource
from ..digital_output import DigitalOutput, get_digital_output

def get_event_source(source: str) -> Tuple[EventSource, DigitalOutput]:
    if source == '':
        source = 'none|none'
    if '|' in source:
        source_name, output_name = source.split('|', 1)
    else:
        source_name = source
        output_name = 'none'
    
    match source_name:
        case 'plexon':
            from butil.plexon import PlexonProxy#, PlexonOutput
            source_obj: EventSource = PlexonProxy() #type: ignore
        case 'neurokey':
            from butil.bridge.data_bridge import DataBridge
            from butil.event_source.process_source import SourceProxy
            source_obj = SourceProxy(DataBridge) #type: ignore
        case 'bridge':
            from ..bridge.direct_bridge import DirectBridge
            from ..event_source.process_source import SourceProxy
            source_obj = SourceProxy(DirectBridge)
        case 'none':
            source_obj = EventSource()
        case _:
            raise ValueError(f"Invalid event_source {source_name}")
    
    output_obj = get_digital_output(output_name)
    
    return source_obj, output_obj
