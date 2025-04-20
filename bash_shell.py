#!/usr/bin/env python3
import os
import subprocess
import sys

historial = []
trabajos = []
MAX_HISTORIAL = 50

def iniciar_shell():
    if not sys.stdin.isatty():
        for linea in sys.stdin.read().splitlines():
            if linea.strip():
                procesar_entrada(linea)
        return
    while True:
        try:
            entrada = input("} ")
            if entrada.strip() == "":
                continue
            procesar_entrada(entrada)
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
            continue

def procesar_entrada(entrada):
    if entrada == "exit":
        sys.exit(0)
    if entrada == "!!":
        ejecutar_ultimo_comando()
        return
    if entrada.startswith("!") and entrada[1:].isdigit():
        ejecutar_por_numero(int(entrada[1:]))
        return
    if entrada.startswith("!"):
        prefijo = entrada[1:]
        for cmd in reversed(historial):
            if cmd.startswith(prefijo):
                ejecutar_comando(cmd)
                return
        print("Error: Comando no encontrado en historial.")
        return
    ejecucion = entrada.lstrip() if entrada.startswith(" ") else entrada
    if not entrada.startswith(" "):
        agregar_a_historial(entrada)
    ejecutar_comando(ejecucion)

def agregar_a_historial(comando):
    if not historial or historial[-1] != comando:
        historial.append(comando)
        if len(historial) > MAX_HISTORIAL:
            del historial[0]

def ejecutar_ultimo_comando():
    if not historial:
        print("Error: No hay comandos anteriores.")
        return
    ejecutar_comando(historial[-1])

def ejecutar_por_numero(n):
    if not historial:
        print("Error: No hay comandos en el historial.")
        return
    if not (1 <= n <= len(historial)):
        print("Error: Número fuera del rango del historial.")
        return
    ejecutar_comando(historial[n-1])

def ejecutar_comando(entrada):
    if entrada.startswith("cd "):
        cambiar_directorio(entrada)
    elif entrada.endswith("&"):
        ejecutar_en_background(entrada)
    elif "|" in entrada:
        manejar_tuberias(entrada)
    elif entrada == "jobs":
        mostrar_trabajos()
    elif entrada == "fg":
        traer_a_foreground()
    elif entrada == "history":
        mostrar_historial()
    else:
        manejar_redireccion(entrada)

def cambiar_directorio(entrada):
    tokens = split_con_comillas(entrada)
    if len(tokens) > 1:
        try:
            os.chdir(tokens[1])
        except:
            print("Directorio no encontrado")

def manejar_redireccion(entrada):
    if entrada.startswith("echo "):
        i = entrada.find('"')
        f = entrada.rfind('"')
        if 0 <= i < f:
            contenido = entrada[i+1:f]
            if "\\n" in contenido:
                a, b = contenido.split("\\n", 1)
                print(a); print(b)
                return
            if "\n" in contenido:
                a, b = contenido.split("\n", 1)
                print(a); print(b)
                return
    if ">>" in entrada:
        cmd, archivo = entrada.split(">>", 1)
        args = normalize(split_con_comillas(cmd.strip()))
        with open(archivo.strip(), "a") as f:
            subprocess.run(args, stdout=f)
    elif ">" in entrada:
        cmd, archivo = entrada.split(">", 1)
        args = normalize(split_con_comillas(cmd.strip()))
        with open(archivo.strip(), "w") as f:
            subprocess.run(args, stdout=f)
    elif "<" in entrada:
        cmd, archivo = entrada.split("<", 1)
        args = normalize(split_con_comillas(cmd.strip()))
        with open(archivo.strip(), "r") as f:
            subprocess.run(args, stdin=f)
    else:
        args = normalize(split_con_comillas(entrada))
        try:
            subprocess.run(args)
        except:
            print("Comando desconocido")

def manejar_tuberias(entrada):
    procesos = []
    prev = None
    for parte in entrada.split("|"):
        args = normalize(split_con_comillas(parte.strip()))
        if prev is None:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        else:
            proc = subprocess.Popen(args, stdin=prev.stdout, stdout=subprocess.PIPE)
        procesos.append(proc)
        prev = proc
    salida, _ = procesos[-1].communicate()
    sys.stdout.write(salida.decode() if isinstance(salida, bytes) else str(salida))

def ejecutar_en_background(entrada):
    comando = entrada[:-1].strip()
    if "|" in comando:
        prev = None
        primero = None
        for parte in comando.split("|"):
            args = normalize(split_con_comillas(parte.strip()))
            if prev is None:
                primero = subprocess.Popen(args, stdout=subprocess.PIPE)
                prev = primero
            else:
                prev = subprocess.Popen(args, stdin=prev.stdout, stdout=subprocess.PIPE)
        if primero:
            trabajos.append(primero)
    else:
        args = normalize(split_con_comillas(comando))
        try:
            p = subprocess.Popen(args)
            trabajos.append(p)
        except:
            print("Comando desconocido")

def mostrar_trabajos():
    i = 1
    for p in trabajos:
        print(f"[{i}] PID {p.pid}")
        i += 1

def traer_a_foreground():
    if trabajos:
        p = trabajos.pop(0)
        p.wait()

def mostrar_historial():
    i = 1
    for cmd in historial:
        print(f"{i} {cmd}")
        i += 1

def split_con_comillas(comando):
    tokens, actual = [], ""
    dobles = simples = False
    for c in comando:
        if c == '"' and not simples:
            dobles = not dobles; actual += c
        elif c == "'" and not dobles:
            simples = not simples; actual += c
        elif c.isspace() and not dobles and not simples:
            if actual:
                tokens.append(actual); actual = ""
        else:
            actual += c
    if actual:
        tokens.append(actual)
    return tokens

def normalize(tokens):
    resultado = []
    for t in tokens:
        if len(t) >= 2 and ((t[0] == '"' == t[-1]) or (t[0] == "'" == t[-1])):
            resultado.append(t[1:-1])
        else:
            resultado.append(t)
    return resultado

if __name__ == "__main__":
    iniciar_shell()
