import os
import sys
from typing import List
import subprocess


class Shell:
    def __init__(self) -> None:
        self.prompt = "$ "
        self.paths: List[str] = [os.path.expanduser("~"), os.getcwd()]
        self.max_history = 5

    def _update_path_history(self, new_path: str) -> None:
        if not self.paths or self.paths[-1] != new_path:
            self.paths.append(new_path)
            if len(self.paths) > self.max_history:
                self.paths.pop(0)

    def _handle_cd(self, tokens: List[str]) -> bool:
        try:
            if len(tokens) > 1 and tokens[1] == "-":
                if len(self.paths) < 2:
                    print("cd: no previous directory", file=sys.stderr)
                    return False
                prev_dir = self.paths[-2]
                os.chdir(prev_dir)
                self._update_path_history(prev_dir)
                print(prev_dir)
                return True

            target_dir = os.path.expanduser("~") if len(tokens) == 1 else tokens[1]
            target_dir = (
                os.path.expanduser(target_dir)
                if target_dir.startswith("~")
                else target_dir
            )
            target_dir = os.path.expandvars(target_dir)

            os.chdir(target_dir)
            self._update_path_history(os.getcwd())
            return True

        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return False

    def _execute_command(self, command: str) -> int:
        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash" if os.name == "posix" else None,
                stdout=sys.stdout,
                stderr=sys.stderr,
                stdin=sys.stdin,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    def process_input(self, input_line: str) -> None:

        input_line = input_line.strip()
        if not input_line:
            return

        tokens = input_line.split()
        if tokens[0] == "cd":
            self._handle_cd(tokens)
        else:
            self._execute_command(input_line)

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
                print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    Shell().run()
