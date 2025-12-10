#include <AccelStepper.h>
#include <Servo.h>

// ==================== BILL HANDLER (Stepper + Limit Switch) ====================

// Stepper X (horizontal H-bot)
const int STEP_X_PIN = 9;
const int DIR_X_PIN  = 10;

// Limit switch
#define LIMIT_X_HOME  A0   // Horizontal homing switch

// Speeds
const float HORIZ_SPEED = 10000;   // steps/sec
const float ACCEL = 5000;

AccelStepper stepperX(AccelStepper::DRIVER, STEP_X_PIN, DIR_X_PIN);

bool isHomed = false;
bool homeSwitchEnabled = true;

// Bin definitions
struct Bin {
  const char* name;
  long stepPos;
};

Bin bins[] = {
  { "HOME",   0     },
  { "20",     0     },
  { "50",     35000 },
  { "100",    64000 },
  { "200",    97000 },
  { "500",    130000 },
  { "1000",   161000 }
};

const int NUM_BINS = sizeof(bins)/sizeof(bins[0]);
int currentBinIndex = 0;
long currentSteps = 0;

// ==================== HOMING (X-Axis) ====================

// ==================== HOMING (X-Axis) ====================

void goHome() {
  if (!homeSwitchEnabled) {
    //Serial.println("Homing switch currently disabled.");
    return;
  }

 // Serial.println("[Homing] Moving toward HOME...");

  stepperX.setMaxSpeed(HORIZ_SPEED);
  stepperX.setSpeed(-HORIZ_SPEED);

  // Move towards limit switch until pressed
  while (digitalRead(LIMIT_X_HOME) == HIGH) {
    stepperX.runSpeed();
  }

  // Small back-off to release switch
  stepperX.setSpeed(1000);
  unsigned long t0 = millis();
  while (digitalRead(LIMIT_X_HOME) == LOW && millis() - t0 < 2000) {
    stepperX.runSpeed();
  }

  // Set the current position as 0 (home)
  stepperX.setCurrentPosition(0);
  isHomed = true;
  homeSwitchEnabled = false; // disable switch after homing
  currentBinIndex = 0; // Reset bin index to HOME
  //Serial.println("Homing complete. Current position set to 0.");
  //Serial.println("Homing switch disabled until next movement.");
}

// ==================== MOVE TO BIN ====================
void moveToBin(int binIndex) {
  if (!isHomed) {
    Serial.println("Please home first using command: h");
    return;
  }

  // Optimization: If already at the target bin, do nothing
  if (binIndex == currentBinIndex) {
    Serial.println("[OK] Already at bin");
    return;
  }

  Bin targetBin = bins[binIndex];

  Serial.print("[Moving] to bin: ");
  Serial.print(targetBin.name);
  Serial.print(" (Steps: ");
  Serial.print(targetBin.stepPos);
  Serial.println(")");

  stepperX.setMaxSpeed(HORIZ_SPEED);
  stepperX.setAcceleration(ACCEL);
  stepperX.moveTo(targetBin.stepPos);

  while (stepperX.distanceToGo() != 0) {
    stepperX.run();
  }

  currentBinIndex = binIndex; // Update current bin index
  Serial.println("Movement complete.");

  // Re-enable homing switch after a move
  if (!homeSwitchEnabled) {
    homeSwitchEnabled = true;
    Serial.println("Homing switch re-enabled for next homing command.");
  }
}

// ==================== COIN HANDLER ====================

const byte COIN_PIN = 2;
const byte ENABLE_PIN = 3;

volatile unsigned int pulseCount = 0;
volatile unsigned long lastPulseTime = 0;

unsigned long pulseTimeout = 400;
bool acceptorEnabled = false;
unsigned int totalAmount = 0;

// Sorter Setup
Servo sorter;
const int SORTER_SERVO_PIN = 4;
const int CENTER = 81;
const int LEFT   = 45;
const int RIGHT  = 120;

// Dispenser Setup
Servo dispenser1, dispenser5, dispenser10, dispenser20;
const int DISPENSE_1_PIN  = 5;
const int DISPENSE_5_PIN  = 6;
const int DISPENSE_10_PIN = 7;
const int DISPENSE_20_PIN = 8;
const int PUSH_ANGLE = 180;
const int RESET_ANGLE = 0;
const int DISPENSE_TIME = 1;

int getCoinValue(unsigned int pulses) {
  switch (pulses) {
    case 1: return 1;
    case 5: return 5;
    case 10: return 10;
    case 20: return 20;
    default: return 0;
  }
}

void coinISR() {
  if (!acceptorEnabled) return;
  lastPulseTime = millis();
  pulseCount++;
}

void setup_sorter() {
  sorter.attach(SORTER_SERVO_PIN);
  sorter.write(CENTER);
  delay(500);
}

void move_sorter(String direction, int denom) {
  if (direction == "LEFT") sorter.write(LEFT);
  else if (direction == "RIGHT") sorter.write(RIGHT);
  delay(800);
  sorter.write(CENTER);
  delay(500);

  Serial.print("SORT_DONE:");
  Serial.println(denom);
}

