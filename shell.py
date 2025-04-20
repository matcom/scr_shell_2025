import os
import shlex
import subprocess
import io

HISTORY_FILE = "command_history.txt"

def ejecutar_comando(comando, background=False, stdin=None, stdout=None):
    try:
        proceso = subprocess.Popen(comando, stdin=stdin, stdout=stdout)
        if not background:
            proceso.communicate()
    except FileNotFoundError:
        print(f"Comando no encontrado: {comando[0]}")

def guardar_en_historial(comando):
    with open(HISTORY_FILE, "a") as historial:
        historial.write(comando + "\n")

def cargar_historial():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as historial:
            return historial.readlines()
    return []

def mostrar_historial():
    historial = cargar_historial()
    for idx, comando in enumerate(historial, 1):
        print(f"{idx}: {comando.strip()}")

def ejecutar_desde_historial(numero):
    historial = cargar_historial()
    try:
        comando = historial[int(numero) - 1].strip()
        print(f"Ejecutando: {comando}")
        procesar_entrada(comando)
    except (IndexError, ValueError):
        print("Número de historial inválido.")

def procesar_entrada(entrada):
    if not entrada.strip():
        return

    guardar_en_historial(entrada)

    comandos = [shlex.split(cmd) for cmd in entrada.split("|")]
    num_comandos = len(comandos)

    procesos = []
    stdin_actual = None

    for i, cmd in enumerate(comandos):
        if ">" in cmd:
            idx = cmd.index(">")
            archivo_salida = cmd[idx + 1]
            stdout_actual = open(archivo_salida, "w")
            cmd = cmd[:idx]
        elif "<" in cmd:
            idx = cmd.index("<")
            archivo_entrada = cmd[idx + 1]
            stdin_actual = open(archivo_entrada, "r")
            cmd = cmd[:idx]
            stdout_actual = subprocess.PIPE if i < num_comandos - 1 else None
        else:
            stdout_actual = subprocess.PIPE if i < num_comandos - 1 else None

        background = False
        if cmd and cmd[-1] == "&":
            background = True
            cmd = cmd[:-1]

        if cmd:
            if cmd[0] == "cd":
                if len(cmd) > 1:
                    try:
                        os.chdir(cmd[1])
                    except FileNotFoundError:
                        print(f"Directorio no encontrado: {cmd[1]}")
                else:
                    print("Uso: cd <directorio>")
            elif cmd[0] == "history":
                mostrar_historial()
            elif cmd[0].startswith("!"):
                ejecutar_desde_historial(cmd[0][1:])
            else:
                proceso = subprocess.Popen(cmd, stdin=stdin_actual, stdout=stdout_actual)
                procesos.append(proceso)
                if stdin_actual:
                    stdin_actual.close()
                stdin_actual = proceso.stdout if i < num_comandos - 1 else None

    for p in procesos:
        p.wait()

def shell():
    while True:
        try:
            entrada = input("Shell> ")
            if entrada.strip() == "exit":
                break
            procesar_entrada(entrada)
        except KeyboardInterrupt:
            print("\nUsa 'exit' para salir.")
        except EOFError:
            break

if __name__ == "__main__":
    shell()
