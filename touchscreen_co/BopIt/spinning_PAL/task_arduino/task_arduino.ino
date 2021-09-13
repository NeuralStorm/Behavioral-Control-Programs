#include <SparkFun_TB6612.h>

// Motor params 
const int offset = 1;
#define STBY 0
#define E3_IN1 37
#define E3_IN2 38
#define E3_PWM 5
Motor motor_E3 = Motor(E3_IN1, E3_IN2, E3_PWM, offset, STBY);

// Connect to the two encoder outputs!
#define ENCODER_A   3
#define ENCODER_B   2

// These let us convert ticks-to-RPM
//#define GEARING_ENCODERMULT     260

bool motordir; 
int count = 0;  

// data reading variables 
char dio_data[1];
double target_count; 
int tc; 
int thresh=0;
int diff; 
int drivez = 100;
int mdrivez = -100;
char c; 

// IR sensor pin
const int IR_sensor_pin = 52; 

// FSR pins 
const int analog_FSR1 = A14;
const int analog_FSR2 = A15;

void interruptB() {
  motordir = digitalRead(ENCODER_A); 
  if (motordir) {
    count += 1; 
  } else {
    count -= 1; 
  }
}

void setup() {

  // Motor Params Setup // 
  Serial.begin(115200);           
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  pinMode(ENCODER_B, INPUT_PULLUP);
  pinMode(ENCODER_A, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENCODER_B), interruptB, RISING);
  delay(100);

  // IR sensor setup // 
  pinMode(IR_sensor_pin, INPUT_PULLUP);
}

void loop() {
  if (Serial.available() >= 1) {
    c = Serial.read();
    if (c=='d') {
      handle_word(); 
      target_count = target_count + 0.1;
      tc = (int) target_count;
      int ct_start = count; 
      go_to_target();
    }
  }
  print_serial();
  delay(5); // runs at 200 hz   
}

void go_to_target() {
  diff = abs(count - tc);
  
  while (diff > thresh) {

    // Keep track of lastPos
    int lastPos = count; 
    int lastTs = micros(); 
  
    if (diff > 10) {
      drivez = 100;
      mdrivez = -100;
    }
    else { 
      drivez = 50;
      mdrivez = -50;
    }
    
    if (count > tc) {
      motor_E3.drive(drivez, 10);
      motor_E3.brake();
    }

    else if (count < tc) {
      motor_E3.drive(mdrivez, 10);
      motor_E3.brake();
    }
    diff = abs(count - tc);
    print_serial();
    delay(5); 

    // compute velocity 
    float vel = (count - lastPos) / (micros() - lastTs); 
    
  }
}

void print_serial() {
  // IR sensor pin //
  Serial.print(digitalRead(IR_sensor_pin)); 
  Serial.print("\t"); 

  // FSR 1 // 
  Serial.print(analogRead(analog_FSR1)); 
  Serial.print("\t"); 

  // FSR 2 // 
  Serial.print(analogRead(analog_FSR2)); 
  Serial.print("\t"); 

  // Wheel location 
  Serial.println(count); 
}

void handle_word() {
  Serial.readBytes(dio_data, 1);
  char d1 = dio_data[0];
  byte data_byte = dio_data[0];
  target_count = 0; 
  
  for (int bit_idx = 0; bit_idx < 8; bit_idx += 1) {
      if (bitRead(data_byte, bit_idx)==1) {
        target_count += pow(2, bit_idx); 
      }
  }
}
