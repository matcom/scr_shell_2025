import os
import re
import subprocess
from pila import Pila


class Shell:
    def __init__(self):
        self.pila = Pila()

    def parse_command(self, _command):
        __command = re.sub(r"\s+", " ", _command).strip()
        return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', __command)

    def execute(self, command):
        if not command:
            return

        if command[0] == "cd":
            try:
                os.chdir(command[1] if len(command) > 1 else os.path.expanduser("~"))
            except Exception as e:
                print(f"{e}")
            return

        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(result.stdout, end="", flush=True)

    def process_input(self, input_line):
        if input_line == "":
            return
        command = self.parse_command(input_line)
        self.execute(command)
        if self.pila.size > 0:
            if self.pila.tail.valor != " ".join(command).strip():
                self.pila.add(" ".join(command).strip())
        else:
            self.pila.add(" ".join(command).strip())

    def run(self):
        while True:
            print("$ ", end="", flush=True)
            input_line = input().strip()
            self.process_input(input_line)


if __name__ == "__main__":
    shell = Shell()
    shell.run()
