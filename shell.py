import os 
import re
import sys
import subprocess
from collections import OrderedDict

ultimo_directorio = None
background_jobs = OrderedDict()
job_id_counter = 1

def espacio_tokens(comando):
    comando = re.sub(r"\s*(>>|[<>|])\s*", r" \1 ", comando)
    comando = " ".join(comando.split())
    return comando.strip()

def split_con_comillas(comando):
    tokens = []
    token_actual = ""
    dentro_comillas_dobles = False
    dentro_comillas_simples = False
    
    for char in comando:
        if char == '"' and not dentro_comillas_simples:
            dentro_comillas_dobles = not dentro_comillas_dobles
        elif char == "'" and not dentro_comillas_dobles:
            dentro_comillas_simples = not dentro_comillas_simples
        elif char == " " and not (dentro_comillas_dobles or dentro_comillas_simples):
            if token_actual:
                tokens.append(token_actual)
                token_actual = ""
        else:
            token_actual += char
            
    if token_actual:
        tokens.append(token_actual)
    
    return tokens

def main():
    if sys.stdin.isatty():
        while True:
            try:
                comando = input("$ ")
                comando = espacio_tokens(comando)
                if comando == "exit":
                    break
                
                tokens = split_con_comillas(comando)  
                
                if tokens:
                    ejecutar_comando(tokens)
            
            except KeyboardInterrupt:
                print("\nSaliendo del shell...")
                break
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
    else:
        for line in sys.stdin:
            comando = line.strip()
            if comando:
                comando = espacio_tokens(comando)
                tokens = split_con_comillas(comando)
                
                if tokens:
                    ejecutar_comando(tokens)
            
def ejecutar_cd(partes):
    global ultimo_directorio
    try:
        directorio_actual = os.getcwd()
        if len(partes) == 1 or partes[1] == "~":
            os.chdir(os.path.expanduser("~"))
        elif partes[1] == "..":
            os.chdir("..")
        elif partes[1] == "-":
            if ultimo_directorio:
                os.chdir(ultimo_directorio)
                print(f"Volviendo al último directorio: {ultimo_directorio}.")
            else:
                print("No hay un directorio anterior al que regresar.")
        elif partes[1].startswith("~/"):
            ruta = os.path.expanduser(partes[1])
            os.chdir(ruta)
        else:
            os.chdir(partes[1])
        ultimo_directorio = directorio_actual
    except FileNotFoundError:
        print(f"Error: No existe el directorio '{partes[1]}'.")
    except Exception as e:
        print(f"Error inesperado: {e}")
            

def manejar_pipes(comando, background=False):
    """
    Maneja comandos con pipes (|) y redirecciones limitadas:
    - < solo permitido en el primer comando.
    - >/>> solo permitidos en el último comando.
    """
    global background_jobs, job_id_counter
    
    partes_del_comando = comando.split("|")
    comandos = []
    for cmd in partes_del_comando:
        cmd_limpio = cmd.strip()
        comandos.append(cmd_limpio)

    procesos = []
    stdin_previo = None
        
    for i in range(len(comandos)):
        partes = comandos[i].split()
        comando_base, redireccion_salida, redireccion_entrada, append = parsear_redirecciones(partes)
        
        if i > 0 and redireccion_entrada:
            print("Error: La redirección de entrada (<) solo se permite en el primer comando")
            return
        if i < len(comandos) - 1 and redireccion_salida:
            print("Error: La redirección de salida (>, >>) solo se permite en el último comando")
            return
        
        stdin_actual = stdin_previo
        if redireccion_entrada and i == 0:
            try:
                stdin_actual = open(redireccion_entrada, 'r')
            except IOError as e:
                print(f"Error al abrir {redireccion_entrada}: {e}")
                return
            
        stdout_actual = subprocess.PIPE if i < len(comandos)-1 else None
        if redireccion_salida and i == len(comandos)-1:
            try:
                stdout_actual = open(redireccion_salida, 'a' if append else 'w')
            except IOError as e:
                print(f"Error al abrir {redireccion_salida}: {e}")
                if isinstance(stdin_actual, io.TextIOWrapper):
                    stdin_actual.close()
                return
            
        proceso = subprocess.Popen(
            comando_base,
            stdin=stdin_actual,
            stdout=stdout_actual,
            stderr=subprocess.PIPE,
            text=True
        )
        
        procesos.append(proceso)
        stdin_previo = proceso.stdout if i < len(comandos)-1 else None
        
        if i > 0:
            procesos[i-1].stdout.close()
    
    if background:
        job_id = job_id_counter
        job_id_counter += 1
        background_jobs[job_id] = {
            "process": procesos,
            "command": comando,
            "ya_mostrado": False
        }
        print(f"[{job_id}] {procesos[-1].pid}")
        return 
        
    salida, error = procesos[-1].communicate()
    
    if procesos[-1].returncode == 0:
        if procesos[-1].stdout == subprocess.PIPE:  
            print(salida or "", end="")
    else:
        print(error or "", end="")
        
