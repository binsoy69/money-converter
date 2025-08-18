/*
  H-Bot Step Calibration Tool (with Distance Capture)
  Uses Stepper A (horizontal) only
  Commands:
    F           -> Jog forward (right) +200 steps
    B           -> Jog backward (left) -200 steps
    RESET       -> Reset step counter to 0 (use at HOME)
    POS?        -> Print current step count
    D           -> Print current ultrasonic distance in cm
    SAVE:50     -> Save current steps and distance as position for bin 50php
    REPORT      -> Print all saved values
*/

#include <AccelStepper.h>

// Stepper A pins
const int STEP_A_PIN = 2;
const int DIR_A_PIN  = 3;

// Ultrasonic pins
const int TRIG_PIN = 6;
const int ECHO_PIN = 7;

// Motor config (AccelStepper)
AccelStepper stepperA(AccelStepper::DRIVER, STEP_A_PIN, DIR_A_PIN);
const long JOG_STEPS = 200;  // adjust as needed for jog size

// Counter
long stepCounter = 0;

// Storage for step and distance
long pos_20_steps  = 0;
long pos_50_steps  = 0;
long pos_100_steps = 0;
long pos_200_steps = 0;
long pos_500_steps = 0;
long pos_1000_steps = 0;

float pos_20_dist  = 0.0;
float pos_50_dist  = 0.0;
float pos_100_dist = 0.0;
float pos_200_dist = 0.0;
float pos_500_dist = 0.0;
float pos_1000_dist = 0.0;

// Read ultrasonic distance
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  return (duration * 0.034 / 2.0);
}

// Movement function
void jog(bool forward, long steps) {
  stepperA.setMaxSpeed(2000);
  stepperA.setAcceleration(2000);
  long dirSteps = forward ? steps : -steps;
  stepperA.move(dirSteps);
  while (stepperA.distanceToGo() != 0) {
    stepperA.run();
  }
  stepCounter += forward ? steps : -steps;
}

// Save both step and distance
void savePosition(const String& name) {
  float distNow = readDistanceCm();
  if (name == "20") {
    pos_20_steps = stepCounter;
    pos_20_dist  = distNow;
    Serial.print("[Saved 20php] Steps = "); Serial.print(pos_20_steps);
    Serial.print("  Distance = "); Serial.println(pos_20_dist);
  } else if (name == "50") {
    pos_50_steps = stepCounter;
    pos_50_dist  = distNow;
    Serial.print("[Saved 50php] Steps = "); Serial.print(pos_50_steps);
    Serial.print("  Distance = "); Serial.println(pos_50_dist);
  } else if (name == "100") {
    pos_100_steps = stepCounter;
    pos_100_dist  = distNow;
    Serial.print("[Saved 100php] Steps = "); Serial.print(pos_100_steps);
    Serial.print("  Distance = "); Serial.println(pos_100_dist);
  } else if (name == "200") {
    pos_200_steps = stepCounter;
    pos_200_dist  = distNow;
    Serial.print("[Saved 200php] Steps = "); Serial.print(pos_200_steps);
    Serial.print("  Distance = "); Serial.println(pos_200_dist);
  } else if (name == "500") {
    pos_500_steps = stepCounter;
    pos_500_dist  = distNow;
    Serial.print("[Saved 500php] Steps = "); Serial.print(pos_500_steps);
    Serial.print("  Distance = "); Serial.println(pos_500_dist);
  } else if (name == "1000") {
    pos_1000_steps = stepCounter;
    pos_1000_dist  = distNow;
    Serial.print("[Saved 1000php] Steps = "); Serial.print(pos_1000_steps);
    Serial.print("  Distance = "); Serial.println(pos_1000_dist);
  } else {
    Serial.println("[ERROR] Unknown name for SAVE.");
  }
}

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println("=== Calibration Mode ===");
  Serial.println("Commands: F, B, RESET, POS?, D, SAVE:50 etc, REPORT");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "F") {
      jog(true, JOG_STEPS);
    } else if (cmd == "B") {
      jog(false, JOG_STEPS);
    } else if (cmd == "RESET") {
      stepCounter = 0;
      Serial.println("[Counter Reset to 0]");
    } else if (cmd == "POS?") {
      Serial.print("[Current Steps] = ");
      Serial.println(stepCounter);
    } else if (cmd == "D") {
      float d = readDistanceCm();
      Serial.print("[Distance] = ");
      Serial.print(d);
      Serial.println(" cm");
    }
    else if (cmd.startsWith("SAVE:")) {
      String label = cmd.substring(5);
      savePosition(label);
    }
    else if (cmd == "REPORT") {
      Serial.println("=== SAVED POSITIONS ===");
      Serial.print("20php  Steps: "); Serial.print(pos_20_steps);
      Serial.print("  Dist: "); Serial.println(pos_20_dist);

      Serial.print("50php  Steps: "); Serial.print(pos_50_steps);
      Serial.print("  Dist: "); Serial.println(pos_50_dist);

      Serial.print("100php Steps: "); Serial.print(pos_100_steps);
      Serial.print("  Dist: "); Serial.println(pos_100_dist);

      Serial.print("200php Steps: "); Serial.print(pos_200_steps);
      Serial.print("  Dist: "); Serial.println(pos_200_dist);

      Serial.print("500php Steps: "); Serial.print(pos_500_steps);
      Serial.print("  Dist: "); Serial.println(pos_500_dist);

      Serial.print("1000php Steps: "); Serial.print(pos_1000_steps);
      Serial.print("  Dist: "); Serial.println(pos_1000_dist);

      Serial.println("========================");
    }
  }
}
