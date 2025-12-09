#include <Servo.h>

Servo myServo;  // Create servo object

void setup() {
  Serial.begin(9600);      // Start Serial Monitor
  myServo.attach(2);       // Attach servo to pin D9
  Serial.println("Enter angle (0 to 180):");
}

void loop() {
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    int angle = input.toInt();

    if (angle >= 0 && angle <= 180) {
      myServo.write(angle);
      Serial.print("Servo set to angle: ");
      Serial.println(angle);
    } else {
      Serial.println("Invalid angle. Please enter a value between 0 and 180.");
    }
  }
}