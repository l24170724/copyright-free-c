#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Comunicacion y compilacion

from machine import UART, Pin
import json
import time
import sintactico

#variable que controla el led de la placa
led = Pin("LED", Pin.OUT)
#variable que define la comunicacion con la pico w (gp0 tx, gp1 rx)
uart_picow = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1), rxbuf=8192, txbuf=8192)
#variable que define la comunicacion con el arduino (gp4 tx, gp5 rx con divisor de voltaje)
uart_uno = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5), rxbuf=512, txbuf=1024)

#variables que guardan lo recibido que aun no forma una linea completa
buffer_picow = b""
buffer_uno = b""


#metodo que convierte bytes a texto e ignora el ruido
def a_texto(crudo):
    try:
        return crudo.decode().strip()
    except Exception:
        return ""


#metodo que reenvia a la pico w los avisos de sonido del arduino
def reenviar_sonido(linea):
    print("Arduino ->", linea)
    uart_picow.write(linea + "\n")


#metodo que espera la respuesta del arduino y reenvia los avisos de sonido que lleguen
def leer_respuesta_uno(espera_ms):
    global buffer_uno
    inicio = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), inicio) < espera_ms:
        if uart_uno.any():
            buffer_uno += uart_uno.read(uart_uno.any())
            while b"\n" in buffer_uno:
                fin = buffer_uno.find(b"\n")
                linea = a_texto(buffer_uno[:fin])
                buffer_uno = buffer_uno[fin + 1:]
                if linea.startswith("SND"):
                    reenviar_sonido(linea)
                elif linea:
                    return linea
        else:
            time.sleep_ms(5)
    return None


#metodo que manda un mensaje al arduino y espera su respuesta
def hablar_con_uno(mensaje, espera_ms):
    uart_uno.write(mensaje)
    return leer_respuesta_uno(espera_ms)


#metodo que manda una respuesta en json a la pico w
def responder(diccionario):
    uart_picow.write(json.dumps(diccionario) + "\n")


#metodo que atiende cada mensaje que llega de la pico w
def atender(linea):
    #prueba de conexion entre las 3 placas
    if linea == "PING":
        r = hablar_con_uno(b"?\n", 1500)
        print("Prueba de conexion ->", r)
        responder({"pico": "Pico lista", "arduino": r or "sin respuesta"})

    #la pico w termino de reproducir el audio: el arduino puede seguir
    elif linea == "LISTO":
        uart_uno.write(b"L\n")

    #compilacion de un programa
    elif linea.startswith("COMPILAR "):
        led.on()
        try:
            tokens = json.loads(linea[9:])
            res = sintactico.compilar(tokens)
            if res["ok"]:
                print("Compilado:", len(res["asm"]), "instrucciones")
                #primero solo la c para que el arduino deje lo que hace y escuche
                uart_uno.write(b"C")
                time.sleep_ms(150)
                r = hablar_con_uno((res["hex"] + "\n").encode(), 6000)
                print("Arduino respondio:", r)
                #el hex no se manda a la pagina para que la respuesta sea corta
                del res["hex"]
                res["arduino"] = r or "sin respuesta"
                if not r or not r.startswith("OK"):
                    res["ok"] = False
                    res["fase"] = "envío al Arduino"
                    res["errores"] = ["El Arduino respondió: %s. Revisa los cables "
                                      "Pico-Arduino, el divisor y el GND común." % (r or "nada")]
            else:
                print("Error", res["fase"], res["errores"])
            responder(res)
        except Exception as e:
            responder({"ok": False, "fase": "Pico", "errores": ["Error interno: %s" % e]})
        led.off()


print("Pico lista: esperando a la Pico W...")
#ciclo principal: escucha a la pico w y al arduino
while True:
    hubo_algo = False

    #mensajes de la pico w
    if uart_picow.any():
        hubo_algo = True
        buffer_picow += uart_picow.read(uart_picow.any())
        while b"\n" in buffer_picow:
            fin = buffer_picow.find(b"\n")
            linea = a_texto(buffer_picow[:fin])
            buffer_picow = buffer_picow[fin + 1:]
            if linea:
                try:
                    atender(linea)
                except Exception as e:
                    print("Error atendiendo:", e)
                    led.off()

    #avisos de sonido del arduino mientras ejecuta un programa
    if uart_uno.any():
        hubo_algo = True
        buffer_uno += uart_uno.read(uart_uno.any())
        while b"\n" in buffer_uno:
            fin = buffer_uno.find(b"\n")
            linea = a_texto(buffer_uno[:fin])
            buffer_uno = buffer_uno[fin + 1:]
            if linea.startswith("SND"):
                reenviar_sonido(linea)

    if not hubo_algo:
        time.sleep_ms(2)
