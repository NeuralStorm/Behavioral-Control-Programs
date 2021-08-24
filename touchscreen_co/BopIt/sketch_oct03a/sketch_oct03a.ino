/* 
  IR Breakbeam sensor demo!
*/

#define IR_SENSORPIN 2 //7
#define LEDPIN 6 //2
#define BUTTON 4
char LED;
int FlexForcePin = A0;
int LED_status = 0;
int sensorState = 0, lastState = 1;
int broken = 0;
int force = 0;

void setup() {
  // initialize the LED pin as an output:
  pinMode(LEDPIN, OUTPUT);      
  // initialize the sensor pins as an input:
  pinMode(IR_SENSORPIN, INPUT);    
  pinMode(BUTTON, INPUT);
  digitalWrite(IR_SENSORPIN, HIGH); // turn on the pullup
  Serial.begin(9600);
}

void loop(){
  if (Serial.available() >= 1) {
    LED = Serial.read();
    Serial.println(LED);
//    
    // TURNS OFF: 
    if ((LED == 'm') && (LED_status == 0)) {
      LED_status = 1;
      digitalWrite(LEDPIN, HIGH);
      }

    // TURNS ON LED: 
    else if ((LED == 'n') && (LED_status == 1)) {
      LED_status = 0;
      digitalWrite(LEDPIN, LOW);
      }
    }
  // Dummy variability for force
  force = analogRead(FlexForcePin);
  Serial.print(force);
  Serial.print("/t");
  
  // read the state of the IR sensor value:
  sensorState = digitalRead(IR_SENSORPIN);
  if (sensorState && !lastState) {
    broken = 0;
  }
  else if (!sensorState && lastState) {
    broken = 1;
  }
  lastState = sensorState;

  Serial.print(broken);
  Serial.print("/t");

  // read the state of the button
  Serial.print(digitalRead(BUTTON));
  Serial.println("/t");
  delay(5); 
}
