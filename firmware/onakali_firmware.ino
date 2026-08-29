#include <Wire.h>
#include <MPU6050.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <math.h>

// ============================================================
// ONAKALI REFEREE
// ESP32 Unified Firmware
// ============================================================

// -------------------------
// Pin Configuration
// -------------------------

#define IR_SENSOR_A 4
#define IR_SENSOR_B 5

#define SERVO_PIN 18

#define HC_TRIG_PIN 13
#define HC_ECHO_PIN 12

#define RELAY_PIN 14

#define I2C_SDA 21
#define I2C_SCL 22

// -------------------------
// Serial Configuration
// -------------------------

#define SERIAL_BAUD 115200

// -------------------------
// Telemetry Configuration
// -------------------------

// 25 Hz = one message every 40 ms
#define TELEMETRY_INTERVAL_MS 40

// -------------------------
// Sensor Configuration
// -------------------------

#define IR_DEBOUNCE_MS 50

// Lemon & Spoon drop threshold
#define DROP_JERK_THRESHOLD_G 3.5

// Musical Chairs seating threshold
// Calibrate this with the real chair/sensor position.
#define SEATING_DISTANCE_CM 30.0

// -------------------------
// Servo Positions
// -------------------------

#define FLAG_HOME_ANGLE 0
#define FLAG_TEAM_A_ANGLE 30
#define FLAG_TEAM_B_ANGLE 150


// ============================================================
// GAME STATES
// ============================================================

enum GameState {
  IDLE,
  ARMED,
  IN_PROGRESS,
  RESULT
};


// ============================================================
// GAME MODES
// ============================================================

enum GameMode {
  KAMBA_VALI,
  LEMON_SPOON,
  MUSICAL_CHAIRS
};


// ============================================================
// GLOBAL OBJECTS
// ============================================================

MPU6050 imu;

Servo flagServo;


// ============================================================
// GLOBAL STATE
// ============================================================

GameState gameState = IDLE;

GameMode gameMode = KAMBA_VALI;


// ============================================================
// IMU STATE
// ============================================================

bool imuAvailable = false;

float accelX = 0.0;
float accelY = 0.0;
float accelZ = 0.0;

float previousAccelerationMagnitude = 0.0;

float accelerationMagnitude = 0.0;

float jerkG = 0.0;


// ============================================================
// GAME VARIABLES
// ============================================================

bool dropDetected = false;

bool finishDetected = false;

bool relayActive = false;

String winner = "";


// ============================================================
// TIMING
// ============================================================

unsigned long matchStartMicros = 0;

unsigned long relayCutoffMicros = 0;

unsigned long lastTelemetryMillis = 0;


// ============================================================
// IR SENSOR DEBOUNCE STATE
// ============================================================

int lastIRStateA = HIGH;

int lastIRStateB = HIGH;

unsigned long lastIRAChangeMillis = 0;

unsigned long lastIRBChangeMillis = 0;


// ============================================================
// MUSICAL CHAIRS
// ============================================================

float reactionTimeMs = -1.0;

bool reactionRecorded = false;


// ============================================================
// Convert Game State to Text
// ============================================================

const char* gameStateToString(GameState state) {

  switch (state) {

    case IDLE:
      return "IDLE";

    case ARMED:
      return "ARMED";

    case IN_PROGRESS:
      return "IN_PROGRESS";

    case RESULT:
      return "RESULT";
  }

  return "UNKNOWN";
}


// ============================================================
// Convert Game Mode to Text
// ============================================================

const char* gameModeToString(GameMode mode) {

  switch (mode) {

    case KAMBA_VALI:
      return "KAMBA_VALI";

    case LEMON_SPOON:
      return "LEMON_SPOON";

    case MUSICAL_CHAIRS:
      return "MUSICAL_CHAIRS";
  }

  return "UNKNOWN";
}


// ============================================================
// Set Game Mode
// ============================================================

