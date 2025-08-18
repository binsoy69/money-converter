#include <AccelStepper.h>
// === Pin Definitions === 
#define dirPin 2 
#define stepPin 3 
#define buttonForwardPin 4
#define buttonReversePin 5

// === Create Stepper Instance ===
 AccelStepper stepper(AccelStepper::DRIVER, stepPin, dirPin);

// === Motion Settings ===
const int stepsPerRevolution = 200; // 1.8° stepper motor
const int microsteps = 16;          // Microstepping setting on A4988 
const float leadScrewLead = 8.0;    // mm per revolution for TR8x8
const float stepsPerMM = (stepsPerRevolution * microsteps) / leadScrewLead;

// === Desired Speed ===
const float mmPerSecond = 160.0;
const float maxSpeed = stepsPerMM * mmPerSecond;
const float accel = 1000;

void setup() {
  stepper.setMaxSpeed(maxSpeed); 
  stepper.setAcceleration(accel);
// Set button pins 
  pinMode(buttonForwardPin, INPUT_PULLUP); // active LOW
  pinMode(buttonReversePin, INPUT_PULLUP); // active LOW 
}

void loop() { 
  // Read buttons 
  bool forwardPressed = digitalRead(buttonForwardPin) == LOW;
  bool reversePressed = digitalRead(buttonReversePin) == LOW;
  if (forwardPressed && !reversePressed) { 
  // Spin forward
  stepper.setSpeed(maxSpeed);
  stepper.runSpeed(); 
  } else if (reversePressed && !forwardPressed) { 
  // Spin reverse
  stepper.setSpeed(-maxSpeed);
  stepper.runSpeed(); 
  } else { 
  // Neither button pressed — hold motor in place (no spin) 
  stepper.setSpeed(0); 
  } 
}

