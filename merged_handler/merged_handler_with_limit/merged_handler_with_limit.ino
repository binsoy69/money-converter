#include <AccelStepper.h>
#include <Servo.h>

// ==================== BILL HANDLER (Stepper + Limit Switches) ====================

// Stepper X (horizontal H-bot)
const int STEP_X_PIN = 9;
const int DIR_X_PIN  = 10;

// Stepper Y (vertical H-bot)
const int STEP_Y_PIN = 11;
const int DIR_Y_PIN  = 12;

// Limit switches
#define LIMIT_X_HOME  A0   // Horizontal homing switch
#define LIMIT_Y_TOP   A1   // Vertical top (accepting)
#define LIMIT_Y_BOTTOM A2  // Vertical bottom (dispensing)

// Speeds
const float HORIZ_SPEED = 10000;   // steps/sec
const float VERT_SPEED  = 10000;   // steps/sec
const float ACCEL = 5000;

AccelStepper stepperX(AccelStepper::DRIVER, STEP_X_PIN, DIR_X_PIN);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_Y_PIN, DIR_Y_PIN);

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

void goHome() {
  if (!homeSwitchEnabled) {
    Serial.println("Homing switch currently disabled.");
    return;
  }

  Serial.println("[Homing] Moving toward HOME...");

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
  Serial.println("Homing complete. Current position set to 0.");
  Serial.println("Homing switch disabled until next movement.");
}

// ==================== VERTICAL CONTROL ====================
// --- State flags ---
bool isAtTop = true;              // True = top position, False = bottom
bool topSwitchEnabled = true;     // Prevent repeated triggering
bool bottomSwitchEnabled = true;

// ==================== MOVE DOWN ====================
void moveVerticalDown() {
  if (!isAtTop) {
    Serial.println("[Vertical] Already at dispensing position");
    return;
  }

  Serial.println("[Vertical] Moving down...");
  stepperY.setMaxSpeed(VERT_SPEED);
  stepperY.setSpeed(VERT_SPEED);  // Positive = down

  while (true) {
    stepperY.runSpeed();

    // --- Stop when bottom switch is pressed ---
    if (digitalRead(LIMIT_Y_BOTTOM) == LOW && bottomSwitchEnabled) {
      Serial.println("[Vertical] Bottom limit triggered");
      bottomSwitchEnabled = false;   // Disable until next upward move
      topSwitchEnabled = true;       // Allow top switch again
      break;
    }
  }

  // Stop motor and set reference position
  stepperY.stop();
  isAtTop = false;

  Serial.println("[Vertical] Down (Dispensing)");
}

// ==================== MOVE UP ====================
void moveVerticalUp() {
  if (isAtTop) {
    Serial.println("[Vertical] Already at accepting position");
    return;
  }

  Serial.println("[Vertical] Moving up...");
  stepperY.setMaxSpeed(VERT_SPEED);
  stepperY.setSpeed(-VERT_SPEED);  // Negative = up

  while (true) {
    stepperY.runSpeed();

    // --- Stop when top switch is pressed ---
    if (digitalRead(LIMIT_Y_TOP) == LOW && topSwitchEnabled) {
      Serial.println("[Vertical] Top limit triggered");
      topSwitchEnabled = false;     // Disable until next downward move
      bottomSwitchEnabled = true;   // Allow bottom switch again
      break;
    }
  }

  // Stop motor and set reference position
  stepperY.stop();
  stepperY.setCurrentPosition(0);
  isAtTop = true;

  Serial.println("[Vertical] Up (Accepting)");
}


// ==================== MOVE TO BIN ====================
void moveToBin(const Bin &bin) {
  if (!isHomed) {
    Serial.println("Please home first using command: h");
    return;
  }

  Serial.print("[Moving] to bin: ");
  Serial.print(bin.name);
  Serial.print(" (Steps: ");
  Serial.print(bin.stepPos);
  Serial.println(")");

  stepperX.setMaxSpeed(HORIZ_SPEED);
  stepperX.setAcceleration(ACCEL);
  stepperX.moveTo(bin.stepPos);

  while (stepperX.distanceToGo() != 0) {
    stepperX.run();
  }

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
const int RIGHT  = 117;

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
  dispenser5.write(PUSH_ANGLE);
  dispenser10.write(PUSH_ANGLE);
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

void setup_coin() {
  pinMode(COIN_PIN, INPUT_PULLUP);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);
}

// ==================== BILL DISPENSER (Servo A) ====================

Servo servoA;
const int SERVO_A_PIN = A3;
const int SERVO_A_RESET = 0;
const int SERVO_A_PUSH  = 90;
const int SERVO_DELAY = 10;

void pushDispenser() {
  for (int pos = SERVO_A_RESET; pos <= SERVO_A_PUSH; pos++) {
    servoA.write(pos);
    delay(SERVO_DELAY);
  }
  Serial.println("[ServoA] Pushed dispenser in");
}

void pullDispenser() {
  for (int pos = SERVO_A_PUSH; pos >= SERVO_A_RESET; pos--) {
    servoA.write(pos);
    delay(SERVO_DELAY);
  }
  Serial.println("[ServoA] Pulled dispenser back");
}

void prepDispense() {
  moveVerticalDown();
  pushDispenser();
  Serial.println("[Prep] Ready to dispense");
}

void finishDispense() {
  moveVerticalUp();
  pullDispenser();
  Serial.println("[Finish] Dispenser reset");
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
      else if (denom == 5) dispenseCoin(dispenser5, 5, qty);
      else if (denom == 10) dispenseCoin(dispenser10, 10, qty);
      else if (denom == 20) dispenseCoin(dispenser20, 20, qty);
      else Serial.println("ERR:Invalid coin denomination");

    } else if (cmd.equalsIgnoreCase("HOME")) {
      goHome();
      Serial.println("[OK]");

    } else if (cmd.startsWith("SORT:")) {
      String denom = cmd.substring(5);
      for (int i = 0; i < NUM_BINS; i++) {
        if (String(bins[i].name) == denom) {
          moveToBin(bins[i]);
          Serial.println("[OK]");
          return;
        }
      }
      Serial.println("[Error] Unknown bill denom");

    } else if (cmd.startsWith("PREP_DISPENSE:")) {
      String denom = cmd.substring(14);
      for (int i = 0; i < NUM_BINS; i++) {
        if (String(bins[i].name) == denom) {
          moveVerticalDown();
          moveToBin(bins[i]);
          prepDispense();
          Serial.println("ACK:PREP_DONE");
          return;
        }
      }
      Serial.println("ERR:Unknown denom");

    } else if (cmd.equalsIgnoreCase("FINISH_DISPENSE")) {
      finishDispense();
      Serial.println("ACK:FINISH_DONE");

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
  pinMode(LIMIT_Y_TOP, INPUT_PULLUP);
  pinMode(LIMIT_Y_BOTTOM, INPUT_PULLUP);

  stepperX.setMaxSpeed(HORIZ_SPEED);
  stepperY.setMaxSpeed(VERT_SPEED);
  stepperX.setCurrentPosition(0);

  setup_coin();
  setup_sorter();
  setup_dispenser();

  servoA.attach(SERVO_A_PIN);
  servoA.write(SERVO_A_RESET);

  goHome();
  moveVerticalUp();
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
