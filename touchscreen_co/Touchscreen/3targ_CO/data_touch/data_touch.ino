/*************************************************** 
  This is a library for the CAP1188 I2C/SPI 8-chan Capacitive Sensor

  Designed specifically to work with the CAP1188 sensor from Adafruit
  ----> https://www.adafruit.com/products/1602

  These sensors use I2C/SPI to communicate, 2+ pins are required to  
  interface
  Adafruit invests time and resources providing this open source code, 
  please support Adafruit and open-source hardware by purchasing 
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.  
  BSD license, all text above must be included in any redistribution
 ****************************************************/
 
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_CAP1188.h>

// Reset Pin is used for I2C or SPI
#define CAP1188_RESET  9

// CS pin is used for software or hardware SPI
#define CAP1188_CS  10

// These are defined for software SPI, for hardware SPI, check your 
// board's SPI pins in the Arduino documentation
#define CAP1188_MOSI  11
#define CAP1188_MISO  12
#define CAP1188_CLK  13

// For I2C, connect SDA to your Arduino's SDA pin, SCL to SCL pin
// On UNO/Duemilanove/etc, SDA == Analog 4, SCL == Analog 5
// On Leonardo/Micro, SDA == Digital 2, SCL == Digital 3
// On Mega/ADK/Due, SDA == Digital 20, SCL == Digital 21

// Use I2C, no reset pin!
Adafruit_CAP1188 cap = Adafruit_CAP1188();

// Or...Use I2C, with reset pin
//Adafruit_CAP1188 cap = Adafruit_CAP1188(CAP1188_RESET);

// Or... Hardware SPI, CS pin & reset pin 
// Adafruit_CAP1188 cap = Adafruit_CAP1188(CAP1188_CS, CAP1188_RESET);

// Or.. Software SPI: clock, miso, mosi, cs, reset
//Adafruit_CAP1188 cap = Adafruit_CAP1188(CAP1188_CLK, CAP1188_MISO, CAP1188_MOSI, CAP1188_CS, CAP1188_RESET);

int reg2;
float chan_ratio;
float chan_rat_thresh = 1.5;

// Baseline, fixed when start task;
float chan_bD=0;

void setup() {
  Serial.begin(9600);
  // Serial.println("CAP1188 test!");

  // Initialize the sensor, if using i2c you can pass in the i2c address
  // if (!cap.begin(0x28)) {
  if (!cap.begin()) {
    Serial.println("CAP1188 not found");
    while (1);
  }
  // Serial.println("CAP1188 found!");

  uint8_t reg = cap.readRegister( 0x1f ) & 0x0f;
  cap.writeRegister( 0x1f, reg | 0x4F ); // or whatever value you want - 101 1111, want 

  // Compute baseline: 
  for (int i=1; i < 200; i ++) {
    // Read from register: 
    byte reg = cap.readRegister( 0x11 );

    // Convert to float:
    if (bitRead(reg, 7) == 1) {
      reg2 = -128  ;
    }
    else {
      reg2 = 0;
    }

    for (int j=0; j < 7; j++) {
      if (bitRead(reg, j) == 1) {
        reg2 += pow(2, j);
      }
    }
    reg2 += 128;
    chan_bD=chan_bD+.005*reg2; 
    delay(10); // wait 10 ms
  }
}

void loop() {
  for (uint8_t i=1; i<2; i++) {
    byte reg = cap.readRegister( 0x11 );

    if (bitRead(reg, 7) == 1) {
      reg2 = -128  ;
    }
    else {
      reg2 = 0;
    }

    for (int j=0; j < 7; j++) {
      if (bitRead(reg, j) == 1) {
        reg2 += pow(2, j);
      }
    }

    reg2 += 128;
    
    // Get channel ratio: 
    chan_ratio = max(0, reg2) / chan_bD;
        
    Serial.print(reg2);
    Serial.print(" ");
    Serial.print(chan_ratio);
//    Serial.print(" ");
//    Serial.print(chan_bD);

    if (chan_ratio > chan_rat_thresh) {
      Serial.print("C"); Serial.print(i);
    }
    else {
      Serial.print("N"); Serial.print(i);
    }   
  }
  Serial.println();
  delay(50);
}

