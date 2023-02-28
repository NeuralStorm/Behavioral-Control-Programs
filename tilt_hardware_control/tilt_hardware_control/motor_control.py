
from typing import List, Literal, Any, TypedDict, Dict
import time
from math import floor
from multiprocessing import Pipe, Event
from multiprocessing.synchronize import Event as EventT
from multiprocessing.connection import Connection
from contextlib import ExitStack

from util import get_logger
from util_multiprocess import spawn_process

logger = get_logger(__name__)

_PROTOCOL_BITS = [
    'default',
    'always_use_address_character',
    'ack_nack',
    'checksum',
    '_reserved',
    '3_digit_numeric_register_addressing',
    'checksum_type',
    'little_big_endian_in_modbus_mode',
    'full_duplex_in_rs_422',
]

# https://docs.python.org/3/library/typing.html#typing.TypedDict.__optional_keys__
class _TiltTypeReq(TypedDict):
    dps: float
    degrees: float

class TiltType(_TiltTypeReq, total=False):
    active_pin: str

def _to_counts(deg):
    """convert degrees to counts"""
    revs = deg / 360 # convert to revolutions
    revs *= 25 # 25:1 gearbox
    return revs * 10000

def _to_revs(deg):
    """converts degrees to revolutions"""
    # multiply by 25 for 25:1 gearbox
    return deg * 25 / 360

def _counts_to_degrees(counts):
    """convert counts to degrees"""
    #                   V counts per revolution (without gearbox)
    #                   |       V gearbox ratio
    #                   |       |    V revolutions / degree
    counts_per_degree = 10000 * 25 / 360
    return counts / counts_per_degree

class CommandError(Exception):
    pass

class ReadTimeout(Exception):
    pass