void setGameMode(String mode) {

  mode.toUpperCase();

  if (mode == "KAMBA_VALI") {

    gameMode = KAMBA_VALI;
  }

  else if (mode == "LEMON_SPOON") {

    gameMode = LEMON_SPOON;
  }

  else if (mode == "MUSICAL_CHAIRS") {

    gameMode = MUSICAL_CHAIRS;
  }
}


// ============================================================
// Move Servo Flag
// ============================================================

void moveFlag(int angle) {

  angle = constrain(angle, 0, 180);

  flagServo.write(angle);
}


// ============================================================
// Reset Game
// ============================================================

void resetGame() {

  gameState = IDLE;

  winner = "";

  dropDetected = false;

  finishDetected = false;

  reactionTimeMs = -1.0;

  reactionRecorded = false;

  relayActive = false;

  matchStartMicros = 0;

  relayCutoffMicros = 0;

  previousAccelerationMagnitude = 0.0;

  accelerationMagnitude = 0.0;

  jerkG = 0.0;

  digitalWrite(RELAY_PIN, LOW);

  moveFlag(FLAG_HOME_ANGLE);
}


// ============================================================
// Start Match
// ============================================================

void startMatch() {

  winner = "";

  dropDetected = false;

  finishDetected = false;

  reactionRecorded = false;

  reactionTimeMs = -1.0;

  previousAccelerationMagnitude = 0.0;

  accelerationMagnitude = 0.0;

  jerkG = 0.0;

  matchStartMicros = micros();

  relayCutoffMicros = 0;

  gameState = IN_PROGRESS;
}


// ============================================================
// Read IMU
// ============================================================

void readIMU() {

  if (!imuAvailable) {

    accelX = 0.0;

    accelY = 0.0;

    accelZ = 0.0;

    accelerationMagnitude = 0.0;

    jerkG = 0.0;

    return;
  }


  int16_t ax;
  int16_t ay;
  int16_t az;

  int16_t gx;
  int16_t gy;
  int16_t gz;


  imu.getMotion6(
    &ax,
    &ay,
    &az,
    &gx,
    &gy,
    &gz
  );


  // MPU6050 default accelerometer range:
  // ±2g = 16384 LSB/g

  accelX = (float)ax / 16384.0;

  accelY = (float)ay / 16384.0;

  accelZ = (float)az / 16384.0;


  // Total acceleration magnitude

  accelerationMagnitude =
    sqrt(
      (accelX * accelX) +
      (accelY * accelY) +
      (accelZ * accelZ)
    );


  // Simple discrete jerk approximation

  jerkG =
    fabs(
      accelerationMagnitude -
      previousAccelerationMagnitude
    );


  previousAccelerationMagnitude =
    accelerationMagnitude;
}


// ============================================================
// Read Ultrasonic Distance
// ============================================================

float readDistanceCM() {

  digitalWrite(HC_TRIG_PIN, LOW);

  delayMicroseconds(2);

  digitalWrite(HC_TRIG_PIN, HIGH);

  delayMicroseconds(10);

  digitalWrite(HC_TRIG_PIN, LOW);


  unsigned long duration =
    pulseIn(
      HC_ECHO_PIN,
      HIGH,
      30000
    );


  if (duration == 0) {

    return -1.0;
  }


  float distance =
    (duration * 0.0343) / 2.0;


  return distance;
}


// ============================================================
// Kamba Vali Processing
// ============================================================

