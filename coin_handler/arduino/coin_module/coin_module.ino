#include <Servo.h>

// --- Coin Acceptor Setup ---
const byte COIN_PIN = 2;        // Coin acceptor output pin (INT0)
const byte ENABLE_PIN = 3;      // Acceptor enable pin

volatile unsigned int pulseCount = 0;
volatile unsigned long lastPulseTime = 0;

unsigned long pulseTimeout = 400;   // ms – no pulse for this time = coin finished
bool acceptorEnabled = false;

unsigned int totalAmount = 0;

// --- Sorter Setup ---
Servo sorter;
const int SORTER_SERVO_PIN = 4;
// Servo Angles
const int CENTER = 81;
const int LEFT   = 45;
const int RIGHT  = 120;

// --- Dispenser Setup ---
Servo dispenser1, dispenser5, dispenser10, dispenser20;
const int DISPENSE_1_PIN  = 5;
const int DISPENSE_5_PIN  = 6;
const int DISPENSE_10_PIN = 7;
const int DISPENSE_20_PIN = 8;
const int PUSH_ANGLE = 180;
const int RESET_ANGLE = 0;
const int DISPENSE_TIME = 1;

// --------------------------------------------
// Map pulse counts to coin values (Philippines)
// --------------------------------------------
int getCoinValue(unsigned int pulses) {
  switch (pulses) {
    case 1: return 1;   // ₱1
    case 5: return 5;   // ₱5
    case 10: return 10; // ₱10
    case 20: return 20; // ₱20
    default: return 0;  // Unknown
  }
}

// --------------------------------------------
// Interrupt Service Routine (ISR)
// --------------------------------------------
void coinISR() {
  if (!acceptorEnabled) return; // Ignore pulses if disabled
  lastPulseTime = millis();
  pulseCount++;
}

// --- Sorter Functions ---
void setup_sorter() {
  sorter.attach(SORTER_SERVO_PIN);
  center_sorter();
}

void center_sorter() {
  sorter.write(CENTER);
  delay(500);
}

void move_sorter(String direction, int denom) {
  if (direction == "LEFT") {
    sorter.write(LEFT);
  } else if (direction == "RIGHT") {
    sorter.write(RIGHT);
  }
  delay(800);  // Allow servo to sort
  center_sorter();

  // Notify Python that sorting finished
  Serial.print("SORT_DONE:");
  Serial.println(denom);
}

void sort_coin(int value) {
  if (value == 1 || value == 5) {
    move_sorter("RIGHT", value);
  } else if (value == 10 || value == 20) {
    move_sorter("LEFT", value);
  } else {
    Serial.println("ERR:Unknown coin value");
  }
}

// --- Dispenser Functions ---
void setup_dispenser() {
  dispenser1.attach(DISPENSE_1_PIN);
  dispenser5.attach(DISPENSE_5_PIN);
  dispenser10.attach(DISPENSE_10_PIN);
  dispenser20.attach(DISPENSE_20_PIN);

  // Set initial position
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

// --- Coin Setup ---
void setup_coin() {
  pinMode(COIN_PIN, INPUT_PULLUP);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); // Start disabled
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);
}

// --- Serial Commands ---
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
      else Serial.println("ERR:Invalid denomination");

    } else {
      Serial.print("ERR:Unknown command ");
      Serial.println(cmd);
    }
  }
}

// --- Setup ---
void setup() {
  Serial.begin(9600);
  setup_coin();
  setup_sorter();
  setup_dispenser();
  Serial.println("READY");
}

// --- Loop ---
void loop() {
  unsigned long now = millis();

  // Detect when a coin pulse train has ended
  if (acceptorEnabled && pulseCount > 0 && (now - lastPulseTime > pulseTimeout)) {
    int value = getCoinValue(pulseCount);
    if (value > 0) {
      Serial.print("COIN:");
      Serial.println(value);
      totalAmount += value;

      // Sort the coin physically
      sort_coin(value);
    } else {
      Serial.print("ERR:Unknown pulses ");
      Serial.println(pulseCount);
    }

    pulseCount = 0; // Reset for next coin
  }

  handle_serial_commands();
  delay(5);
}
