// Arduino: 22 --> 46
// Pinout: 1 --> 25

// BYTE A PINOUT BYTEs : [7, 6, 5, 4, 3, 2, 1, 0]
// BYTE A PINOUT DB25  : [9, 21, 8, 20, 7, 19, 6, 18]
// BYTE A PINOUT ARDUINO: [30, 42, 29, 41, 28, 40, 27, 39]

// Make sure DB25, PIN 5 = GND
// Make sure ARD GND --> DB25

int led = 13;
char c;
char d;
char dio_data[1]; // One byte
//int data_pins[] = {30, 42, 29, 41, 28, 40, 27, 39};
int data_pins[] = {39, 27, 40, 28, 41, 29, 42, 30};
int strobe = 36;
String inString = "";

void setup () {
  Serial.begin(115200);
  
  // initialize the output pins
  for (int k = 0; k < (sizeof(data_pins)/sizeof(int)); k += 1) {
    pinMode(data_pins[k], OUTPUT);
  }
  pinMode(strobe, OUTPUT);
  pinMode(led, OUTPUT);  
}

void loop() {
  if (Serial.available() >= 1) {
    c = Serial.read();
    if (c=='d') {
      Serial.readBytes(dio_data, 1);
      byte data_byte = dio_data[0];
      
      for (int bit_idx = 0; bit_idx < 8; bit_idx += 1) {
        byte mask = 1 << bit_idx;
        if (mask & data_byte) {
          digitalWrite(data_pins[bit_idx], HIGH);
        } else {
          digitalWrite(data_pins[bit_idx], LOW);         
        }
      }
    digitalWrite(strobe, HIGH);
    delay(1);
    digitalWrite(strobe, LOW);
    }
  }
}
