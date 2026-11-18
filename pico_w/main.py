#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Interfaz web, fase lexica y bocina

import network
import socket
import json
import time
import math
import struct
from machine import UART, Pin, I2S
import lexico

#variable que define el nombre de la red wi-fi que crea la pico w
SSID = "Copyright Free C"
#variable que define la contrasena de la red (minimo 8 caracteres)
PASSWORD = "compilador"

#variable que controla el led de la placa
led = Pin("LED", Pin.OUT)
#variable que define la comunicacion con la pico (gp0 tx, gp1 rx)
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1), rxbuf=8192, txbuf=8192)

#variable que define la frecuencia de muestreo de las notas
RATE = 16000
#variable que define el volumen de la bocina (0.0 a 1.0)
VOLUMEN = 0.3
#variable que define el archivo de audio que se reproduce
ARCHIVO_WAV = "cancion.wav"


#metodo que abre el i2s del amplificador max98357a (bclk gp10, lrc gp11, din gp9)
def abrir_i2s(rate):
    return I2S(0, sck=Pin(10), ws=Pin(11), sd=Pin(9), mode=I2S.TX,
               bits=16, format=I2S.MONO, rate=rate, ibuf=4000)


#variable que guarda la salida de audio
audio = abrir_i2s(RATE)
#variable que guarda las ondas ya calculadas para no repetirlas
_ondas = {}


#metodo que calcula un bloque de onda senoidal para una frecuencia
def onda(freq):
    if freq not in _ondas:
        n = max(2, int(RATE / freq))
        amp = int(32767 * VOLUMEN)
        periodo = bytearray(n * 2)
        for i in range(n):
            struct.pack_into("<h", periodo, i * 2, int(amp * math.sin(2 * math.pi * i / n)))
        bloque = bytearray()
        for _ in range(max(1, 800 // n)):
            bloque.extend(periodo)
        _ondas[freq] = bloque
    return _ondas[freq]


#metodo que toca una nota en la bocina durante cierto tiempo
def tocar_nota(freq, ms):
    bloque = onda(freq)
    restantes = RATE * ms // 1000 * 2
    while restantes > 0:
        k = min(restantes, len(bloque))
        audio.write(bloque[:k])
        restantes -= k


#metodo que reproduce el archivo wav en la bocina
def reproducir_wav():
    global audio
    try:
        f = open(ARCHIVO_WAV, "rb")
    except OSError:
        print("No existe %s en la Pico W" % ARCHIVO_WAV)
        return
    try:
        if f.read(4) != b"RIFF":
            raise ValueError("no es WAV")
        f.read(8)
        canales = rate = bits = None
        #se buscan los bloques fmt y data del archivo
        while True:
            cabeza = f.read(8)
            if len(cabeza) < 8:
                raise ValueError("WAV sin datos")
            tam = struct.unpack("<I", cabeza[4:8])[0]
            if cabeza[:4] == b"fmt ":
                d = f.read(tam)
                _, canales, rate, _, _, bits = struct.unpack("<HHIIHH", d[:16])
            elif cabeza[:4] == b"data":
                break
            else:
                f.read(tam)
        if bits != 16:
            raise ValueError("el WAV debe ser de 16 bits")
        audio.deinit()
        audio = I2S(0, sck=Pin(10), ws=Pin(11), sd=Pin(9), mode=I2S.TX, bits=16,
                    format=I2S.MONO if canales == 1 else I2S.STEREO,
                    rate=rate, ibuf=8000)
        buf = bytearray(4096)
        vista = memoryview(buf)
        print("Reproduciendo", ARCHIVO_WAV)
        while True:
            n = f.readinto(buf)
            if not n:
                break
            audio.write(vista[:n])
    except Exception as e:
        print("Error al reproducir:", e)
    finally:
        f.close()
        audio.deinit()
        audio = abrir_i2s(RATE)


#variable que guarda lo recibido que aun no forma una linea completa
pendiente = b""


#metodo que atiende los avisos del arduino: snd b frec dur (nota) o snd w (wav)
def atender_sonido(linea):
    partes = linea.split()
    if len(partes) == 4 and partes[1] == "B":
        tocar_nota(int(partes[2]), int(partes[3]))
    elif len(partes) == 2 and partes[1] == "W":
        reproducir_wav()
        #el arduino espera este aviso para seguir
        uart.write("LISTO\n")


#metodo que revisa si llegaron avisos de sonido
def revisar_sonidos():
    global pendiente
    if uart.any():
        pendiente += uart.read(uart.any())
    while b"\n" in pendiente:
        fin = pendiente.find(b"\n")
        try:
            linea = pendiente[:fin].decode().strip()
        except Exception:
            linea = ""
        pendiente = pendiente[fin + 1:]
        if linea.startswith("SND"):
            try:
                atender_sonido(linea)
            except Exception as e:
                print("Error de sonido:", e)


#metodo que espera una respuesta de la pico y atiende los sonidos que lleguen
def leer_linea(espera_ms):
    datos = b""
    inicio = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), inicio) < espera_ms:
        if uart.any():
            datos += uart.read(uart.any())
            while b"\n" in datos:
                fin = datos.find(b"\n")
                crudo = datos[:fin]
                datos = datos[fin + 1:]
                try:
                    linea = crudo.decode().strip()
                except Exception:
                    #linea con ruido: se descarta
                    continue
                if linea.startswith("SND"):
                    #el programa ya corre en el arduino: se toca el sonido
                    try:
                        atender_sonido(linea)
                    except Exception as e:
                        print("Error de sonido:", e)
                    continue
                if linea:
                    return linea
        else:
            time.sleep_ms(5)
    return None


#metodo que manda un mensaje a la pico y espera su respuesta
def hablar_con_pico(mensaje, espera_ms):
    global pendiente
    pendiente = b""
    while uart.any():
        uart.read()
    uart.write(mensaje + "\n")
    return leer_linea(espera_ms)


#metodo que prueba la conexion entre las 3 placas
def ping():
    r = hablar_con_pico("PING", 3000)
    if r is None:
        return {"pico": "sin respuesta", "arduino": "?"}
    try:
        return json.loads(r)
    except Exception:
        return {"pico": "respuesta con ruido: %s" % r, "arduino": "?"}


