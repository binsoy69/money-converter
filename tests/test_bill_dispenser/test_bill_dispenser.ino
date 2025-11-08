/*
  Bill Dispenser Test for Arduino

  This sketch tests a bill dispenser mechanism using two DC motors controlled by an L298N motor driver.
  - It listens for the "Enter" key press on the Serial Monitor.
  - When triggered, it runs two motors in the same direction but at different speeds for a set duration.

  Board: Arduino Uno
  Motor Driver: L298N
*/

// --- Configuration ---

// Motor 1 connections (adjust pins as needed)
const int MOTOR1_IN1 = 4;
const int MOTOR1_IN2 = 5;
const int MOTOR1_ENA = 6; // PWM capable pin for speed

// Motor 2 connections (adjust pins as needed)
const int MOTOR2_IN3 = 7;
const int MOTOR2_IN4 = 8;
const int MOTOR2_ENB = 9; // PWM capable pin for speed

// Motor speeds (0-255)
const int MOTOR1_SPEED = 200; // ~78% power
const int MOTOR2_SPEED = 150; // ~59% power

// Dispense duration
const int DISPENSE_DURATION_MS = 10000; // 10 seconds

void setup() {
  // Initialize Serial communication
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port to connect. Needed for native USB port only
  }

  // Set motor control pins as outputs
  pinMode(MOTOR1_IN1, OUTPUT);
  pinMode(MOTOR1_IN2, OUTPUT);
  pinMode(MOTOR1_ENA, OUTPUT);
  pinMode(MOTOR2_IN3, OUTPUT);
  pinMode(MOTOR2_IN4, OUTPUT);
  pinMode(MOTOR2_ENB, OUTPUT);

  // Ensure motors are stopped at startup
  stopMotors();

  Serial.println("Bill Dispenser Test Ready.");
  Serial.println("Open Serial Monitor, set line ending to 'Newline', and press Enter to dispense.");
}

void loop() {
  // Check if there is data available to read from the serial port
  if (Serial.available() > 0) {
    // Read the incoming byte
    char incomingByte = Serial.read();

    // Check if the incoming byte is a newline character (sent when Enter is pressed)
    if (incomingByte == '\n') {
      dispense();
    }
  }
}

// Function to run the dispense cycle
void dispense() {
  Serial.print("--- Dispensing for ");
  Serial.print(DISPENSE_DURATION_MS / 1000);
  Serial.println(" seconds ---");

  // Set Motor 1 to run forward
  digitalWrite(MOTOR1_IN1, HIGH);
  digitalWrite(MOTOR1_IN2, LOW);
  analogWrite(MOTOR1_ENA, MOTOR1_SPEED);
  Serial.print("Motor 1 running at speed: ");
  Serial.println(MOTOR1_SPEED);

  // Set Motor 2 to run forward
  digitalWrite(MOTOR2_IN3, HIGH);
  digitalWrite(MOTOR2_IN4, LOW);
  analogWrite(MOTOR2_ENB, MOTOR2_SPEED);
  Serial.print("Motor 2 running at speed: ");
  Serial.println(MOTOR2_SPEED);

  // Wait for the specified duration
  delay(DISPENSE_DURATION_MS);

  // Stop the motors
  stopMotors();
  Serial.println("--- Dispense cycle complete ---");
}

// Function to stop both motors
void stopMotors() {
  // Stop Motor 1
  digitalWrite(MOTOR1_IN1, LOW);
  digitalWrite(MOTOR1_IN2, LOW);
  analogWrite(MOTOR1_ENA, 0);

  // Stop Motor 2
  digitalWrite(MOTOR2_IN3, LOW);
  digitalWrite(MOTOR2_IN4, LOW);
  analogWrite(MOTOR2_ENB, 0);
}
