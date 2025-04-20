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
        if len(history) >= MAX_HISTORY:
            history.pop(0)
        history.append(command)

def split_pipeline(command: str) -> List[str]:
    parts = []
    current = []
    in_quote = None
    escape = False
    
    for c in command:
        if escape:
            current.append(c)
            escape = False
        elif c == '\\':
            escape = True
            current.append(c)
        elif in_quote:
            current.append(c)
            if c == in_quote:
                in_quote = None
        elif c in ('"', "'"):
            in_quote = c
            current.append(c)
        elif c == '|' and not in_quote:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(c)
    
    if current:
        parts.append(''.join(current).strip())
    return parts

def handle_redirections(command: str) -> Tuple[List[str], Optional[str], Optional[str], str]:
    tokens = []
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()
    
    cmd_parts = []
    input_file = None
    output_file = None
    mode = 'w'
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        if token == '>>':
            if i + 1 < len(tokens):
                output_file = tokens[i+1]
                mode = 'a'
                i += 2
            else:
                print("Syntax error: no output file after '>>'", file=sys.stderr)
                return ([], None, None, 'w')
        elif token == '>':
            if i + 1 < len(tokens):
                output_file = tokens[i+1]
                mode = 'w'
                i += 2
            else:
                print("Syntax error: no output file after '>'", file=sys.stderr)
                return ([], None, None, 'w')
        elif token == '<':
            if i + 1 < len(tokens):
                input_file = tokens[i+1]
                i += 2
            else:
                print("Syntax error: no input file after '<'", file=sys.stderr)
                return ([], None, None, 'w')
        else:
            cmd_parts.append(token)
            i += 1
    
    return (cmd_parts, input_file, output_file, mode)

def execute_pipeline(commands: List[str]) -> int:
    processes = []
    prev_proc = None
    
    for i, cmd_str in enumerate(commands):
        cmd_parts, input_file, output_file, mode = handle_redirections(cmd_str)
        if not cmd_parts:
            return 1

        stdin_source = prev_proc.stdout if prev_proc else None
        stdout_dest = subprocess.PIPE if i < len(commands)-1 else sys.stdout

        try:
            if input_file:
                stdin_source = open(input_file, 'r')
            
            if output_file and i == len(commands)-1:
                stdout_dest = open(output_file, mode)
                
            proc = subprocess.Popen(
                cmd_parts,
                stdin=stdin_source,
                stdout=stdout_dest,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            processes.append(proc)
            
            if prev_proc:
                prev_proc.stdout.close()
            prev_proc = proc

        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return 1

    for proc in processes:
        proc.wait()
        if proc.stderr:
            for line in proc.stderr:
                print(line, file=sys.stderr, end='')

    return processes[-1].returncode if processes else 0

def execute_external(cmd_parts: List[str], input_file: Optional[str], output_file: Optional[str], mode: str) -> int:
    try:
        stdin = open(input_file, 'r') if input_file else None
        stdout = open(output_file, mode) if output_file else None
        
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

    if '|' in command:
        return execute_pipeline(split_pipeline(command))
    else:
        cmd_parts, input_file, output_file, mode = handle_redirections(command)
        if not cmd_parts:
            return 1
        if handle_internal(cmd_parts):
            return 0
        return execute_external(cmd_parts, input_file, output_file, mode)

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