#!/usr/bin/env python3
import os
import sys
import re
import subprocess
from typing import List, Optional, IO


MAX_HISTORY = 50
HISTORY_FILE = os.path.expanduser("~/.shell_history")
history: List[str] = []



def print_prompt() -> None:
    """Muestra el prompt del shell."""
    print("$ ", end="", flush=True)

def read_command() -> str:
    """Lee un comando desde la entrada estándar."""
    try:
        return input().strip()
    except EOFError:
        print("\nExit")
        sys.exit(0)
    except KeyboardInterrupt:
        return ""

def add_to_history(command: str) -> None:
    """Añade un comando al historial."""
    if command and (not history or command != history[-1]):
        if len(history) >= MAX_HISTORY:
            history.pop(0)
        history.append(command)

def execute_external(command: List[str], input_fd: Optional[IO] = None, 
                    output_fd: Optional[IO] = None) -> None:
    """Ejecuta un comando externo con redirecciones."""
    try:
        subprocess.run(
            command,
            stdin=input_fd or sys.stdin,
            stdout=output_fd or sys.stdout,
            stderr=sys.stderr,
            check=True
        )
    except FileNotFoundError:
        print(f"{command[0]}: comando no encontrado", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar {command[0]} (código {e.returncode})", file=sys.stderr)

def handle_redirections(command: str) -> tuple:
    """Analiza y aplica redirecciones de entrada/salida."""
    input_file = None
    output_file = None
    mode = "w"


    if '>' in command:
        if '>>' in command:
            parts = command.split('>>')
            command = parts[0].strip()
            output_file = parts[1].strip()
            mode = "a"
        else:
            parts = command.split('>')
            command = parts[0].strip()
            output_file = parts[1].strip()
            mode = "w"

    if '<' in command:
        parts = command.split('<')
        command = parts[0].strip()
        input_file = parts[1].strip()

    return command, input_file, output_file, mode

def execute_pipeline(commands: List[str]) -> None:
    """Ejecuta una serie de comandos conectados por pipes."""
    prev_output = None
    processes = []  

    for cmd in commands:
        cmd_parts = cmd.strip().split()
        input_file = None
        output_file = None
        mode = "w"

 
        cmd_processed, input_file, output_file, mode = handle_redirections(cmd)

        if input_file:
            stdin = open(input_file, "r")
        else:
            stdin = prev_output

        if output_file:
            stdout = open(output_file, mode)
        else:
            stdout = subprocess.PIPE if cmd != commands[-1] else None

        process = subprocess.Popen(
            cmd_processed.split(),
            stdin=stdin if isinstance(stdin, IO) else prev_output,
            stdout=stdout,
            stderr=sys.stderr
        )

        processes.append(process) 

        if prev_output and not input_file:
            prev_output.close()
        prev_output = process.stdout

    if prev_output:
        prev_output.close()

    for process in processes:
        process.wait()


def handle_internal(command: List[str]) -> bool:
    """Maneja comandos internos como cd, history, etc."""
    if command[0] == "cd":
        try:
            os.chdir(command[1] if len(command) > 1 else os.environ["HOME"])
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
        return True

    if command[0] == "history":
        for i, cmd in enumerate(history[-MAX_HISTORY:], start=1):
            print(f"{i} {cmd}")
        return True

    return False

def process_command(command: str) -> None:
    """Procesa y ejecuta un comando."""
    add_to_history(command)


    if '|' in command:
        commands = command.split('|')
        execute_pipeline(commands)
        return


    cmd_processed, input_file, output_file, mode = handle_redirections(command)
    cmd_parts = cmd_processed.split()

    if not cmd_parts:
        return

    if handle_internal(cmd_parts):
        return


    input_fd = None
    output_fd = None

    try:
        if input_file:
            input_fd = open(input_file, "r")
        
        if output_file:
            output_fd = open(output_file, mode)

        execute_external(cmd_parts, input_fd, output_fd)

    except FileNotFoundError as e:
        print(f"{e.filename}: No existe el archivo o directorio", file=sys.stderr)
    finally:
        if input_fd:
            input_fd.close()
        if output_fd:
            output_fd.close()


def main() -> None:

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history.extend(line.strip() for line in f.readlines()[-MAX_HISTORY:])

    try:
        while True:
            print_prompt()
            command = read_command()
            process_command(command)
    finally:

        with open(HISTORY_FILE, "w") as f:
            f.write("\n".join(history[-MAX_HISTORY:]))

if __name__ == "__main__":
    main()