//Granados Vazquez Pedro Daniel - 24212797
//Rodriguez Camarena Joshua Nezib - 24210524
//Ruan López Tai Ping Alejandra - 24170724
//Maquina virtual

#include <SoftwareSerial.h>
#include <DHT.h>
#include <LiquidCrystal.h>

//variable que define la comunicacion con la pico (rx d10, tx d11)
SoftwareSerial pico(10, 11);

//variable que define los pines de los 3 leds
const byte PIN_LED[3] = {2, 3, 4};
//variable que define el pin del buzzer
const byte PIN_BUZZER = 8;
//variable que define el pin del boton
const byte PIN_BOTON  = 7;
//variable que define el sensor dht11 en a3
DHT dht(A3, DHT11);
//variable que define la pantalla lcd (rs, e, d4, d5, d6, d7)
LiquidCrystal lcd(12, 9, 5, 6, A1, A2);
//variables que guardan la ultima lectura buena del dht11
int ultimaTemp = 0;
int ultimaHum = 0;

//variables que definen los codigos de operacion (iguales a los del compilador)
enum { FIN, LED, ESPERAR, BUZZER, REP_INI, REP_FIN, SI_FALSO, SALTAR, BOCINA, REPRODUCIR,
       LIMPIAR, LINEA, TEXTO, MOSTRAR };

//estructura que guarda una instruccion de 6 bytes
struct Instruccion {
  byte op;
  byte a;
  int b;
  unsigned int c;
};

//variable que define cuantas instrucciones caben
const byte MAX_INSTR = 50;
//variable que guarda el programa recibido
Instruccion programa[MAX_INSTR];
//variable que guarda cuantas instrucciones tiene el programa
byte numInstr = 0;

//variable que indica si hay un programa corriendo
bool ejecutando = false;
//variable que guarda el contador de programa
byte pc = 0;
//variable que guarda los contadores de los ciclos repetir
unsigned int pilaCiclos[8];
//variable que guarda la cima de la pila de ciclos
byte sp = 0;
//variable que guarda hasta cuando se espera
unsigned long esperarHasta = 0;
//variable que indica si se espera a que la pico w termine el audio
bool esperandoAudio = false;
//variable que guarda el tiempo limite para esperar el audio
unsigned long limiteAudio = 0;

//metodo que apaga los leds y el buzzer
void apagarTodo() {
  for (byte i = 0; i < 3; i++) digitalWrite(PIN_LED[i], LOW);
  noTone(PIN_BUZZER);
}

//metodo que detiene el programa
void detener() {
  ejecutando = false;
  esperandoAudio = false;
  apagarTodo();
}

//metodo que convierte un caracter hexadecimal en numero
int valorHex(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  return -1;
}

//metodo que carga el programa: lee el texto hexadecimal y lo convierte en instrucciones
void cargarPrograma() {
  detener();
  byte buf[6];
  byte nb = 0;
  byte n = 0;
  int alto = -1;
  bool error = false;
  unsigned long ultimo = millis();

  while (true) {
    if (pico.available()) {
      char ch = pico.read();
      ultimo = millis();
      if (ch == '\n') break;
      if (ch == '\r') continue;
      int v = valorHex(ch);
      if (v < 0) { error = true; continue; }
      if (alto < 0) {
        alto = v;
      } else {
        buf[nb++] = (alto << 4) | v;
        alto = -1;
        if (nb == 6) {
          if (n < MAX_INSTR) {
            programa[n].op = buf[0];
            programa[n].a  = buf[1];
            programa[n].b  = (int)((unsigned int)buf[2] | ((unsigned int)buf[3] << 8));
            programa[n].c  = (unsigned int)buf[4] | ((unsigned int)buf[5] << 8);
            n++;
          } else {
            error = true;
          }
          nb = 0;
        }
      }
    } else if (millis() - ultimo > 2000) {
      //se corto la transmision
      error = true;
      break;
    }
  }

  if (error || nb != 0 || alto >= 0 || n == 0) {
    numInstr = 0;
    pico.println(F("ERR"));
    Serial.println(F("Error al recibir el programa"));
    return;
  }

  numInstr = n;
  //se reinicia la pantalla por si se desincronizo
  lcd.begin(16, 2);
  pc = 0;
  sp = 0;
  esperarHasta = millis();
  ejecutando = true;
  pico.print(F("OK "));
  pico.println(n);
  Serial.print(F("\nPrograma recibido: "));
  Serial.print(n);
  Serial.println(F(" instrucciones. Ejecutando..."));
}

//metodo que lee la temperatura (si falla usa la anterior)
int leerTemperatura() {
  float t = dht.readTemperature();
  if (!isnan(t)) ultimaTemp = (int)(t + 0.5);
  return ultimaTemp;
}

//metodo que lee la humedad (si falla usa la anterior)
int leerHumedad() {
  float h = dht.readHumidity();
  if (!isnan(h)) ultimaHum = (int)(h + 0.5);
  return ultimaHum;
}

//metodo que lee un sensor: 0 temperatura, 1 boton, 2 humedad
int leerSensor(byte sensor) {
  if (sensor == 0) return leerTemperatura();
  if (sensor == 2) return leerHumedad();
  return (digitalRead(PIN_BOTON) == LOW) ? 1 : 0;
}

//metodo que escribe una letra en la pantalla si no es cero
void escribirLetra(byte x) {
  if (x) lcd.write(x);
}