#metodo que compila un programa: fase lexica aqui y las demas en la pico
def compilar(codigo):
    tokens, errores = lexico.analizar(codigo)
    if errores:
        return {"ok": False, "fase": "léxico", "errores": errores, "tokens": tokens}
    if not tokens:
        return {"ok": False, "fase": "léxico", "errores": ["El programa está vacío"], "tokens": []}

    #si el arduino estaba leyendo el dht11 puede perder letras y responder err: se reintenta
    for intento in range(3):
        r = hablar_con_pico("COMPILAR " + json.dumps(tokens), 15000)
        if r is None:
            return {"ok": False, "fase": "comunicación", "tokens": tokens,
                    "errores": ["La Pico no respondió. Revisa los cables Pico W-Pico y el GND común."]}
        try:
            res = json.loads(r)
        except Exception:
            res = {"ok": False, "fase": "comunicación",
                   "errores": ["La respuesta de la Pico llegó con ruido. Intenta de nuevo."]}
        if res.get("fase") not in ("envío al Arduino", "comunicación"):
            break
        time.sleep_ms(300)
    res["tokens"] = tokens
    return res


#variable que guarda la pagina web del compilador
HTML = """<!DOCTYPE html>
<html lang="es" data-tema="oscuro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Copyright Free C</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%236d28d9'/%3E%3Cpath d='M21 9H11v14h10' fill='none' stroke='white' stroke-width='3.2' stroke-linecap='square'/%3E%3Crect x='19' y='14.5' width='4' height='3' fill='%23fb923c'/%3E%3C/svg%3E">
<style>
:root,[data-tema="oscuro"]{--fondo:#1a1126;--panel:#231835;--panel2:#2c1f42;--codigo:#150d20;--borde:#3d2d5a;--borde2:#57417e;
--texto:#f1ebfa;--suave:#c3b4dc;--tenue:#8f7fae;--morado:#a78bfa;--morado-fondo:#33244d;--naranja:#fb923c;--naranja-texto:#1a1126;--ok:#c4b5fd;--err:#fb923c}
[data-tema="claro"]{--fondo:#efe9fa;--panel:#f8f4ff;--panel2:#e9dffa;--codigo:#fdfbff;--borde:#d3c3ef;--borde2:#b9a2e3;
--texto:#2a1a45;--suave:#5b4884;--tenue:#8a78ad;--morado:#6d28d9;--morado-fondo:#e4d8fb;--naranja:#ea580c;--naranja-texto:#ffffff;--ok:#5b21b6;--err:#c2410c}
*{box-sizing:border-box;border-radius:0 !important}
html,body{margin:0;background:var(--fondo);color:var(--texto);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px}
code,pre,textarea,.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
button{font-family:inherit}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-thumb{background:var(--borde2)}::-webkit-scrollbar-track{background:transparent}
.vidrio{background:var(--panel);border:1px solid var(--borde)}
.barra{position:sticky;top:0;z-index:5;height:56px;display:flex;align-items:center;gap:14px;padding:0 16px;border-width:0 0 2px 0;border-bottom-color:var(--naranja)}
.marca{display:flex;align-items:center;gap:10px}
.marca svg{width:30px;height:30px;flex:none}
.marca b{font-size:15px;font-weight:700}
.marca span{color:var(--tenue);font-size:12.5px;padding-left:12px;border-left:1px solid var(--borde2)}
.espacio{flex:1}
.icono{width:34px;height:34px;display:grid;place-items:center;border:1px solid var(--borde2);background:var(--panel2);color:var(--texto);cursor:pointer}
.icono:hover{border-color:var(--naranja);color:var(--naranja)}
.icono svg{width:17px;height:17px}
.app{display:grid;grid-template-columns:300px 1fr;gap:16px;padding:16px}
.app.cerrado{grid-template-columns:0 1fr;gap:0}
aside{position:sticky;top:72px;height:calc(100vh - 88px);overflow-y:auto;overflow-x:hidden}
.app.cerrado aside{border:0;padding:0}
.ref{width:300px;padding:18px 20px 40px}
.ref h2{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--naranja);font-weight:700;margin:24px 0 10px}
.ref h2:first-child{margin-top:2px}
.ref p,.ref li{font-size:13px;line-height:1.6;color:var(--suave)}
.ref ul{padding-left:16px;margin:0}
.ref code{color:var(--morado);font-size:12.5px}
.palabras{display:flex;flex-wrap:wrap;gap:5px}
.palabras code{padding:2px 7px;background:var(--morado-fondo);border:1px solid var(--borde)}
.pista{font-size:12px!important;color:var(--tenue)!important;margin:0 0 8px}
.ins{display:flex;flex-direction:column;gap:6px}
.ins button{display:block;width:100%;text-align:left;cursor:pointer;background:var(--panel2);border:1px solid var(--borde);border-left:3px solid var(--morado);padding:8px 10px;font:inherit;color:inherit}
.ins button:hover{border-left-color:var(--naranja);background:var(--morado-fondo)}
.ins button.activo{border-color:var(--naranja);border-left-color:var(--naranja)}
.ins button code{display:block;color:var(--texto);font-weight:600;font-size:12.5px}
.ins button span{display:block;font-size:12px;color:var(--suave);line-height:1.45;margin-top:3px}
dl{margin:0}
dt{font-size:12.5px;margin-top:10px}
dt code{color:var(--texto);font-weight:600}
dd{margin:2px 0 0;font-size:12.5px;color:var(--suave);line-height:1.5}
.tabla{width:100%;border-collapse:collapse;font-size:12.5px}
.tabla td{padding:6px 0;border-bottom:1px solid var(--borde);text-align:left;vertical-align:top;color:var(--suave)}
.tabla td:first-child{color:var(--texto);padding-right:10px;white-space:nowrap}
.bloque{background:var(--codigo);border:1px solid var(--borde);padding:10px 12px;font-size:12px;line-height:1.55;color:var(--suave);white-space:pre;overflow-x:auto}
main{min-width:0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
section{min-width:0;display:flex;flex-direction:column}
.cab{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 16px;background:var(--panel2);border-bottom:1px solid var(--borde)}
.cab h3{margin:0;font-size:13px;font-weight:700;display:flex;align-items:center;gap:9px}
.cab h3 .num{width:22px;height:22px;display:grid;place-items:center;font-size:12px;font-weight:700;background:var(--naranja);color:var(--naranja-texto)}
.cab h3 small{font-weight:400;color:var(--tenue);font-size:12px}
.dato{font-size:12px;color:var(--tenue)}
.cuerpo{padding:14px 16px;flex:1;display:flex;flex-direction:column;min-height:0}
textarea{width:100%;height:320px;resize:vertical;background:var(--codigo);color:var(--texto);border:1px solid var(--borde);padding:12px 14px;font-size:13.5px;line-height:1.6;outline:none;tab-size:2}
textarea:focus{border-color:var(--naranja)}
.acciones{display:flex;gap:8px;align-items:center;margin-top:12px;flex-wrap:wrap}
.btn{padding:9px 16px;font-weight:600;font-size:13.5px;cursor:pointer;border:1px solid var(--borde2)}
.prim{background:var(--naranja);border-color:var(--naranja);color:var(--naranja-texto)}
.prim:hover{filter:brightness(1.08)}
.sec{background:var(--morado-fondo);color:var(--texto)}
.sec:hover{border-color:var(--morado)}
.atajo{margin-left:auto;color:var(--tenue);font-size:12px}
kbd{font-family:inherit;font-size:11px;border:1px solid var(--borde2);padding:1px 5px}
#estado{white-space:pre-wrap;margin:12px 0 0;font-size:13px;line-height:1.5;min-height:20px;color:var(--suave)}
#estado.ok{color:var(--ok);font-weight:600}#estado.err{color:var(--err);font-weight:600}
.caja{height:320px;overflow:auto}
table.tok{border-collapse:collapse;width:100%;font-size:12.5px}
table.tok th{position:sticky;top:0;background:var(--panel);color:var(--tenue);font-weight:600;text-align:left;padding:0 8px 8px;border-bottom:1px solid var(--borde2)}
table.tok td{padding:6px 8px;border-bottom:1px solid var(--borde)}
.t{font:11px ui-monospace,Consolas,monospace;padding:1px 6px;border:1px solid var(--borde2);color:var(--suave)}
.t-RES{color:var(--morado);background:var(--morado-fondo);border-color:var(--morado-fondo)}
.t-CADENA{color:var(--morado);border-style:dashed}
pre{margin:0;height:320px;overflow:auto;font-size:13px;line-height:1.6;color:var(--texto)}
.op{color:var(--naranja);font-weight:700}
.dir{color:var(--tenue)}
.vacio{color:var(--tenue);font-size:13px;font-family:inherit}
.circuito{margin-top:16px}
.circuito .cuerpo{padding:0}
.circuito svg{width:100%;height:auto;display:block}
@media(max-width:1100px){.grid{grid-template-columns:1fr}}
@media(max-width:820px){.app,.app.cerrado{grid-template-columns:1fr}aside{position:static;height:auto;max-height:55vh}.app.cerrado aside{display:none}.ref{width:auto}.marca span{display:none}}
</style>
</head>
<body>

<header class="barra vidrio">
  <button class="icono" id="btnRef" title="Mostrar u ocultar la referencia" aria-label="Mostrar u ocultar la referencia del lenguaje">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>
  </button>
  <div class="marca">
    <svg viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" fill="#6d28d9"/><path d="M21 9H11v14h10" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="square"/><rect x="19" y="14.5" width="4" height="3" fill="#fb923c"/></svg>
    <b>Copyright Free C</b>
    <span>Compilador distribuido · Pico W · Pico · Arduino</span>
  </div>
  <div class="espacio"></div>
  <button class="icono" id="btnTema" title="Cambiar a tema claro" aria-label="Cambiar entre tema claro y oscuro">
    <svg id="icoSol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
    <svg id="icoLuna" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="display:none"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>
  </button>
</header>

<div class="app" id="app">
<aside class="vidrio">
 <div class="ref">
  <h2>Estructura</h2>
  <ul>
    <li>Las instrucciones se ejecutan de arriba a abajo.</li>
    <li>Los bloques van entre <code>{ }</code>.</li>
    <li><code>#</code> inicia un comentario.</li>
    <li>Los espacios y saltos de línea no importan.</li>
    <li>Sin acentos: <code>boton</code>, no <code>botón</code>.</li>
  </ul>

  <h2>Palabras reservadas</h2>
  <div class="palabras">
    <code>led</code><code>encender</code><code>apagar</code><code>esperar</code><code>buzzer</code><code>bocina</code>
    <code>reproducir</code><code>mostrar</code><code>limpiar</code><code>linea</code><code>repetir</code><code>si</code>
    <code>sino</code><code>temperatura</code><code>humedad</code><code>boton</code>
  </div>

  <h2>Instrucciones</h2>
  <p class="pista">Toca una instrucción para cargar un ejemplo en el editor.</p>
  <div class="ins">
    <button type="button" data-ej="led"><code>led N encender | apagar</code><span>Prende o apaga el LED 1 (rojo), 2 (verde) o 3 (amarillo).</span></button>
    <button type="button" data-ej="esperar"><code>esperar ms</code><span>Pausa de 1 a 30000 milisegundos.</span></button>
    <button type="button" data-ej="bocina"><code>bocina frec ms</code><span>Nota en la bocina, de 50 a 4000 Hz.</span></button>
    <button type="button" data-ej="buzzer"><code>buzzer frec ms</code><span>Nota en el pin 8 del Arduino, de 31 a 5000 Hz.</span></button>
    <button type="button" data-ej="reproducir"><code>reproducir</code><span>Reproduce cancion.wav y espera a que termine.</span></button>
    <button type="button" data-ej="texto"><code>mostrar "texto"</code><span>Escribe en la pantalla. Máximo 16 letras, sin acentos.</span></button>
    <button type="button" data-ej="sensor"><code>mostrar sensor</code><span>Escribe el valor de temperatura, humedad o boton.</span></button>
    <button type="button" data-ej="limpiar"><code>limpiar</code><span>Borra la pantalla.</span></button>
    <button type="button" data-ej="linea"><code>linea N</code><span>Pasa al renglón 1 o 2.</span></button>
    <button type="button" data-ej="repetir"><code>repetir N { ... }</code><span>Repite el bloque de 1 a 1000 veces.</span></button>
    <button type="button" data-ej="si"><code>si condicion { ... } sino { ... }</code><span>Ejecuta un bloque si se cumple; el sino es opcional.</span></button>
  </div>

  <h2>Sensores</h2>
  <table class="tabla">
    <tr><td>temperatura</td><td>0 a 50 °C</td></tr>
    <tr><td>humedad</td><td>0 a 100 %</td></tr>
    <tr><td>boton</td><td>0 o 1, solo == y !=</td></tr>
  </table>

  <h2>Operadores</h2>
  <div class="palabras"><code>&lt;</code><code>&gt;</code><code>&lt;=</code><code>&gt;=</code><code>==</code><code>!=</code></div>

  <h2>Tipos de token</h2>
  <table class="tabla">
    <tr><td>RES</td><td>Palabra reservada</td></tr>
    <tr><td>NUM</td><td>Número entero</td></tr>
    <tr><td>CADENA</td><td>Texto entre comillas</td></tr>
    <tr><td>OP</td><td>Operador de comparación</td></tr>
    <tr><td>LLAVE_A / C</td><td>Llaves { y }</td></tr>
  </table>

  <h2>Gramática (EBNF)</h2>
  <div class="bloque">programa  = { sentencia } ;
sentencia = led | esperar | bocina
          | buzzer | reproducir
          | mostrar | limpiar | linea
          | repetir | si ;
led       = "led" NUM
            ( "encender" | "apagar" ) ;
repetir   = "repetir" NUM bloque ;
si        = "si" condicion bloque
            [ "sino" bloque ] ;
condicion = sensor OP NUM ;
mostrar   = "mostrar" ( CADENA | sensor ) ;
bloque    = "{" { sentencia } "}" ;</div>

  <h2>Límites</h2>
  <ul>
    <li>Máximo 50 instrucciones de bytecode.</li>
    <li>Cada 5 letras de texto ocupan 1 instrucción.</li>
    <li>LEDs del 1 al 3; renglones 1 y 2.</li>
  </ul>

  <h2>Errores por fase</h2>
  <table class="tabla">
    <tr><td>Léxico</td><td><code>led 1 prender</code></td></tr>
    <tr><td>Léxico</td><td><code>mostrar "Hola</code></td></tr>
    <tr><td>Sintáctico</td><td><code>repetir 3 { led 1 encender</code></td></tr>
    <tr><td>Semántico</td><td><code>led 5 encender</code></td></tr>
    <tr><td>Generación</td><td>Más de 50 instrucciones</td></tr>
  </table>

  <h2>Bytecode</h2>
  <table class="tabla">
    <tr><td>0 FIN</td><td>Termina</td></tr>
    <tr><td>1 LED</td><td>Prende o apaga</td></tr>
    <tr><td>2 ESPERAR</td><td>Pausa</td></tr>
    <tr><td>3 BUZZER</td><td>Nota en pin 8</td></tr>
    <tr><td>4 REP_INI</td><td>Inicia ciclo</td></tr>
    <tr><td>5 REP_FIN</td><td>Resta y regresa</td></tr>
    <tr><td>6 SI_FALSO</td><td>Salta si es falso</td></tr>
    <tr><td>7 SALTAR</td><td>Salto</td></tr>
    <tr><td>8 BOCINA</td><td>Nota en la Pico W</td></tr>
    <tr><td>9 REPRODUCIR</td><td>Audio WAV</td></tr>
    <tr><td>10 LIMPIAR</td><td>Borra la pantalla</td></tr>
    <tr><td>11 LINEA</td><td>Cambia de renglón</td></tr>
    <tr><td>12 TEXTO</td><td>Hasta 5 letras</td></tr>
    <tr><td>13 MOSTRAR</td><td>Valor de un sensor</td></tr>
  </table>
 </div>
</aside>

<main>
  <div class="grid">
    <section class="vidrio">
      <div class="cab"><h3>Código fuente</h3><span class="dato" id="nlineas">0 líneas</span></div>
      <div class="cuerpo">
      <textarea id="src" spellcheck="false"># Prueba de todos los componentes
limpiar
mostrar "Copyright Free C"
repetir 2 {
  led 1 encender
  bocina 440 150
  led 1 apagar
  led 2 encender
  bocina 550 150
  led 2 apagar
  led 3 encender
  bocina 660 150
  led 3 apagar
}
limpiar
mostrar "Temp: "
mostrar temperatura
mostrar " C"
linea 2
mostrar "Humedad: "
mostrar humedad
mostrar "%"
si temperatura > 30 {
  led 1 encender
}
si humedad > 60 {
  led 2 encender
}
esperar 4000
limpiar
mostrar "Aprieta boton"
esperar 3000
limpiar
si boton == 1 {
  mostrar "Boton: OK"
  led 3 encender
  reproducir
} sino {
  mostrar "Sin boton"
  bocina 220 500
}
led 3 apagar
limpiar
mostrar "Fin"</textarea>
      <div class="acciones">
        <button class="btn prim" onclick="compilar()">Compilar y ejecutar</button>
        <button class="btn sec" onclick="ping()">Probar conexión</button>
        <span class="atajo"><kbd>Ctrl</kbd> + <kbd>Enter</kbd></span>
      </div>
      <p id="estado"></p>
      </div>
    </section>

    <section class="vidrio">
      <div class="cab"><h3><span class="num">1</span>Tokens <small>Pico W</small></h3><span class="dato" id="ntok">—</span></div>
      <div class="cuerpo"><div class="caja" id="tokens"><p class="vacio">Compila para ver los tokens.</p></div></div>
    </section>

    <section class="vidrio">
      <div class="cab"><h3><span class="num">2</span>Árbol sintáctico <small>Pico</small></h3></div>
      <div class="cuerpo"><pre id="ast"><span class="vacio">Compila para ver el árbol.</span></pre></div>
    </section>

    <section class="vidrio">
      <div class="cab"><h3><span class="num">3</span>Bytecode <small>Pico → Arduino</small></h3><span class="dato" id="ninst">0 / 50</span></div>
      <div class="cuerpo"><pre id="asm"><span class="vacio">Compila para ver el bytecode.</span></pre></div>
    </section>
  </div>

  <section class="circuito vidrio">
    <div class="cab"><h3>Circuito</h3><span class="dato">3 placas · 7 componentes</span></div>
    <div class="cuerpo"><svg id="circ" viewBox="0 0 1280 600" role="img" aria-label="Diagrama del circuito: Pico W, Pico y Arduino Uno con sus componentes"></svg></div>
  </section>
</main>
</div>

<script>
const $ = id => document.getElementById(id);
const NL = String.fromCharCode(10);
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
function leer(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }

//metodo que aplica el tema claro u oscuro
function aplicarTema(t) {
  document.documentElement.setAttribute('data-tema', t);
  $('icoSol').style.display = t === 'oscuro' ? '' : 'none';
  $('icoLuna').style.display = t === 'oscuro' ? 'none' : '';
  $('btnTema').title = t === 'oscuro' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro';
  dibujarCircuito();
}
$('btnTema').onclick = () => {
  const t = document.documentElement.getAttribute('data-tema') === 'oscuro' ? 'claro' : 'oscuro';
  guardar('tema', t); aplicarTema(t);
};

//metodo que abre o cierra la referencia
function aplicarRef(cerrado) { $('app').classList.toggle('cerrado', cerrado); }
$('btnRef').onclick = () => { const c = !$('app').classList.contains('cerrado'); guardar('refCerrada', c ? '1' : '0'); aplicarRef(c); };

//metodos del editor
function est(t, c) { $('estado').textContent = t; $('estado').className = c || ''; }
function contarLineas() { $('nlineas').textContent = $('src').value.split(NL).length + ' líneas'; }
$('src').addEventListener('input', contarLineas);
$('src').addEventListener('keydown', e => {
  if (e.key === 'Tab') {
    e.preventDefault();
    const t = e.target, a = t.selectionStart;
    t.value = t.value.slice(0, a) + '  ' + t.value.slice(t.selectionEnd);
    t.selectionStart = t.selectionEnd = a + 2;
  }
  if (e.key === 'Enter' && e.ctrlKey) { e.preventDefault(); compilar(); }
});

function nodo(n) {
  switch (n.tipo) {
    case 'led': return 'led ' + n.n + ' ' + n.accion;
    case 'esperar': return 'esperar ' + n.ms + ' ms';
    case 'buzzer': return 'buzzer ' + n.freq + ' Hz, ' + n.dur + ' ms';
    case 'bocina': return 'bocina ' + n.freq + ' Hz, ' + n.dur + ' ms';
    case 'reproducir': return 'reproducir cancion.wav';
    case 'mostrar': return 'mostrar ' + (n.texto !== undefined ? '"' + n.texto + '"' : n.sensor);
    case 'limpiar': return 'limpiar pantalla';
    case 'renglon': return 'linea ' + n.n;
    case 'repetir': return 'repetir x' + n.veces;
    case 'si': return 'si ' + n.sensor + ' ' + n.op + ' ' + n.valor;
    default: return n.tipo;
  }
}
function arbol(lista, pre) {
  let s = '';
  lista.forEach((n, i) => {
    const u = i === lista.length - 1;
    s += pre + (u ? '└─ ' : '├─ ') + nodo(n) + NL;
    const p = pre + (u ? '   ' : '│  ');
    if (n.tipo === 'repetir') s += arbol(n.cuerpo, p);
    if (n.tipo === 'si') {
      const hs = !!n.sino;
      s += p + (hs ? '├─ ' : '└─ ') + 'entonces' + NL + arbol(n.entonces, p + (hs ? '│  ' : '   '));
      if (hs) s += p + '└─ sino' + NL + arbol(n.sino, p + '   ');
    }
  });
  return s;
}
function pintarAsm(lineas) {
  return lineas.map(l => {
    const k = l.indexOf(': ');
    const num = l.slice(0, k), resto = l.slice(k + 2);
    const sp = resto.indexOf(' ');
    const op = sp < 0 ? resto : resto.slice(0, sp);
    const args = sp < 0 ? '' : resto.slice(sp);
    return '<span class="dir">' + num + '</span>  <span class="op">' + esc(op) + '</span>' + esc(args);
  }).join(NL);
}
function limpiarPaneles() {
  $('tokens').innerHTML = '<p class="vacio">…</p>';
  $('ast').innerHTML = ''; $('asm').innerHTML = '';
  $('ntok').textContent = '—'; $('ninst').textContent = '0 / 50';
}
async function compilar() {
  limpiarPaneles();
  est('Compilando…');
  try {
    const r = await fetch('/compilar', {method: 'POST', body: $('src').value});
    const d = await r.json();
    if (d.tokens) {
      $('ntok').textContent = d.tokens.length + ' tokens';
      $('tokens').innerHTML = '<table class="tok"><tr><th>#</th><th>Tipo</th><th>Valor</th><th>Línea</th></tr>' +
        d.tokens.map((t, i) => '<tr><td class="dir">' + i + '</td><td><span class="t t-' + t[0] + '">' + t[0] +
        '</span></td><td class="mono">' + esc(t[1]) + '</td><td class="dir">' + t[2] + '</td></tr>').join('') + '</table>';
    }
    if (d.ast) $('ast').textContent = 'programa' + NL + arbol(d.ast.cuerpo, '');
    if (d.asm) { $('asm').innerHTML = pintarAsm(d.asm); $('ninst').textContent = d.asm.length + ' / 50'; }
    if (d.ok) est('Compilado: ' + d.asm.length + ' instrucciones · Arduino: ' + d.arduino, 'ok');
    else est('Error ' + d.fase + ':' + NL + d.errores.join(NL), 'err');
  } catch (e) {
    est('No se pudo conectar con la Pico W.' + NL + 'Si abriste este archivo en la computadora es normal: la página debe servirla la Pico W.', 'err');
  }
}
async function ping() {
  est('Probando conexión…');
  try {
    const d = await (await fetch('/ping')).json();
    est('Pico: ' + d.pico + '  ·  Arduino: ' + d.arduino, d.arduino === 'Arduino listo' ? 'ok' : 'err');
  } catch (e) { est('No se pudo conectar con la Pico W.', 'err'); }
}

//metodo que dibuja el circuito segun el tema
function dibujarCircuito() {
  const S = $('circ'), NS = 'http://www.w3.org/2000/svg';
  while (S.firstChild) S.removeChild(S.firstChild);
  const claro = document.documentElement.getAttribute('data-tema') === 'claro';
  const C = claro
    ? {fondo:'none', placa:'#f8f4ff', borde:'#b9a2e3', txt:'#2a1a45', suave:'#5b4884', u1:'#6d28d9', u2:'#8b5cf6', u3:'#7c3aed', i2s:'#a78bfa', v5:'#ea580c', gnd:'#a99bc4', dato:'#7c3aed', res:'#5b21b6', resf:'#e9dffa'}
    : {fondo:'none', placa:'#231835', borde:'#57417e', txt:'#f1ebfa', suave:'#c3b4dc', u1:'#a78bfa', u2:'#c4b5fd', u3:'#8b5cf6', i2s:'#d8b4fe', v5:'#fb923c', gnd:'#6f5f8e', dato:'#b197fc', res:'#e9d5ff', resf:'#33244d'};
  function el(t, a, txt) { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); if (txt != null) e.textContent = txt; S.appendChild(e); return e; }
  function texto(x, y, t, o) { o = o || {}; return el('text', {x, y, fill: o.c || C.txt, 'font-size': o.s || 11, 'text-anchor': o.a || 'start', 'dominant-baseline': 'central', 'font-family': o.m ? 'ui-monospace,Consolas,monospace' : 'Inter,system-ui,sans-serif', 'font-weight': o.w || 400}, t); }
  function cable(p, c, w) { el('polyline', {points: p.map(q => q.join(',')).join(' '), fill: 'none', stroke: c, 'stroke-width': w || 1.8, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}); }
  function punto(x, y, c) { el('circle', {cx: x, cy: y, r: 3, fill: c}); }
  function placa(x, y, w, h, nombre, rol) {
    el('rect', {x, y, width: w, height: h, rx: 0, fill: C.placa, stroke: C.borde});
    texto(x + w / 2, y + 26, nombre, {a: 'middle', s: 14, w: 600});
    texto(x + w / 2, y + 44, rol, {a: 'middle', s: 11, c: C.suave});
  }
  function tierra(x, y) { cable([[x - 9, y], [x + 9, y]], C.gnd); cable([[x - 6, y + 4], [x + 6, y + 4]], C.gnd); cable([[x - 3, y + 8], [x + 3, y + 8]], C.gnd); }
  function resH(x1, x2, y, et) { el('rect', {x: x1, y: y - 6, width: x2 - x1, height: 12, rx: 0, fill: C.resf, stroke: C.res}); texto((x1 + x2) / 2, y - 15, et, {a: 'middle', s: 10.5, c: C.res}); }
  function resV(x, y1, y2, et) { el('rect', {x: x - 5, y: y1, width: 10, height: y2 - y1, rx: 0, fill: C.resf, stroke: C.res}); if (et) texto(x - 10, (y1 + y2) / 2, et, {a: 'end', s: 10.5, c: C.res}); }

  el('rect', {x: 0, y: 0, width: 1280, height: 600, fill: C.fondo});
  placa(40, 40, 220, 200, 'Raspberry Pi Pico W', 'léxico · web · audio');
  placa(470, 40, 220, 200, 'Raspberry Pi Pico', 'sintáctico · semántico · código');
  placa(920, 40, 320, 200, 'Arduino Uno', 'máquina virtual');

  [['GP0 TX', 110], ['GP1 RX', 140], ['GND', 170]].forEach(p => texto(250, p[1], p[0], {a: 'end', m: 1, c: C.suave, s: 10.5}));
  const pwAbajo = [['GP9', 70, 'DIN'], ['GP10', 110, 'BCLK'], ['GP11', 150, 'LRC'], ['VBUS', 190, 'VIN'], ['GND', 230, 'GND']];
  pwAbajo.forEach(p => texto(p[1], 226, p[0], {a: 'middle', m: 1, c: C.suave, s: 10}));
  [['GP1 RX', 110], ['GP0 TX', 140], ['GND', 170]].forEach(p => texto(480, p[1], p[0], {m: 1, c: C.suave, s: 10.5}));
  [['GP4 TX', 110], ['VSYS', 140], ['GND', 170], ['GP5 RX', 200]].forEach(p => texto(680, p[1], p[0], {a: 'end', m: 1, c: C.suave, s: 10.5}));
  [['D10', 110], ['5V', 140], ['GND', 170], ['D11', 200]].forEach(p => texto(930, p[1], p[0], {m: 1, c: C.suave, s: 10.5}));
  [['D2', 945], ['D3', 975], ['D4', 1005], ['D7', 1035], ['A3', 1065], ['D12', 1105], ['D9', 1130], ['D5', 1155], ['D6', 1180], ['A1', 1205], ['A2', 1230]]
    .forEach(p => texto(p[1], 226, p[0], {a: 'middle', m: 1, c: C.suave, s: 10}));

  cable([[260, 110], [470, 110]], C.u1); cable([[260, 140], [470, 140]], C.u2); cable([[260, 170], [470, 170]], C.gnd);
  texto(365, 100, 'TX → RX', {a: 'middle', s: 10, c: C.u1}); texto(365, 130, 'RX ← TX', {a: 'middle', s: 10, c: C.u2});
  texto(365, 196, 'UART 115200 baud (cruzado)', {a: 'middle', s: 10.5, c: C.suave});
  cable([[690, 110], [920, 110]], C.u3); texto(805, 100, 'GP4 → D10', {a: 'middle', s: 10, c: C.u3});
  cable([[690, 140], [920, 140]], C.v5); texto(805, 130, '5V → VSYS', {a: 'middle', s: 10, c: C.v5});
  cable([[690, 170], [920, 170]], C.gnd);
  cable([[920, 200], [875, 200]], C.dato); resH(825, 875, 200, '5.1 kΩ'); cable([[825, 200], [690, 200]], C.dato);
  punto(790, 200, C.dato); cable([[790, 200], [790, 214]], C.dato); resV(790, 214, 248, '10 kΩ'); cable([[790, 248], [790, 260]], C.gnd); tierra(790, 260);
  texto(805, 236, 'divisor 5 V → 3.3 V', {s: 10, c: C.suave});

  pwAbajo.forEach(p => cable([[p[1], 240], [p[1], 330]], p[0] === 'VBUS' ? C.v5 : p[0] === 'GND' ? C.gnd : C.i2s));
  el('rect', {x: 40, y: 330, width: 220, height: 90, rx: 0, fill: C.placa, stroke: C.borde});
  pwAbajo.forEach(p => texto(p[1], 345, p[2], {a: 'middle', m: 1, c: C.suave, s: 9.5}));
  texto(150, 384, 'MAX98357A', {a: 'middle', s: 13, w: 600}); texto(150, 402, 'amplificador I2S', {a: 'middle', s: 10.5, c: C.suave});
  cable([[130, 420], [130, 470]], C.i2s); cable([[170, 420], [170, 470]], C.i2s);
  texto(122, 445, '+', {a: 'end', c: C.suave}); texto(178, 445, '−', {c: C.suave});
  el('rect', {x: 125, y: 470, width: 50, height: 22, rx: 0, fill: C.placa, stroke: C.borde});
  el('polygon', {points: '125,492 175,492 195,540 105,540', fill: C.placa, stroke: C.borde});
  texto(150, 560, 'Bocina 4 Ω · 3 W', {a: 'middle', s: 11.5});

  const ley = [['UART (serial)', C.u1], ['Audio I2S', C.i2s], ['5 V', C.v5], ['GND', C.gnd], ['Señales del Arduino', C.dato]];
  texto(330, 300, 'Leyenda', {s: 12, w: 600});
  ley.forEach((l, i) => { cable([[330, 326 + i * 24], [362, 326 + i * 24]], l[1], 3); texto(372, 326 + i * 24, l[0], {s: 11, c: C.suave}); });
  texto(330, 470, 'Pico W ⇄ Pico: 115200 baud', {s: 11, c: C.suave});
  texto(330, 490, 'Pico ⇄ Arduino: 9600 baud', {s: 11, c: C.suave});
  texto(330, 510, 'GND común entre las tres placas', {s: 11, c: C.suave});

  [[945, '#ef4444', 'L1'], [975, '#22c55e', 'L2'], [1005, '#eab308', 'L3']].forEach(l => {
    const x = l[0];
    cable([[x, 240], [x, 286]], C.dato); resV(x, 286, 322);
    cable([[x, 322], [x, 344]], C.dato);
    el('polygon', {points: (x - 8) + ',344 ' + (x + 8) + ',344 ' + x + ',360', fill: l[1], stroke: l[1]});
    cable([[x - 8, 361], [x + 8, 361]], l[1]);
    cable([[x, 361], [x, 384]], C.gnd); tierra(x, 384);
    texto(x, 408, l[2], {a: 'middle', s: 10, c: C.suave});
  });
  texto(935, 304, '220 Ω', {a: 'end', s: 10, c: C.res});

  cable([[1035, 240], [1035, 306]], C.dato); punto(1035, 306, C.dato); punto(1035, 330, C.gnd);
  cable([[1030, 302], [1046, 334]], C.txt, 2); cable([[1035, 330], [1035, 384]], C.gnd); tierra(1035, 384);
  texto(1030, 408, 'botón', {a: 'middle', s: 10, c: C.suave});

  cable([[1065, 240], [1065, 296]], C.dato);
  el('rect', {x: 1050, y: 296, width: 30, height: 46, rx: 0, fill: C.placa, stroke: C.borde});
  for (let i = 0; i < 4; i++) el('rect', {x: 1056, y: 302 + i * 9, width: 18, height: 4, rx: 0, fill: C.borde});
  cable([[1065, 342], [1065, 384]], C.gnd); tierra(1065, 384);
  texto(1068, 424, 'DHT11', {a: 'middle', s: 10, c: C.suave});
  texto(1068, 440, '10 kΩ a 5 V', {a: 'end', s: 9.5, c: C.res});

  const lcd = [['RS', 1105], ['E', 1130], ['D4', 1155], ['D5', 1180], ['D6', 1205], ['D7', 1230]];
  lcd.forEach(p => cable([[p[1], 240], [p[1], 440]], C.dato));
  el('rect', {x: 1092, y: 440, width: 152, height: 92, rx: 0, fill: C.placa, stroke: C.borde});
  lcd.forEach(p => texto(p[1], 452, p[0], {a: 'middle', m: 1, s: 9.5, c: C.suave}));
  el('rect', {x: 1102, y: 466, width: 132, height: 44, rx: 0, fill: '#3b5bdb'});
  texto(1110, 480, 'Copyright Free C', {m: 1, s: 11, c: '#eef2ff'});
  texto(1110, 498, 'Temp: 24 C', {m: 1, s: 11, c: '#eef2ff'});
  texto(1168, 522, 'LCD 1602A', {a: 'middle', s: 10, c: C.suave});
  texto(1240, 552, 'V0: 10 kΩ a 5 V + 2 kΩ a GND · RW a GND', {a: 'end', s: 10, c: C.suave});
  texto(1240, 570, 'VDD y BLA a 5 V · GND y BLK a GND', {a: 'end', s: 10, c: C.suave});
}

//inicio de la pagina
contarLineas();
//ejemplos que se cargan al tocar una instruccion
const EJEMPLOS = {
  led: ['# prende y apaga los 3 leds', 'led 1 encender', 'esperar 500', 'led 2 encender', 'esperar 500', 'led 3 encender', 'esperar 1000', 'led 1 apagar', 'led 2 apagar', 'led 3 apagar'],
  esperar: ['# el led 1 se queda prendido 2 segundos', 'led 1 encender', 'esperar 2000', 'led 1 apagar'],
  bocina: ['# escala musical en la bocina', 'bocina 262 300', 'bocina 294 300', 'bocina 330 300', 'bocina 349 300', 'bocina 392 300', 'bocina 440 300', 'bocina 494 300', 'bocina 523 600'],
  buzzer: ['# tres pitidos en el buzzer', 'repetir 3 {', '  buzzer 880 200', '  esperar 300', '}'],
  reproducir: ['# reproduce la cancion mientras el led 2 esta prendido', 'led 2 encender', 'reproducir', 'led 2 apagar'],
  texto: ['# escribe en los dos renglones de la pantalla', 'limpiar', 'linea 1', 'mostrar "Copyright Free C"', 'linea 2', 'mostrar "Hola equipo"'],
  sensor: ['# muestra la temperatura y la humedad', 'limpiar', 'linea 1', 'mostrar "Temp: "', 'mostrar temperatura', 'linea 2', 'mostrar "Humedad: "', 'mostrar humedad'],
  limpiar: ['# escribe un texto y despues lo borra', 'mostrar "Se va a borrar"', 'esperar 2000', 'limpiar'],
  linea: ['# usa el renglon 1 y el renglon 2', 'limpiar', 'linea 1', 'mostrar "Renglon 1"', 'linea 2', 'mostrar "Renglon 2"'],
  repetir: ['# el led 3 parpadea 5 veces', 'repetir 5 {', '  led 3 encender', '  esperar 300', '  led 3 apagar', '  esperar 300', '}'],
  si: ['# durante 10 segundos revisa el boton', 'repetir 20 {', '  si boton == 1 {', '    led 2 encender', '    led 1 apagar', '  } sino {', '    led 1 encender', '    led 2 apagar', '  }', '  esperar 500', '}', 'led 1 apagar', 'led 2 apagar']
};
document.querySelectorAll('.ins button').forEach(b => {
  b.onclick = () => {
    $('src').value = EJEMPLOS[b.dataset.ej].join(NL) + NL;
    contarLineas();
    limpiarPaneles();
    document.querySelectorAll('.ins button').forEach(x => x.classList.toggle('activo', x === b));
    est('Ejemplo cargado: ' + b.querySelector('code').textContent + '. Presiona Compilar y ejecutar.');
    if (window.innerWidth <= 820) $('src').scrollIntoView({behavior: 'smooth'});
  };
});
aplicarRef(leer('refCerrada') === '1');
aplicarTema(leer('tema') || 'oscuro');
</script>
</body>
</html>
"""