def parsear_redirecciones(tokens):
    redireccion_salida = None
    redireccion_entrada = None
    append = False 
    comando_base = tokens.copy()
    
    i = 0
    while i < len(comando_base):
        if comando_base[i] == ">":
            if i+1 < len(comando_base):
                redireccion_salida = comando_base[i+1]
                comando_base = comando_base[:i]
                break
        elif comando_base[i] == ">>":
            if i+1 < len(comando_base):
                redireccion_salida = comando_base[i+1]
                append = True
                comando_base = comando_base[:i]
                break
        elif comando_base[i] == '<':
            if i+1 < len(comando_base):
                redireccion_entrada = comando_base[i+1]
                comando_base = comando_base[:i]
                break
        i+=1
    
    return comando_base, redireccion_salida, redireccion_entrada, append
        
def ejecutar_comando_redirecciones(comando_base, redireccion_salida, redireccion_entrada, append, background=False):
    global background_jobs, job_id_counter
    
    stdin_file = None
    if redireccion_entrada:
        try:
            stdin_file = open(redireccion_entrada, "r")
        except IOError as e:
            print(f"Error al abrir {redireccion_entrada}: {e}")
            return
            
    stdout_file = None
    if redireccion_salida:
        try:
            mode = "a" if append else "w"
            stdout_file = open(redireccion_salida, mode)
        except IOError as e:
            print(f"Error al abrir {redireccion_salida}: {e}")
            if stdin_file:
                stdin_file.close()
            return    
    
    try:
        proceso = subprocess.Popen(
            comando_base,
            stdin=stdin_file if redireccion_entrada else None,
            stdout=stdout_file if redireccion_salida else subprocess.PIPE,  
            stderr=subprocess.PIPE,  
            text=True  
        )
        
        if background:
            job_id = job_id_counter
            background_jobs[job_id] = {
                "pid": proceso.pid,
                "command": " ".join(comando_base),
                "process": [proceso],
                "ya_mostrado": False
            }
            print(f"[{job_id}] {proceso.pid}")
            job_id_counter += 1
        else:
            salida, error = proceso.communicate()
            
            if not redireccion_salida:
                if proceso.returncode == 0:
                    print(salida or "", end="")
                else:
                    print(error or "", end="")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if stdin_file:
            stdin_file.close()
        if stdout_file:
            stdout_file.close()
            