void processKambaVali() {

  int currentIR_A =
    digitalRead(IR_SENSOR_A);

  int currentIR_B =
    digitalRead(IR_SENSOR_B);


  unsigned long currentMillis =
    millis();


  bool sensorATriggered =
    currentIR_A == LOW &&
    lastIRStateA == HIGH &&
    (
      currentMillis -
      lastIRAChangeMillis
    ) >= IR_DEBOUNCE_MS;


  bool sensorBTriggered =
    currentIR_B == LOW &&
    lastIRStateB == HIGH &&
    (
      currentMillis -
      lastIRBChangeMillis
    ) >= IR_DEBOUNCE_MS;


  // Team A crossed the winning line

  if (sensorATriggered) {

    winner = "TEAM_A";

    gameState = RESULT;

    moveFlag(FLAG_TEAM_A_ANGLE);
  }


  // Team B crossed the winning line

  if (sensorBTriggered) {

    winner = "TEAM_B";

    gameState = RESULT;

    moveFlag(FLAG_TEAM_B_ANGLE);
  }


  // Track sensor changes

  if (currentIR_A != lastIRStateA) {

    lastIRAChangeMillis =
      currentMillis;
  }


  if (currentIR_B != lastIRStateB) {

    lastIRBChangeMillis =
      currentMillis;
  }


  lastIRStateA =
    currentIR_A;

  lastIRStateB =
    currentIR_B;
}


// ============================================================
// Lemon & Spoon Processing
// ============================================================

void processLemonSpoon() {

  readIMU();


  // Detect a sudden movement spike

  if (
    !dropDetected &&
    jerkG > DROP_JERK_THRESHOLD_G
  ) {

    dropDetected = true;

    winner = "LEMON_DROPPED";

    gameState = RESULT;
  }


  // IR sensor A acts as finish-line sensor

  int finishSensor =
    digitalRead(IR_SENSOR_A);


  if (
    !finishDetected &&
    finishSensor == LOW
  ) {

    finishDetected = true;


    if (!dropDetected) {

      winner = "FINISHED";

      gameState = RESULT;
    }
  }
}


// ============================================================
// Musical Chairs Processing
// ============================================================

void processMusicalChairs() {

  // Don't calculate another reaction
  // after one has already been recorded.

  if (reactionRecorded) {
    return;
  }


  float distance =
    readDistanceCM();


  if (
    distance > 0 &&
    distance < SEATING_DISTANCE_CM
  ) {

    unsigned long seatTime =
      micros();


    unsigned long elapsed =
      seatTime -
      matchStartMicros;


    reactionTimeMs =
      elapsed / 1000.0;


    reactionRecorded = true;

    winner = "SEATED";

    gameState = RESULT;
  }
}


// ============================================================
// Relay Control
// ============================================================

void setRelay(bool active) {

  relayActive = active;

  digitalWrite(
    RELAY_PIN,
    relayActive
      ? HIGH
      : LOW
  );


  // Record the moment the relay
  // changes state.

  if (!active) {

    relayCutoffMicros =
      micros();
  }
}


// ============================================================
// Process JSON Command
// ============================================================

void processCommand(String input) {

  StaticJsonDocument<512> document;


  DeserializationError error =
    deserializeJson(
      document,
      input
    );


  if (error) {

    return;
  }


  String command =
    document["command"] | "";


  command.toUpperCase();


  // ----------------------------------------------------------
  // START
  // ----------------------------------------------------------

  if (command == "START") {

    startMatch();

    return;
  }


  // ----------------------------------------------------------
  // RESET
  // ----------------------------------------------------------

  if (command == "RESET") {

    resetGame();

    return;
  }


  // ----------------------------------------------------------
  // SET MODE
  // ----------------------------------------------------------

  if (command == "SET_MODE") {

    String mode =
      document["mode"] |
      "KAMBA_VALI";


    setGameMode(mode);

    resetGame();

    return;
  }


  // ----------------------------------------------------------
  // SERVO
  // ----------------------------------------------------------

  if (command == "SERVO") {

    int angle =
      document["angle"] |
      FLAG_HOME_ANGLE;


    moveFlag(angle);

    return;
  }


  // ----------------------------------------------------------
  // RELAY
  // ----------------------------------------------------------

  if (command == "RELAY") {

    bool active =
      document["active"] |
      false;


    setRelay(active);

    return;
  }
}


// ============================================================
// Send Telemetry
// ============================================================

