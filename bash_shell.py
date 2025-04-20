import os
import shlex
import subprocess
import sys

historial = []
trabajos = []
MAX_HISTORIAL = 50

def iniciar_shell():
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
    if entrada == "!!":
        ejecutar_ultimo_comando()
        return
    if entrada.startswith("!") and entrada[1:].isdigit():
        ejecutar_por_numero(int(entrada[1:]))
        return
    if entrada.startswith("!"):
        print("Error: Comando no válido. Usa !número")
        return
    if entrada.startswith(" "):
        return
    agregar_a_historial(entrada)
    ejecutar_comando(entrada)

def agregar_a_historial(comando):
    if len(historial) == 0 or historial[-1] != comando:
        historial.append(comando)
        if len(historial) > MAX_HISTORIAL:
            nueva = historial[1:]
            historial.clear()
            historial.extend(nueva)

def ejecutar_ultimo_comando():
    if not historial:
        print("Error: No hay comandos anteriores.")
        return
    ejecutar_comando(historial[-1])

def ejecutar_por_numero(n):
    if not historial:
        print("Error: No hay comandos en el historial.")
        return
    if n < 1 or n > len(historial):
        print("Error: Número fuera del rango del historial.")
        return
    ejecutar_comando(historial[n-1])

def ejecutar_comando(entrada):
    if entrada == "exit":
        sys.exit(0)
    if entrada.startswith("cd "):
        cambiar_directorio(entrada)
    elif " | " in entrada:
        manejar_tuberias(entrada)
    elif "&" in entrada:
        ejecutar_en_background(entrada)
    elif entrada == "jobs":
        mostrar_trabajos()
    elif entrada == "fg":
        traer_a_foreground()
    elif entrada == "history":
        mostrar_historial()
    else:
        manejar_redireccion(entrada)

def cambiar_directorio(entrada):
    partes = shlex.split(entrada)
    if len(partes) > 1:
        try:
            os.chdir(partes[1])
        except:
            print("Directorio no encontrado")

def manejar_redireccion(entrada):
    if entrada.startswith("echo "):
        inicio = entrada.find('"')
        fin = entrada.find('"', inicio+1)
        if inicio != -1 and fin != -1:
            contenido = entrada[inicio+1:fin]
            if '\n' in contenido:
                antes, despues = contenido.split('\n', 1)
                print(antes)
                print(despues if despues else "")
                return
            if '\\n' in contenido:
                antes, despues = contenido.split('\\n', 1)
                print(antes)
                print(despues if despues else "")
                return
    if ">>" in entrada:
        cmd, archivo = entrada.split(">>", 1)
        args = shlex.split(cmd)
        with open(archivo.strip(), "a") as f:
            subprocess.run(args, stdout=f)
    elif ">" in entrada:
        cmd, archivo = entrada.split(">", 1)
        args = shlex.split(cmd)
        with open(archivo.strip(), "w") as f:
            subprocess.run(args, stdout=f)
    elif "<" in entrada:
        cmd, archivo = entrada.split("<", 1)
        args = shlex.split(cmd)
        with open(archivo.strip(), "r") as f:
            subprocess.run(args, stdin=f)
    else:
        try:
            args = shlex.split(entrada)
            subprocess.run(args)
        except:
            print("Comando desconocido")

def manejar_tuberias(entrada):
    partes = [p.strip() for p in entrada.split("|")]
    procesos = []
    prev = None
    for p in partes:
        args = shlex.split(p)
        if prev is None:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE)
        else:
            proc = subprocess.Popen(args, stdin=prev.stdout, stdout=subprocess.PIPE)
        procesos.append(proc)
        prev = proc
    salida, _ = procesos[-1].communicate()
    print(salida.decode(), end="")

def ejecutar_en_background(entrada):
    limpio = entrada.replace("&", "").strip()
    try:
        args = shlex.split(limpio)
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

if __name__ == "__main__":
    iniciar_shell()
