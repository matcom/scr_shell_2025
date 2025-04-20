import os
import subprocess
import shlex
import sys
from collections import deque

history = deque(maxlen=50)
background_jobs = []

def print_prompt():
    cwd = os.getcwd()
    sys.stdout.write(f'{cwd}$ ')
    sys.stdout.flush()

def update_history(command):
    stripped = command.strip()
    if stripped and (not history or history[-1] != stripped):
        history.append(stripped)

def show_history():
    for i, cmd in enumerate(history, 1):
        print(f"{i:3}  {cmd}")

def execute_history_command(token):
    if token == "!!":
        return history[-1] if history else None
    if token.startswith("!"):
        try:
            index = int(token[1:]) - 1
            return history[index] if 0 <= index < len(history) else None
        except ValueError:
            for cmd in reversed(history):
                if cmd.startswith(token[1:]):
                    return cmd
    return None

def change_directory(path):
    try:
        if not path:
            path = os.path.expanduser("~")
        os.chdir(path)
    except Exception as e:
        print(f"cd: {e}")

def run_background(command):
    try:
        proc = subprocess.Popen(command)
        background_jobs.append(proc)
        print(f"[{len(background_jobs)}] {proc.pid}")
    except FileNotFoundError:
        print(f"{command[0]}: command not found")

def list_jobs():
    for i, proc in enumerate(background_jobs, 1):
        status = "Running" if proc.poll() is None else "Done"
        print(f"[{i}] {status} PID: {proc.pid}")

def bring_foreground():
    for i, proc in enumerate(background_jobs):
        if proc.poll() is None:
            proc.wait()
            background_jobs.pop(i)
            return
    print("No background jobs")

def parse_command(command):
    try:
        return shlex.split(command, posix=True)
    except ValueError as e:
        print(f"Syntax error: {e}")
        return None

def execute_redirection(tokens):
    stdin = stdout = None
    cmd = []
    input_file = output_file = None
    append = False
    
    i = 0
    while i < len(tokens):
        if tokens[i] in ('>', '>>', '<'):
            if i+1 >= len(tokens):
                print(f"Syntax error near {tokens[i]}")
                return False
            
            if tokens[i] == '<':
                input_file = tokens[i+1]
            else:
                output_file = tokens[i+1]
                append = (tokens[i] == '>>')
            i += 2
        else:
            cmd.append(tokens[i])
            i += 1

    try:
        if input_file:
            stdin = open(input_file, 'r')
        if output_file:
            stdout = open(output_file, 'a' if append else 'w')
            
        subprocess.run(cmd, stdin=stdin, stdout=stdout, check=True)
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        for f in (stdin, stdout):
            if f: f.close()
    return True

def execute_pipeline(segments, background=False):
    processes = []
    prev_out = None
    
    for i, segment in enumerate(segments):
        tokens = parse_command(segment)
        if not tokens:
            return
            
        stdin = prev_out if prev_out else None
        stdout = subprocess.PIPE if i < len(segments)-1 else None
        
        try:
            proc = subprocess.Popen(
                tokens,
                stdin=stdin,
                stdout=stdout,
                text=True
            )
        except FileNotFoundError:
            print(f"{tokens[0]}: command not found")
            return
            
        if prev_out:
            prev_out.close()
        prev_out = proc.stdout if stdout else None
        processes.append(proc)

    if background:
        background_jobs.append(processes[-1])
    else:
        for p in processes:
            p.wait()

def process_command(command_line):
    command_line = command_line.strip()
    if not command_line:
        return

    if command_line.startswith("!"):
        cmd = execute_history_command(command_line)
        if cmd:
            process_command(cmd)
        return

    update_history(command_line)

    if '|' in command_line:
        segments = [s.strip() for s in command_line.split('|')]
        bg = segments[-1].endswith('&')
        if bg:
            segments[-1] = segments[-1][:-1].strip()
        execute_pipeline(segments, bg)
        return

    tokens = parse_command(command_line)
    if not tokens:
        return

    if tokens[0] == 'cd':
        change_directory(tokens[1] if len(tokens) > 1 else None)
    elif tokens[0] == 'history':
        show_history()
    elif tokens[0] == 'jobs':
        list_jobs()
    elif tokens[0] == 'fg':
        bring_foreground()
    elif '>' in tokens or '>>' in tokens or '<' in tokens:
        execute_redirection(tokens)
    elif tokens[-1] == '&':
        run_background(tokens[:-1])
    else:
        try:
            subprocess.run(tokens)
        except FileNotFoundError:
            print(f"{tokens[0]}: command not found")

def is_balanced(command):
    quote = None
    escape = False
    for c in command:
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
        elif c in ('"', "'"):
            if quote == c:
                quote = None
            elif not quote:
                quote = c
    return quote is None

def main():
    while True:
        try:
            cmd_lines = []
            print_prompt()
            while True:
                line = sys.stdin.readline()
                if not line:
                    raise EOFError
                cmd_lines.append(line.strip())
                full_cmd = ' '.join(cmd_lines)
                if is_balanced(full_cmd):
                    break
                sys.stdout.write('> ')
                sys.stdout.flush()
                
            command = ' '.join(cmd_lines)
            if command.lower() in ('exit', 'quit'):
                break
            process_command(command)
            
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit")

if __name__ == "__main__":
    main()