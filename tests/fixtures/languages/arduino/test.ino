// Simple Arduino sketch

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // Main code that runs repeatedly
  digitalWrite(LED_BUILTIN, HIGH);
  delay(1000);
  digitalWrite(LED_BUILTIN, LOW);
  delay(1000);
  Serial.println("Blinking LED");
}

// A custom function
int calculateDelay(int baseDelay, int multiplier) {
  return baseDelay * multiplier;
}
