import os
import subprocess
import shlex

def ejecutar_comando(comando):
    """
    Ejecuta un comando en el sistema.
    """
    try:
        subprocess.run(comando, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando el comando: {e}")
    except FileNotFoundError as e:
        print(f"Comando no encontrado: {e}")

def procesar_entrada(entrada):
    """
    Procesa la entrada y ejecuta los comandos, manejando pipes y redirecciones.
    """

    if '|' in entrada:
        comandos = [shlex.split(cmd) for cmd in entrada.split("|")]
        try:
  
            proc = subprocess.Popen(comandos[0], stdout=subprocess.PIPE)
            for cmd in comandos[1:]:
                proc = subprocess.Popen(cmd, stdin=proc.stdout, stdout=subprocess.PIPE)
            proc.communicate()
        except ValueError as e:
            print(f"Error en la entrada con pipes: {e}")
        return
    elif '>' in entrada or '>>' in entrada:

        comando, archivo = entrada.split('>', 1) if '>' in entrada else entrada.split('>>', 1)
        comando = comando.strip()
        archivo = archivo.strip()
        append = True if '>>' in entrada else False
        with open(archivo, 'a' if append else 'w') as f:
            subprocess.run(shlex.split(comando), stdout=f)
        return
    else:
   
        if entrada.startswith("echo"):

            print(entrada[5:].strip())
            return
        else:
   
            comando = shlex.split(entrada)
            ejecutar_comando(comando)

def shell():
    """
    La función principal del shell.
    """
    while True:
        entrada = input("Shell> ")
        if entrada.lower() == 'exit':
            break
        procesar_entrada(entrada)

if __name__ == "__main__":
    shell()
