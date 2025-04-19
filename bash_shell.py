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
                subprocess.run(cmd, stdout=archivo)
                archivo.close()
                return
            i += 1
    except Exception as e:
        print("\033[31mError al redirigir salida: " + str(e) + "\033[0m")

def redirigir_entrada(tokens):
    try:
        i = 0
        while i < len(tokens):
            if tokens[i] == "<":
                nombre = tokens[i+1]
                archivo = open(nombre, "r")
                cmd = tokens[:i]
                subprocess.run(cmd, stdin=archivo)
                archivo.close()
                return
            i += 1
    except Exception as e:
        print("\033[31mError al redirigir entrada: " + str(e) + "\033[0m")

def ejecutar_pipe(linea):
    partes_str = linea.split("|")
    procesos = []
    i = 0
    while i < len(partes_str):
        procesos.append(shlex.split(partes_str[i]))
        i += 1
    try:
        primero = subprocess.Popen(procesos[0], stdout=subprocess.PIPE)
        actual = primero
        j = 1
        while j < len(procesos):
            p = subprocess.Popen(procesos[j], stdin=actual.stdout, stdout=subprocess.PIPE)
            actual.stdout.close()
            actual = p
            j += 1
        salida, _ = actual.communicate()
        if salida:
            print(salida.decode(), end = "")
    except Exception:
        print("\033[31mError al ejecutar pipe.\033[0m")

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
        num = i + 1
        print(str(num) + ": " + historial_comandos[i])
        i += 1

def ejecutar_background(tokens):
    try:
        p = subprocess.Popen(tokens)
        background_jobs.append(p)
    except Exception:
        print("\033[31mError al ejecutar en segundo plano.\033[0m")

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
        print("\033[31mError: No hay trabajo con ID " + str(idx + 1) + ".\033[0m")
        return
    bg = background_jobs[idx]
    bg.wait()
    background_jobs.remove(bg)

def comando_no_reconocido():
    print("\033[31mError: Comando no reconocido.\033[0m")

def ejecutar_shell():
    readline.set_history_length(1000)
    while True:
        try:
            linea = input("} ")
        except EOFError:
            print()
            break
        if linea == "":
            continue
        buffer = linea
        while buffer.count('"') % 2 != 0 or buffer.count("'") % 2 != 0:
            try:
                cont = input("> ")
            except EOFError:
                print("\033[31mError: comillas sin cerrar.\033[0m")
                buffer = ""
                break
            buffer += "\n" + cont
        if not buffer:
            continue
        linea = buffer
        if not linea.startswith(" "):
            ultimo = historial_comandos[-1] if historial_comandos else None
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
        if not tokens:
            continue
        if tokens[0] == "cd":
            cambiar_directorio(tokens)
            continue
        if tokens[0] == "fg":
            fg(tokens)
            continue
        try:
            subprocess.run(tokens)
        except (FileNotFoundError, subprocess.CalledProcessError):
            comando_no_reconocido()

if __name__ == "__main__":
    ejecutar_shell()
