#include <Servo.h>

// --- Coin Acceptor ---
volatile int pulseCount = 0;
int intervalCounter = 0;
const unsigned long intervalThreshold = 30;  // Adjustable delay ticks

// --- Servo Setup ---
Servo sorter;
const int SORTER_SERVO_PIN = 3;
const int COIN_PIN = 2;

// Servo angles
const int CENTER = 75;
const int LEFT = 40;
const int RIGHT = 110;

void setup() {
  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), incomingPulse, FALLING);

  sorter.attach(SORTER_SERVO_PIN);
  center_sorter();

  Serial.begin(9600);
  Serial.println("[READY] Insert a coin...");
}

// Interrupt triggered by falling edge from coin acceptor
void incomingPulse() {
  pulseCount++;
  intervalCounter = 0;  // Reset interval
}

void loop() {
  intervalCounter++;

  if (intervalCounter >= intervalThreshold && pulseCount > 0) {
    Serial.print("[IMPULSES RECEIVED] → ");
    Serial.println(pulseCount);

    // Sort based on pulse count mapping
    if (pulseCount == 1 || pulseCount == 5) {
      move_sorter("RIGHT");
    } else if (pulseCount == 2 || pulseCount == 10 || pulseCount == 20) {
      move_sorter("LEFT");
    } else {
      Serial.println("[WARN] Unknown coin value, skipping sort.");
    }

    pulseCount = 0;
    intervalCounter = 0;
    Serial.println("[READY] Insert next coin...");
  }

  delay(10);  // Rough timer granularity
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

void center_sorter() {
  sorter.write(CENTER);
  delay(500);
  Serial.println("[SORT] → CENTER");
}