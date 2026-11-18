#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Prueba de la bocina

from machine import I2S, Pin
import math, struct, time

#variable que controla el led de la placa
led = Pin("LED", Pin.OUT)
#variable que define la frecuencia de muestreo
RATE = 22050
#variable que define la salida i2s al max98357a (bclk gp10, lrc gp11, din gp9)
audio = I2S(0, sck=Pin(10), ws=Pin(11), sd=Pin(9),
            mode=I2S.TX, bits=16, format=I2S.MONO,
            rate=RATE, ibuf=8000)

#variable que define las muestras por periodo (cerca de 441 hz)
n = RATE // 441
#variable que guarda 20 periodos de la onda
buf = bytearray(n * 2 * 20)
for i in range(n * 20):
    s = int(20000 * math.sin(2 * math.pi * i / n))
    struct.pack_into("<h", buf, i * 2, s)

print("Debe sonar un pitido continuo...")
t0 = time.ticks_ms()
escrito = 0
try:
    while True:
        escrito += audio.write(buf)
        if time.ticks_diff(time.ticks_ms(), t0) > 500:
            led.toggle()
            print("bytes enviados:", escrito)
            t0 = time.ticks_ms()
finally:
    audio.deinit()
    led.off()
