#include <Arduino.h>

void setup() {
  Serial.begin(115200);
}

void loop() {
  Serial.println("Bonds-eye ESP32-S3 node active");
  delay(1000);
}
