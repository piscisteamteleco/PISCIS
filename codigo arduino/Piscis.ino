/**************************************************************************
  Ejemplo completo ESP32:
  - Mide TDS (sensor analógico) y temperatura (DS18B20)
  - Compensa TDS según temperatura
  - Sube TDS y temperatura a ThingSpeak (fields 1 y 2) cada 15 s
  - Lee un comando de color de ThingSpeak (field 3): RRGGBB o “RAINBOW”
  - Enciende una tira WS2812B con Adafruit_NeoPixel según el comando
  - Muestra alternadamente en OLED la lectura de TDS y de temperatura
**************************************************************************/

// ——————————— INCLUYE LIBRERÍAS ———————————
#include <WiFi.h>                // Conexión Wi-Fi
#include <HTTPClient.h>          // Cliente HTTP para leer ThingSpeak
#include <ThingSpeak.h>          // Biblioteca ThingSpeak (para escribir)
#include <OneWire.h>             // Comunicación 1-Wire (DS18B20)
#include <DallasTemperature.h>   // Lectura de DS18B20
#include <Wire.h>                // I2C para OLED
#include <Adafruit_GFX.h>        // Gráficos base para OLED
#include <Adafruit_SH110X.h>     // Driver para pantallas SH1106/SH1107
#include <Adafruit_NeoPixel.h>   // Control de tira WS2812B

// —————— 1) CREDENCIALES Y PARÁMETROS ——————
const char* ssid        = "mmmacademyAP";              // Nombre de tu red Wi-Fi
const char* password    = "MMMacademy2021";              // Contraseña de tu Wi-Fi

// ThingSpeak: canal y claves
const unsigned long channelID   = 2833025;        // ID de tu canal
const char* writeAPIKey          = "8S422K718DH5XBQW";  // Para escribir fields 1 y 2
const char* readAPIKey           = "78JUDN4L97ZJEZ3V";   // Si el canal es privado; si no, deja ""

WiFiClient  tsClient;          // Cliente para ThingSpeak (escritura)

// —————— 2) DEFINICIONES DE PINES ——————
#define TDS_PIN     34         // Pin analógico donde va el sensor TDS
#define ONE_WIRE_PIN 32        // Pin digital DATA del DS18B20
#define OLED_SDA    21         // Pin SDA para OLED (I2C)
#define OLED_SCL    22         // Pin SCL para OLED (I2C)
#define LED_PIN     2         // Pin de datos de la tira WS2812B
#define NUM_LEDS    30         // Número total de LEDs en la tira

// —————— 3) OBJETOS GLOBALES ——————

OneWire oneWire(ONE_WIRE_PIN);                 // Bus OneWire para DS18B20
DallasTemperature sensors(&oneWire);           // Objeto sensor DS18B20

Adafruit_SH1106G display(128, 64, &Wire, -1);  // Pantalla OLED SH1106 128×64

Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
// strip.begin() y strip.show() se llaman en setup()

// ThingSpeak timing
unsigned long lastTSWrite = 0;
const unsigned long TS_INTERVAL = 15000;  // 15.000 ms mínimo entre escrituras

// —————— 4) FUNCIONES AUXILIARES ——————

/**
 * Wheel(pos):
 *  Genera un color del arcoíris (255 colores).
 *  pos: valor de 0 a 255
 *  Devuelve un uint32_t con el color RGB empaquetado.
 */
uint32_t Wheel(uint8_t pos) {
  pos = 255 - pos;
  if (pos < 85)  return strip.Color(255 - pos * 3, 0, pos * 3);
  if (pos < 170) { pos -= 85; return strip.Color(0, pos * 3, 255 - pos * 3); }
                  pos -= 170;
  return strip.Color(pos * 3, 255 - pos * 3, 0);
}

/**
 * showRainbow():
 *  Recorre todos los LEDs y aplica un degradado arcoíris
 */
void showRainbow() {
  for (int i = 0; i < NUM_LEDS; i++) {
    // Distribuye los 256 tonos equitativamente en la tira
    uint8_t idx = (i * 256) / NUM_LEDS;
    strip.setPixelColor(i, Wheel(idx));
  }
  strip.show();
}

