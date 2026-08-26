#include <SPI.h>
#include <MFRC522.h>
#include <WiFi.h>
#include <HTTPClient.h>

// Put your WiFi name here. Example: "WiFi_5G"
const char* ssid = "";

// Put your WiFi password here. Example: "XXXXYYYY"
const char* password = "";

// Put the full scan API link here. Example: "http://YOUR_PC_IP/rfid_api/scan_tool.php"
const char* serverURL = "";

// RC522 pins

#define SS_PIN 5
#define RST_PIN 22

MFRC522 rfid(SS_PIN, RST_PIN);

// Save the last tag so the reader does not scan it twice.
String lastUID = "";
unsigned long lastScan = 0;

void setupWifi();
void reconnectWifi();
void sendUID(String uid);

void setup() {

  Serial.begin(115200);

  SPI.begin(18, 19, 23, SS_PIN);

  rfid.PCD_Init();

  setupWifi();

  Serial.println("RFID Tool Tracking System Ready");
}

// Keep checking until a new RFID tag is detected.

void loop() {

  reconnectWifi();

  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }

  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }

  String uid = "";

  for (byte i = 0; i < rfid.uid.size; i++) {

    if (rfid.uid.uidByte[i] < 0x10) {
      uid += "0";
    }

    uid += String(rfid.uid.uidByte[i], HEX);
  }

  uid.toUpperCase();

  // Do not accept the same tag again for 3 seconds.
  if (uid == lastUID && millis() - lastScan < 3000) {

    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    return;
  }

  lastUID = uid;
  lastScan = millis();

  Serial.print("UID : ");
  Serial.println(uid);

  Serial.println("Sending request...");

  sendUID(uid);

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
}

// Connect or reconnect to WiFi.

void setupWifi() {

  Serial.print("Connecting to WiFi");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");

  Serial.print("ESP32 IP : ");
  Serial.println(WiFi.localIP());
}

void reconnectWifi() {

  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  Serial.println("Reconnecting WiFi...");

  WiFi.disconnect();
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi reconnected");
}

// Send the scanned UID to the PHP API.

void sendUID(String uid) {

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("WiFi unavailable");
    return;
  }

  HTTPClient http;

  String url = String(serverURL) + "?uid=" + uid;

  Serial.print("Request URL : ");
  Serial.println(url);

  http.setTimeout(5000);

  http.begin(url);

  int httpCode = http.GET();

  if (httpCode > 0) {

    Serial.print("HTTP Code : ");
    Serial.println(httpCode);

    String response = http.getString();

    Serial.println("----------------");
    Serial.println("Server Response:");
    Serial.println(response);
    Serial.println("----------------");

  } else {

    Serial.print("HTTP Error : ");
    Serial.println(httpCode);
  }

  http.end();
}
