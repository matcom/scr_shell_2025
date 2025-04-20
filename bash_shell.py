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
            nueva_lista = []
            i = 1
            while i < len(historial):
                nueva_lista.append(historial[i])
                i = i + 1
            historial.clear()
            for cmd in nueva_lista:
                historial.append(cmd)

def ejecutar_ultimo_comando():
    if len(historial) == 0:
        print("Error: No hay comandos anteriores.")
        return
    ultimo = historial[-1]
    ejecutar_comando(ultimo)

def ejecutar_por_numero(numero):
    if len(historial) == 0:
        print("Error: No hay comandos en el historial.")
        return
    if numero < 1 or numero > len(historial):
        print("Error: Número fuera del rango del historial.")
        return
    comando = historial[numero - 1]
    ejecutar_comando(comando)

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
        destino = partes[1]
        try:
            os.chdir(destino)
        except:
            print("Directorio no encontrado")

def manejar_redireccion(entrada):
    # Si el comando es echo, se procesa manualmente
    if entrada.startswith("echo "):
        # Buscar la primera y última comilla dobles
        primero = entrada.find('"')
        ultimo = entrada.rfind('"')
        if primero != -1 and ultimo != -1 and primero != ultimo:
            contenido = entrada[primero+1:ultimo]
            # Verificar si existe la secuencia literal "\n"
            if "\\n" in contenido:
                partes = contenido.split("\\n", 1)
                print(partes[0])
                if partes[1]:
                    print(partes[1])
                else:
                    print()
                return
        # Si no se cumple la condición anterior, se procesa de forma normal
    # Procesamiento de redirecciones con >>, > o <
    if ">>" in entrada:
        partes = entrada.split(">>")
        comando = shlex.split(partes[0])
        archivo = partes[1].strip()
        with open(archivo, "a") as archivo_salida:
            subprocess.run(comando, stdout=archivo_salida)
    elif ">" in entrada:
        partes = entrada.split(">")
        comando = shlex.split(partes[0])
        archivo = partes[1].strip()
        with open(archivo, "w") as archivo_salida:
            subprocess.run(comando, stdout=archivo_salida)
    elif "<" in entrada:
        partes = entrada.split("<")
        comando = shlex.split(partes[0])
        archivo = partes[1].strip()
        with open(archivo, "r") as archivo_entrada:
            subprocess.run(comando, stdin=archivo_entrada)
    else:
        try:
            comando = shlex.split(entrada)
            subprocess.run(comando)
        except Exception as e:
            print("Comando desconocido")

def manejar_tuberias(entrada):
    partes = entrada.split("|")
    lista_de_comandos = []
    i = 0
    while i < len(partes):
        cmd = partes[i].strip()
        if cmd:
            comando = shlex.split(cmd)
            lista_de_comandos.append(comando)
        i = i + 1

    procesos = []
    anterior = None
    j = 0
    while j < len(lista_de_comandos):
        actual = lista_de_comandos[j]
        if anterior is None:
            proceso = subprocess.Popen(actual, stdout=subprocess.PIPE)
        else:
            proceso = subprocess.Popen(actual, stdin=anterior.stdout, stdout=subprocess.PIPE)
        procesos.append(proceso)
        anterior = proceso
        j = j + 1

    salida, _ = procesos[-1].communicate()
    print(salida.decode(), end="")

def ejecutar_en_background(entrada):
    limpio = entrada.replace("&", "").strip()
    try:
        comando = shlex.split(limpio)
        proceso = subprocess.Popen(comando)
        trabajos.append(proceso)
    except:
        print("Comando desconocido")

def mostrar_trabajos():
    i = 0
    while i < len(trabajos):
        proc = trabajos[i]
        pid = proc.pid
        print("[{}] PID {}".format(i + 1, pid))
        i = i + 1

def traer_a_foreground():
    if len(trabajos) > 0:
        proc = trabajos[0]
        trabajos.pop(0)
        proc.wait()

def mostrar_historial():
    i = 0
    while i < len(historial):
        print(str(i + 1) + " " + historial[i])
        i = i + 1

iniciar_shell()