#metodo que lee una peticion http y regresa (metodo, ruta, cuerpo)
def leer_peticion(cliente):
    datos = b""
    while b"\r\n\r\n" not in datos:
        trozo = cliente.recv(1024)
        if not trozo:
            break
        datos += trozo
    fin = datos.find(b"\r\n\r\n")
    if fin < 0:
        return None, None, b""
    cabecera = datos[:fin].decode()
    cuerpo = datos[fin + 4:]
    lineas = cabecera.split("\r\n")
    partes = lineas[0].split(" ")
    if len(partes) < 2:
        return None, None, b""
    largo = 0
    for l in lineas[1:]:
        if l.lower().startswith("content-length:"):
            largo = int(l.split(":")[1])
    while len(cuerpo) < largo:
        trozo = cliente.recv(1024)
        if not trozo:
            break
        cuerpo += trozo
    return partes[0], partes[1], cuerpo


#metodo que manda una respuesta http al navegador
def enviar(cliente, tipo, texto):
    cuerpo = texto.encode()
    cliente.sendall(("HTTP/1.1 200 OK\r\nContent-Type: %s; charset=utf-8\r\n"
                     "Content-Length: %d\r\nConnection: close\r\n\r\n" % (tipo, len(cuerpo))).encode())
    cliente.sendall(cuerpo)


