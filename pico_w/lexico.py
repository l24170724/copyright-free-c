#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Fase lexica

#variable que guarda las palabras reservadas del lenguaje
PALABRAS_RESERVADAS = (
    "led", "encender", "apagar",
    "esperar", "buzzer", "bocina", "reproducir",
    "repetir", "si", "sino",
    "temperatura", "humedad", "boton",
    "mostrar", "limpiar", "linea",
)

#variable que guarda los operadores de comparacion validos
OPERADORES = ("<", ">", "<=", ">=", "==", "!=")


#metodo que revisa si un caracter es letra o guion bajo
def es_letra(c):
    return ("a" <= c <= "z") or ("A" <= c <= "Z") or c == "_"


#metodo que revisa si un caracter es un digito
def es_digito(c):
    return "0" <= c <= "9"


#metodo que separa el texto del programa en tokens y regresa (tokens, errores)
#cada token es una lista [tipo, valor, linea]
#tipos: RES, NUM, CADENA, OP, LLAVE_A, LLAVE_C
def analizar(codigo):
    tokens = []
    errores = []
    i = 0
    linea = 1
    n = len(codigo)

    while i < n:
        c = codigo[i]

        #salto de linea: se cuenta la linea
        if c == "\n":
            linea += 1
            i += 1
            continue
        #espacios y tabuladores: se ignoran
        if c in " \t\r":
            i += 1
            continue

        #comentario: se ignora desde # hasta el final de la linea
        if c == "#":
            while i < n and codigo[i] != "\n":
                i += 1
            continue

        #numero entero
        if es_digito(c):
            inicio = i
            while i < n and es_digito(codigo[i]):
                i += 1
            tokens.append(["NUM", codigo[inicio:i], linea])
            continue

        #palabra: debe ser una palabra reservada
        if es_letra(c):
            inicio = i
            while i < n and (es_letra(codigo[i]) or es_digito(codigo[i])):
                i += 1
            palabra = codigo[inicio:i].lower()
            if palabra in PALABRAS_RESERVADAS:
                tokens.append(["RES", palabra, linea])
            else:
                errores.append("Línea %d: palabra desconocida '%s'" % (linea, palabra))
            continue

        #cadena de texto entre comillas
        if c == '"':
            fin = codigo.find('"', i + 1)
            salto = codigo.find("\n", i + 1)
            if fin < 0 or (0 <= salto < fin):
                errores.append('Línea %d: falta cerrar el texto con "' % linea)
                i = salto if salto >= 0 else n
                continue
            tokens.append(["CADENA", codigo[i + 1:fin], linea])
            i = fin + 1
            continue

        #llaves de bloque
        if c == "{":
            tokens.append(["LLAVE_A", "{", linea])
            i += 1
            continue
        if c == "}":
            tokens.append(["LLAVE_C", "}", linea])
            i += 1
            continue

        #operadores de comparacion de uno o dos caracteres
        if c in "<>=!":
            if i + 1 < n and codigo[i + 1] == "=":
                op = c + "="
                i += 2
            else:
                op = c
                i += 1
            if op in OPERADORES:
                tokens.append(["OP", op, linea])
            else:
                errores.append("Línea %d: operador inválido '%s'" % (linea, op))
            continue

        #cualquier otro caracter es error lexico
        errores.append("Línea %d: carácter no válido '%s'" % (linea, c))
        i += 1

    return tokens, errores
