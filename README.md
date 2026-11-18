# Copyright Free C

Compilador distribuido para un lenguaje de programación en español que controla hardware. El programa se escribe en una página web y pasa por tres placas que lo traducen y lo ejecutan en LEDs, un botón, un sensor de temperatura y humedad, una pantalla LCD y una bocina.

Proyecto del Instituto Tecnológico de Tijuana.

## Integrantes

| Nombre | Número de control |
|---|---|
| Granados Vazquez Pedro Daniel | 24212797 |
| Rodriguez Camarena Joshua Nezib | 24210524 |
| Ruan López Tai Ping Alejandra | 24170724 |

## Cómo funciona

1. **Raspberry Pi Pico W.** Crea la red Wi-Fi, muestra la página web y hace el análisis léxico (separa el programa en tokens). También toca los sonidos en la bocina.
2. **Raspberry Pi Pico.** Hace el análisis sintáctico y el semántico, y genera el bytecode.
3. **Arduino UNO.** Ejecuta el bytecode con una máquina virtual y controla los componentes.

Las placas se comunican por UART. La Pico W y la Pico usan 115 200 baudios, y la Pico y el Arduino usan 9600 baudios.

## Archivos

| Carpeta | Placa | Archivos |
|---|---|---|
| `pico_w` | Raspberry Pi Pico W | `main.py`, `lexico.py`, `cancion.wav` y pruebas de la bocina |
| `pico` | Raspberry Pi Pico | `main.py`, `sintactico.py` y `prueba_uart.py` |
| `arduino_uno` | Arduino UNO | `maquina_virtual` y pruebas de los componentes |
| `pc` | Computadora | `probar_en_pc.py` para probar el compilador sin placas |

## Cómo usarlo

1. Instala MicroPython en las dos Pico y la librería **DHT sensor library** de Adafruit en el Arduino IDE.
2. Carga `maquina_virtual.ino` en el Arduino.
3. Guarda los archivos de la carpeta `pico` en la Pico y los de la carpeta `pico_w` en la Pico W.
4. Conecta tu celular o laptop a la red **Copyright Free C** con la contraseña **compilador**.
5. Abre **http://192.168.4.1**, escribe un programa y presiona **Compilar y ejecutar**.

## Ejemplo del lenguaje

```
repetir 3 {
  led 1 encender
  esperar 500
  led 1 apagar
  esperar 500
}
si temperatura > 28 {
  mostrar "Hace calor"
} sino {
  bocina 440 300
}
```

## Instrucciones

| Instrucción | Qué hace |
|---|---|
| `led N encender` / `apagar` | Prende o apaga el LED 1, 2 o 3 |
| `esperar ms` | Espera de 1 a 30 000 milisegundos |
| `bocina frec ms` | Toca una nota en la bocina |
| `buzzer frec ms` | Toca una nota en el buzzer |
| `reproducir` | Reproduce `cancion.wav` |
| `mostrar "texto"` | Escribe un texto en la pantalla |
| `mostrar sensor` | Muestra la temperatura, la humedad o el botón |
| `limpiar` | Borra la pantalla |
| `linea N` | Pasa al renglón 1 o 2 |
| `repetir N { }` | Repite un bloque N veces |
| `si condicion { } sino { }` | Ejecuta un bloque si se cumple la condición |
