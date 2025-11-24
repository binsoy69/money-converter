#include <AccelStepper.h>

// Stepper A pins (horizontal)
const int STEP_A_PIN = 2;
const int DIR_A_PIN  = 3;

// Ultrasonic pins
const int TRIG_PIN = 6;
const int ECHO_PIN = 7;

// Mechanical constants (8mm per rev TRx8 lead screw)
const int stepsPerRevolution = 200;
const int microsteps = 16;
const float leadScrewLead = 8.0;
const float stepsPerMM = (stepsPerRevolution * microsteps) / leadScrewLead; // 400

// Speed / acceleration
const float mmPerSecond = 100.0;
const float maxSpeed = stepsPerMM * mmPerSecond;
const float accel = 2000.0;

// AccelStepper for A
AccelStepper stepperA(AccelStepper::DRIVER, STEP_A_PIN, DIR_A_PIN);

// Bin definitions with pre-calibrated step counts
struct Bin {
  const char* name;
  float distanceCm;  // for fine check
  long stepPos;      // from HOME in steps
};

Bin bins[] = {
  { "HOME",  0.0,    0    },
  { "20",    2.7,  2500  },
  { "50",    5.7,  5000  },  // replace with your calibrated step counts
  { "100",  14.0,  12000 },
  { "200",  22.4,  20000 },
  { "500",  30.8,  28000 },
  { "1000", 36.8,  35000 }
};

const int NUM_BINS = sizeof(bins)/sizeof(bins[0]);
int currentBinIndex = 0;
long currentSteps = 0;

// Tolerance for ultrasonic
const float TOLERANCE_CM = 1.5;

// Ultrasonic read
float readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  return (duration * 0.034 / 2.0);
}

void moveSteps(long steps) {
  long toMove = steps;
  stepperA.setMaxSpeed(maxSpeed);
  stepperA.setAcceleration(accel);
  stepperA.move(toMove);
  while (stepperA.distanceToGo() != 0) {
    stepperA.run();
  }
}

void moveToBin(int index) {
  if (index < 0 || index >= NUM_BINS) {
    Serial.println("[Error] Invalid bin index");
    return;
  }
  long delta = bins[index].stepPos - currentSteps;
  moveSteps(delta);
  currentSteps = bins[index].stepPos;
  currentBinIndex = index;

  // Optional fine ultrasonic adjust
  float expectedCm = bins[index].distanceCm;
  float actual = readDistanceCm();
  if (fabs(actual - expectedCm) > TOLERANCE_CM) {
    Serial.println("[Fine Adjust]");
    while (fabs(readDistanceCm() - expectedCm) > TOLERANCE_CM) {
      long smallStep = (readDistanceCm() < expectedCm) ? 200 : -200;
      stepperA.move(smallStep);
      while (stepperA.distanceToGo() != 0) {
        stepperA.run();
      }
    }
  }
  Serial.println("[Aligned]");
}

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  Serial.println("[Sorter] Ready - Stepper B ignored here (vertical)");
}

void loop() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input == "HOME") {
      moveToBin(0);
    }
    if (input.startsWith("SORT:")) {
      String denom = input.substring(5);
      for (int i=0; i<NUM_BINS; i++) {
        if (String(bins[i].name) == denom) {
          moveToBin(i);
          Serial.println("[OK]");
          return;
        }
      }
      Serial.println("[Error] Unknown denom");
    }
  }
}
