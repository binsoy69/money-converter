
// --- Coin Acceptor Setup---
volatile int pulseCount = 0;
int intervalCounter = 0;
const unsigned long intervalThreshold = 30;  // Adjustable delay ticks
const int COIN_PIN = 2;

void setup_coin() {
  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), incomingPulse, FALLING);
}

void incomingPulse() {
  pulseCount++;
  intervalCounter = 0;
}

void setup() {
  pinMode(COIN_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(COIN_PIN), incomingPulse, FALLING);
  Serial.begin(9600);
  Serial.println("[READY] Insert a coin...");
}

void loop() {
  intervalCounter++;

  if (intervalCounter >= intervalThreshold && pulseCount > 0) {
    Serial.print("[IMPULSES RECEIVED] → ");
    Serial.println(pulseCount);
    pulseCount = 0;
    intervalCounter = 0;
    Serial.println("[READY] Insert next coin...");
  }
  
  delay(10);
}
