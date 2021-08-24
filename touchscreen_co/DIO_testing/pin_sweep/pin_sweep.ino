
int data_pins[] = {22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46};
String inString = "";    // string to hold input

void setup() {
  for (int k = 0; k < (sizeof(data_pins)/sizeof(int)); k += 1) {
    pinMode(data_pins[k], OUTPUT);
  }
  Serial.begin(115200);
}

void loop(){
  while (Serial.available() >= 1) {
    int inChar = Serial.read();
    if (isDigit(inChar)) {
      // convert the incoming byte to a char and add it to the string:
      inString += (char)inChar;
    }
    if (inChar == '\n') {
      int pin = inString.toInt();
      Serial.println(pin);    
      inString = "";  

      // Turn this pin on, then off
      digitalWrite(pin, HIGH);
      delay(1000);
      digitalWrite(pin, LOW);
    }
  }
}

