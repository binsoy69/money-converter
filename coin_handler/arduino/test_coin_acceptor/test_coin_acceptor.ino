// --- Coin Acceptor Setup ---
volatile int pulseCount = 0;
int intervalCounter = 0;
const unsigned long intervalThreshold = 30;  // Adjustable delay ticks

const int COIN_PIN = 2;
const int ENABLE_PIN = 3;
bool acceptorEnabled = false;

void incomingPulse() {
  pulseCount++;
  intervalCounter = 0;
}

void setup() {
  pinMode(COIN_PIN, INPUT);
  pinMode(ENABLE_PIN, OUTPUT);
  digitalWrite(ENABLE_PIN, LOW); // Start disabled

  attachInterrupt(digitalPinToInterrupt(COIN_PIN), incomingPulse, FALLING);

  Serial.begin(9600);
  Serial.println("Coin Acceptor Ready. Send 'ENABLE' or 'DISABLE'.");
}

void loop() {
  intervalCounter++;

  // Handle serial commands
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.equalsIgnoreCase("EN")) {
      digitalWrite(ENABLE_PIN, HIGH);
      acceptorEnabled = true;
      Serial.println("[SYSTEM] Coin Acceptor ENABLED");
      Serial.println("[READY] Insert next coin...");
    } else if (command.equalsIgnoreCase("DIS")) {
      digitalWrite(ENABLE_PIN, LOW);
      pulseCount = 0;
      acceptorEnabled = false;
      Serial.println("[SYSTEM] Coin Acceptor DISABLED");
    } else {
      Serial.println("[ERROR] Unknown command. Use 'ENABLE' or 'DISABLE'.");
    }
  }

  // Report pulses if interval threshold is reached
  if (intervalCounter >= intervalThreshold && pulseCount > 0 ) {
    Serial.print("[IMPULSES RECEIVED] → ");
    Serial.println(pulseCount);
    pulseCount = 0;
    intervalCounter = 0;
  }

  delay(10);
}