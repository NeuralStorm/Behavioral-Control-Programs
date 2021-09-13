import serial, struct
import time

def test(pause=0.1):
    # Init
    dio_port = serial.Serial(port='COM13', baudrate=115200)
    time.sleep(3)

    print('Start DIO')
    for i in range(1000):
        word_str = b'd' + struct.pack('<H', int(i % 256))
        dio_port.write(word_str)
        time.sleep(pause)