void sendTelemetry() {

  StaticJsonDocument<1024> document;


  document["type"] =
    "telemetry";


  document["state"] =
    gameStateToString(
      gameState
    );


  document["mode"] =
    gameModeToString(
      gameMode
    );


  document["timestamp_ms"] =
    millis();


  // IR

  document["ir_a"] =
    digitalRead(
      IR_SENSOR_A
    );


  document["ir_b"] =
    digitalRead(
      IR_SENSOR_B
    );


  // IMU

  document["accel_x_g"] =
    accelX;


  document["accel_y_g"] =
    accelY;


  document["accel_z_g"] =
    accelZ;


  document["accel_magnitude_g"] =
    accelerationMagnitude;


  document["jerk_g"] =
    jerkG;


  // Lemon & Spoon

  document["drop_detected"] =
    dropDetected;


  document["finish_detected"] =
    finishDetected;


  // Musical Chairs

  document["distance_cm"] =
    (
      gameMode ==
      MUSICAL_CHAIRS
    )
      ? readDistanceCM()
      : -1.0;


  document["reaction_time_ms"] =
    reactionTimeMs;


  // Relay

  document["relay_active"] =
    relayActive;


  // Result

  document["winner"] =
    winner;


  // Serialize as one line

  serializeJson(
    document,
    Serial
  );


  Serial.println();
}


// ============================================================
// Setup
// ============================================================

void setup() {

  Serial.begin(
    SERIAL_BAUD
  );


  // ----------------------------------------------------------
  // GPIO
  // ----------------------------------------------------------

  pinMode(
    IR_SENSOR_A,
    INPUT_PULLUP
  );


  pinMode(
    IR_SENSOR_B,
    INPUT_PULLUP
  );


  pinMode(
    HC_TRIG_PIN,
    OUTPUT
  );


  pinMode(
    HC_ECHO_PIN,
    INPUT
  );


  pinMode(
    RELAY_PIN,
    OUTPUT
  );


  digitalWrite(
    RELAY_PIN,
    LOW
  );


  // ----------------------------------------------------------
  // Servo
  // ----------------------------------------------------------

  flagServo.setPeriodHertz(
    50
  );


  flagServo.attach(
    SERVO_PIN,
    500,
    2400
  );


  flagServo.write(
    FLAG_HOME_ANGLE
  );


  // ----------------------------------------------------------
  // I2C
  // ----------------------------------------------------------

  Wire.begin(
    I2C_SDA,
    I2C_SCL
  );


  // ----------------------------------------------------------
  // MPU6050
  // ----------------------------------------------------------

  imu.initialize();


  if (imu.testConnection()) {

    imuAvailable = true;

  } else {

    imuAvailable = false;
  }


  // ----------------------------------------------------------
  // Initial State
  // ----------------------------------------------------------

  resetGame();
}


// ============================================================
// Main Loop
// ============================================================

void loop() {

  // ----------------------------------------------------------
  // Read incoming commands
  // ----------------------------------------------------------

  while (Serial.available() > 0) {

    String input =
      Serial.readStringUntil(
        '\n'
      );


    input.trim();


    if (input.length() > 0) {

      processCommand(input);
    }
  }


  // ----------------------------------------------------------
  // Process active game
  // ----------------------------------------------------------

  if (
    gameState ==
    IN_PROGRESS
  ) {

    switch (gameMode) {

      case KAMBA_VALI:

        readIMU();

        processKambaVali();

        break;


      case LEMON_SPOON:

        processLemonSpoon();

        break;


      case MUSICAL_CHAIRS:

        processMusicalChairs();

        break;
    }
  }


  // ----------------------------------------------------------
  // 25 Hz telemetry
  // ----------------------------------------------------------

  unsigned long currentMillis =
    millis();


  if (
    currentMillis -
    lastTelemetryMillis
    >= TELEMETRY_INTERVAL_MS
  ) {

    lastTelemetryMillis =
      currentMillis;


    sendTelemetry();
  }
}