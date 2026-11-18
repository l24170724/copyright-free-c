#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Prueba de conexion con el arduino

from machine import UART, Pin
import time

#variable que define la comunicacion con el arduino
uno = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))


#metodo que lee la respuesta del arduino hasta un salto de linea
def leer(espera_ms=1500):
    datos = b""
    t0 = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), t0) < espera_ms:
        if uno.any():
            datos += uno.read()
            if b"\n" in datos:
                break
        time.sleep_ms(5)
    return datos


print("Mandando '?' al Arduino...")
while uno.any():
    uno.read()
uno.write(b"?\n")
r = leer()
print("Respuesta:", r)
if b"Arduino listo" in r:
    print("OK: Pico <-> Arduino funciona (GP4->D10, D11->divisor->GP5, GND)")
elif r:
    print("Llegó algo pero no 'Arduino listo': revisa el divisor y el GND común")
else:
    print("Sin respuesta: revisa GP4->D10, D11->divisor->GP5 y el GND")

#programa de prueba ya compilado: el led 1 parpadea 3 veces
prog = ("040003000000" "010101000000" "02002C010000"
        "010100000000" "02002C010000" "050000000100" "000000000000")
uno.write(("C" + prog + "\n").encode())
print("Programa de prueba enviado. Respuesta:", leer(3000))
print("El LED 1 debe parpadear 3 veces.")
