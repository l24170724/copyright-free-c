//Granados Vazquez Pedro Daniel - 24212797
//Rodriguez Camarena Joshua Nezib - 24210524
//Ruan López Tai Ping Alejandra - 24170724
//Prueba del dht11

#include <DHT.h>

//variable que define el sensor dht11 en a3
DHT dht(A3, DHT11);

//metodo que inicia el sensor
void setup() {
  Serial.begin(9600);
  dht.begin();
  Serial.println(F("Prueba DHT11: una lectura cada 2 segundos"));
}

//metodo que lee el sensor cada 2 segundos
void loop() {
  //el dht11 solo da una lectura nueva cada 1 o 2 segundos
  delay(2000);
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  if (isnan(h) || isnan(t)) {
    Serial.println(F("No se pudo leer el DHT11: revisa VCC, DATA (A3), GND y la resistencia de 10k"));
    return;
  }
  Serial.print(F("Temperatura: ")); Serial.print(t, 0);
  Serial.print(F(" C   Humedad: ")); Serial.print(h, 0); Serial.println(F(" %"));
}
