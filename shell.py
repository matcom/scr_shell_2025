import os
from cola import Cola
import re
import subprocess


class Shell:
    def __init__(self):
        self.cola = Cola()

    def parse_command(self, _command):
        __command = re.sub(r"\s+", " ", _command).strip()
        tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', __command)
        return tokens

    def execute(self, command):
        result = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print(result.stdout, end="")

    def process_input(self, input_line):
        if input_line == "":
            return
        command = self.parse_command(input_line)
        self.execute(command)

    def run(self):
        while True:
            print("$", end="")
            input_line = input()
            self.process_input(input_line)


if __name__ == "__main__":
    shell = Shell()
    shell.run()
