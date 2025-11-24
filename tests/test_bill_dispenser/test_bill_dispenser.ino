/*
  Single Bill Dispenser (Timing-Based Only)
  - No sensors
  - Motor runs for a precise time to dispense exactly 1 bill
*/

// Motor 1
const int MOTOR1_IN1 = 4;
const int MOTOR1_IN2 = 5;
const int MOTOR1_ENA = 6;

// Motor 2
const int MOTOR2_IN3 = 7;
const int MOTOR2_IN4 = 8;
const int MOTOR2_ENB = 9;

// Motor speeds
const int MOTOR1_SPEED = 200;
const int MOTOR2_SPEED = 150;

// Time needed to dispense exactly ONE bill
// Adjust this value (start around 350–600 ms)
const int SINGLE_DISPENSE_MS = 450;

void setup() {
  Serial.begin(9600);

  pinMode(MOTOR1_IN1, OUTPUT);
  pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR1_ENA, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT);
  pinMode(MOTOR2_IN4, OUTPUT);
  pinMode(MOTOR2_ENB, OUTPUT);

  stopMotors();

  Serial.println("Single-Bill Dispenser Ready.");
  Serial.println("Press Enter to dispense one bill.");
}

void loop() {
  if (Serial.available() > 0) {
    char incomingByte = Serial.read();

    if (incomingByte == '\n') {
      dispenseOneBill();
    }
  }
}

void dispenseOneBill() {
  Serial.println("--- Dispensing 1 bill ---");

  // Run motors forward
  digitalWrite(MOTOR1_IN1, HIGH);
  digitalWrite(MOTOR1_IN2, LOW);
  analogWrite(MOTOR1_ENA, MOTOR1_SPEED);

  digitalWrite(MOTOR2_IN3, HIGH);
  digitalWrite(MOTOR2_IN4, LOW);
  analogWrite(MOTOR2_ENB, MOTOR2_SPEED);

  Serial.print("Motors running for ");
  Serial.print(SINGLE_DISPENSE_MS);
  Serial.println(" ms");

  delay(SINGLE_DISPENSE_MS);

  stopMotors();

  Serial.println("--- 1 bill dispensed ---");
}

void stopMotors() {
  digitalWrite(MOTOR1_IN1, LOW);
  digitalWrite(MOTOR1_IN2, LOW);
  analogWrite(MOTOR1_ENA, 0);

  digitalWrite(MOTOR2_IN3, LOW);
  digitalWrite(MOTOR2_IN4, LOW);
  analogWrite(MOTOR2_ENB, 0);

  Serial.println("Motors stopped");
}
