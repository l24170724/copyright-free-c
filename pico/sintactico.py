#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Fase sintactica, semantica y generacion de codigo

#gramatica del lenguaje ebnf:
#programa   = { sentencia } ;
#sentencia  = led | esperar | buzzer | bocina | reproducir | mostrar | limpiar | linea | repetir | si ;
#led        = "led" num ( "encender" | "apagar" ) ;
#esperar    = "esperar" num ;
#buzzer     = "buzzer" num num ;
#bocina     = "bocina" num num ;
#reproducir = "reproducir" ;
#mostrar    = "mostrar" ( cadena | "temperatura" | "humedad" | "boton" ) ;
#limpiar    = "limpiar" ;
#linea      = "linea" num ;
#repetir    = "repetir" num bloque ;
#si         = "si" condicion bloque [ "sino" bloque ] ;
#condicion  = ( "temperatura" | "humedad" | "boton" ) op num ;
#bloque     = "{" { sentencia } "}" ;


#clase que representa un error de la fase sintactica
class ErrorSintactico(Exception):
    pass


#clase que hace el analisis sintactico por descenso recursivo
class Parser:
    #metodo que guarda los tokens y empieza en la posicion 0
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    #metodo que regresa el token actual o none si ya no hay
    def actual(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    #metodo que revisa si el token actual es del tipo y valor indicados
    def es(self, tipo, valor=None):
        tok = self.actual()
        return tok is not None and tok[0] == tipo and (valor is None or tok[1] == valor)

    #metodo que lanza un error sintactico con la linea y lo que se esperaba
    def error(self, esperado):
        tok = self.actual()
        if tok is None:
            linea = self.tokens[-1][2] if self.tokens else 1
            encontrado = "el final del programa"
        else:
            linea = tok[2]
            encontrado = "'%s'" % tok[1]
        raise ErrorSintactico("Línea %d: se esperaba %s, pero se encontró %s" % (linea, esperado, encontrado))

    #metodo que avanza si el token es el esperado o lanza error
    def consumir(self, tipo, valor=None, descripcion=None):
        if not self.es(tipo, valor):
            self.error(descripcion or ("'%s'" % valor if valor else tipo))
        tok = self.actual()
        self.pos += 1
        return tok

    #metodo que lee un numero entero
    def numero(self, descripcion):
        return int(self.consumir("NUM", descripcion=descripcion)[1])

    #metodo de la regla programa = { sentencia }
    def programa(self):
        cuerpo = []
        while self.actual() is not None:
            cuerpo.append(self.sentencia())
        return {"tipo": "programa", "cuerpo": cuerpo}

    #metodo de la regla bloque = "{" { sentencia } "}"
    def bloque(self):
        self.consumir("LLAVE_A", descripcion="'{'")
        cuerpo = []
        while not self.es("LLAVE_C"):
            if self.actual() is None:
                self.error("'}' para cerrar el bloque")
            cuerpo.append(self.sentencia())
        self.pos += 1
        return cuerpo

    #metodo de la regla sentencia: decide que instruccion sigue
    def sentencia(self):
        tok = self.actual()
        if tok[0] != "RES":
            self.error("una instrucción (led, esperar, buzzer, bocina, reproducir, mostrar, limpiar, linea, repetir o si)")
        palabra = tok[1]
        linea = tok[2]

        if palabra == "led":
            self.pos += 1
            n = self.numero("el número de LED")
            if self.es("RES", "encender") or self.es("RES", "apagar"):
                accion = self.actual()[1]
                self.pos += 1
            else:
                self.error("'encender' o 'apagar'")
            return {"tipo": "led", "n": n, "accion": accion, "linea": linea}

        if palabra == "esperar":
            self.pos += 1
            ms = self.numero("los milisegundos a esperar")
            return {"tipo": "esperar", "ms": ms, "linea": linea}

        if palabra == "buzzer":
            self.pos += 1
            freq = self.numero("la frecuencia del buzzer (Hz)")
            dur = self.numero("la duración del buzzer (ms)")
            return {"tipo": "buzzer", "freq": freq, "dur": dur, "linea": linea}

        if palabra == "bocina":
            self.pos += 1
            freq = self.numero("la frecuencia de la bocina (Hz)")
            dur = self.numero("la duración de la nota (ms)")
            return {"tipo": "bocina", "freq": freq, "dur": dur, "linea": linea}

        if palabra == "reproducir":
            self.pos += 1
            return {"tipo": "reproducir", "linea": linea}

        if palabra == "mostrar":
            self.pos += 1
            if self.es("CADENA"):
                texto = self.actual()[1]
                self.pos += 1
                return {"tipo": "mostrar", "texto": texto, "linea": linea}
            if self.es("RES", "temperatura") or self.es("RES", "humedad") or self.es("RES", "boton"):
                sensor = self.actual()[1]
                self.pos += 1
                return {"tipo": "mostrar", "sensor": sensor, "linea": linea}
            self.error('un texto entre comillas, "temperatura", "humedad" o "boton"')

        if palabra == "limpiar":
            self.pos += 1
            return {"tipo": "limpiar", "linea": linea}

        if palabra == "linea":
            self.pos += 1
            n = self.numero("el número de renglón de la pantalla (1 o 2)")
            return {"tipo": "renglon", "n": n, "linea": linea}

        if palabra == "repetir":
            self.pos += 1
            veces = self.numero("cuántas veces repetir")
            cuerpo = self.bloque()
            return {"tipo": "repetir", "veces": veces, "cuerpo": cuerpo, "linea": linea}

        if palabra == "si":
            self.pos += 1
            if self.es("RES", "temperatura") or self.es("RES", "humedad") or self.es("RES", "boton"):
                sensor = self.actual()[1]
                self.pos += 1
            else:
                self.error("'temperatura', 'humedad' o 'boton'")
            op = self.consumir("OP", descripcion="un operador (<, >, <=, >=, ==, !=)")[1]
            valor = self.numero("un número para comparar")
            entonces = self.bloque()
            sino = None
            if self.es("RES", "sino"):
                self.pos += 1
                sino = self.bloque()
            return {"tipo": "si", "sensor": sensor, "op": op, "valor": valor,
                    "entonces": entonces, "sino": sino, "linea": linea}

        self.error("una instrucción (led, esperar, buzzer, bocina, reproducir, mostrar, limpiar, linea, repetir o si)")


#variable que define cuantos repetir anidados caben en la pila del arduino
MAX_ANIDAMIENTO = 8


#metodo que hace el analisis semantico y regresa la lista de errores
def semantico(ast):
    errores = []

    #metodo que revisa que un valor este dentro de su rango
    def rango(valor, minimo, maximo, que, linea):
        if valor < minimo or valor > maximo:
            errores.append("Línea %d: %s debe estar entre %d y %d (se puso %d)"
                           % (linea, que, minimo, maximo, valor))

    #metodo que recorre el arbol revisando cada sentencia
    def revisar(sentencias, nivel_ciclos):
        for s in sentencias:
            t = s["tipo"]
            L = s["linea"]
            if t == "led":
                rango(s["n"], 1, 3, "el número de LED", L)
            elif t == "esperar":
                rango(s["ms"], 1, 30000, "el tiempo de espera", L)
            elif t == "buzzer":
                rango(s["freq"], 31, 5000, "la frecuencia", L)
                rango(s["dur"], 1, 10000, "la duración", L)
            elif t == "bocina":
                rango(s["freq"], 50, 4000, "la frecuencia de la bocina", L)
                rango(s["dur"], 1, 10000, "la duración de la nota", L)
            elif t == "renglon":
                rango(s["n"], 1, 2, "el renglón de la pantalla", L)
            elif t == "mostrar" and "texto" in s:
                texto = s["texto"]
                if len(texto) == 0 or len(texto) > 16:
                    errores.append("Línea %d: el texto debe tener de 1 a 16 letras (la pantalla "
                                   "tiene 16 columnas; este tiene %d)" % (L, len(texto)))
                for ch in texto:
                    if not (32 <= ord(ch) <= 126):
                        errores.append("Línea %d: la pantalla no puede mostrar '%s' "
                                       "(usa letras sin acentos ni ñ)" % (L, ch))
                        break
            elif t == "repetir":
                rango(s["veces"], 1, 1000, "el número de repeticiones", L)
                if nivel_ciclos + 1 > MAX_ANIDAMIENTO:
                    errores.append("Línea %d: demasiados 'repetir' anidados (máximo %d)"
                                   % (L, MAX_ANIDAMIENTO))
                revisar(s["cuerpo"], nivel_ciclos + 1)
            elif t == "si":
                if s["sensor"] == "temperatura":
                    rango(s["valor"], 0, 50, "la temperatura (el DHT11 mide de 0 a 50)", L)
                elif s["sensor"] == "humedad":
                    rango(s["valor"], 0, 100, "la humedad (%)", L)
                else:
                    if s["valor"] not in (0, 1):
                        errores.append("Línea %d: 'boton' solo puede compararse con 0 o 1" % L)
                    if s["op"] not in ("==", "!="):
                        errores.append("Línea %d: 'boton' solo admite == o !=" % L)
                revisar(s["entonces"], nivel_ciclos)
                if s["sino"] is not None:
                    revisar(s["sino"], nivel_ciclos)

    revisar(ast["cuerpo"], 0)
    return errores


#variables que definen los codigos del bytecode (cada instruccion mide 6 bytes: op, a, b, c)
#0 fin, 1 led, 2 esperar, 3 buzzer, 4 rep_ini, 5 rep_fin, 6 si_falso, 7 saltar,
#8 bocina, 9 reproducir, 10 limpiar, 11 linea, 12 texto, 13 mostrar
(FIN, LED, ESPERAR, BUZZER, REP_INI, REP_FIN, SI_FALSO, SALTAR, BOCINA, REPRODUCIR,
 LIMPIAR, LINEA, TEXTO, MOSTRAR) = range(14)
#variable que guarda el nombre de cada codigo
NOMBRES = ("FIN", "LED", "ESPERAR", "BUZZER", "REP_INI", "REP_FIN", "SI_FALSO", "SALTAR",
           "BOCINA", "REPRODUCIR", "LIMPIAR", "LINEA", "TEXTO", "MOSTRAR")
#variable que define el numero de cada sensor en el arduino (0, 1, 2)
SENSORES = ("temperatura", "boton", "humedad")
#variable que define el numero de cada comparador
COMPARADORES = ("<", ">", "<=", ">=", "==", "!=")
#variable que define cuantas instrucciones caben en la ram del arduino
MAX_INSTRUCCIONES = 50


#metodo que genera el bytecode a partir del arbol
def generar(ast):
    codigo = []

    #metodo que agrega una instruccion y regresa su posicion
    def emitir(op, a=0, b=0, c=0):
        codigo.append([op, a, b, c])
        return len(codigo) - 1

    #metodo que traduce una lista de sentencias
    def gen(sentencias):
        for s in sentencias:
            t = s["tipo"]
            if t == "led":
                emitir(LED, s["n"], 1 if s["accion"] == "encender" else 0)
            elif t == "esperar":
                emitir(ESPERAR, 0, s["ms"])
            elif t == "buzzer":
                emitir(BUZZER, 0, s["freq"], s["dur"])
            elif t == "bocina":
                emitir(BOCINA, 0, s["freq"], s["dur"])
            elif t == "reproducir":
                emitir(REPRODUCIR)
            elif t == "limpiar":
                emitir(LIMPIAR)
            elif t == "renglon":
                emitir(LINEA, s["n"])
            elif t == "mostrar" and "texto" in s:
                texto = s["texto"]
                #cada instruccion texto guarda 5 letras
                for i in range(0, len(texto), 5):
                    k = [ord(ch) for ch in texto[i:i + 5]]
                    k += [0] * (5 - len(k))
                    emitir(TEXTO, k[0], k[1] | (k[2] << 8), k[3] | (k[4] << 8))
            elif t == "mostrar":
                emitir(MOSTRAR, SENSORES.index(s["sensor"]))
            elif t == "repetir":
                emitir(REP_INI, 0, s["veces"])
                inicio = len(codigo)
                gen(s["cuerpo"])
                emitir(REP_FIN, 0, 0, inicio)
            elif t == "si":
                cond = SENSORES.index(s["sensor"]) * 16 + COMPARADORES.index(s["op"])
                i_si = emitir(SI_FALSO, cond, s["valor"], 0)
                gen(s["entonces"])
                #backpatching: se rellena el destino del salto al terminar el bloque
                if s["sino"] is None:
                    codigo[i_si][3] = len(codigo)
                else:
                    i_saltar = emitir(SALTAR)
                    codigo[i_si][3] = len(codigo)
                    gen(s["sino"])
                    codigo[i_saltar][3] = len(codigo)

    gen(ast["cuerpo"])
    emitir(FIN)
    return codigo


#metodo que convierte el bytecode en texto legible para la pagina web
def desensamblar(codigo):
    lineas = []
    for i, (op, a, b, c) in enumerate(codigo):
        if op == LED:
            txt = "LED %d, %s" % (a, "ON" if b else "OFF")
        elif op == ESPERAR:
            txt = "ESPERAR %d ms" % b
        elif op == BUZZER:
            txt = "BUZZER %d Hz, %d ms" % (b, c)
        elif op == REP_INI:
            txt = "REP_INI %d" % b
        elif op == REP_FIN:
            txt = "REP_FIN -> %02d" % c
        elif op == SI_FALSO:
            txt = "SI_FALSO %s %s %d -> %02d" % (SENSORES[a // 16], COMPARADORES[a % 16], b, c)
        elif op == SALTAR:
            txt = "SALTAR -> %02d" % c
        elif op == BOCINA:
            txt = "BOCINA %d Hz, %d ms" % (b, c)
        elif op == REPRODUCIR:
            txt = "REPRODUCIR cancion.wav"
        elif op == LIMPIAR:
            txt = "LIMPIAR pantalla"
        elif op == LINEA:
            txt = "LINEA %d" % a
        elif op == TEXTO:
            letras = [a, b & 0xFF, b >> 8, c & 0xFF, c >> 8]
            txt = 'TEXTO "%s"' % "".join(chr(x) for x in letras if x)
        elif op == MOSTRAR:
            txt = "MOSTRAR %s" % SENSORES[a]
        else:
            txt = "FIN"
        lineas.append("%02d: %s" % (i, txt))
    return lineas


#metodo que convierte el bytecode en texto hexadecimal para enviarlo al arduino
def a_hex(codigo):
    partes = []
    for op, a, b, c in codigo:
        for byte in (op, a, b & 0xFF, (b >> 8) & 0xFF, c & 0xFF, (c >> 8) & 0xFF):
            partes.append("%02X" % byte)
    return "".join(partes)


#metodo que ejecuta las fases sintactica, semantica y de generacion
def compilar(tokens):
    try:
        ast = Parser(tokens).programa()
    except ErrorSintactico as e:
        return {"ok": False, "fase": "sintáctico", "errores": [str(e)]}

    errores = semantico(ast)
    if errores:
        return {"ok": False, "fase": "semántico", "errores": errores, "ast": ast}

    codigo = generar(ast)
    if len(codigo) > MAX_INSTRUCCIONES:
        return {"ok": False, "fase": "generación de código", "ast": ast,
                "asm": desensamblar(codigo),
                "errores": ["El programa usa %d instrucciones y el Arduino solo admite %d"
                            % (len(codigo), MAX_INSTRUCCIONES)]}

    return {"ok": True, "ast": ast, "asm": desensamblar(codigo), "hex": a_hex(codigo)}
