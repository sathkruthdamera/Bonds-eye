#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

#ifndef BONDSEYE_WIFI_SSID
#define BONDSEYE_WIFI_SSID "YOUR_T_MOBILE_HOTSPOT_SSID"
#endif

#ifndef BONDSEYE_WIFI_PASSWORD
#define BONDSEYE_WIFI_PASSWORD "YOUR_T_MOBILE_HOTSPOT_PASSWORD"
#endif

#ifndef BONDSEYE_GATEWAY_IP
#define BONDSEYE_GATEWAY_IP "192.168.1.100"
#endif

#ifndef BONDSEYE_GATEWAY_PORT
#define BONDSEYE_GATEWAY_PORT 45454
#endif

#ifndef BONDSEYE_NODE_ID
#define BONDSEYE_NODE_ID "esp32s3-node-01"
#endif

#ifndef BONDSEYE_SAMPLE_MS
#define BONDSEYE_SAMPLE_MS 500
#endif

WiFiUDP udp;
uint32_t sequenceNumber = 0;
unsigned long lastSampleMs = 0;

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.print("Connecting to WiFi: ");
  Serial.println(BONDSEYE_WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(BONDSEYE_WIFI_SSID, BONDSEYE_WIFI_PASSWORD);

  unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("Connected. Node IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("WiFi connection failed; retrying later");
  }
}

void sendTelemetry() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
    return;
  }

  int rssi = WiFi.RSSI();
  unsigned long timestamp = millis();

  String payload = "{";
  payload += "\"node_id\":\"";
  payload += BONDSEYE_NODE_ID;
  payload += "\",";
  payload += "\"rssi\":";
  payload += String(rssi);
  payload += ",";
  payload += "\"sequence\":";
  payload += String(sequenceNumber++);
  payload += ",";
  payload += "\"timestamp_ms\":";
  payload += String(timestamp);
  payload += "}";

  udp.beginPacket(BONDSEYE_GATEWAY_IP, BONDSEYE_GATEWAY_PORT);
  udp.print(payload);
  udp.endPacket();

  Serial.println(payload);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Bonds-eye ESP32-S3 RSSI node starting");
  connectWifi();
}

void loop() {
  if (millis() - lastSampleMs >= BONDSEYE_SAMPLE_MS) {
    lastSampleMs = millis();
    sendTelemetry();
  }
}
