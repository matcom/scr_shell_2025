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
            if c == in_quote:
                in_quote = None
            current.append(c)
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

def handle_redirections(command: str) -> Tuple[Optional[List[str]], Optional[str], Optional[str], str]:
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        print(f"Syntax error: {e}", file=sys.stderr)
        return (None, None, None, 'w')
    
    cmd_parts = []
    input_file = None
    output_file = None
    mode = 'w'
    i = 0
    
    while i < len(tokens):
        token = tokens[i]
        if token == '>>':
            if i + 1 >= len(tokens):
                print("Syntax error: no output file after '>>'", file=sys.stderr)
                return (None, None, None, 'w')
            output_file = tokens[i+1]
            mode = 'a'
            i += 2
        elif token == '>':
            if i + 1 >= len(tokens):
                print("Syntax error: no output file after '>'", file=sys.stderr)
                return (None, None, None, 'w')
            output_file = tokens[i+1]
            mode = 'w'
            i += 2
        elif token == '<':
            if i + 1 >= len(tokens):
                print("Syntax error: no input file after '<'", file=sys.stderr)
                return (None, None, None, 'w')
            input_file = tokens[i+1]
            i += 2
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

        stdin_source = None
        if input_file:
            try:
                stdin_source = open(input_file, 'r')
            except FileNotFoundError:
                print(f"Input file not found: {input_file}", file=sys.stderr)
                return 1
        elif prev_proc:
            stdin_source = prev_proc.stdout

        stdout_dest = subprocess.PIPE
        if output_file and i == len(commands) - 1:
            try:
                stdout_dest = open(output_file, mode)
            except OSError as e:
                print(f"Error opening output file: {e}", file=sys.stderr)
                return 1

        try:
            proc = subprocess.Popen(
                cmd_parts,
                stdin=stdin_source,
                stdout=stdout_dest,
                stderr=subprocess.PIPE
            )
        except FileNotFoundError:
            print(f"{cmd_parts[0]}: command not found", file=sys.stderr)
            return 127

        processes.append(proc)
        if prev_proc and prev_proc.stdout:
            prev_proc.stdout.close()
        prev_proc = proc

    for proc in processes[:-1]:
        proc.wait()
        if proc.stderr:
            err_output = proc.stderr.read().decode()
            if err_output:
                print(err_output, file=sys.stderr)

    final_proc = processes[-1]
    final_proc.wait()
    
    if final_proc.stderr:
        err_output = final_proc.stderr.read().decode()
        if err_output:
            print(err_output, file=sys.stderr)

    if final_proc.stdout and hasattr(final_proc.stdout, 'close'):
        final_proc.stdout.close()

    return final_proc.returncode

def execute_external(cmd_parts: List[str], input_file: Optional[str], output_file: Optional[str], mode: str) -> int:
    stdin = None
    stdout = None
    
    try:
        if input_file:
            stdin = open(input_file, 'r')
    except FileNotFoundError:
        print(f"Input file not found: {input_file}", file=sys.stderr)
        return 1

    try:
        if output_file:
            stdout = open(output_file, mode)
    except OSError as e:
        print(f"Error opening output file: {e}", file=sys.stderr)
        if stdin:
            stdin.close()
        return 1

    try:
        proc = subprocess.run(
            cmd_parts,
            stdin=stdin or sys.stdin,
            stdout=stdout or sys.stdout,
            stderr=sys.stderr
        )
        return proc.returncode
    except FileNotFoundError:
        print(f"{cmd_parts[0]}: command not found", file=sys.stderr)
        return 127
    finally:
        if stdin:
            stdin.close()
        if stdout:
            stdout.close()

def handle_internal(cmd_parts: List[str]) -> bool:
    if not cmd_parts:
        return True
    
    if cmd_parts[0] == "cd":
        if len(cmd_parts) > 2:
            print("cd: too many arguments", file=sys.stderr)
            return True
        
        path = cmd_parts[1] if len(cmd_parts) >= 2 else os.environ.get("HOME", "")
        try:
            os.chdir(path)
        except FileNotFoundError:
            print(f"cd: directory not found: {path}", file=sys.stderr)
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
        return True
    
    if cmd_parts[0] == "history":
        if len(cmd_parts) > 1:
            print("history: too many arguments", file=sys.stderr)
            return True
        
        for i, cmd in enumerate(history[-MAX_HISTORY:], start=1):
            print(f"{i} {cmd}")
        return True
    
    return False

def process_command(command: str) -> int:
    if not command:
        return 0

    add_to_history(command)

    pipeline_commands = split_pipeline(command)
    if len(pipeline_commands) > 1:
        return execute_pipeline(pipeline_commands)
    else:
        cmd_str = pipeline_commands[0]
        cmd_parts, input_file, output_file, mode = handle_redirections(cmd_str)
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