void sort_coin(int value) {
  if (value == 1 || value == 5) move_sorter("RIGHT", value);
  else if (value == 10 || value == 20) move_sorter("LEFT", value);
  else Serial.println("ERR:Unknown coin value");
}

void setup_dispenser() {
  dispenser1.attach(DISPENSE_1_PIN);
  dispenser5.attach(DISPENSE_5_PIN);
  dispenser10.attach(DISPENSE_10_PIN);
  dispenser20.attach(DISPENSE_20_PIN);
  dispenser1.write(PUSH_ANGLE);
  dispenser5.write(RESET_ANGLE);
  dispenser10.write(RESET_ANGLE);
  dispenser20.write(PUSH_ANGLE);
}

void dispenseCoin(Servo &s, int value, int count) {
  Serial.print("ACK:DISPENSE:");
  Serial.print(value);
  Serial.print(":");
  Serial.println(count);

  for (int i = 0; i < count; i++) {
    for (int pos = PUSH_ANGLE; pos >= RESET_ANGLE; pos--) {
      s.write(pos);
      delay(DISPENSE_TIME);
    }
    for (int pos = RESET_ANGLE; pos <= PUSH_ANGLE; pos++) {
      s.write(pos);
      delay(DISPENSE_TIME);
    }
    delay(300);
  }

  Serial.print("DISPENSE_DONE:");
  Serial.print(value);
  Serial.print(":");
  Serial.println(count);
}

void dispenseCoinReverse(Servo &s, int value, int count) {
  Serial.print("ACK:DISPENSE:");
  Serial.print(value);
  Serial.print(":");
  Serial.println(count);

  for (int i = 0; i < count; i++) {
    for (int pos = RESET_ANGLE; pos <= PUSH_ANGLE; pos++) {
      s.write(pos);
      delay(DISPENSE_TIME);
    }
    for (int pos = PUSH_ANGLE; pos >= RESET_ANGLE; pos--) {
      s.write(pos);
      delay(DISPENSE_TIME);
    }
    delay(300);
  }

  Serial.print("DISPENSE_DONE:");
  Serial.print(value);
  Serial.print(":");
  Serial.println(count);
}

void setup_coin() {
  pinMode(COIN_PIN, INPUT_PULLUP);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);
}



// ==================== SERIAL COMMAND HANDLER ====================

void handle_serial_commands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.equalsIgnoreCase("ENABLE_COIN")) {
      digitalWrite(ENABLE_PIN, HIGH);
      acceptorEnabled = true;
      pulseCount = 0;
      Serial.println("ACK:ENABLE_COIN");

    } else if (cmd.equalsIgnoreCase("DISABLE_COIN")) {
      digitalWrite(ENABLE_PIN, LOW);
      acceptorEnabled = false;
      pulseCount = 0;
      Serial.println("ACK:DISABLE_COIN");

    } else if (cmd.startsWith("DISPENSE:")) {
      int d1 = cmd.indexOf(":");
      int d2 = cmd.lastIndexOf(":");
      int denom = cmd.substring(d1 + 1, d2).toInt();
      int qty   = cmd.substring(d2 + 1).toInt();

      if (denom == 1) dispenseCoin(dispenser1, 1, qty);
      else if (denom == 5) dispenseCoinReverse(dispenser5, 5, qty);
      else if (denom == 10) dispenseCoinReverse(dispenser10, 10, qty);
      else if (denom == 20) dispenseCoin(dispenser20, 20, qty);
      else Serial.println("ERR:Invalid coin denomination");

    } else if (cmd.equalsIgnoreCase("HOME")) {
      goHome();
      Serial.println("[OK]");

    } else if (cmd.startsWith("SORT:")) {
      String denom = cmd.substring(5);
      bool found = false;
      for (int i = 0; i < NUM_BINS; i++) {
        if (String(bins[i].name) == denom) {
          moveToBin(i); // Pass index instead of struct
          Serial.println("[OK]");
          found = true;
          break;
        }
      }
      if (!found) {
        Serial.println("[Error] Unknown bill denom");
      }

    } else {
      Serial.print("ERR:Unknown command ");
      Serial.println(cmd);
    }
  }
}

// ==================== MAIN SETUP & LOOP ====================

void setup() {
  Serial.begin(9600);

  pinMode(LIMIT_X_HOME, INPUT_PULLUP);

  stepperX.setMaxSpeed(HORIZ_SPEED);
  stepperX.setCurrentPosition(0);

  setup_coin();
  setup_sorter();
  setup_dispenser();

  goHome();
  Serial.println("READY");
}

void loop() {
  unsigned long now = millis();

  if (acceptorEnabled && pulseCount > 0 && (now - lastPulseTime > pulseTimeout)) {
    int value = getCoinValue(pulseCount);
    if (value > 0) {
      Serial.print("COIN:");
      Serial.println(value);
      totalAmount += value;
      sort_coin(value);
    } else {
      Serial.print("ERR:Unknown pulses ");
      Serial.println(pulseCount);
    }
    pulseCount = 0;
  }

  handle_serial_commands();
  stepperX.run();
  delay(5);
}
