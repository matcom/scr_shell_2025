import os
import re
import subprocess


class Shell:
    def __init__(self) -> None:
        self.prompt = "$: "

    def process_input(self, input_line: str):
        if not input_line:
            return
        try:
            result = subprocess.run(
                input_line,
                check=True,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if isinstance(result, subprocess.CompletedProcess):
                print(result.stdout, end="", flush=True)

        except subprocess.CalledProcessError as e:
            print(f"{e.stderr}", end="", flush=True)
            return None
        except Exception as e:
            print(f"Error: {str(e)}", flush=True)
            return None

    def run(self) -> None:
        while True:
            try:
                input_line = input(self.prompt)
                self.process_input(input_line)
            except:
                pass


if __name__ == "__main__":
    Shell().run()
