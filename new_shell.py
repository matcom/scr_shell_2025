import os
import sys
import shlex
import subprocess
import signal
import re
from collections import deque

COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
}


class Shell:
    def __init__(self, use_colors=True):
        self.use_colors = use_colors
        self.HISTORY_SIZE = 50
        self.history = deque(maxlen=self.HISTORY_SIZE)
        self.background_jobs = []
        signal.signal(signal.SIGINT, self.signal_handler)

    def color(self, text, color_name):
        if not self.use_colors or not sys.stdout.isatty():
            return text
        return f"{COLORS.get(color_name, '')}{text}{COLORS['RESET']}"

    def signal_handler(self, signum, frame):
        print("\nSaliendo del shell...")
        sys.exit(0)

    def normalize_input(self, input_line):
        try:
            return " ".join(shlex.split(input_line))
        except ValueError:
            return ""

    def update_history(self, command):
        if not command or command.startswith(" "):
            return
        if len(self.history) == 0 or self.history[-1] != command:
            self.history.append(command)

    def expand_history_references(self, command_line):
        def replacer(match):
            token = match.group(0)
            if token == "!!":
                if self.history:
                    return self.history[-1]
                else:
                    print("No hay comandos en el historial.")
                    return ""
            elif token[1:].isdigit():
                idx = int(token[1:]) - 1
                if 0 <= idx < len(self.history):
                    return list(self.history)[idx]
                else:
                    print("No existe ese comando en el historial.")
                    return ""
            else:
                prefix = token[1:]
                matches = [cmd for cmd in self.history if cmd.startswith(prefix)]
                if matches:
                    return matches[-1]
                else:
                    print(
                        f"No hay comandos que comiencen con '{prefix}' en el historial."
                    )
                    return ""

        pattern = r"!\w+|!!"
        expanded_line = re.sub(pattern, replacer, command_line)
        if expanded_line != command_line:
            print(f"Comando expandido: {expanded_line}")
        return expanded_line

    def check_background_jobs(self):
        finished_jobs = []
        for pid, cmd in self.background_jobs:
            try:
                result = subprocess.run(
                    f"ps -p {pid} > /dev/null",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if result.returncode != 0:
                    finished_jobs.append((pid, cmd))
            except subprocess.SubprocessError:
                finished_jobs.append((pid, cmd))

        for job in finished_jobs:
            if job in self.background_jobs:
                self.background_jobs.remove(job)
                print(f"Proceso en background terminado: {job[1]} (PID: {job[0]})")

    def execute_command(self, command, background=False):
        try:
            if background:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                self.background_jobs.append((process.pid, command))
                print(
                    f"[{len(self.background_jobs)}] {process.pid} ejecutándose en background"
                )
                return None
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.stdout:
                    print(result.stdout, end="")
                if result.stderr:
                    print(result.stderr, end="", file=sys.stderr)
                return result.returncode
        except Exception as e:
            print(f"Error al ejecutar comando: {e}")
            return None

    def handle_redirection(self, command):
        return command

    def run_piped_commands(self, commands, background=False):
        if not commands:
            return

        full_command = " | ".join(commands)
        return self.execute_command(full_command, background)

    def run_command(self, command_line, s):
        command_line = self.normalize_input(command_line)
        if not command_line:
            return

        background = command_line.endswith("&")
        if background:
            command_line = command_line[:-1].strip()

        command_line = self.expand_history_references(command_line)
        if not command_line:
            return

        self.update_history(s)

        if command_line == "history":
            for idx, cmd in enumerate(self.history, 1):
                print(f"{idx} {cmd}")
            return

        if command_line == "jobs":
            self.check_background_jobs()
            for i, (pid, cmd) in enumerate(self.background_jobs, 1):
                print(f"[{i}] {pid} {cmd}")
            return

        if command_line.startswith("fg"):
            if not self.background_jobs:
                print("No hay trabajos en background")
                return

            job_num = command_line[2:].strip()
            if not job_num:
                pid, cmd = self.background_jobs.pop(0)
            else:
                try:
                    job_num = int(job_num)
                    if 1 <= job_num <= len(self.background_jobs):
                        pid, cmd = self.background_jobs.pop(job_num - 1)
                    else:
                        print(f"Número de trabajo inválido: {job_num}")
                        return
                except ValueError:
                    print(f"Número de trabajo inválido: {job_num}")
                    return

            print(f"Ejecutando en foreground: {cmd}")
            result = subprocess.run(
                f"wait {pid}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            return

        commands = [cmd.strip() for cmd in command_line.split("|") if cmd.strip()]
        if commands:
            self.run_piped_commands(commands, background)

    def run(self):
        while True:
            try:
                self.check_background_jobs()
                cwd = os.getcwd()
                prompt = f"{os.path.basename(cwd)}:$ "
                command_line = input(prompt)

                if command_line.strip() == "exit":
                    print("Saliendo del shell...")
                    break

                if command_line.startswith("cd"):
                    parts = command_line.split()
                    if len(parts) > 1:
                        try:
                            os.chdir(parts[1])
                        except FileNotFoundError:
                            print(f"Directorio no encontrado: {parts[1]}")
                        except Exception as e:
                            print(f"Error al cambiar de directorio: {e}")
                    else:
                        os.chdir(os.path.expanduser("~"))
                    continue

                self.run_command(command_line, command_line)

            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print()
                break


if __name__ == "__main__":
    shell = Shell(use_colors=False)
    shell.run()
