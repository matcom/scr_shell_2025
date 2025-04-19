import os
import subprocess
import readline
import shlex

historial_comandos = []
background_jobs = []

def cambiar_directorio(args):
    if len(args) < 2:
        print("\033[31mError: se requiere un directorio.\033[0m")
        return
    try:
        os.chdir(args[1])
    except FileNotFoundError:
        print("\033[31mError: directorio '" + args[1] + "' no encontrado.\033[0m")

def redirigir_salida(tokens):
    try:
        i = 0
        while i < len(tokens):
            if tokens[i] == ">" or tokens[i] == ">>":
                modo = tokens[i]
                nombre = tokens[i+1]
                archivo = open(nombre, "a" if modo == ">>" else "w")
                cmd = tokens[:i]
                subprocess.run(cmd, stdout=archivo, stderr=subprocess.DEVNULL, check=True)
                archivo.close()
                return
            i += 1
    except Exception:
        print("\033[31mError: Comando no reconocido.\033[0m")

def redirigir_entrada(tokens):
    try:
        i = 0
        while i < len(tokens):
            if tokens[i] == "<":
                nombre = tokens[i+1]
                archivo = open(nombre, "r")
                cmd = tokens[:i]
                subprocess.run(cmd, stdin=archivo, stderr=subprocess.DEVNULL, check=True)
                archivo.close()
                return
            i += 1
    except Exception:
        print("\033[31mError: Comando no reconocido.\033[0m")

def ejecutar_pipe(linea):
    partes = linea.split("|")
    procesos = []
    i = 0
    while i < len(partes):
        procesos.append(shlex.split(partes[i]))
        i += 1
    try:
        primero = subprocess.Popen(procesos[0], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        actual = primero
        j = 1
        while j < len(procesos):
            p = subprocess.Popen(procesos[j], stdin=actual.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            actual.stdout.close()
            actual = p
            j += 1
        salida, _ = actual.communicate()
        if salida:
            print(salida.decode(), end="")
    except Exception:
        print("\033[31mError: Comando no reconocido.\033[0m")

def mostrar_historial():
    total = len(historial_comandos)
    inicio = total - 50
    if inicio < 0:
        inicio = 0
    if total == 0:
        print("\033[31mNo hay comandos en el historial.\033[0m")
        return
    i = inicio
    while i < total:
        print(str(i+1) + ": " + historial_comandos[i])
        i += 1

def ejecutar_background(tokens):
    try:
        p = subprocess.Popen(tokens, stderr=subprocess.DEVNULL)
        background_jobs.append(p)
    except Exception:
        print("\033[31mError: Comando no reconocido.\033[0m")

def jobs():
    if len(background_jobs) == 0:
        print("\033[31mNo hay trabajos en segundo plano.\033[0m")
        return
    k = 0
    id = 1
    while k < len(background_jobs):
        print("[" + str(id) + "] PID: " + str(background_jobs[k].pid))
        k += 1
        id += 1

def fg(args):
    if len(args) < 2:
        print("\033[31mError: Se debe especificar un ID de trabajo.\033[0m")
        return
    try:
        idx = int(args[1]) - 1
    except ValueError:
        print("\033[31mError: ID de trabajo no válido.\033[0m")
        return
    if idx < 0 or idx >= len(background_jobs):
        print("\033[31mError: No hay trabajo con ID " + str(idx+1) + ".\033[0m")
        return
    bg = background_jobs[idx]
    bg.wait()
    background_jobs.remove(bg)

def comando_no_reconocido():
    print("\033[31mError: Comando no reconocido.\033[0m")

def leer_comando():
    linea = input("} ")
    while (linea.count('"') % 2 != 0) or (linea.count("'") % 2 != 0):
        extra = input("> ")
        linea += "\n" + extra
    return linea

def ejecutar_shell():
    readline.set_history_length(1000)
    while True:
        try:
            linea = leer_comando()
        except EOFError:
            print()
            break

        if linea == "":
            continue

        if linea == "!!":
            if len(historial_comandos) == 0:
                print("\033[31mError: No hay comandos en el historial.\033[0m")
                continue
            linea = historial_comandos[-1]
        elif linea.startswith("!"):
            n_str = linea[1:]
            if n_str.isdigit():
                n = int(n_str)
                total = len(historial_comandos)
                if n < 1 or n > total:
                    print("\033[31mError: solo hay " + str(total) + " comandos en el historial.\033[0m")
                    continue
                linea = historial_comandos[n-1]
            else:
                print("\033[31mError: comando histórico no soportado.\033[0m")
                continue

        if not linea.startswith(" "):
            ultimo = None
            if len(historial_comandos) > 0:
                ultimo = historial_comandos[-1]
            if linea != ultimo:
                historial_comandos.append(linea)
                if len(historial_comandos) > 50:
                    del historial_comandos[0]
                readline.add_history(linea)

        if linea == "exit":
            break
        if linea == "history":
            mostrar_historial()
            continue
        if linea == "jobs":
            jobs()
            continue
        if linea.endswith("&"):
            cmd = shlex.split(linea[:-1])
            ejecutar_background(cmd)
            continue
        if "|" in linea:
            ejecutar_pipe(linea)
            continue

        tokens = shlex.split(linea)
        if ">" in tokens or ">>" in tokens:
            redirigir_salida(tokens)
            continue
        if "<" in tokens:
            redirigir_entrada(tokens)
            continue

        if len(tokens) == 0:
            continue
        if tokens[0] == "cd":
            cambiar_directorio(tokens)
            continue
        if tokens[0] == "fg":
            fg(tokens)
            continue

        try:
            subprocess.run(tokens, check=True, stderr=subprocess.DEVNULL)
        except Exception:
            comando_no_reconocido()

if __name__ == "__main__":
    ejecutar_shell()