class SerialMotorControl:
    def __init__(self):
        
        import serial
        import serial.tools.list_ports
        port_list = list(serial.tools.list_ports.comports())
        open_ports = [comport.device for comport in port_list]
        if len(open_ports) != 1:
            found_port = None
            for p in port_list:
                if 'Prolific' in p.description:
                    found_port = p
            if found_port is None:
                for p in port_list:
                    print (p)
                raise ValueError(f"unexpected com ports available {open_ports}")
            else:
                # print(p.description)
                open_ports = [found_port.device]
        com_port: str = open_ports[0]
        
        self._ser = serial.Serial(com_port, baudrate=38400, timeout=1)
        
        # if communication fails 
        try:
            self._cmd('IP')
        except ReadTimeout:
            logger.info("changing baud rate to 38400")
            self._ser.baudrate = 9600
            self._change_baud_rate(38400)
        
        prot = self._get_protocol()
        prot_sparse = {k for k, v in prot.items() if v}
        if prot_sparse != {'ack_nack'}:
            logger.debug("protocal not set correctly, currently {}", prot)
            self._set_protocol({'ack_nack': True})
        
        # clear any pending commands/paused state
        self._cmd('SKD')
        
        # self._cmd('AC5400')
        # self._cmd('DE5400')
        self._cmd('AC40')
        self._cmd('DE40')
        # self._cmd('AC1')
        # self._cmd('DE1')
        self._cmd('VE0.05')
        self.feed_pos(0)
        
        # degrees per second and max angle in degrees of each tilt type
        # active pin is set high while the tilt of a given type is occuring when using wrapper
        self.tilt_types: Dict[str, TiltType] = {
            'slow_left': {
                'dps': 12.5,
                'degrees': 16,
                'active_pin': '/Dev6/port2/line3',
            },
            'fast_left': {
                'dps': 68,
                'degrees': 16,
                'active_pin': '/Dev6/port2/line5',
            },
            'slow_right': {
                'dps': 12.5,
                'degrees': -16,
                'active_pin': '/Dev6/port2/line2',
            },
            'fast_right': {
                'dps': 68,
                'degrees': -16,
                'active_pin': '/Dev6/port2/line4',
            },
        }
        # speed at which the platform returns to home after tilt_return or tilt_punish
        self.return_dps = 12.5
        # self.return_dps = 1
        # punish degrees per second
        self.punish_dps = 71.4
        
        self._current_tilt = None
    
    def _read_to(self, *, end=b'\r'):
        out = []
        while True:
            x = self._ser.read()
            if x == end:
                break
            if not x:
                raise ReadTimeout()
                # break
            out.append(x)
        
        return b''.join(out)
    
    def _cmd(self, c):
        if isinstance(c, str):
            c = c.encode('ascii')
        raw = b''.join([c, b'\r'])
        # print(raw)
        self._ser.write(raw)
        self._ser.flush()
        # res = ser.read(30)
        # res = text.readline()
        res = self._read_to()
        if res in [b'%', b'*']:
            pass # command ack
        elif b'=' in res:
            pass
        else:
            # print(c, res)
            raise CommandError(f"{c.decode('ascii')} {res.decode('ascii')}")
        # sleep(0.01)
        return res
    
    def _change_baud_rate(self, rate):
        if rate == 38400:
            self._ser.write(b'BR3\r')
        elif rate == 9600:
            self._ser.write(b'BR1\r')
        else:
            raise ValueError(f'invalid baud rate {rate}')
        self._ser.flush()
        time.sleep(0.5)
        self._ser.baudrate = rate
        try:
            res = self._read_to()
        except ReadTimeout:
            res = '<read timeout>'
        logger.debug("change baud rate {}", res)
    
    def _get_protocol(self):
        res = self._cmd('PR')
        num_str = res.strip().split(b'=')[1]
        x = int(num_str)
        out = {}
        for i, k in enumerate(_PROTOCOL_BITS):
            is_set = (x >> i) & 1
            out[k] = bool(is_set)
        
        return out
    
    def _set_protocol(self, prot):
        acc = 0
        for i, k in enumerate(_PROTOCOL_BITS):
            if prot.get(k):
                acc += 1 << i
        try:
            self._cmd(f'PR{acc}')
        except ReadTimeout:
            # read timeout expected if protocol hasn't been set
            pass
    
    def set_home(self):
        self._cmd('EP0')
        self._cmd('SP0')
    
    def close(self):
        self._ser.close()
    
    def set_velocity(self, deg_per_sec):
        self._cmd(f'VE{round(_to_revs(deg_per_sec), 4)}')
    
    def feed_pos(self, deg):
        self._cmd(f'FP{floor(_to_counts(deg))}')
    
    def tilt(self, tilt_type: str):
        """perform a tilt of type"""
        self._current_tilt = tilt_type
        self.set_velocity(self.tilt_types[tilt_type]['dps'])
        self._cmd('PS')
        self.feed_pos(self.tilt_types[tilt_type]['degrees'])
        self.feed_pos(0)
        self._cmd('CT')
    
    def tilt_return(self):
        """stop the current tilt and return to neutral"""
        self._cmd('SKD')
        self.set_velocity(self.return_dps)
        self.feed_pos(0)
    
    def tilt_punish(self):
        """move to end of tilt at punish_dps and return to neutral"""
        if self._current_tilt is None:
            return
        tilt = self.tilt_types[self._current_tilt]
        self._cmd('SKD')
        self.set_velocity(self.punish_dps)
        self.feed_pos(tilt['degrees'])
        self.set_velocity(self.return_dps)
        self.feed_pos(0)
    
    def get_pos(self) -> int:
        res = self._cmd('IP')
        pos = int(res.split(b'=')[1], 16)
        
        # apply two's compliment
        if pos > 1<<31:
            pos -= 1<<32
        
        return pos
    
    def stop(self):
        """present for compatability with MotorControl"""

class SerialMotorProcessError(Exception):
    def __init__(self, exc: Any):
        Exception.__init__(self, str(exc))

class SerialMotorProcessStuck(Exception):
    """Thrown if the motor control process does not exit in a timely mannery after being sent a stop command"""

