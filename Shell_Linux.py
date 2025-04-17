#!/usr/bin/env python3
import os
import re
import subprocess

historial = {}
trabajos = []
contador_trabajos = 1

def reindexar_historial():
    global historial
    comandos = list(historial.values())
    historial = {i+1: cmd for i, cmd in enumerate(comandos)}

def agregar_comando_al_historial(comando):
    global historial
    claves_a_eliminar = [clave for clave, cmd in historial.items() if cmd == comando]
    for clave in claves_a_eliminar:
        del historial[clave]
    historial[len(historial)+1] = comando
    if len(historial) > 50:
        del historial[min(historial.keys())]
        reindexar_historial()

def obtener_historial_como_lista():
    return list(historial.items())

def analizar_linea_comando(linea):
    elementos = re.findall(r'"[^"]*"|\'[^\']*\'|>>|<<|<|>|\||&|[\w\-\.\/]+', linea)  
    # ELIMINAR COMILLAS Y DIVIDIR ELEMENTOS
    elementos = [elem.strip('"\'').strip() for elem in elementos if elem.strip() != '']  
    parsed = []
    for elem in elementos:
        if re.match(r'^(>>|<<|<|>|\||&)$', elem):
            parsed.append(elem)
        else:
            parsed.extend(re.findall(r'[^"\'\s]+', elem))  
    return parsed


def ejecutar_comando(lista_elementos):
    global trabajos, contador_trabajos

    if not lista_elementos:
        return
    
    if lista_elementos[0] == 'cd':
        try:
            destino = lista_elementos[1] if len(lista_elementos) > 1 else os.path.expanduser("~")
            os.chdir(destino)
        except Exception as err:
            print("cd:", err)
        return
    
    if lista_elementos[0] == 'history':
        for clave, cmd in obtener_historial_como_lista():
            print(f"{clave}  {cmd}")
        return
    
    if lista_elementos[0] == 'jobs':
        for trabajo in trabajos:
            proceso = trabajo['proceso']
            if proceso.poll() is None:
                print(f"[{trabajo['id']}] {trabajo['comando']}")
        return
    
    if lista_elementos[0] == 'fg':
        if len(lista_elementos) > 1:
            try:
                id_trabajo = int(lista_elementos[1])
                trabajo = next((t for t in trabajos if t['id'] == id_trabajo), None)
                if trabajo:
                    proceso = trabajo['proceso']
                    print(f"Trayendo al primer plano el trabajo [{id_trabajo}]: {trabajo['comando']}")
                    proceso.wait()
                    trabajos.remove(trabajo)
                else:
                    print("fg: no existe ese trabajo")
            except ValueError:
                print("fg: id de trabajo inválido")
        else:
            if trabajos:
                trabajo = trabajos.pop()
                proceso = trabajo['proceso']
                print(f"Trayendo al primer plano el trabajo [{trabajo['id']}]: {trabajo['comando']}")
                proceso.wait()
            else:
                print("fg: no hay trabajos")
        return
    
    ejecutar_segundo_plano = False
    if lista_elementos and lista_elementos[-1] == '&':
        ejecutar_segundo_plano = True
        lista_elementos = lista_elementos[:-1]

    tuberia = []
    comando_actual = []
    for elemento in lista_elementos:
        if elemento == '|':
            tuberia.append(comando_actual)
            comando_actual = []
        else:
            comando_actual.append(elemento)
    tuberia.append(comando_actual)

    procesos = []
    cantidad_comandos = len(tuberia)
    proceso_anterior = None

    for i, elementos_comando in enumerate(tuberia):
        archivo_entrada = None
        archivo_salida = None
        modo_salida = 'w'
        elementos_nuevos = []
        j = 0
        while j < len(elementos_comando):
            elemento = elementos_comando[j]
            if elemento == '<':
                if j + 1 < len(elementos_comando):
                    archivo_entrada = elementos_comando[j + 1].strip('"\'')  
                    j += 2
                    continue
                else:
                    print("Error: falta nombre de fichero para <")  
                    return
            elif elemento == '>':
                if j + 1 < len(elementos_comando):
                    archivo_salida = elementos_comando[j + 1].strip('"\'')  
                    modo_salida = 'w'
                    j += 2
                    continue
                else:
                    print("Error: falta nombre de fichero para >")  
                    return
            elif elemento == '>>':
                if j + 1 < len(elementos_comando):
                    # CAMBIO: Eliminar comillas del nombre de archivo
                    archivo_salida = elementos_comando[j + 1].strip('"\'')  
                    modo_salida = 'a'
                    j += 2
                    continue
                else:
                    print("Error: falta nombre de fichero para >>")  
                    return
            else:
                elementos_nuevos.append(elemento)
                j += 1

        entrada = None
        salida = None

        if i == 0 and archivo_entrada:
            try:
                entrada = open(archivo_entrada, 'r')
            except Exception as err:
                print("Error abriendo entrada:", err)  
                return

        if i == cantidad_comandos - 1 and archivo_salida:
            try:
                salida = open(archivo_salida, modo_salida)
            except Exception as err:
                print("Error abriendo salida:", err)  
                return

        if proceso_anterior:
            entrada = proceso_anterior.stdout

        try:
            if i < cantidad_comandos - 1:
                proc = subprocess.Popen(elementos_nuevos, stdin=entrada,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            else:
                proc = subprocess.Popen(elementos_nuevos, stdin=entrada,
                                        stdout=salida if salida else subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:  # <<< NUEVO MANEJO DE ERRORES
            print(f"comando no encontrado: {elementos_nuevos[0]}")  
            return
        

        procesos.append(proc)
        proceso_anterior = proc

    if ejecutar_segundo_plano:
        trabajos.append({'id': contador_trabajos, 'proceso': procesos[-1], 'comando': " ".join(lista_elementos)})
        print(f"[{contador_trabajos}] {procesos[-1].pid}")
        contador_trabajos += 1
    else:
        salida_final, error_final = procesos[-1].communicate()
        if salida_final and not archivo_salida:  
            print(salida_final, end='')
        if error_final:
            print(error_final, end='')
        for proc in procesos[:-1]:
            proc.wait()
        if salida:  
            salida.close()
        if entrada and not entrada.closed:  
            entrada.close()

def principal():
    global historial
    while True:
        try:
            linea_comando = input("$ ")
        except EOFError:
            print()
            break

        if not linea_comando.strip():
            continue

        if linea_comando.startswith("!"):
            if linea_comando.startswith("!!"):
                if historial:
                    ultima_clave = max(historial.keys())
                    linea_comando = historial[ultima_clave]
                    print(linea_comando)
                else:
                    print("No hay comandos en el historial.")
                    continue
            elif linea_comando[1:].isdigit():
                indice = int(linea_comando[1:])
                if indice in historial:
                    linea_comando = historial[indice]
                    print(linea_comando)
                else:
                    print("No existe ese comando en el historial.")
                    continue
            else:
                prefijo = linea_comando[1:]
                encontrado = None
                for clave, cmd in obtener_historial_como_lista():
                    if cmd.startswith(prefijo):
                        encontrado = cmd
                if encontrado:
                    linea_comando = encontrado
                    print(linea_comando)
                else:
                    print(f"No se encontró comando con prefijo '{prefijo}'")
                    continue

        if not linea_comando.startswith(" "):
            agregar_comando_al_historial(linea_comando)

        elementos_linea = analizar_linea_comando(linea_comando)
        ejecutar_comando(elementos_linea)

if __name__ == '__main__':
    principal()