//metodo que evalua la condicion de un si
bool evaluar(byte a, int valor) {
  byte sensor = a >> 4;
  byte comp = a & 0x0F;
  int x;
  if (sensor == 0) {
    x = leerTemperatura();
    Serial.print(F("   temperatura = ")); Serial.println(x);
  } else if (sensor == 2) {
    x = leerHumedad();
    Serial.print(F("   humedad = ")); Serial.println(x);
  } else {
    x = (digitalRead(PIN_BOTON) == LOW) ? 1 : 0;
    Serial.print(F("   boton = ")); Serial.println(x);
  }
  switch (comp) {
    case 0: return x <  valor;
    case 1: return x >  valor;
    case 2: return x <= valor;
    case 3: return x >= valor;
    case 4: return x == valor;
    case 5: return x != valor;
  }
  return false;
}

//metodo que ejecuta una instruccion
void paso() {
  if (pc >= numInstr) { detener(); return; }
  Instruccion &in = programa[pc];
  Serial.print(pc < 10 ? F("0") : F(""));
  Serial.print(pc);
  Serial.print(F(": "));
  pc++;

  switch (in.op) {
    case FIN:
      Serial.println(F("FIN"));
      detener();
      Serial.println(F("Programa terminado."));
      break;
    case LED:
      Serial.print(F("LED ")); Serial.print(in.a); Serial.println(in.b ? F(" ON") : F(" OFF"));
      if (in.a >= 1 && in.a <= 3) digitalWrite(PIN_LED[in.a - 1], in.b ? HIGH : LOW);
      break;
    case ESPERAR:
      Serial.print(F("ESPERAR ")); Serial.println(in.b);
      esperarHasta = millis() + in.b;
      break;
    case BUZZER:
      Serial.print(F("BUZZER ")); Serial.print(in.b); Serial.print(F(" Hz ")); Serial.println(in.c);
      tone(PIN_BUZZER, in.b, in.c);
      esperarHasta = millis() + in.c;
      break;
    case REP_INI:
      Serial.print(F("REP_INI ")); Serial.println(in.b);
      if (sp < 8) pilaCiclos[sp++] = in.b;
      break;
    case REP_FIN:
      Serial.println(F("REP_FIN"));
      if (sp > 0) {
        pilaCiclos[sp - 1]--;
        if (pilaCiclos[sp - 1] > 0) pc = in.c;
        else sp--;
      }
      break;
    case SI_FALSO:
      Serial.println(F("SI_FALSO"));
      if (!evaluar(in.a, in.b)) pc = in.c;
      break;
    case SALTAR:
      Serial.println(F("SALTAR"));
      pc = in.c;
      break;
    case BOCINA:
      //la nota la toca la pico w: el aviso viaja arduino -> pico -> pico w
      Serial.print(F("BOCINA ")); Serial.print(in.b); Serial.print(F(" Hz ")); Serial.println(in.c);
      pico.print(F("SND B ")); pico.print(in.b); pico.print(' '); pico.println(in.c);
      esperarHasta = millis() + in.c;
      break;
    case REPRODUCIR:
      Serial.println(F("REPRODUCIR cancion.wav (esperando a la Pico W)"));
      pico.println(F("SND W"));
      esperandoAudio = true;
      //limite por si nunca llega la respuesta
      limiteAudio = millis() + 60000UL;
      break;
    case LIMPIAR:
      Serial.println(F("LIMPIAR"));
      lcd.clear();
      break;
    case LINEA:
      Serial.print(F("LINEA ")); Serial.println(in.a);
      lcd.setCursor(0, in.a == 2 ? 1 : 0);
      break;
    case TEXTO: {
      Serial.println(F("TEXTO"));
      unsigned int b = (unsigned int)in.b;
      escribirLetra(in.a);
      escribirLetra(b & 0xFF);
      escribirLetra(b >> 8);
      escribirLetra(in.c & 0xFF);
      escribirLetra(in.c >> 8);
      break;
    }
    case MOSTRAR: {
      int v = leerSensor(in.a);
      Serial.print(F("MOSTRAR ")); Serial.println(v);
      lcd.print(v);
      break;
    }
    default:
      Serial.println(F("instruccion desconocida"));
      detener();
  }
}

//metodo que configura los pines, la pantalla y el sensor
void setup() {
  Serial.begin(9600);
  pico.begin(9600);
  for (byte i = 0; i < 3; i++) pinMode(PIN_LED[i], OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_BOTON, INPUT_PULLUP);
  dht.begin();
  //espera a que se estabilice la corriente
  delay(300);
  lcd.begin(16, 2);
  lcd.print(F("Arduino listo"));
  apagarTodo();
  Serial.println(F("Arduino listo. Esperando programa..."));
}

//metodo que se repite siempre: escucha a la pico y ejecuta el programa
void loop() {
  //revisa si llego algo de la pico
  if (pico.available()) {
    char ch = pico.read();
    if (ch == 'C') {
      cargarPrograma();
    } else if (ch == '?') {
      //confirmacion de conexion
      pico.println(F("Arduino listo"));
      Serial.println(F("Prueba de conexion -> Arduino listo"));
    } else if (ch == 'L' && esperandoAudio) {
      //la pico w termino de reproducir el audio
      esperandoAudio = false;
      esperarHasta = millis();
      Serial.println(F("   audio terminado"));
    }
  }

  //si la pico w nunca contesta se sigue despues de 60 s
  if (esperandoAudio && (long)(millis() - limiteAudio) >= 0) {
    esperandoAudio = false;
    Serial.println(F("   sin respuesta del audio, continuo"));
  }

  //ejecuta la siguiente instruccion cuando termina la espera
  if (ejecutando && !esperandoAudio && (long)(millis() - esperarHasta) >= 0) {
    paso();
  }
}
