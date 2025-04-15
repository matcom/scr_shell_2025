#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import signal
from typing import List, Dict

MAX_HISTORY = 50
history: List[str] = []
background_jobs: List[Dict] = []  


def print_prompt():
    print("$ ", end="", flush=True)

def read_input() -> str:
    try:
        return input().strip()
    except EOFError: 
        print("\nExit")
        sys.exit(0)
    except KeyboardInterrupt:  
        return ""

def preprocess_input(input_line: str) -> str:
    if input_line.startswith("!"):
        if input_line == "!!":
            return history[-1] if history else ""
        elif input_line[1:].isdigit():
            idx = int(input_line[1:]) - 1
            return history[idx] if 0 <= idx < len(history) else ""
        else:
            search = input_line[1:]
            for cmd in reversed(history):
                if cmd.startswith(search):
                    return cmd
            print(f"Comando no encontrado: {input_line}", file=sys.stderr)
            return ""
    return input_line

def update_history(cmd: str):
    if cmd.startswith(" ") or (history and history[-1] == cmd):
        return
    if len(history) >= MAX_HISTORY:
        history.pop(0)
    history.append(cmd)

def handle_cd(path: str):
    try:
        os.chdir(path or os.environ["HOME"])
    except Exception as e:
        print(f"cd: {e}", file=sys.stderr)

def print_history():
    start = max(0, len(history) - MAX_HISTORY)
    for i, cmd in enumerate(history[start:], start=start+1):
        print(f"{i} {cmd}")

def print_jobs():
    for idx, job in enumerate(background_jobs):
        print(f"[{idx+1}] {job['cmd']} (PID: {job['pid']})")

def handle_fg(job_num: str):
    if not job_num:
        print("fg: falta número de job", file=sys.stderr)
        return
    try:
        idx = int(job_num) - 1
        job = background_jobs[idx]
        os.waitpid(job["pid"], 0)
        del background_jobs[idx]
    except (ValueError, IndexError):
        print("fg: job inválido", file=sys.stderr)

def parse_command(cmd: str) -> List[str]:
    return re.split(r'\s+', cmd.strip())

def split_pipe_commands(parts: List[str]) -> List[List[str]]:
    commands = []
    current = []
    for part in parts:
        if part == "|":
            commands.append(current)
            current = []
        else:
            current.append(part)
    commands.append(current)
    return commands

def parse_redirections(parts: List[str]):
    stdin = None
    stdout = None
    stderr = None
    i = 0
    while i < len(parts):
        if parts[i] == "<":
            stdin = open(parts[i+1], "r")
            del parts[i:i+2]
        elif parts[i] == ">":
            stdout = open(parts[i+1], "w")
            del parts[i:i+2]
        elif parts[i] == ">>":
            stdout = open(parts[i+1], "a")
            del parts[i:i+2]
        elif parts[i] == "2>":
            stderr = open(parts[i+1], "w")
            del parts[i:i+2]
        else:
            i += 1
    return stdin, stdout, stderr

def execute_pipes(commands: List[List[str]]):
    prev_pipe = None
    processes = []
    for i, cmd in enumerate(commands):
        stdin = prev_pipe if prev_pipe else None
        stdout = subprocess.PIPE if i < len(commands)-1 else None
        process = subprocess.Popen(
            cmd,
            stdin=stdin,
            stdout=stdout,
            stderr=None,
            text=True
        )
        processes.append(process)
        if prev_pipe:
            prev_pipe.close()
        prev_pipe = process.stdout
    for p in processes:
        p.wait()

def execute_single_command(parts, stdin, stdout, stderr, original_cmd, in_background):
    process = subprocess.Popen(
        parts,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        text=True
    )
    if in_background:
        background_jobs.append({"pid": process.pid, "cmd": original_cmd})
    else:
        process.wait()

def process_command(cmd: str):
    parts = parse_command(cmd)
    if not parts:
        return
    if parts[0] == "cd":
        handle_cd(parts[1] if len(parts) > 1 else None)
    elif parts[0] == "exit":
        sys.exit(0)
    elif parts[0] == "history":
        print_history()
    elif parts[0] == "jobs":
        print_jobs()
    elif parts[0] == "fg":
        handle_fg(parts[1] if len(parts) > 1 else None)
    else:
        try:
            if "|" in parts:
                commands = split_pipe_commands(parts)
                execute_pipes(commands)
            else:
                in_background = "&" in parts
                if in_background:
                    parts.remove("&")
                stdin, stdout, stderr = parse_redirections(parts)
                execute_single_command(parts, stdin, stdout, stderr, cmd, in_background)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

def handle_sigint(sig, frame):
    print("\n$ ", end="", flush=True)

def main():
    signal.signal(signal.SIGINT, handle_sigint)
    while True:
        print_prompt()
        input_line = read_input()
        if not input_line:
            continue
        input_line = preprocess_input(input_line)
        if not input_line:
            continue
        update_history(input_line)
        process_command(input_line)

if __name__ == "__main__":
    main()