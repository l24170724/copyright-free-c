#Granados Vazquez Pedro Daniel - 24212797
#Rodriguez Camarena Joshua Nezib - 24210524
#Ruan López Tai Ping Alejandra - 24170724
#Prueba del compilador en la computadora

import sys
import os
import json

#se agregan las carpetas de la pico w y la pico para importar sus codigos
carpeta = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(carpeta, "..", "pico_w"))
sys.path.insert(0, os.path.join(carpeta, "..", "pico"))
sys.path.insert(0, carpeta)

import lexico
import sintactico

#variable que guarda el programa de ejemplo
PROGRAMA = """
repetir 3 {
  led 1 encender
  buzzer 440 200
  esperar 300
  led 1 apagar
  esperar 300
}
si temperatura > 28 {
  led 2 encender
  buzzer 880 500
} sino {
  led 3 encender
}
esperar 2000
led 2 apagar
led 3 apagar
"""

#si se pasa un archivo se compila ese en lugar del ejemplo
if len(sys.argv) > 1:
    with open(sys.argv[1], encoding="utf-8") as f:
        PROGRAMA = f.read()

print("=== FASE 1: TOKENS ===")
tokens, errores = lexico.analizar(PROGRAMA)
for t in tokens:
    print("  %-8s %-12s línea %d" % (t[0], t[1], t[2]))
if errores:
    print("\nERRORES LÉXICOS:")
    for e in errores:
        print("  ", e)
    sys.exit(1)

#se simula el viaje por el cable: tokens -> json -> tokens
tokens = json.loads(json.dumps(tokens))

res = sintactico.compilar(tokens)
if not res["ok"]:
    print("\nERROR %s:" % res["fase"].upper())
    for e in res["errores"]:
        print("  ", e)
    sys.exit(1)

print("\n=== FASE 2: ÁRBOL SINTÁCTICO ===")
print(json.dumps(res["ast"], indent=2, ensure_ascii=False))

print("\n=== FASE 4: BYTECODE ===")
for linea in res["asm"]:
    print("  " + linea)
print("\nHex que se manda al Arduino:")
print("  C" + res["hex"])
