
char door;

// button FSRs
const int FSR1_PIN = A2; // Pin connected to FSR/resistor divider
const int FSR2_PIN = A3; // Pin connected to FSR/resistor divider
int fsr1ADC = 0;
int fsr2ADC = 0;
const int FSR1_thresh = 30; // baseline seems to be 15-20
const int FSR2_thresh = 10; // baseline seems to be 0-1

// slide potentiometer
int potPin = 1;
int pos = 0;
int lastpos = -1;
int velo = 0;
int lastvelo = -1500;
int accel = -1500;
int T = 0;
int lastT = 0;
int lastT_register = 0;
int Tdiff = -1;
int doorthresh = 950; 

// motor
int enablePin = 6;
int in1Pin = 8;
int in2Pin = 9;
bool opendoor = false;
bool closedoor = false;
bool abortclose = false;

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode (A1, INPUT);
  Serial.begin( 9600 );

  // motor
  pinMode(in1Pin, OUTPUT);
  pinMode(in2Pin, OUTPUT);
  pinMode(enablePin, OUTPUT);
  digitalWrite( enablePin, LOW );
}

void loop() {
  
  // Listen for command
  if (Serial.available() >= 1) {
    door = Serial.read();
    if (door == 'm') {
      opendoor = true;
    } else if (door == 'n') {
      closedoor = true;
    }
  }
  
  // Determine and send the state of the button and the door
  fsr1ADC = analogRead(FSR1_PIN);
  fsr2ADC = analogRead(FSR2_PIN);
//  Serial.print(fsr1ADC);
//  Serial.print('/');
//  Serial.println(fsr2ADC);
  if ((fsr1ADC > FSR1_thresh) || (fsr2ADC > FSR2_thresh)) {
    Serial.print("button_active");
    Serial.print("\t");
  } else {
    Serial.print("button_inactive");
    Serial.print("\t");
  }
  pos = analogRead(potPin);    // read the value from the sensor
  if (pos < doorthresh) {
    Serial.print("door_open");
    Serial.println();
  } else {
    Serial.print("door_closed");
    Serial.println();
  } 

  // Open the door
  if (opendoor == true) {
    // Run the motor until the door is open
    while (pos > 670) {
      
      analogWrite(enablePin, 255);
      digitalWrite(in2Pin, HIGH);
      digitalWrite(in1Pin, LOW);
      pos = analogRead(potPin);    // read the value from the sensor
    }
    opendoor = false;
    analogWrite(enablePin, 0);
  }
  
  while (closedoor == true) {

    // Run the motor until the door is closed
    while ((pos < doorthresh) && (abortclose == false)) {
      analogWrite(enablePin, 255);
      digitalWrite(in2Pin, LOW);
      digitalWrite(in1Pin, HIGH);

      if (pos < doorthresh) {
        // Track acceleration to open the door if the slider decelerates
        T = millis();
        pos = analogRead(potPin);    // read the value from the sensor
        //Serial.println(pos);
        if (lastT != 0) {
          Tdiff = T - lastT_register;
          if (Tdiff > 5) {
            if (lastpos != -1) {
              velo = (pos - lastpos)/(Tdiff);
              if (lastvelo != -1500) {
                accel = 100*(velo - lastvelo)/(Tdiff);
                if (accel < 0) {
                  abortclose = true;
//                  Serial.print("abortclose");
                    //Serial.println(accel);
                }
              } // end if there is a previous velo calc
              lastvelo = velo;
            } // end if there is a previous pos calc
            lastpos = pos;
            lastT_register = T;
          }
        }
        lastT = T;
      }
    }

    if (abortclose == true) {
      // Run the motor until the door is open
      while (pos > 660) {
        analogWrite(enablePin, 255);
        digitalWrite(in2Pin, HIGH);
        digitalWrite(in1Pin, LOW);
        pos = analogRead(potPin);    // read the value from the sensor
      }
      analogWrite(enablePin, 0);
      abortclose = false;
      delay(1000);
    } else {
      analogWrite(enablePin, 0);
      closedoor = false;
    }
  }
}
