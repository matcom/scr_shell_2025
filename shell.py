import os
from cola import Cola


class Shell:
    def __init__(self):
        self.cola = Cola()

    def parse_command(self, _command):
        pass  # hay que hacer un parser xxddxdxd

    def process_input(self, input_line):
        if input_line == "":
            return
        command = self.parse_command(input_line)

    def run(self):
        while True:
            print("$", end="")
            input_line = input()
            self.process_input(input_line)


if __name__ == "__main__":
    shell = Shell()
    shell.run()