def listar_jobs(mostrar_detalles=False):
    global background_jobs
    
    limpiar_jobs_terminados()
    
    if not background_jobs:
        print("No hay procesos en el background.")
        return
    
    max_job_id = 0
    for job_id in background_jobs.keys():
        if job_id > max_job_id:
            max_job_id = job_id
    
    for job_id, job_info in background_jobs.items():
        job_en_ejecucion = False
        for proceso in job_info["process"]:
            if proceso.poll() is None:
                job_en_ejecucion = True
                break
            
        estado = "Running" if job_en_ejecucion else "Done"
        simbolo = "+" if job_id == max_job_id else "-"
        
        comando = job_info["command"]
        if not job_en_ejecucion:
            comando = comando.rstrip(" &")
            
        if mostrar_detalles: 
            if len(job_info["process"]) > 1:
                partes_comando = job_info["command"].split('|')
                for i, proceso in enumerate(job_info["process"]):
                    if i == 0:
                        print(f"[{job_id}]{simbolo} {proceso.pid:>6} {estado:<7} {partes_comando[i].strip()}")
                    else:
                        es_ultimo = i == len(job_info["process"])-1
                        terminator = " &" if (job_en_ejecucion and es_ultimo) else ""
                        print(f"    {proceso.pid:>6}       | {partes_comando[i].strip()}{terminator}")
            else:
                terminator = " &" if job_en_ejecucion else ""
                print(f"[{job_id}]{simbolo} {job_info['process'][0].pid:>6} {estado:<7} {job_info['command']}{terminator}")
        else:
            terminator = " &" if job_en_ejecucion else ""
            print(f"[{job_id}]{simbolo} {estado:<7} {job_info['command']}{terminator}")
            
def limpiar_jobs_terminados():
    global background_jobs, job_id_counter
    jobs_a_eliminar = []
    
    for job_id, job_info in list(background_jobs.items()): 
        todos_terminados = True 
        
        for proceso in job_info["process"]:
            if proceso.poll() is None:
                todos_terminados = False
                break 
            
        if todos_terminados:
            if job_info.get("ya_mostrado", False):
                jobs_a_eliminar.append(job_id)
            else:
                job_info["ya_mostrado"] = True
            
    for job_id in jobs_a_eliminar:
        del background_jobs[job_id]
        
    if not background_jobs:
        job_id_counter = 1
        
def ejecutar_fg(job_arg):
    global background_jobs, job_id_counter
    
    if not background_jobs:
        print("No hay procesos en el background.")
        return
    
    if job_arg is None:
        job_id = max(background_jobs.keys())
    else:
        job_str = job_arg.replace("%", "")
        try:
            job_id = int(job_str)
            if job_id not in background_jobs:
                print(f"fg: %{job_id}: no existe ese job")
                return
        except ValueError:
            print("fg: el job_id debe ser un número")
            return
        
    job_info = background_jobs[job_id]
    
    max_job_id = max(background_jobs.keys())
    simbolo = "+" if job_id == max_job_id else "-"
    comando = job_info["command"].rstrip(" &")
    print(f"{comando}")
    
    del background_jobs[job_id]
    
    if not background_jobs:
        job_id_counter = 1
    
    try:
        for proceso in job_info["process"]:
            proceso.wait()
        del background_jobs[job_id]
    except KeyboardInterrupt:
        print() 
            
def ejecutar_comando(tokens):
    global background_jobs, job_id_counter
    
    if not tokens:
        return
    
    if tokens[0] == "jobs":
        if len(tokens) > 1 and tokens[1] == "-l":
            listar_jobs(mostrar_detalles=True)
        else:
            listar_jobs()
        return
    
    if tokens[0] == "fg":
        if len(tokens) > 1:
            ejecutar_fg(tokens[1])
        else:
            ejecutar_fg(None)
        return
    
    if tokens[0] == "cd":
        ejecutar_cd(tokens)
        return
    
    is_background = tokens[-1] == "&"
    if is_background:
        tokens = tokens[:-1] 
    
    comando_str = " ".join(tokens)  
    if "|" in comando_str:
        manejar_pipes(comando_str, is_background)
        return
        
    comando_base, redireccion_salida, redireccion_entrada, append = parsear_redirecciones(tokens)
    ejecutar_comando_redirecciones(comando_base, redireccion_salida, redireccion_entrada, append, is_background)


if __name__ == "__main__":
    main()