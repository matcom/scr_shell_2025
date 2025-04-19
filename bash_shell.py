#!/usr/bin/env python3
import os
import shlex
import subprocess

historia = []
trabajos = []

def parsear_redireccion(comando):
    tokens = shlex.split(comando)
    args = []
    in_f = None
    out_f = None
    append = False
    i = 0
    while i < len(tokens):
        if tokens[i] == '<':
            in_f = tokens[i+1]
            i += 2
        elif tokens[i] == '>>':
            out_f = tokens[i+1]
            append = True
            i += 2
        elif tokens[i] == '>':
            out_f = tokens[i+1]
            append = False
            i += 2
        else:
            args.append(tokens[i])
            i += 1
    return args, in_f, out_f, append

def cd(directorio):
    try:
        os.chdir(directorio)
    except:
        pass

def manejar_historial(comando):
    if comando.startswith(' '):
        return
    if len(historia) > 0 and comando == historia[-1]:
        return
    historia.append(comando)
    if len(historia) > 50:
        historia.pop(0)

def expandir_comando(comando):
    if comando.startswith('!!'):
        if len(historia) > 0:
            return historia[-1]
        else:
            return ''
    if comando.startswith('!'):
        clave = comando[1:]
        if clave.isdigit():
            indice = int(clave) - 1
            if 0 <= indice < len(historia):
                return historia[indice]
            else:
                return ''
        for cmd in reversed(historia):
            if cmd.startswith(clave):
                return cmd
        return ''
    return comando

def mostrar_historial():
    numero = 1
    for cmd in historia:
        print(f'{numero} {cmd}')
        numero += 1

def mostrar_jobs():
    for proc, cmd in trabajos:
        print(cmd)

def fg():
    if len(trabajos) > 0:
        proc, cmd = trabajos.pop(0)
        proc.wait()

def ejecutar_basico(comando, background):
    args, in_f, out_f, append = parsear_redireccion(comando)
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
    if in_f:
        stdin = open(in_f, 'r')

    stdout = None
    if out_f:
        if append:
            stdout = open(out_f, 'a')
        else:
            stdout = open(out_f, 'w')

    if background:
        proc = subprocess.Popen(
            args,
            stdin=stdin,
            stdout=stdout if stdout else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
        trabajos.append((proc, comando))
    else:
        proc = subprocess.Popen(
            args,
            stdin=stdin,
            stdout=stdout if stdout else subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        salida, _ = proc.communicate()
        if salida:
            print(salida, end='')

def ejecutar_tuberias(comando, background):
    partes = comando.split('|')
    entrada = None
    ultimo_proc = None

    for indice in range(len(partes)):
        segmento = partes[indice].strip()
        args, in_f, out_f, append = parsear_redireccion(segmento)
        if len(args) == 0:
            continue

        if entrada is not None:
            stdin = subprocess.PIPE
        else:
            if in_f:
                stdin = open(in_f, 'r')
            else:
                stdin = None

        if indice < len(partes) - 1:
            stdout = subprocess.PIPE
        else:
            if out_f:
                if append:
                    stdout = open(out_f, 'a')
                else:
                    stdout = open(out_f, 'w')
            else:
                if background:
                    stdout = subprocess.DEVNULL
                else:
                    stdout = subprocess.PIPE

        try:
            proc = subprocess.Popen(
                args,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE,
                text=True
            )

            if entrada is not None:
                proc.stdin.write(entrada)
                proc.stdin.close()

            salida, _ = proc.communicate()

            if indice == len(partes) - 1 and salida:
                print(salida, end='')

            entrada = salida
            ultimo_proc = proc

        except FileNotFoundError:
            print(f'{args[0]}: comando no encontrado')
            return

    if background and ultimo_proc:
        trabajos.append((ultimo_proc, comando))

def ejecutar_comando(comando):
    comando = comando.strip()
    manejar = not comando.startswith('!')
    background = False

    if comando.endswith('&'):
        background = True
        comando = comando[:-1].strip()

    comando_expandido = expandir_comando(comando)
    if comando_expandido == '':
        return

    if manejar:
        manejar_historial(comando)

    if '|' in comando_expandido:
        ejecutar_tuberias(comando_expandido, background)
    else:
        ejecutar_basico(comando_expandido, background)

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
