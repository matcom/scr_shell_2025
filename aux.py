import os
import sys
import subprocess
from typing import List, Deque, Optional
from collections import deque


class Shell:
    def __init__(self) -> None:
        self.prompt = "$ "
        self.paths: List[str] = [os.path.expanduser("~"), os.getcwd()]
        self.max_dir_history = 5
        self.command_history: Deque[str] = deque(maxlen=50)
        self.last_command: Optional[str] = None

    def _update_path_history(self, new_path: str) -> None:

        if not self.paths or self.paths[-1] != new_path:
            self.paths.append(new_path)
            if len(self.paths) > self.max_dir_history:
                self.paths.pop(0)

    def _add_to_command_history(self, command: str) -> None:

        command = command.strip()
        if command and not command.startswith(" ") and command != self.last_command:
            self.command_history.append(command)
            self.last_command = command

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
            os.chdir(os.path.expandvars(os.path.expanduser(target_dir)))
            self._update_path_history(os.getcwd())
            return True

        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return False

    def _show_command_history(self) -> None:
        for i, cmd in enumerate(self.command_history, 1):
            print(f"{i:4d}  {cmd}")

    def _execute_command(self, command: str) -> int:

        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                stdout=sys.stdout,
                stderr=sys.stderr,
                stdin=sys.stdin,
                text=True,
            )
            return result.returncode
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    def process_input(self, input_line: str) -> None:

        input_line = input_line.strip()
        if not input_line:
            return

        self._add_to_command_history(input_line)

        tokens = input_line.split()
        if tokens[0] == "cd":
            self._handle_cd(tokens)
        elif tokens[0] == "history":
            self._show_command_history()
        else:
            self._execute_command(input_line)

    def run(self) -> None:
        """Bucle principal"""
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
