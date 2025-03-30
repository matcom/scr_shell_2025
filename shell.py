import os
import re
import subprocess
from cola import Cola


class Shell:
    def __init__(self):
        self.cola = Cola()

    def parse_command(self, _command):
        normalized = re.sub(r"\s+", " ", _command).strip()
        return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', normalized)

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

    def run(self):
        while True:
            print("$ ", end="", flush=True)
            input_line = input().strip()
            self.process_input(input_line)


if __name__ == "__main__":
    shell = Shell()
    shell.run()
