import os
import subprocess

def mostrar_prompt():
    print("} ", end="")

def cambiar_directorio(comando):
    try:
        os.chdir(comando[1])
    except IndexError:
        print("Error: se requiere un directorio.")
    except FileNotFoundError:
        print(f"Error: directorio '{comando[1]}' no encontrado.")

def redirigir_salida(comando):
    with open(comando[2], 'w') as archivo:
        subprocess.run(comando[:2], stdout=archivo)

def redirigir_entrada(comando):
    with open(comando[2], 'r') as archivo:
        subprocess.run(comando[:2], stdin=archivo)

def redirigir_salida_append(comando):
    with open(comando[2], 'a') as archivo:
        subprocess.run(comando[:2], stdout=archivo)

def ejecutar_pipe(comando):
    comando1 = comando[0].split()
    comando2 = comando[2].split()
    p1 = subprocess.Popen(comando1, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(comando2, stdin=p1.stdout, stdout=subprocess.PIPE)
    p1.stdout.close()
    p2.communicate()

def ejecutar_shell():
    while True:
        mostrar_prompt()
        entrada = input()
        comando = entrada.split(' ')

        if comando[0] == 'cd':
            cambiar_directorio(comando)
        elif '>' in comando:
            if '>>' in comando:
                redirigir_salida_append(comando)
            else:
                redirigir_salida(comando)
        elif '<' in comando:
            redirigir_entrada(comando)
        elif '|' in comando:
            ejecutar_pipe(comando)
        else:
            subprocess.run(comando)

if __name__ == "__main__":
    ejecutar_shell()
