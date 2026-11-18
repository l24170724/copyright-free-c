#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Prueba del audio wav

from machine import I2S, Pin
import struct
import os

#variable que define el nombre del archivo en la pico w
ARCHIVO = "cancion.wav"


#metodo que lee la cabecera del wav y regresa (canales, frecuencia, bits, tamano)
def leer_cabecera(f):
    if f.read(4) != b"RIFF":
        raise ValueError("No es un archivo WAV")
    f.read(4)
    if f.read(4) != b"WAVE":
        raise ValueError("No es un archivo WAV")
    canales = frecuencia = bits = None
    while True:
        cabeza = f.read(8)
        if len(cabeza) < 8:
            raise ValueError("No se encontró el audio en el WAV")
        ident = cabeza[0:4]
        tam = struct.unpack("<I", cabeza[4:8])[0]
        if ident == b"fmt ":
            datos = f.read(tam)
            formato, canales, frecuencia, _, _, bits = struct.unpack("<HHIIHH", datos[:16])
            if formato != 1:
                raise ValueError("El WAV debe ser PCM sin comprimir")
        elif ident == b"data":
            return canales, frecuencia, bits, tam
        else:
            #bloque que no se usa
            f.read(tam)


print("Espacio libre en la Pico W: %d KB" % (os.statvfs("/")[0] * os.statvfs("/")[3] // 1024))

with open(ARCHIVO, "rb") as f:
    canales, frecuencia, bits, tam = leer_cabecera(f)
    print("WAV: %d Hz, %d bits, %s, %.1f segundos"
          % (frecuencia, bits, "mono" if canales == 1 else "estéreo",
             tam / (frecuencia * canales * bits // 8)))
    if bits != 16:
        raise ValueError("Exporta el WAV como PCM de 16 bits")

    #variable que define la salida i2s al max98357a
    audio = I2S(0, sck=Pin(10), ws=Pin(11), sd=Pin(9),
                mode=I2S.TX, bits=16,
                format=I2S.MONO if canales == 1 else I2S.STEREO,
                rate=frecuencia, ibuf=20000)
    buf = bytearray(4096)
    vista = memoryview(buf)
    try:
        print("Reproduciendo...")
        while True:
            n = f.readinto(buf)
            if not n:
                break
            audio.write(vista[:n])
        print("Fin")
    finally:
        audio.deinit()
