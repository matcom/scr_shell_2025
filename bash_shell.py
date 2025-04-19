import os
import subprocess
import readline

historial_comandos = []
background_jobs = []

def mostrar_prompt():
    print("} ", end="", flush=True)

def cambiar_directorio(comando):
    if len(comando) < 2:
        print("\033[31m" + "Error: se requiere un directorio.\033[0m")
    else:
        try:
            os.chdir(comando[1])
        except FileNotFoundError:
            print(f"\033[31m" + f"Error: directorio '{comando[1]}' no encontrado.\033[0m")

def redirigir_salida(comando):
    try:
        if ">" in comando:
            index = comando.index(">")
            salida = comando[index + 1]
            subprocess.run(comando[:index], stdout=open(salida, 'w'))
        elif ">>" in comando:
            index = comando.index(">>")
            salida = comando[index + 1]
            subprocess.run(comando[:index], stdout=open(salida, 'a'))
    except Exception as e:
        print("\033[31m" + f"Error al redirigir salida: {e}\033[0m")

def redirigir_entrada(comando):
    try:
        if "<" in comando:
            index = comando.index("<")
            entrada = comando[index + 1]
            subprocess.run(comando[:index], stdin=open(entrada, 'r'))
    except Exception as e:
        print("\033[31m" + f"Error al redirigir entrada: {e}\033[0m")

def ejecutar_pipe(comando):
    try:
        comandos = [com.split() for com in comando]
        p = subprocess.Popen(comandos[0], stdout=subprocess.PIPE)

        for i in range(1, len(comandos) - 1):
            p2 = subprocess.Popen(comandos[i], stdin=p.stdout, stdout=subprocess.PIPE)
            p.stdout.close()
            p = p2

        p3 = subprocess.Popen(comandos[-1], stdin=p.stdout)
        p.stdout.close()
        p3.communicate()
    except Exception:
        print("\033[31m" + "Error al ejecutar pipe.\033[0m")

def ejecutar_historial():
    global historial_comandos
    entrada = input().strip()

    if entrada and (entrada != historial_comandos[-1] if historial_comandos else True) and not entrada.startswith(" "):
        historial_comandos.append(entrada)

    return historial_comandos

def reutilizar_comando(comando):
    global historial_comandos
    if comando.startswith("!"):
        if comando == "!!":
            if historial_comandos:
                return historial_comandos[-1]
            else:
                return "\033[31m" + "Error: No hay comandos en el historial.\033[0m"
        else:
            try:
                index = int(comando[1:])
                if index <= len(historial_comandos):
                    return historial_comandos[index-1]
                else:
                    return "\033[31m" + "Error: No hay comando en la posición solicitada del historial.\033[0m"
            except ValueError:
                return "\033[31m" + "Error: Se esperaba un número después de '!'.\033[0m"
    return comando

def mostrar_historial():
    global historial_comandos
    if historial_comandos:
        for i in range(len(historial_comandos)):
            print(f"{i + 1}: {historial_comandos[i]}")
    else:
        print("\033[31m" + "No hay comandos en el historial.\033[0m")

def ejecutar_background(comando):
    try:
        p = subprocess.Popen(comando)
        background_jobs.append(p)
        return p
    except Exception:
        print("\033[31m" + "Error al ejecutar en segundo plano.\033[0m")

def jobs():
    if background_jobs:
        for i in range(len(background_jobs)):
            print(f"[{i + 1}] PID: {background_jobs[i].pid}")
    else:
        print("\033[31m" + "No hay trabajos en segundo plano.\033[0m")

def fg(job_id):
    try:
        job_id = int(job_id) - 1
        if 0 <= job_id < len(background_jobs):
            job = background_jobs[job_id]
            job.wait()
            background_jobs.remove(job)
        else:
            print("\033[31m" + f"Error: No hay trabajo con ID {job_id + 1}.\033[0m")
    except ValueError:
        print("\033[31m" + "Error: ID de trabajo no válido.\033[0m")

def comando_no_reconocido():
    return "\033[31m" + "Error: Comando no reconocido.\033[0m"

def ejecutar_shell():
    while True:
        mostrar_prompt()
        entrada = input().strip()

        if entrada == 'exit':
            break

        if entrada == 'history':
            mostrar_historial()
            continue

        if entrada == 'jobs':
            jobs()  
            continue

        if entrada.startswith('!'):
            entrada = reutilizar_comando(entrada)
            if entrada.startswith("\033[31m"):
                print(entrada)  
                continue

        historial_comandos.append(entrada)

        if entrada.endswith('&'):
            entrada = entrada[:-1].strip()
            comando = entrada.split(' ')
            ejecutar_background(comando)
            continue

        if '|' in entrada:
            comando = entrada.split('|')
            ejecutar_pipe(comando)
        elif '>' in entrada:
            comando = entrada.split(' ')
            redirigir_salida(comando)
        elif '<' in entrada:
            comando = entrada.split(' ')
            redirigir_entrada(comando)
        elif 'cd' in entrada:
            comando = entrada.split(' ')
            cambiar_directorio(comando)
        elif entrada.startswith("fg"):
            job_id = entrada.split(" ")[1] if len(entrada.split(" ")) > 1 else None
            if job_id:
                fg(job_id)
            else:
                print("\033[31m" + "Error: Se debe especificar un ID de trabajo.\033[0m")
        else:
            comando = entrada.split(' ')
            try:
                subprocess.run(comando, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(comando_no_reconocido())

if __name__ == "__main__":
    readline.set_history_length(1000)
    ejecutar_shell()
