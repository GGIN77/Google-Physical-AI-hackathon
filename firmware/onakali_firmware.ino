#include <ESP32Servo.h>

// ===== PIN CONFIG =====
const int IR_SENSOR_A = 5;
const int IR_SENSOR_B = 19;
const int SERVO_PIN   = 18;

// ===== SERVO CONFIG =====
Servo myServo;
const unsigned long HOLD_TIME = 2000; // How long to stay at 0 or 180 before returning

// State tracking for edge detection (movement)
int lastA = 1;
int lastB = 1;
unsigned long moveTimer = 0;
bool isHolding = false;

void setup() {
  Serial.begin(115200);

  pinMode(IR_SENSOR_A, INPUT_PULLUP);
  pinMode(IR_SENSOR_B, INPUT_PULLUP);

  ESP32PWM::allocateTimer(0);
  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 500, 2400);

  myServo.write(90); // Initial state
  Serial.println("System ready - Servo at 90°");
}

void loop() {
  int a = digitalRead(IR_SENSOR_A);
  int b = digitalRead(IR_SENSOR_B);
  unsigned long currentMillis = millis();

  // Trigger only on the MOMENT sensor A goes from 1 to 0 (movement detected)
  if (a == 0 && lastA == 0 && b == 0) {
    myServo.write(0);
    moveTimer = currentMillis;
    isHolding = true;
    Serial.println("Movement at A - 0°");
  } 
  // Trigger only on the MOMENT sensor B goes from 1 to 0 (movement detected)
  else if (b == 1 && lastB == 1 && a == 1) {
    myServo.write(180);
    moveTimer = currentMillis;
    isHolding = true;
    Serial.println("Movement at B - 180°");
  }

  // Return to 90 degrees after HOLD_TIME expires
  if (isHolding && (currentMillis - moveTimer >= HOLD_TIME)) {
    myServo.write(90);
    isHolding = false;
    Serial.println("Returned to 90°");
  }

  // Save the current states for the next loop
  lastA = a;
  lastB = b;

  delay(15);
}
