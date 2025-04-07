import os
import subprocess
from typing import List


class Shell:
    def __init__(self) -> None:
        self.prompt = "$: "
        self.paths: List[str] = [
            os.path.expanduser("~"),
            os.getcwd(),
        ]
        self.max_history = 5

    def _update_path_history(self, new_path: str) -> None:
        if not self.paths or self.paths[-1] != new_path:
            self.paths.append(new_path)
            if len(self.paths) > self.max_history:
                self.paths.pop(0)

    def _handle_cd_command(self, tokens: List[str]) -> None:
        try:
            if len(tokens) > 1 and tokens[1] == "-":
                if len(self.paths) < 2:
                    print("cd: no previous directory", flush=True)
                    return
                prev_dir = self.paths[-2]
                os.chdir(prev_dir)
                self._update_path_history(os.getcwd())
                print(prev_dir, flush=True)
                return

            if len(tokens) > 1 and tokens[1] == "--":
                tokens = tokens[:1] + tokens[2:]

            if len(tokens) == 1 or tokens[1] == "~":
                new_dir = os.path.expanduser("~")
            else:
                new_dir = tokens[1]
                if new_dir.startswith("~") and not new_dir.startswith("~/"):
                    new_dir = os.path.expanduser(new_dir)
                new_dir = os.path.expandvars(new_dir)

            os.chdir(new_dir)
            self._update_path_history(os.getcwd())

        except FileNotFoundError:
            print(f"cd: no such file or directory: {tokens[1]}", flush=True)
        except NotADirectoryError:
            print(f"cd: not a directory: {tokens[1]}", flush=True)
        except PermissionError:
            print(f"cd: permission denied: {tokens[1]}", flush=True)
        except Exception as e:
            print(f"cd: {str(e)}: {tokens[1] if len(tokens) > 1 else ''}", flush=True)

    def _handle_other_commands(self, input_line: str) -> None:
        try:
            result = subprocess.run(
                input_line,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.stdout:
                print(result.stdout, end="", flush=True)
            if result.stderr:
                print(result.stderr, end="", flush=True)

        except Exception as e:
            print(f"Error: {str(e)}", flush=True)

    def process_input(self, input_line: str) -> None:
        if not input_line.strip():
            return

        tokens = input_line.split()

        if tokens[0] == "cd":
            self._handle_cd_command(tokens)
        else:
            self._handle_other_commands(input_line)

    def run(self) -> None:
        while True:
            try:
                input_line = input(self.prompt)
                self.process_input(input_line)
            except EOFError:
                print("\nExit")
                break
            except KeyboardInterrupt:
                print("^C")
            except Exception as e:
                print(f"Unexpected error: {str(e)}", flush=True)


if __name__ == "__main__":
    Shell().run()
