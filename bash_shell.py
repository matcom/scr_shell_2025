#!/usr/bin/env python3
import os
import subprocess

historia = []
trabajos = []

def tokenizar(linea):
    tokens = []
    actual = ''
    dentro = False
    comilla = ''
    for c in linea:
        if dentro:
            if c == comilla:
                dentro = False
                comilla = ''
            else:
                actual += c
        else:
            if c == '"' or c == "'":
                dentro = True
                comilla = c
            elif c.isspace():
                if actual != '':
                    tokens.append(actual)
                    actual = ''
            else:
                actual += c
    if actual != '':
        tokens.append(actual)
    return tokens

def parsear_redireccion(comando):
    tokens = tokenizar(comando)
    args = []
    ent = None
    sal = None
    anex = False
    i = 0
    while i < len(tokens):
        if tokens[i] == '<':
            ent = tokens[i+1]
            i += 2
        elif tokens[i] == '>>':
            sal = tokens[i+1]
            anex = True
            i += 2
        elif tokens[i] == '>':
            sal = tokens[i+1]
            anex = False
            i += 2
        else:
            args.append(tokens[i])
            i += 1
    return args, ent, sal, anex

def cd(ruta):
    try:
        os.chdir(ruta)
    except FileNotFoundError:
        print(f"{ruta}: no existe el directorio")

def manejar_historial(cmd):
    if cmd.startswith(' '):
        return
    if len(historia) > 0 and cmd == historia[-1]:
        return
    historia.append(cmd)
    if len(historia) > 50:
        historia.pop(0)

def expandir_comando(cmd):
    if cmd == '!!':
        if len(historia) > 0:
            return historia[-1]
        return ''
    if cmd.startswith('!'):
        clave = cmd[1:]
        if clave.isdigit():
            idx = int(clave) - 1
            if 0 <= idx < len(historia):
                return historia[idx]
            return ''
        for h in reversed(historia):
            if h.startswith(clave):
                return h
        return ''
    return cmd

def mostrar_historial():
    num = 1
    for h in historia:
        print(f"{num} {h}")
        num += 1

def mostrar_jobs():
    for p, c in trabajos:
        print(c)

def fg():
    if len(trabajos) > 0:
        p, c = trabajos.pop(0)
        p.wait()

def ejecutar_basico(cmd, fondo):
    args, ent, sal, anex = parsear_redireccion(cmd)
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
            p = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout or subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            trabajos.append((p, cmd))
        else:
            p = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout or subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            salida, _ = p.communicate()
            if salida:
                print(salida, end='')
    except FileNotFoundError:
        print(f"{args[0]}: comando no encontrado")

def ejecutar_tuberias(cmd, fondo):
    partes = cmd.split('|')
    canal = None
    ultimo = None

    for idx in range(len(partes)):
        seg = partes[idx].strip()
        args, ent, sal, anex = parsear_redireccion(seg)
        if len(args) == 0:
            return

        if canal is not None:
            stdin = subprocess.PIPE
        else:
            if ent:
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
            p = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE,
                text=True
            )
        except FileNotFoundError:
            print(f"{args[0]}: comando no encontrado")
            return

        if canal is not None:
            p.stdin.write(canal)
            p.stdin.close()

        salida, _ = p.communicate()
        if idx == len(partes) - 1 and salida:
            print(salida, end='')

        canal = salida
        ultimo = p

    if fondo and ultimo:
        trabajos.append((ultimo, cmd))

def ejecutar_comando(linea):
    linea = linea.strip()
    fondo = False
    if linea.endswith('&'):
        fondo = True
        linea = linea[:-1].strip()

    cmd = expandir_comando(linea)
    if cmd == '':
        return

    if not linea.startswith('!'):
        manejar_historial(linea)

    if '|' in cmd:
        ejecutar_tuberias(cmd, fondo)
    else:
        ejecutar_basico(cmd, fondo)

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
