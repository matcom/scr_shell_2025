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
    # Eliminar si ya existe el comando
    claves_a_eliminar = [clave for clave, cmd in historial.items() if cmd == comando]
    for clave in claves_a_eliminar:
        del historial[clave]
    # Agregar el nuevo comando al final
    historial[len(historial)+1] = comando
    # Si se exceden los 50 comandos, eliminar el primero y reindexar
    if len(historial) > 50:
        del historial[min(historial.keys())]
        reindexar_historial()
def obtener_historial_como_lista():
    return list(historial.items())

def analizar_linea_comando(linea):
    # Maneja comillas y operadores correctamente
    elementos = re.findall(r'"[^"]*"|\'[^\']*\'|>>|<<|<|>|\||&|[\w\-\.\/]+', linea)
    elementos = [elem.strip('"\'') for elem in elementos if elem.strip() != '']
    # Separa elementos concatenados (ej: 'echo"hola"' -> ['echo', 'hola'])
    parsed = []
    for elem in elementos:
        if re.match(r'^(>>|<<|<|>|\||&)$', elem):
            parsed.append(elem)
    elementos = []
    current = ""
    in_quotes = None

    for char in linea:
        if char in ['"', "'"]:
            if in_quotes is None:
                in_quotes = char
            elif in_quotes == char:
                in_quotes = None
            else:
                current += char
        elif char in [' ', '\t'] and in_quotes is None:
            if current:
                elementos.append(current)
                current = ""
        else:
            current += char

    if current:
        elementos.append(current)

    # Procesa operadores especiales
    final_elements = []
    i = 0
    while i < len(elementos):
        if elementos[i] in ['>>', '<<', '<', '>', '|', '&']:
            final_elements.append(elementos[i])
        else:
            parsed.extend(re.findall(r'[^"\'\s]+', elem))
    return parsed
            # Limpia las comillas solo si están al inicio y final
            elem = elementos[i]
            if (elem.startswith('"') and elem.endswith('"')) or (elem.startswith("'") and elem.endswith("'")):
                elem = elem[1:-1]
            final_elements.append(elem)
        i += 1

    return final_elements

def ejecutar_comando(lista_elementos):
    global trabajos, contador_trabajos
@@ -115,7 +142,6 @@ def ejecutar_comando(lista_elementos):
    cantidad_comandos = len(tuberia)
    proceso_anterior = None


    # Recorre cada comando en el pipeline y gestiona redirecciones
    for i, elementos_comando in enumerate(tuberia):
        archivo_entrada = None
@@ -135,7 +161,7 @@ def ejecutar_comando(lista_elementos):
                    return
            elif elemento == '>':
                if j + 1 < len(elementos_comando):
                    archivo_salida = elementos_comando[j + 1].strip('"\'')
                    archivo_salida = elementos_comando[j + 1]
                    modo_salida = 'w'
                    j += 2
                    continue
@@ -144,8 +170,8 @@ def ejecutar_comando(lista_elementos):
                    return
            elif elemento == '>>':
                if j + 1 < len(elementos_comando):
                    archivo_salida = elementos_comando[j + 1].strip('"\'')
                    modo_salida = 'a'  
                    archivo_salida = elementos_comando[j + 1]
                    modo_salida = 'a'
                    j += 2
                    continue
                else:
@@ -176,52 +202,42 @@ def ejecutar_comando(lista_elementos):
                if entrada:
                    entrada.close()
                return
            

        # Si hay un proceso anterior en la tubería, su salida se conecta como entrada
        if proceso_anterior is not None:
            entrada = proceso_anterior.stdout

        try:
            if i < cantidad_comandos - 1:
                proc = subprocess.Popen(elementos_nuevos, stdin=entrada,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            else:
                proc = subprocess.Popen(elementos_nuevos, stdin=entrada,
                                        stdout=salida if salida else subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:  # <<< NUEVO MANEJO DE ERRORES
            print(f"comando no encontrado: {elementos_nuevos[0]}")  # Mensaje útil
                                      stdout=salida if salida else subprocess.PIPE,
                                      stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            print(f"comando no encontrado: {elementos_nuevos[0]}")
            return

        # Para comandos intermedios se crea un pipe para la salida
        if i < cantidad_comandos - 1:
            proc = subprocess.Popen(elementos_nuevos, stdin=entrada,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        else:
            proc = subprocess.Popen(elementos_nuevos, stdin=entrada,
                                    stdout=salida if salida is not None else subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
        procesos.append(proc)
        proceso_anterior = proc


    # Si se indicó ejecución en segundo plano, se registra el trabajo
    if ejecutar_segundo_plano:
        trabajos.append({'id': contador_trabajos, 'proceso': procesos[-1], 'comando': " ".join(lista_elementos)})
        print(f"[{contador_trabajos}] {procesos[-1].pid}")
        contador_trabajos += 1
    else:
        salida_final, error_final = procesos[-1].communicate()
        if salida_final and not archivo_salida:  # <<< CONDICIÓN AÑADIDA
        if salida_final and not archivo_salida:
            print(salida_final, end='')
        if error_final:
            print(error_final, end='')
        for proc in procesos[:-1]:
            proc.wait()
        # CAMBIO: Cierre seguro de archivos
        if salida:  
        if salida:
            salida.close()
        if entrada and not entrada.closed:  
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
        # Manejo para re-ejecución de comandos:
        # !!   => último comando
        # !n   => comando número n del historial
        # !abc => último comando que comience por "abc"
        if linea_comando.startswith("!"):
            if linea_comando.startswith("!!"):
                if historial:
                    # Se toma el último comando del historial
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
                # Se recorre el historial en orden (del más antiguo al más reciente)
                for clave, cmd in obtener_historial_como_lista():
                    if cmd.startswith(prefijo):
                        encontrado = cmd
                if encontrado:
                    linea_comando = encontrado
                    print(linea_comando)
                else:
                    print("No se encontró ningún comando que comience con", prefijo)
                    continue
        # Si la línea no empieza con espacio, se agrega al historial
        if not linea_comando.startswith(" "):
            agregar_comando_al_historial(linea_comando)
        elementos_linea = analizar_linea_comando(linea_comando)
        ejecutar_comando(elementos_linea)
if __name__ == '__main__':
    principal()