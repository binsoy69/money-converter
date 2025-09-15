// ============================================
// Coin Acceptor Pulse Counter – Stable Version
// With ENABLE/DISABLE control (Arduino UNO/Nano/MEGA)
// ============================================

const byte COIN_PIN = 2;        // Coin acceptor output pin (INT0)
const byte ENABLE_PIN = 3;      // Acceptor enable pin

volatile unsigned int pulseCount = 0;
volatile unsigned long lastPulseTime = 0;

unsigned long pulseTimeout = 400;   // ms – no pulse for this time = coin finished
bool acceptorEnabled = false;

unsigned int totalAmount = 0;

// --------------------------------------------
// Map pulse counts to coin values (Philippines)
// Adjust to your acceptor DIP switch config
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

  unsigned long now = millis();
  unsigned long gap = now - lastPulseTime;
  lastPulseTime = now;

  pulseCount++;

  Serial.print("[DEBUG] Pulse gap: ");
  Serial.print(gap);
  Serial.println(" ms");
}

// --------------------------------------------
// Setup
// --------------------------------------------
void setup() {
  Serial.begin(9600);
  pinMode(COIN_PIN, INPUT_PULLUP);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); // Start disabled

  attachInterrupt(digitalPinToInterrupt(COIN_PIN), coinISR, FALLING);

  Serial.println("Coin Acceptor Ready. Send 'EN' or 'DIS'.");
}

// --------------------------------------------
// Main loop
// --------------------------------------------
void loop() {
  unsigned long now = millis();

  // Handle serial commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.equalsIgnoreCase("EN")) {
      digitalWrite(ENABLE_PIN, HIGH);
      acceptorEnabled = true;
      pulseCount = 0;
      Serial.println("[SYSTEM] Coin Acceptor ENABLED");
      Serial.println("[READY] Insert next coin...");
    } else if (command.equalsIgnoreCase("DIS")) {
      digitalWrite(ENABLE_PIN, LOW);
      acceptorEnabled = false;
      pulseCount = 0;
      Serial.println("[SYSTEM] Coin Acceptor DISABLED");
    } else {
      Serial.println("[ERROR] Unknown command. Use 'EN' or 'DIS'.");
    }
  }

  // Detect when a coin pulse train has ended
  if (acceptorEnabled && pulseCount > 0 && (now - lastPulseTime > pulseTimeout)) {
    int value = getCoinValue(pulseCount);
    if (value > 0) {
      Serial.print("[COIN DETECTED] → ₱");
      Serial.println(value);
      totalAmount += value;
      Serial.print("[TOTAL] ₱");
      Serial.println(totalAmount);
    } else {
      Serial.print("[COIN DETECTED] → Unknown denomination (");
      Serial.print(pulseCount);
      Serial.println(" pulses)");
    }

    pulseCount = 0; // Reset for next coin
    Serial.println("[READY] Insert next coin...");
  }
}