def _wrapper_inner(pipe: Connection, start_event: EventT, mid_event: EventT, *, collect_positions: bool = False):
    with ExitStack() as stack:
        class ErrorHandler:
            def __enter__(self):
                pass
            def __exit__(self, *exc):
                if exc != (None, None, None):
                    # convert traceback to string so it can be pickled
                    pipe.send(['error', (exc[0], exc[1], str(exc[2]))])
        stack.enter_context(ErrorHandler())
        
        motor = SerialMotorControl()
        stack.callback(motor.close)
        
        # first two channels for tilt active and tilt mid
        channels = ['/Dev6/port2/line0', '/Dev6/port2/line1']
        tilt_pins = []
        for tilt_type, tilt_info in motor.tilt_types.items():
            if 'active_pin' in tilt_info:
                channels.append(tilt_info['active_pin'])
                tilt_pins.append(tilt_type)
        
        out_list_off = [False for _ in channels]
        
        import nidaqmx # type: ignore
        from nidaqmx.constants import LineGrouping # type: ignore
        task = stack.enter_context(nidaqmx.Task())
        task.do_channels.add_do_chan(','.join(channels), line_grouping = LineGrouping.CHAN_PER_LINE)
        task.start()
        
        state: Literal['idle', 'before_mid', 'after_mid'] = 'idle'
        
        while True:
            command: List[str] = pipe.recv()
            if command[0] == 'stop':
                return
            elif command[0] == 'tilt':
                _, tilt_type = command
                
                tilt_type_out_list = [tilt_type == pin_tilt_type for pin_tilt_type in tilt_pins]
                out_list_start = [True, False, *tilt_type_out_list]
                out_list_mid = [True, True, *tilt_type_out_list]
                
                motor.tilt(tilt_type)
                start_event.set()
                task.write(out_list_start)
                state = 'before_mid'
                position_log = []
                
                # last_pos = motor.get_pos()
                while state != 'idle':
                    if pipe.poll():
                        command: List[str] = pipe.recv()
                        if command == ['stop']:
                            motor.tilt_return()
                            return
                        
                        if command == ['return']:
                            motor.tilt_return()
                        elif command == ['punish']:
                            motor.tilt_punish()
                        else:
                            raise ValueError(f"Invalid command in tilt {command}")
                    
                    def parse_i32(hex_str):
                        val = int(hex_str, 16)
                        assert val < (1 << 32)
                        if val & (1<<31):
                            # 1 << 32 == (1 << 31) * 2
                            # subtract the most significant bit twice
                            val -= 1 << 32
                        
                        return val
                    
                    # aa = time.perf_counter()
                    if collect_positions:
                        # target_pos = parse_i32(motor._cmd('IP').split(b'=')[1])
                        encoder_pos = parse_i32(motor._cmd('IE').split(b'=')[1])
                        # target_pos = _counts_to_degrees(target_pos)
                        encoder_pos = _counts_to_degrees(encoder_pos)
                        target_pos = 0
                        # encoder_pos = 0
                        # print(target_pos, encoder_pos)
                        position_log.append((time.perf_counter(), target_pos, encoder_pos))
                    
                    # a = time.perf_counter()
                    queue_size = 63 - int(motor._cmd('BS').split(b'=')[1])
                    # b = time.perf_counter()
                    # print(b - aa, b - a)
                    # print(queue_size)
                    
                    if state == 'before_mid' and queue_size <= 1:
                        state = 'after_mid'
                        # motor.tilt_return()
                        mid_event.set()
                        task.write(out_list_mid)
                    
                    if queue_size <= 0:
                        task.write(out_list_off)
                        pipe.send(['tilt_done', position_log])
                        state = 'idle'
                    
                    # pos = motor.get_pos()
                    # # print(pos, motor._cmd('BS'))
                    
                    # if state == 'before_mid':
                    #     if abs(pos) < abs(last_pos):
                    #         state = 'after_mid'
                    #         task.write([True, True])
                    #     last_pos = pos
                    
                    # if pos == 0:
                    #     task.write([False, False])
                    #     state = 'idle'
                    #     pipe.send(['tilt_done'])

