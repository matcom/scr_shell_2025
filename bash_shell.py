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

def parsear_redireccion(cmd):
    tokens = tokenizar(cmd)
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
    except:
        pass

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
    if cmd.startswith('!') and len(cmd) > 1:
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
        print(f'{num} {h}')
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
        except:
            print(f'{ent}: no existe')
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
            out, _ = p.communicate()
            if out:
                print(out, end='')
    except:
        print(f'{args[0]}: comando no encontrado')

def ejecutar_tuberias(cmd, fondo):
    partes = cmd.split('|')
    canal = None
    ultimo = None
    for i, seg in enumerate(partes):
        seg = seg.strip()
        args, ent, sal, anex = parsear_redireccion(seg)
        if not args:
            return
        if args[0] in ('cd', 'history', 'jobs', 'fg'):
            out = ''
            if args[0] == 'cd':
                if len(args) > 1:
                    cd(args[1])
                else:
                    cd(os.path.expanduser('~'))
            elif args[0] == 'history':
                out = '\n'.join(f'{n} {h}' for n, h in enumerate(historia, 1))
                if out:
                    out += '\n'
            elif args[0] == 'jobs':
                out = '\n'.join(c for p, c in trabajos)
                if out:
                    out += '\n'
            elif args[0] == 'fg':
                if trabajos:
                    p, c = trabajos.pop(0)
                    p.wait()
            canal = out
            continue
        if canal is not None:
            stdin_pipe = subprocess.PIPE
        else:
            if ent:
                try:
                    stdin_pipe = open(ent, 'r')
                except FileNotFoundError:
                    print(f'{ent}: no existe')
                    return
            else:
                stdin_pipe = None
        if i < len(partes) - 1:
            stdout_pipe = subprocess.PIPE
        else:
            if sal:
                modo = 'a' if anex else 'w'
                stdout_pipe = open(sal, modo)
            else:
                stdout_pipe = subprocess.DEVNULL if fondo else subprocess.PIPE
        try:
            p = subprocess.Popen(
                args,
                stdin=stdin_pipe,
                stdout=stdout_pipe,
                stderr=subprocess.PIPE,
                text=True
            )
        except:
            print(f'{args[0]}: comando no encontrado')
            return
        if canal is not None:
            out, _ = p.communicate(input=canal)
        else:
            out, _ = p.communicate()
        if i == len(partes) - 1 and out:
            print(out, end='')
        canal = out
        ultimo = p
    if fondo and ultimo:
        trabajos.append((ultimo, cmd))

def quotes_balanced(s):
    single = False
    double = False
    for c in s:
        if c == "'" and not double:
            single = not single
        elif c == '"' and not single:
            double = not double
    return not single and not double

def leer_comando():
    try:
        linea = input('} ')
    except EOFError:
        return None
    cmd = linea
    if not quotes_balanced(cmd):
        while True:
            try:
                linea2 = input('> ')
            except EOFError:
                break
            cmd += '\n' + linea2
            if quotes_balanced(cmd):
                break
    return cmd

def ejecutar_comando(cmd):
    fondo = False
    if cmd.endswith('&'):
        fondo = True
        cmd = cmd[:-1].strip()
    cmd_e = expandir_comando(cmd)
    if cmd_e == '':
        return
    if not cmd.startswith('!'):
        manejar_historial(cmd)
    if '|' in cmd_e:
        ejecutar_tuberias(cmd_e, fondo)
    else:
        ejecutar_basico(cmd_e, fondo)

def main():
    while True:
        cmd = leer_comando()
        if cmd is None:
            break
        if cmd:
            ejecutar_comando(cmd)

if __name__ == '__main__':
    main()