#arranque: la pico w crea su propia red wi-fi
print("Creando la red Wi-Fi '%s'..." % SSID)
ap = network.WLAN(network.AP_IF)
ap.config(essid=SSID, password=PASSWORD)
ap.active(True)
for _ in range(20):
    if ap.active():
        break
    time.sleep(0.5)
ip = ap.ifconfig()[0]
led.on()
print("Red lista. Conéctate a '%s' (contraseña: %s) y abre:  http://%s" % (SSID, PASSWORD, ip))

print("Probando conexión con la Pico y el Arduino...")
estado = ping()
print(estado.get("pico"), "/", estado.get("arduino"))

#variable que guarda el servidor web
direccion = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
servidor = socket.socket()
servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
servidor.bind(direccion)
servidor.listen(2)
#tiempo corto para que el ciclo no se quede esperando y pueda atender la bocina
servidor.settimeout(0.05)

#ciclo principal: atiende sonidos y peticiones de la pagina
while True:
    revisar_sonidos()
    cliente = None
    try:
        try:
            cliente, _ = servidor.accept()
        except OSError:
            #nadie abrio la pagina: se siguen revisando los sonidos
            continue
        cliente.settimeout(10)
        metodo, ruta, cuerpo = leer_peticion(cliente)
        if metodo == "POST" and ruta == "/compilar":
            res = compilar(cuerpo.decode())
            enviar(cliente, "application/json", json.dumps(res))
        elif ruta == "/ping":
            enviar(cliente, "application/json", json.dumps(ping()))
        elif ruta == "/":
            enviar(cliente, "text/html", HTML)
        else:
            cliente.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
    except Exception as e:
        print("Error:", e)
    finally:
        if cliente:
            cliente.close()
