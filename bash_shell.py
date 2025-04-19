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
    if ">>" in tokens or ">" in tokens:
        op = ">>" if ">>" in tokens else ">"
        idx = tokens.index(op)
        cmd = tokens[:idx]
        nombre = tokens[idx+1]
        with open(nombre, "a" if op==">>" else "w") as f:
            subprocess.Popen(cmd, stdout=f).wait()
        return True
    return False

def redirigir_entrada(tokens):
    if "<" in tokens:
        idx = tokens.index("<")
        cmd = tokens[:idx]
        nombre = tokens[idx+1]
        with open(nombre, "r") as f:
            subprocess.Popen(cmd, stdin=f).wait()
        return True
    return False

def ejecutar_pipe(linea):
    partes_str = linea.split("|")
    procesos = [shlex.split(p) for p in partes_str]
    try:
        primero = subprocess.Popen(procesos[0], stdout=subprocess.PIPE)
        actual = primero
        for proc in procesos[1:]:
            p = subprocess.Popen(proc, stdin=actual.stdout, stdout=subprocess.PIPE)
            actual.stdout.close()
            actual = p
        salida, _ = actual.communicate()
        if salida:
            print(salida.decode(), end="")
    except Exception:
        print("\033[31mError al ejecutar pipe.\033[0m")

def mostrar_historial():
    total = len(historial_comandos)
    inicio = max(0, total - 50)
    if total == 0:
        print("\033[31mNo hay comandos en el historial.\033[0m")
        return
    for i in range(inicio, total):
        print(f"{i+1}: {historial_comandos[i]}")

def ejecutar_background(tokens):
    try:
        p = subprocess.Popen(tokens)
        background_jobs.append(p)
    except Exception:
        print("\033[31mError al ejecutar en segundo plano.\033[0m")

def jobs():
    if not background_jobs:
        print("\033[31mNo hay trabajos en segundo plano.\033[0m")
        return
    for idx, p in enumerate(background_jobs, start=1):
        print(f"[{idx}] PID: {p.pid}")

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
        print(f"\033[31mError: No hay trabajo con ID {idx+1}.\033[0m")
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
        if not linea:
            continue
        if linea.count('"') % 2 != 0 or linea.count("'") % 2 != 0:
            buffer = [linea]
            while True:
                try:
                    cont = input("} ")
                except EOFError:
                    break
                buffer.append(cont)
                linea = "\n".join(buffer)
                if linea.count('"') % 2 == 0 and linea.count("'") % 2 == 0:
                    break
        if linea == "!!":
            if not historial_comandos:
                print("\033[31mError: No hay comandos en el historial.\033[0m")
                continue
            linea = historial_comandos[-1]
        elif linea.startswith("!"):
            n_str = linea[1:]
            if n_str.isdigit():
                n = int(n_str)
                total = len(historial_comandos)
                if n < 1 or n > total:
                    print(f"\033[31mError: solo hay {total} comandos en el historial.\033[0m")
                    continue
                linea = historial_comandos[n-1]
            else:
                print("\033[31mError: comando histórico no soportado.\033[0m")
                continue
        if not linea.startswith(" "):
            if not historial_comandos or linea != historial_comandos[-1]:
                historial_comandos.append(linea)
                if len(historial_comandos) > 50:
                    historial_comandos.pop(0)
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
            ejecutar_background(shlex.split(linea[:-1]))
            continue
        if "|" in linea:
            ejecutar_pipe(linea)
            continue
        tokens = shlex.split(linea)
        if redirigir_salida(tokens):
            continue
        if redirigir_entrada(tokens):
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
