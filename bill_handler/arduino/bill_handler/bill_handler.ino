// --- Libraries --- //
#include <AccelStepper.h>

// --- Pin Definitions --- //
// Stepper driver pins
const int DIR_PIN  = 3;
const int STEP_PIN = 4;

AccelStepper stepper(AccelStepper::DRIVER, STEP_PIN, DIR_PIN);

// Ultrasonic sensor pins
const int ECHO_PIN = 6;
const int TRIG_PIN = 5;

// Bin distance mapping (in cm) - must match your mechanical setup
struct Bin {
  const char* name;
  float distanceCm;
};

Bin bins[] = {
  { "50",   5.7 },
  { "100", 14.0 },
  { "200", 22.4 },
  { "500", 30.8 },
  { "1000", 36.8 }
};

const float TOLERANCE = 1.5;  // Acceptable range in cm

// --- Function to read distance --- //
float readDistanceCm() {
  long duration;
  float distanceCm;

  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH, 30000); // 30ms timeout
  distanceCm = duration * 0.034 / 2.0;
  return distanceCm;
}

// --- Setup --- //
void setup() {
  Serial.begin(9600);

  // Setup ultrasonic pins
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Setup stepper
  stepper.setMaxSpeed(400);   // adjust as needed
  stepper.setAcceleration(200);
  
  Serial.println("[Sorter] Ready for commands.");
}

// --- Stepper Move Continuous --- //
void moveStepperContinuous(bool forward, int steps = 100) {
  long direction = (forward ? 1 : -1);
  for (int i = 0; i < steps; i++) {
    stepper.move(direction);
    stepper.runSpeed();
  }
}

// --- Align to Bin --- //
bool alignToBin(float targetCm) {
  for (int i = 0; i < 1000; i++) {
    float current = readDistanceCm();
    if (fabs(current - targetCm) <= TOLERANCE) {
      Serial.println("[Aligned]");
      return true;
    }
    bool moveForward = (current < targetCm);
    moveStepperContinuous(moveForward, 200);
  }
  Serial.println("[Fail] Could not align.");
  return false;
}

// --- Loop: Listen for Serial --- //
void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();

    if (input.startsWith("SORT:")) {
      String denom = input.substring(5); // e.g. "100"

      // Find matching bin
      bool found = false;
      for (auto &b : bins) {
        if (String(b.name) == denom) {
          Serial.print("[Sorter] Aligning to ");
          Serial.println(denom);
          found = true;
          if (alignToBin(b.distanceCm)) {
            Serial.println("[Sorter] OK");
          } else {
            Serial.println("[Sorter] Failed to align");
          }
          break;
        }
      }
      if (!found) {
        Serial.println("[Error] Unknown denom");
      }
    }
  }

  stepper.run();  // required by AccelStepper
}
