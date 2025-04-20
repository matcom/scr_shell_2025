#!/usr/bin/env python3
import os
import sys
import subprocess
import shlex
from typing import List, Optional, Tuple

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
        print("\nExit")
        sys.exit(0)
    except KeyboardInterrupt:
        return ""

def add_to_history(command: str) -> None:
    if command and (not history or command != history[-1]):
        history.append(command)
        if len(history) > MAX_HISTORY:
            history.pop(0)

def split_pipeline(command: str) -> List[str]:
    parts = []
    current = []
    in_quote = None
    for c in command:
        if c == in_quote:
            in_quote = None
        elif c in ('"', "'"):
            in_quote = c
        elif c == '|' and not in_quote:
            parts.append(''.join(current).strip())
            current = []
            continue
        current.append(c)
    parts.append(''.join(current).strip())
    return parts

def handle_redirections(command: str) -> Tuple[List[str], Optional[str], Optional[str], str]:
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()
    
    cmd_parts = []
    input_file, output_file, mode = None, None, 'w'
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token == '>>':
            output_file = tokens[i+1] if i+1 < len(tokens) else None
            mode = 'a'
            i += 2
        elif token == '>':
            output_file = tokens[i+1] if i+1 < len(tokens) else None
            mode = 'w'
            i += 2
        elif token == '<':
            input_file = tokens[i+1] if i+1 < len(tokens) else None
            i += 2
        else:
            cmd_parts.append(token)
            i += 1
    return cmd_parts, input_file, output_file, mode

def execute_pipeline(commands: List[str]) -> int:
    processes = []
    prev_proc = None
    for cmd_str in commands:
        cmd_parts, input_file, output_file, mode = handle_redirections(cmd_str)
        stdin = prev_proc.stdout if prev_proc else None
        stdout = subprocess.PIPE if cmd_str != commands[-1] else sys.stdout
        
        if input_file:
            stdin = open(input_file, 'r')
        if output_file and cmd_str == commands[-1]:
            stdout = open(output_file, mode)
        
        proc = subprocess.Popen(
            cmd_parts,
            stdin=stdin,
            stdout=stdout,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        processes.append(proc)
        if prev_proc:
            prev_proc.stdout.close()
        prev_proc = proc
    
    for proc in processes:
        proc.wait()
        if proc.stderr:
            for line in proc.stderr:
                print(line, file=sys.stderr, end='')
    
    return processes[-1].returncode if processes else 0

def execute_external(cmd_parts: List[str], input_file: Optional[str], output_file: Optional[str], mode: str) -> int:
    stdin = open(input_file, 'r') if input_file else None
    stdout = open(output_file, mode) if output_file else None
    try:
        proc = subprocess.run(
            cmd_parts,
            stdin=stdin or sys.stdin,
            stdout=stdout or sys.stdout,
            stderr=sys.stderr,
            check=True
        )
        return proc.returncode
    except FileNotFoundError:
        print(f"{cmd_parts[0]}: command not found", file=sys.stderr)
        return 127
    except subprocess.CalledProcessError as e:
        return e.returncode
    finally:
        if stdin: stdin.close()
        if stdout: stdout.close()

def handle_internal(cmd_parts: List[str]) -> bool:
    if not cmd_parts:
        return True
    if cmd_parts[0] == "cd":
        path = cmd_parts[1] if len(cmd_parts) > 1 else os.getenv("HOME", "")
        try:
            os.chdir(path)
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return False
        return True
    if cmd_parts[0] == "history":
        for i, cmd in enumerate(history[-MAX_HISTORY:], 1):
            print(f"{i}\t{cmd}")
        return True
    return False

def process_command(command: str) -> int:
    if not command:
        return 0
    add_to_history(command)
    return_code = 0
    
    # Manejar múltiples comandos separados por ;
    for sub_cmd in command.split(';'):
        sub_cmd = sub_cmd.strip()
        if not sub_cmd:
            continue
        
        if '|' in sub_cmd:
            rc = execute_pipeline(split_pipeline(sub_cmd))
        else:
            cmd_parts, input_file, output_file, mode = handle_redirections(sub_cmd)
            if not cmd_parts:
                rc = 1
            elif handle_internal(cmd_parts):
                rc = 0
            else:
                rc = execute_external(cmd_parts, input_file, output_file, mode)
        
        if rc != 0:
            return_code = rc
    
    return return_code

def main() -> None:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            history.extend(line.strip() for line in f.readlines()[-MAX_HISTORY:])
    
    try:
        while True:
            print_prompt()
            command = read_command()
            return_code = process_command(command)
            if not INTERACTIVE:
                sys.exit(return_code)
    finally:
        with open(HISTORY_FILE, "w") as f:
            f.write("\n".join(history[-MAX_HISTORY:]))

if __name__ == "__main__":
    main()