//Granados Vazquez Pedro Daniel - 24212797
//Rodriguez Camarena Joshua Nezib - 24210524
//Ruan López Tai Ping Alejandra - 24170724
//Prueba de pantalla y dht11

#include <LiquidCrystal.h>
#include <DHT.h>

//variable que define la pantalla lcd (rs, e, d4, d5, d6, d7)
LiquidCrystal lcd(12, 9, 5, 6, A1, A2);
//variable que define el sensor dht11 en a3
DHT dht(A3, DHT11);

//metodo que inicia la pantalla y el sensor
void setup() {
  Serial.begin(9600);
  lcd.begin(16, 2);
  lcd.print("Copyright Free C");
  lcd.setCursor(0, 1);
  lcd.print("Probando DHT11..");
  dht.begin();
  delay(2000);
}

//metodo que muestra la temperatura y la humedad cada 2 segundos
void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  lcd.clear();
  if (isnan(h) || isnan(t)) {
    lcd.print("DHT11: sin datos");
    lcd.setCursor(0, 1);
    lcd.print("Revisa cables");
    Serial.println(F("No se pudo leer el DHT11"));
  } else {
    lcd.print("Temp: ");
    lcd.print(t, 0);
    //simbolo de grado
    lcd.print((char)223);
    lcd.print("C");
    lcd.setCursor(0, 1);
    lcd.print("Humedad: ");
    lcd.print(h, 0);
    lcd.print("%");
    Serial.print(F("Temperatura: ")); Serial.print(t);
    Serial.print(F(" C   Humedad: ")); Serial.print(h); Serial.println(F(" %"));
  }
  //el dht11 solo da una lectura nueva cada 1 o 2 segundos
  delay(2000);
}
