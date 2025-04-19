#!/usr/bin/env python3
import os
import shlex
import subprocess

historia = []
trabajos = []

def parsear_redireccion(comando):
    try:
        tokens = shlex.split(comando)
    except ValueError:
        raise
    args = []
    entrada = None
    salida = None
    anexar = False
    i = 0
    while i < len(tokens):
        if tokens[i] == '<':
            entrada = tokens[i+1]
            i += 2
        elif tokens[i] == '>>':
            salida = tokens[i+1]
            anexar = True
            i += 2
        elif tokens[i] == '>':
            salida = tokens[i+1]
            anexar = False
            i += 2
        else:
            args.append(tokens[i])
            i += 1
    return args, entrada, salida, anexar

def cd(ruta):
    try:
        os.chdir(ruta)
    except FileNotFoundError:
        print(f"{ruta}: no existe el directorio")

def manejar_historial(comando):
    if comando.startswith(' '):
        return
    if len(historia) > 0 and comando == historia[-1]:
        return
    historia.append(comando)
    if len(historia) > 50:
        historia.pop(0)

def expandir_comando(comando):
    if comando == '!!':
        if len(historia) > 0:
            return historia[-1]
        return ''
    if comando.startswith('!'):
        clave = comando[1:]
        if clave.isdigit():
            idx = int(clave) - 1
            if 0 <= idx < len(historia):
                return historia[idx]
            return ''
        for cmd in reversed(historia):
            if cmd.startswith(clave):
                return cmd
        return ''
    return comando

def mostrar_historial():
    num = 1
    for cmd in historia:
        print(f"{num} {cmd}")
        num += 1

def mostrar_jobs():
    for proc, cmd in trabajos:
        print(cmd)

def fg():
    if len(trabajos) > 0:
        proc, cmd = trabajos.pop(0)
        proc.wait()

def ejecutar_basico(comando, fondo):
    try:
        args, ent, sal, anex = parsear_redireccion(comando)
    except ValueError:
        print("Error de sintaxis: comilla sin cerrar")
        return
    if len(args) == 0:
        return
    if args[0] == 'cd':
        if len(args) > 1:
            cd(args[1])
        else:
            cd(os.path.expanduser('~'))
        return
    if args[0] == 'history':
        mostrar_historial()
        return
    if args[0] == 'jobs':
        mostrar_jobs()
        return
    if args[0] == 'fg':
        fg()
        return
    stdin = None
    if ent:
        try:
            stdin = open(ent, 'r')
        except FileNotFoundError:
            print(f"{ent}: no existe el fichero")
            return
    stdout = None
    if sal:
        modo = 'a' if anex else 'w'
        stdout = open(sal, modo)
    try:
        if fondo:
            proc = subprocess.Popen(args, stdin=stdin, stdout=stdout or subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            trabajos.append((proc, comando))
        else:
            proc = subprocess.Popen(args, stdin=stdin, stdout=stdout or subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            salida, _ = proc.communicate()
            if salida:
                print(salida, end='')
    except FileNotFoundError:
        print(f"{args[0]}: comando no encontrado")

def ejecutar_tuberias(comando, fondo):
    partes = comando.split('|')
    canal_entrada = None
    ultimo = None
    for idx in range(len(partes)):
        seg = partes[idx].strip()
        try:
            args, ent, sal, anex = parsear_redireccion(seg)
        except ValueError:
            print("Error de sintaxis: comilla sin cerrar")
            return
        if len(args) == 0:
            return
        if args[0] == 'cd':
            if len(args) > 1:
                cd(args[1])
            else:
                cd(os.path.expanduser('~'))
            canal_entrada = None
            continue
        if args[0] == 'history':
            texto = ''
            num = 1
            for cmd in historia:
                texto += f"{num} {cmd}\n"
                num += 1
            canal_entrada = texto
            continue
        if args[0] == 'jobs':
            texto = ''
            for p, c in trabajos:
                texto += f"{c}\n"
            canal_entrada = texto
            continue
        if args[0] == 'fg':
            fg()
            canal_entrada = None
            continue
        if canal_entrada is not None:
            stdin = subprocess.PIPE
        elif ent:
            try:
                stdin = open(ent, 'r')
            except FileNotFoundError:
                print(f"{ent}: no existe el fichero")
                return
        else:
            stdin = None
        if idx < len(partes) - 1:
            stdout = subprocess.PIPE
        else:
            if sal:
                modo = 'a' if anex else 'w'
                stdout = open(sal, modo)
            else:
                if fondo:
                    stdout = subprocess.DEVNULL
                else:
                    stdout = subprocess.PIPE
        try:
            proc = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            print(f"{args[0]}: comando no encontrado")
            return
        if canal_entrada is not None:
            proc.stdin.write(canal_entrada)
            proc.stdin.close()
        salida, _ = proc.communicate()
        if idx == len(partes) - 1 and salida:
            print(salida, end='')
        canal_entrada = salida
        ultimo = proc
    if fondo and ultimo:
        trabajos.append((ultimo, comando))

def ejecutar_tuberias_background(comando):
    partes = comando.split('|')
    previo = None
    ultimo = None
    for idx in range(len(partes)):
        seg = partes[idx].strip()
        try:
            args, ent, sal, anex = parsear_redireccion(seg)
        except ValueError:
            print("Error de sintaxis: comilla sin cerrar")
            return
        if len(args) == 0:
            return
        if previo:
            stdin = previo
        elif ent:
            try:
                stdin = open(ent, 'r')
            except FileNotFoundError:
                print(f"{ent}: no existe el fichero")
                return
        else:
            stdin = None
        if idx < len(partes) - 1:
            stdout = subprocess.PIPE
        else:
            if sal:
                modo = 'a' if anex else 'w'
                stdout = open(sal, modo)
            else:
                stdout = subprocess.DEVNULL
        try:
            proc = subprocess.Popen(args, stdin=stdin, stdout=stdout, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print(f"{args[0]}: comando no encontrado")
            return
        previo = proc.stdout
        ultimo = proc
    if ultimo:
        trabajos.append((ultimo, comando))

def ejecutar_comando(comando):
    fondo = False
    if comando.endswith('&'):
        fondo = True
        comando = comando[:len(comando)-1]
        comando = comando.strip()
    manejo = expandir_comando(comando)
    if manejo == '':
        return
    if not comando.startswith('!'):
        manejar_historial(comando)
    if '|' in manejo:
        ejecutar_tuberias(manejo, fondo)
    else:
        ejecutar_basico(manejo, fondo)

def main():
    while True:
        try:
            linea = input('} ')
        except EOFError:
            break
        if linea:
            ejecutar_comando(linea)

if __name__ == '__main__':
    main()
