/*********************************************************
  This just sends out a 5v 50hz trigger pulse for running the cameras
**********************************************************/

int sIn=0;
int camTriggers = 0;
int triggerPin1 = 4;
int triggerPin2 = 5;
//
//int mcsTriggers = 0;
//int mcs_triggerPin = 7;


///////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////

void setup() {
  Serial.setTimeout(5); //this will make the Arduino wait a max of only 5ms per incoming set of serial data, before moving on

  while (!Serial);        // needed to keep leonardo/micro from starting too fast!

  Serial.begin(9600);

  pinMode (triggerPin1,OUTPUT);
  pinMode (triggerPin2,OUTPUT);
  //pinMode (mcs_triggerPin,OUTPUT);

  // This will wait for the matlab connection before running the script

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  establishContact();  // send a byte to establish contact until receiver responds

  digitalWrite (triggerPin1,1); // Trigger phase is low on cameras
  digitalWrite (triggerPin2,1);

}

///////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////

void loop() {

//////////////////////////////////////////
// Check for input
  if (Serial.available() != 0) {

    // Read the input and then clear it
    sIn = Serial.parseInt();
    while (Serial.available() != 0) {
      Serial.read();
    }

    
    if (sIn == 1) { // run at 50 hz
      Serial.println("Camera started at 50hz");
     camTriggers=1 ;
    }
    
    else if (sIn == 2) { // run at 2 hz
      Serial.println("Camera started at 2hz");
      camTriggers=2 ;   
    }
    
    else if (sIn == 0) { // stop triggers
      camTriggers=0 ;   
      Serial.println("Camera stopped");
    }
    
    else if (sIn == 3) { // trigger MCS stim 
      Serial.println("MCS started");
      mcsTriggers=1 ;   
    }
    
    else if (sIn == 4) { // trigger MCS stim 
      Serial.println("MCS stopped");
      mcsTriggers=0 ;   
    }
    
    
  }
  ////////////////////////////////////////
  
//////////////////////////
// Control Cameras 
    if (camTriggers == 1) { // run at 50 hz
      digitalWrite(triggerPin1,0);
      digitalWrite(triggerPin2,0);
      //Serial.println ("0");
      delay (1);
      digitalWrite(triggerPin1,1);
      digitalWrite(triggerPin2,1);
      //Serial.println ("1");
      delay (19);      
    }

    else if (camTriggers == 2) { // run at 2 hz
      digitalWrite(triggerPin1,0);
      digitalWrite(triggerPin2,0);
      //Serial.println ("0");
      delay (1);
      digitalWrite(triggerPin1,1);
      digitalWrite(triggerPin2,1);
      //Serial.println ("1");
      delay (499);      
    }
    

    else if (camTriggers == 0) { //
      
      // do nothing
      //Serial.println ("1");
  }

  ///////////////////////// 

///////////////////////////
  // Control MCS

//  if (mcsTriggers == 1) { // trigger the MCS stim
//    
//      digitalWrite(mcs_triggerPin,1);
//  }
//  else {
//    digitalWrite(mcs_triggerPin,0);
//  }
//
//}
//////////////////////////////////


void establishContact() {
  int flipper = 0;

  Serial.println ("Waiting for serial input");

  while (Serial.available() <= 0) {

    delay(300);

    if (flipper == 1) {
      digitalWrite(LED_BUILTIN, HIGH);
      flipper = 0;
    }
    else {
      digitalWrite(LED_BUILTIN, LOW);
      flipper = 1;
    }
  }

  // This will read until the buffer is clear
  while (Serial.available() != 0) {
    Serial.read();
  }
  Serial.println("Connected");

}

