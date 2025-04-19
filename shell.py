#!/usr/bin/env python3
import os
import sys
import subprocess
from typing import List, Optional

MAX_HISTORY = 50
HISTORY_FILE = os.path.expanduser("~/.shell_history")
history: List[str] = []

INTERACTIVE = sys.stdin.isatty()

def print_prompt() -> None:
    if INTERACTIVE:
        print("$ ", end="", flush=True)

def read_command() -> str:
    try:
        return input().strip()
    except EOFError:
        sys.exit(0)
    except KeyboardInterrupt:
        return ""

def add_to_history(command: str) -> None:
    if command and (not history or command != history[-1]):
        if len(history) >= MAX_HISTORY:
            history.pop(0)
        history.append(command)

def handle_redirections(command: str) -> tuple:
    input_file = None
    output_file = None
    mode = "w"

    if '>>' in command:
        command, output_file = command.split('>>', 1)
        mode = "a"
    elif '>' in command:
        command, output_file = command.split('>', 1)
        mode = "w"

    if '<' in command:
        command, input_file = command.split('<', 1)

    return command.strip(), input_file.strip() if input_file else None, output_file.strip() if output_file else None, mode

def execute_pipeline(commands: List[str]) -> None:
    processes = []
    prev_proc = None
    open_files = []

    for i, raw_cmd in enumerate(commands):
        cmd, input_file, output_file, mode = handle_redirections(raw_cmd)
        cmd_parts = cmd.strip().split()

        stdin = None
        if input_file:
            stdin = open(input_file, "r")
            open_files.append(stdin)
        elif prev_proc:
            stdin = prev_proc.stdout

        stdout = None
        if i == len(commands) - 1:
            if output_file:
                stdout = open(output_file, mode)
                open_files.append(stdout)
        else:
            stdout = subprocess.PIPE

        proc = subprocess.Popen(cmd_parts, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE)
        processes.append(proc)
        if prev_proc and prev_proc.stdout:
            prev_proc.stdout.close()
        prev_proc = proc

    for proc in processes:
        proc.wait()

    for f in open_files:
        f.close()

def execute_external(cmd_parts: List[str], input_file: Optional[str], output_file: Optional[str], mode: str) -> None:
    input_fd = open(input_file, "r") if input_file else None
    output_fd = open(output_file, mode) if output_file else None

    try:
        subprocess.run(
            cmd_parts,
            stdin=input_fd or sys.stdin,
            stdout=output_fd or sys.stdout,
            stderr=sys.stderr,
            check=True
        )
    except FileNotFoundError:
        print(f"{cmd_parts[0]}: comando no encontrado", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar {cmd_parts[0]} (código {e.returncode})", file=sys.stderr)
    finally:
        if input_fd:
            input_fd.close()
        if output_fd:
            output_fd.close()

def handle_internal(command: List[str]) -> bool:
    if not command:
        return True
    if command[0] == "cd":
        try:
            os.chdir(command[1] if len(command) > 1 else os.environ["HOME"])
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
        return True
    if command[0] == "history":
        for i, cmd in enumerate(history[-MAX_HISTORY:], start=1):
            print(f"{i} {cmd}")
        return True
    return False

def process_command(command: str) -> None:
    if not command:
        return

    add_to_history(command)

    if '|' in command:
        execute_pipeline([segment.strip() for segment in command.split('|')])
        return

    cmd_str, input_file, output_file, mode = handle_redirections(command)
    cmd_parts = cmd_str.split()

    if handle_internal(cmd_parts):
        return

    execute_external(cmd_parts, input_file, output_file, mode)

def main() -> None:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history.extend(line.strip() for line in f.readlines()[-MAX_HISTORY:])

    try:
        while True:
            print_prompt()
            command = read_command()
            process_command(command)
    finally:
        with open(HISTORY_FILE, "w") as f:
            f.write("\n".join(history[-MAX_HISTORY:]))

if __name__ == "__main__":
    main()
