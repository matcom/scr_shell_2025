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
                agregar_a_historial(cmd)
                ejecutar_comando(cmd)
                return
        print("Error: Comando no encontrado en historial.")
        return
    ejec = entrada.lstrip() if entrada.startswith(" ") else entrada
    if not entrada.startswith(" "):
        agregar_a_historial(entrada)
    ejecutar_comando(ejec)

def agregar_a_historial(comando):
    if not historial or historial[-1] != comando:
        historial.append(comando)
        if len(historial) > MAX_HISTORIAL:
            del historial[0]

def ejecutar_ultimo_comando():
    if not historial:
        print("Error: No hay comandos anteriores.")
        return
    cmd = historial[-1]
    agregar_a_historial(cmd)
    ejecutar_comando(cmd)

def ejecutar_por_numero(n):
    if not historial:
        print("Error: No hay comandos en el historial.")
        return
    if not (1 <= n <= len(historial)):
        print("Error: Número fuera del rango del historial.")
        return
    cmd = historial[n-1]
    agregar_a_historial(cmd)
    ejecutar_comando(cmd)

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
                print(a)
                print(b)
                return
            if "\n" in contenido:
                a, b = contenido.split("\n", 1)
                print(a)
                print(b)
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
    partes = [p.strip() for p in entrada.split("|")]
    salida = None
    for parte in partes:
        args = normalize(split_con_comillas(parte))
        cmd = args[0]
        if cmd == "history":
            buf = ""
            for i, h in enumerate(historial, 1):
                buf += f"{i} {h}\n"
            salida = buf
        elif cmd == "jobs":
            buf = ""
            for i, p in enumerate(trabajos, 1):
                buf += f"[{i}] PID {p.pid}\n"
            salida = buf
        else:
            if salida is not None:
                proc = subprocess.run(args, input=salida, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
            else:
                proc = subprocess.run(args, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
            salida = proc.stdout
    if salida:
        sys.stdout.write(salida)

def ejecutar_en_background(entrada):
    limpio = entrada[:-1].strip()
    tokens = normalize(split_con_comillas(limpio))
    if not tokens:
        return
    try:
        p = subprocess.Popen(tokens)
        trabajos.append(p)
    except:
        print("Comando desconocido")

def mostrar_trabajos():
    for i, p in enumerate(trabajos, 1):
        print(f"[{i}] PID {p.pid}")

def traer_a_foreground():
    if trabajos:
        p = trabajos.pop(0)
        p.wait()

def mostrar_historial():
    for i, cmd in enumerate(historial, 1):
        print(f"{i} {cmd}")

def split_con_comillas(comando):
    tokens = []
    actual = ""
    dobles = False
    simples = False
    for c in comando:
        if c == '"' and not simples:
            dobles = not dobles
            actual += c
        elif c == "'" and not dobles:
            simples = not simples
            actual += c
        elif c.isspace() and not dobles and not simples:
            if actual:
                tokens.append(actual)
                actual = ""
        else:
            actual += c
    if actual:
        tokens.append(actual)
    return tokens

def normalize(tokens):
    res = []
    for t in tokens:
        if len(t) >= 2 and ((t[0] == '"' == t[-1]) or (t[0] == "'" == t[-1])):
            res.append(t[1:-1])
        else:
            res.append(t)
    return res

if __name__ == "__main__":
    iniciar_shell()
