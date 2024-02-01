
import os
import termios

from .. import DigitalOutput

def _prep_port(fd):
    # https://github.com/pyserial/pyserial/blob/31fa4807d73ed4eb9891a88a15817b439c4eea2d/serial/serialposix.py#L410
    # https://man7.org/linux/man-pages/man3/termios.3.html
    
    orig_attr = termios.tcgetattr(fd)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = orig_attr
    
    cflag |= (termios.CLOCAL | termios.CREAD)
    lflag &= ~(termios.ICANON | termios.ECHO | termios.ECHOE |
                termios.ECHOK | termios.ECHONL |
                termios.ISIG | termios.IEXTEN)
    
    for flag in ('ECHOCTL', 'ECHOKE'):  # netbsd workaround for Erk
        if hasattr(termios, flag):
            lflag &= ~getattr(termios, flag)
    oflag &= ~(termios.OPOST | termios.ONLCR | termios.OCRNL)
    iflag &= ~(termios.INLCR | termios.IGNCR | termios.ICRNL | termios.IGNBRK)
    
    if hasattr(termios, 'IUCLC'):
        iflag &= ~termios.IUCLC
    if hasattr(termios, 'PARMRK'):
        iflag &= ~termios.PARMRK
    
    _baudrate = 9600
    ispeed = ospeed = getattr(termios, 'B{}'.format(_baudrate))
    
    cflag &= ~termios.CSIZE
    cflag |= termios.CS8 # bytesize 8
    
    # CMSPAR = 0o10000000000  # Use "stick" (mark/space) parity
    # parity bits
    iflag &= ~(termios.INPCK | termios.ISTRIP)
    # cflag &= ~(termios.PARENB | termios.PARODD | CMSPAR)
    
    # xonxoff
    if hasattr(termios, 'IXANY'):
        iflag &= ~(termios.IXON | termios.IXOFF | termios.IXANY)
    else:
        iflag &= ~(termios.IXON | termios.IXOFF)
    
     # rtscts
    if hasattr(termios, 'CRTSCTS'):
        # if self._rtscts:
        #     cflag |= (termios.CRTSCTS)
        # else:
        cflag &= ~(termios.CRTSCTS)
    elif hasattr(termios, 'CNEW_RTSCTS'):   # try it with alternate constant name
        # if self._rtscts:
        #     cflag |= (termios.CNEW_RTSCTS)
        # else:
        cflag &= ~(termios.CNEW_RTSCTS)
    
    cc[termios.VMIN] = 0
    cc[termios.VTIME] = 0
    
    force_update = True
    if force_update or [iflag, oflag, cflag, lflag, ispeed, ospeed, cc] != orig_attr:
        termios.tcsetattr(
            # self.fd,
            fd,
            termios.TCSANOW,
            [iflag, oflag, cflag, lflag, ispeed, ospeed, cc])
    
    termios.tcflush(fd, termios.TCIFLUSH)

class BridgeOutput(DigitalOutput):
    def __init__(self):
        path = '/dev/serial/by-id/usb-Fake_Company_Serial_port_TEST-if00'
        self._fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        _prep_port(self._fd)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *exc):
        os.close(self._fd)
    
    def _send_command(self, cmd):
        cfd = self._fd
        cmd_buf = f'{cmd}\n'.encode()
        # print(cmd_buf)
        assert len(cmd_buf) < 64
        os.write(cfd, cmd_buf)
        res = None
        while not res:
            res = os.read(cfd, 1)
        assert res[-1] == b'\n'[0], res
        return res
    
    def water_on(self):
        self._send_command('on 2')
    
    def water_off(self):
        self._send_command('off 2')
