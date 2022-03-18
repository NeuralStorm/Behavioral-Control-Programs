
for devices besides the voltage conversion board the pinouts can be found in the manual for the given device. note that for the for the USB pinout information is in the SCB-68 quick reference for the SCSI version

the force/toque sensors connect to the nidaq directly via a scsi connector. the SCB-68 breakout board is daisy chained through the sensor amplifier  
"CONNECTOR 0" on the nidaq connects to "Connector 0 to DAQ Card" on the amplifier  
"CONNECTOR 1" on the nidaq connects to "Connector 1 to DAQ Card" on the amplifier  
"Connector 1 from User" connects to the SCB-68 breakout board

## devices

pin numbers are prefixed based on the device/port, e.g. tim(5) is pin 5 on the plexon timing board

---
`conv` - voltage conversion board, see [the image of the conversion board](voltage_conversion_board/voltage_conversion_board_pinout.png) for pin numbers

---
`downsample` - clock downsampling board

port numbers correspond to the labels on the downsampling board

---
`nidaq` - SCB-68 breakout board on conenctor 0 of the NI 6225 nidaq connected to the tilt computer

port numbers will have both the number labeled on the breakout board and the pin's name  
e.g. `nidaq(P0.0|52)` is pin P0.0 and labeled 52 on the SCB-68 breakout board

in cases where pins have multiple functions only the relevent one will be written, e.g. `PFI 6 / P1.6` will be listed as `PFI 6`

---
`motor` - SV7-Si motor controller IN/OUT1

port numbers will have both the port number and part or all of the name, e.g. `motor(Y2|15)` is port 15 which has the name "Y2 / MOTION"

the SI software refers to pins Y1-Y4 as output 1-4, X1-X4 as input 1-4. these terms may be used interchangably in some places

---
`tim` - plexon TIM board d-sub connector

port numbers will have both the port number and the name, e.g. `tim(40 kHz|5)` is port 5 which is named "40 kHz"

---
`din` - plexon DIN board port A

port numbers will have both the port number and part or all of the name, e.g. `din(Data 1|1)` is port 1 which has the name "Data 1"

---
---

## ground
the following pins should all be connected together

`nidaq(AI GND|67)`  
`nidaq(D GND|12)`  
`conv(5)`  
`conv(18)` (optional)  
`conv(16)` (optional)  
`downsample(In -)`
`downsample(Pwr -)`
`downsample(out -)`
`motor(GND|19)`  
`din(Ground|19)`  
`tim(GND|15)`

## power
the nidaq, plexon, f/t sensor amp and motor controller have external power sources that need to be connected

`conv(1)` 5v  
`conv(2)` 12v  
`conv(17)` 24v (shared with the V+ connector on the motor controller)

`downsample(Pwr +)` - `nidaq(+5V|8)`

## tilt type

`nidaq(P0.0|52)` - `conv(15)` - `din(Data 1|1)`  
`conv(14)` - `motor(X3|7)`

`nidaq(P0.1|17)` - `conv(13)` - `din(Data2|2)`  
`conv(12)` - `motor(X4|6)`

`nidaq(P0.2|49)` - `conv(11)` - `din(Data3|3)`  
`conv(10)` - `motor(X5|5)`

## tilt trigger (sent by tilt computer to indicate a tilt should occur)

`nidaq(P0.3|47)` - `conv(9)`  
`conv(8)` - `motor(X6|4)`

## tilt start (sent by motor controller at the start of tilt)

`motor(Y2|15)` - `conv(4)`  
`conv(3)` - `nidaq(AI 8|34)` - `din(Data ready|22)`

## plexon start/sync signal

tbd, start signal was connected to `nidaq(P2.1|3)` and `nidaq(AI 9|66)` with the old plexon system

## inclinometer

the inclinometer should be connected to `nidaq(AI 10|31)`

## plexon clock

`tim(40 kHz|5)` - `downsample(In +)`  
`downsample(out +)` - `nidaq(PFI 6|5)`

