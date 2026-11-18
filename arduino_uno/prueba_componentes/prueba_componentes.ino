//Granados Vazquez Pedro Daniel - 24212797
//Rodriguez Camarena Joshua Nezib - 24210524
//Ruan López Tai Ping Alejandra - 24170724
//Prueba de leds, buzzer y boton

//variable que define los pines de los 3 leds
const byte LEDS[3] = {2, 3, 4};
//variable que define el pin del buzzer
const byte PIN_BUZZER = 8;
//variable que define el pin del boton
const byte PIN_BOTON = 7;

//metodo que prueba los leds y el buzzer una vez
void setup() {
  Serial.begin(9600);
  for (byte i = 0; i < 3; i++) pinMode(LEDS[i], OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BOTON, INPUT_PULLUP);

  Serial.println(F("1) LEDs uno por uno"));
  for (byte i = 0; i < 3; i++) {
    Serial.print(F("   LED ")); Serial.println(i + 1);
    digitalWrite(LEDS[i], HIGH); delay(700); digitalWrite(LEDS[i], LOW);
  }

  Serial.println(F("2) Buzzer: tres notas"));
  tone(PIN_BUZZER, 440, 300); delay(400);
  tone(PIN_BUZZER, 660, 300); delay(400);
  tone(PIN_BUZZER, 880, 300); delay(400);

  Serial.println(F("3) Presiona el boton: prende el LED 1 y pita"));
}

//variable que guarda la ultima vez que se imprimio
unsigned long ultimo = 0;

//metodo que revisa el boton todo el tiempo
void loop() {
  bool presionado = digitalRead(PIN_BOTON) == LOW;
  digitalWrite(LEDS[0], presionado ? HIGH : LOW);
  if (presionado) tone(PIN_BUZZER, 1000); else noTone(PIN_BUZZER);

  if (millis() - ultimo > 1000) {
    ultimo = millis();
    Serial.print(F("   boton: ")); Serial.println(presionado ? F("PRESIONADO") : F("suelto"));
  }
}