class SerialMotorOutputWrapper:
    """wraps SerialMotorControl and sets nidaq output based on state"""
    def __init__(self):
        pipe, child_pipe = Pipe()
        self._start_event: EventT = Event()
        self._mid_event: EventT = Event()
        self._proc = spawn_process(_wrapper_inner, child_pipe, self._start_event, self._mid_event)
        self._pipe: Connection = pipe
    
    def close(self):
        self._pipe.send(['stop'])
        self._proc.join(5)
        if self._proc.exitcode is None:
            raise SerialMotorProcessStuck()
    
    def wait_for_tilt_start(self):
        self._start_event.wait(timeout=5)
    
    def wait_for_tilt_finish(self):
        res = self._pipe.recv()
        if res[0] == 'error':
            raise SerialMotorProcessError(res[1])
        
        assert res[0] == 'tilt_done'
        _, position_log = res
        position_out = []
        for t, target_pos, actual_pos in position_log:
            position_out.append({
                't': t,
                'pos': actual_pos,
                'target': target_pos,
            })
        
        out = {
            'position': position_out,
        }
        
        return out
    
    def tilt(self, tilt_type: str):
        self._start_event.clear()
        self._mid_event.clear()
        if tilt_type == 'stop':
            return
        self._pipe.send(['tilt', tilt_type])
    
    def tilt_return(self):
        self._start_event.set()
        self._mid_event.set()
        self._pipe.send(['return'])
    
    def tilt_punish(self):
        self._start_event.set()
        self._mid_event.set()
        self._pipe.send(['punish'])
    
    def stop(self):
        pass

class MotorControl:
    def __init__(self, *, port: int = 1, mock: bool = False):
        self.mock: bool = mock
        
        if mock:
            self.task: Any = None
        else:
            import nidaqmx # type: ignore
            task = nidaqmx.Task()
            task.do_channels.add_do_chan(f"/Dev6/port{port}/line0:7")
            
            task.start()
            
            self.task = task
        
        """
        tilt type is signaled using the first 3 bits of the array for each tilt type
        the first 3 bits are connected to inputs 3, 4, 5 on the motor controller
        e.g. the array [1,1,0,1,0,0,0,0] would have inputs 3 and 4 high and input 5 low
        
        the fourth bit is connected to input 6
        
        the inputs are marked as X3, X4, X5 and X6 in the manual and
        pinout and as simply 3, 4, 5 and 6 in the SI programmer software
        
        a tilt is started by setting bits 3,4,5 to one of a set of specific sequences defined
        in the SI programmer script
        
        a tilt is stopped by bringing input 6 low (speculative)
        
        the start of tilt is signaled by output 2 (Y2) being brought high for 2ms
        """
        
        # variable name / number / strobe number / label in SI5 file
        self.tilt_types = {
            # tilt1 / 1 / 9 / tilt6
            # Slow Counter Clockwise
            'slow_left': [0,0,0,1],
            # tilt3 / 2 / 11 / tilt4
            # Fast Counter Clockwise
            'fast_left': [0,1,0,1],
            # tilt4 / 3 / 12 / tilt3
            # Slow Clockwise
            'slow_right': [0,0,1,1],
            # tilt6 / 4 / 14 / tilt1
            # Fast Clockwise
            'fast_right': [0,1,1,1],
        }
        self._state = [0,0,0,0,0,0,0,0]
        
        self.tilt('stop')
    
    def close(self):
        self.tilt('stop')
        if not self.mock:
            self.task.close()
    
    def _print_mock_debug(self, data):
        for k, v in self.tilt_types.items():
            if v == data:
                print(f"mock tilt {k}")
                return
        
        bin_str = "".join(reversed(f"{data[0]:0>8b}"))
        assert len(data) == 1
        print(f"mock tilt {bin_str}")
    
    def _update_output(self, data=None):
        if data is None:
            data = self._state
        
        assert len(data) == 8
        for x in data:
            assert x in [0, 1]
        
        num = 0
        for bit in reversed(data):
            num <<= 1
            num += bit
        data = [num]
        
        if not self.mock:
            self.task.write(data)
        else:
            self._print_mock_debug(data)
    
    def tilt(self, tilt_type: str):
        if tilt_type == 'stop':
            self.stop()
            return
        self._state[0:4] = self.tilt_types[tilt_type][0:4]
        
        self._update_output()
    
    def tilt_return(self):
        """stop the current tilt and return to neutral"""
        self._state[0:2] = [1, 0]
        self._update_output()
    
    def tilt_punish(self):
        self._state[0:2] = [1, 1]
        self._update_output()
    
    def stop(self):
        for i in range(len(self._state)):
            self._state[i] = 0
        self._update_output()
    
    def water_on(self):
        self._state[4] = 1
        self._update_output()
    
    def water_off(self):
        self._state[4] = 0
        self._update_output()
    
    def water(self, duration: float):
        self.water_on()
        time.sleep(duration)
        self.water_off()
