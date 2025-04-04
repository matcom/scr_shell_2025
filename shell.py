import os
import re
import subprocess
from pila import Pila


class Shell:
    def __init__(self):
        self.pila = Pila()

    def add_stack(self, command):
        if self.pila.size > 0:
            if self.pila.tail.valor != " ".join(command).strip():
                self.pila.add(" ".join(command).strip())
        else:
            self.pila.add(" ".join(command).strip())

    def parse_command(self, _command):
        __command = re.sub(r"\s+", " ", _command).strip()
        return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', __command)

    def sub(self, command, shell=False):
        if shell and isinstance(command, list):
            command = " ".join(command)
        try:
            return subprocess.run(
                command,
                check=True,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            print(f"{e.stderr}", end="", flush=True)
            return

    def execute(self, command):
        if not command:
            return

        if command[0] == "cd":
            try:
                os.chdir(command[1] if len(command) > 1 else os.path.expanduser("~"))
            except Exception as e:
                print(f"{e}")
            return
        if command[0] == "history":
            print(self.pila, flush=True)
            return
        if command[0] == "ls":
            result = self.sub(command, True)
            if result:
                print(result.stdout, end="", flush=True)
            return

        result = self.sub(command, True)
        if result:
            print(result.stdout, end="", flush=True)

    def search_history(self, comando):
        if len(comando) == 1:
            return
        elif comando == "!!":
            if self.pila.size > 0:
                ultimo_comando = self.pila.tail.valor
                command = self.parse_command(ultimo_comando)
                self.execute(command)
                return
            else:
                print("No hay comandos en el historial", flush=True)
        elif comando.startswith("!") and comando[1:].isdigit():
            try:
                comand = self.pila.search(comando[1:])
                result = self.parse_command(comand)
                self.execute(result)
                return result
            except IndexError:
                print(f"No existe el comando en la posición {index}", flush=True)
                return

        else:
            return

    def process_input(self, input_line):
        if input_line == "":
            return
        if input_line.startswith("!"):
            command = self.search_history(input_line)
            if command and input_line[0] != " ":
                self.add_stack(command)
            return

        command = self.parse_command(input_line)
        self.execute(command)
        if input_line[0] != " ":
            self.add_stack(command)

    def run(self):
        while True:
            try:
                print("$ ", end="", flush=True)
                input_line = input()
                self.process_input(input_line)
            except KeyboardInterrupt:
                continue


if __name__ == "__main__":
    shell = Shell()
    shell.run()