// —————— 5) setup(): configuración inicial ——————
void setup() {
  // Serial para debug
  Serial.begin(115200);
  delay(100);

  // 5.1 Conectar a Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());

  // 5.2 Inicializar ThingSpeak (escritura)
  ThingSpeak.begin(tsClient);

  // 5.3 Inicializar NeoPixel
  strip.begin();      // Configura pin y buffers
  strip.show();       // Apaga todos al arrancar

  // 5.4 Inicializar sensores y pantalla OLED
  sensors.begin();    // DS18B20
  Wire.begin(OLED_SDA, OLED_SCL); // I2C para OLED
  delay(250);
  display.begin(0x3C, true);      // Dirección 0x3C, sin reset pin
  display.setTextColor(SH110X_WHITE);
}

// —————— 6) loop(): bucle principal ——————
void loop() {
  // 6.1) Medir temperatura con DS18B20
  sensors.requestTemperatures();
  float tempC = sensors.getTempCByIndex(0);  // °C

  // 6.2) Leer sensor TDS (voltaje) y convertir a ppm
  int analogValue = analogRead(TDS_PIN);
  float voltage   = analogValue * (3.3 / 4095.0);
  float tdsRaw    = (133.42 * pow(voltage, 3)
                   - 255.86 * pow(voltage, 2)
                   
                   + 857.39 * voltage) * 0.5;
  // Compensación por temperatura (ref 25 °C, coef 2%/°C)
  int tdsInt = round(tdsRaw / (1.0 + 0.02 * (tempC - 25.0)));

  // 6.3) Escribir TDS y Temp en ThingSpeak cada 15 s
  if (millis() - lastTSWrite >= TS_INTERVAL) {
    ThingSpeak.setField(1, tdsInt);    // Field 1 = TDS (ppm)
    ThingSpeak.setField(2, tempC);     // Field 2 = Temp (°C)
    int resp = ThingSpeak.writeFields(channelID, writeAPIKey);
    Serial.print("ThingSpeak write result: ");
    Serial.println(resp);
    lastTSWrite = millis();
  }

  // 6.4) Leer comando de color (field 3) desde ThingSpeak
  String cmd;
  {
    HTTPClient http;
    String url = String("http://api.thingspeak.com/channels/") +
                 channelID + "/fields/3/last.txt";
    if (strlen(readAPIKey) > 0) {
      url += "?api_key=" + String(readAPIKey);
    }
    http.begin(url);
    int httpCode = http.GET();
    if (httpCode == 200) {
      cmd = http.getString();
      cmd.trim();  // Elimina espacios y saltos de línea
    }
    http.end();
  }
  Serial.print("Comando leido: ");
  Serial.println(cmd);

  // 6.5) Interpretar comando y cambiar LEDs
  if (cmd.equalsIgnoreCase("RAINBOW")) {
    // Efecto arcoíris
    showRainbow();
  }
  else if (cmd.length() == 6) {
    // Asume un hex RRGGBB
    long val = strtol(cmd.c_str(), NULL, 16);
    uint8_t r = (val >> 16) & 0xFF;
    uint8_t g = (val >>  8) & 0xFF;
    uint8_t b =  val        & 0xFF;
    // Pintar todos los LEDs con ese color
    for (int i = 0; i < NUM_LEDS; i++) {
      strip.setPixelColor(i, strip.Color(r, g, b));
    }
    strip.show();
  }
  // Si cmd no coincide con nada, mantiene el color anterior

  // 6.6) Mostrar en OLED: lectura de TDS + estado
  String estado, emoji;
  if      (tdsInt < 300) { estado = "Agua limpia"; emoji = ":)"; }
  else if (tdsInt < 600) { estado = "Calidad media"; emoji = ":|"; }
  else                   { estado = "Agua sucia";  emoji = ":("; }

  display.clearDisplay();
  // Línea de título
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("TDS");
  // Valor grande
  display.setTextSize(3);
  display.setCursor(0, 12);
  display.print(tdsInt);
  // Unidad
  display.setTextSize(2);
  display.print(" ppm");
  // Estado + emoji en la parte inferior
  display.setTextSize(1);
  display.setCursor(0, 55);
  display.print(estado);
  display.setCursor(80, 55);
  display.print(emoji);
  display.display();

  // Debug serial
  Serial.printf("TDS: %d ppm   %s %s\n", tdsInt, estado.c_str(), emoji.c_str());

  delay(5000);  // Espera 5 s antes de mostrar temperatura

  // 6.7) Mostrar en OLED: lectura de temperatura
  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("Temperatura");
  display.setTextSize(3);
  display.setCursor(0, 12);
  display.print(tempC, 1);
  display.setTextSize(2);
  display.print(" C");
  display.display();

  Serial.printf("Temperatura: %.1f °C\n", tempC);

  delay(5000);  // Espera 5 s antes de repetir el bucle
}
