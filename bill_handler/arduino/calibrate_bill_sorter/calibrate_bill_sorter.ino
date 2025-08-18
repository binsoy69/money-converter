// Calibration Helper for Bill Sorter
// Uses ultrasonic sensor + manual stepper jogging to determine bin distances

#include <AccelStepper.h>

const int DIR_PIN  = 3;
const int STEP_PIN = 4;
AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

// Ultrasonic pins
const int TRIG_PIN = 5;
const int ECHO_PIN = 6;

// Step Config
const int JOG_STEPS = 200;     // steps per jog command
const int SPEED = 400;

void setup() {
  Serial.begin(9600);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  stepper.setMaxSpeed(SPEED);
  stepper.setAcceleration(200);

  Serial.println("=== Calib Mode ===");
  Serial.println("Commands:");
  Serial.println("F - move forward");
  Serial.println("B - move backward");
  Serial.println("D - read distance");
  Serial.println("==================");
}

float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  float dist = duration * 0.034 / 2.0;
  return dist;
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();

    if (cmd == 'F') {
      Serial.println("[Jog] Forward");
      stepper.move(JOG_STEPS);
    } else if (cmd == 'B') {
      Serial.println("[Jog] Backward");
      stepper.move(-JOG_STEPS);
    } else if (cmd == 'D') {
      float d = readDistanceCm();
      Serial.print("[Distance] ");
      Serial.print(d);
      Serial.println(" cm");
    }
  }

  stepper.run();
}
