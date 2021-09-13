import serial

button_ard = serial.Serial(port='COM10', baudrate=9600)
button_ard.flushInput()
button_ard.write('open_door'.encode())