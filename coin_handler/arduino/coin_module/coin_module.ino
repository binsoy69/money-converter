#include <Servo.h>

// --- Coin Acceptor Setup---
volatile int pulseCount = 0;
int intervalCounter = 0;
const unsigned long intervalThreshold = 30;  // Adjustable delay ticks
const int COIN_PIN = 2;
const int ENABLE_PIN = 8;

// --- Sorter Setup ---
Servo sorter;
const int SORTER_SERVO_PIN = 3;
// Servo Angles
const int CENTER = 75;
const int LEFT = 40;
const int RIGHT = 110;

// --- Dispenser Setup ---
Servo dispenser1, dispenser5, dispenser10, dispenser20;
const int DISPENSE_1_PIN = 4;
const int DISPENSE_5_PIN = 5;
const int DISPENSE_10_PIN = 6;
const int DISPENSE_20_PIN = 7;
const int PUSH_ANGLE = 180;
const int RESET_ANGLE = 0;
const int DISPENSE_TIME = 1;

void setup_coin() {
  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), incomingPulse, FALLING);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, HIGH); // Disabled by default (active LOW)
}

void incomingPulse() {
  pulseCount++;
  intervalCounter = 0;
}

void setup_sorter() {
  sorter.attach(SORTER_SERVO_PIN);
  center_sorter();
}

void center_sorter() {
  sorter.write(CENTER);
  delay(500);
  Serial.println("[SORT] → CENTER");
}

void move_sorter(String direction) {
  if (direction == "LEFT") {
    sorter.write(LEFT);
    Serial.println("[SORT] → LEFT");
  } else if (direction == "RIGHT") {
    sorter.write(RIGHT);
    Serial.println("[SORT] → RIGHT");
  }

  delay(800);  // Allow servo to sort
  center_sorter();
}

void sort_coin(int pulses) {
 // Sort based on pulse count mapping
 if (pulses == 1 || pulses == 5) {
  move_sorter("RIGHT");
  } else if (pulses == 10 || pulses == 20) {
    move_sorter("LEFT");
    } else {
      Serial.println("[WARN] Unknown coin value, skipping sort.");
      }
}

void setup_dispenser() {
  dispenser1.attach(DISPENSE_1_PIN);
  dispenser5.attach(DISPENSE_5_PIN);
  dispenser10.attach(DISPENSE_10_PIN);
  dispenser20.attach(DISPENSE_20_PIN);

  // Set initial position
  dispenser1.write(PUSH_ANGLE);
  dispenser5.write(PUSH_ANGLE);
  dispenser10.write(PUSH_ANGLE);
  dispenser20.write(PUSH_ANGLE);
}

void dispenseCoin(Servo &s, int value, int count) {
  Serial.print("[DISPENSING ");
  Serial.print(count);
  Serial.print(" COIN(S) → ₱");
  Serial.print(value);
  Serial.println("]");
  
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

  Serial.println("[DONE]");
}

void display_ready_message() {
  Serial.println("[READY] Insert a coin...");
}

void handle_coin_detection() {
  intervalCounter++;

  if (intervalCounter >= intervalThreshold && pulseCount > 0) {
    Serial.print("[IMPULSES RECEIVED] → ");
    Serial.println(pulseCount);
    sort_coin(pulseCount);

    sort_coin(pulseCount);

    pulseCount = 0;
    intervalCounter = 0;

    display_ready_message();
  }
}

void handle_serial_commands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "ENABLE_COIN") {
      digitalWrite(ENABLE_PIN, LOW);
      Serial.println("[COIN MODE] Enabled");
    } else if (cmd == "DISABLE_COIN") {
      digitalWrite(ENABLE_PIN, HIGH);
      Serial.println("[COIN MODE] Disabled");
    } else if (cmd.startsWith("DISPENSE:")) {
      // Parse format: DISPENSE:5:3 → ₱5, 3 times
      int d1 = cmd.indexOf(":");
      int d2 = cmd.lastIndexOf(":");
      int denom = cmd.substring(d1 + 1, d2).toInt();
      int qty = cmd.substring(d2 + 1).toInt();

      if (denom == 1) dispenseCoin(dispenser1, 1, qty);
      else if (denom == 5) dispenseCoin(dispenser5, 5, qty);
      else if (denom == 10) dispenseCoin(dispenser10, 10, qty);
      else if (denom == 20) dispenseCoin(dispenser20, 20, qty);
      else Serial.println("[ERROR] Invalid denomination.");
    } else {
      Serial.println("[ERROR] Unknown command.");
    }
  }
}



void setup() {
  Serial.begin(9600);
  setup_coin();
  setup_sorter();
  setup_dispenser();
  display_ready_message();
}

void loop() {
  handle_coin_detection();
  handle_serial_commands();
  delay(10);
}


