import os
import subprocess
import shlex
import sys

history = []
background_jobs = []

def print_prompt():
 
    if sys.stdin.isatty():
        cwd = os.getcwd()
        sys.stdout.write(f'{cwd}$ ')
        sys.stdout.flush()

def update_history(command):
    command = command.strip()
    if not command or command.startswith(" "):
        return
    if not history or (history and history[-1] != command):
        history.append(command)
    if len(history) > 50:
        history.pop(0)

def show_history():
    for i, cmd in enumerate(history, start=1):
        print(f"{i} {cmd}")

def execute_history_command(token):
    if token == "!!":
        if not history:
            print("No commands in history.")
            return None
        return history[-1]
    elif token.startswith("!"):
        ref = token[1:]
        if ref.isdigit():
            idx = int(ref) - 1
            if 0 <= idx < len(history):
                return history[idx]
            else:
                print("No such command in history.")
        else:
            for cmd in reversed(history):
                if cmd.startswith(ref):
                    return cmd
            print("No such command in history.")
    return None

def change_directory(path):
    try:
        os.chdir(path)
    except FileNotFoundError:
        print(f"No such directory: {path}")

def run_in_background(command_tokens):
    try:
        proc = subprocess.Popen(command_tokens)
        background_jobs.append(proc)
        print(f"[{len(background_jobs)}] {proc.pid}")
    except FileNotFoundError:
        print(f"{command_tokens[0]}: command not found")

def list_jobs():
    for i, proc in enumerate(background_jobs):
        if proc.poll() is None:
            print(f"[{i+1}] Running PID: {proc.pid}")
        else:
            print(f"[{i+1}] Done PID: {proc.pid}")

def bring_fg():
    for i, proc in enumerate(background_jobs):
        if proc.poll() is None:
            print(f"Bringing PID {proc.pid} to foreground...")
            proc.wait()
            background_jobs.pop(i)
            return
    print("No background jobs.")

def parse_command(command):
    command = command.strip()
    if not command:
        return []
    return shlex.split(command)

def execute_pipeline(commands, background=False):
    processes = []
    prev_stdout = None


    last_command = commands[-1].rstrip('&').strip()
    tokens = parse_command(last_command)
    cmd, redir_out, append = [], None, False
    i = 0
    while i < len(tokens):
        if tokens[i] in ('>', '>>'):
            append = tokens[i] == '>>'
            if i+1 < len(tokens):
                redir_out = tokens[i+1]
                i += 2
            else:
                i += 1
        else:
            cmd.append(tokens[i])
            i += 1
    if redir_out:
        commands[-1] = ' '.join(cmd)

    for i, cmd in enumerate(commands):
        cmd = cmd.strip()
        tokens = parse_command(cmd)
        stdin = prev_stdout if prev_stdout else None
        stdout = subprocess.PIPE if i < len(commands)-1 else None


        if i == len(commands)-1 and redir_out:
            try:
                stdout = open(redir_out, 'a' if append else 'w')
            except IOError as e:
                print(f"Error: {e}")
                return

        try:
            proc = subprocess.Popen(tokens, stdin=stdin, stdout=stdout)
        except FileNotFoundError:
            print(f"{tokens[0]}: command not found")
            return

        if prev_stdout:
            prev_stdout.close()
        prev_stdout = proc.stdout if stdout == subprocess.PIPE else None
        processes.append(proc)

    if not background:
        for p in processes:
            p.wait()
        if redir_out and stdout:
            stdout.close()
    else:
        background_jobs.append(processes[-1])

def redirect_input_output(tokens):
    cmd = []
    input_file = None
    output_file = None
    append = False

    i = 0
    while i < len(tokens):
        if tokens[i] == '>':
            output_file = tokens[i + 1]
            i += 2
        elif tokens[i] == '>>':
            output_file = tokens[i + 1]
            append = True
            i += 2
        elif tokens[i] == '<':
            input_file = tokens[i + 1]
            i += 2
        else:
            cmd.append(tokens[i])
            i += 1

    stdin = open(input_file, 'r') if input_file else None
    mode = 'a' if append else 'w'
    stdout = open(output_file, mode) if output_file else None

    try:

        if not output_file and not input_file:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
            if proc.stdout:
                print(proc.stdout.strip())
        else:
            subprocess.run(cmd, stdin=stdin, stdout=stdout)
    except FileNotFoundError:
        print(f"{cmd[0]}: command not found")
    finally:
        if stdin: stdin.close()
        if stdout: stdout.close()

def process_command(command_line):
    command_line = command_line.strip()
    if not command_line:
        return

    if command_line.startswith("!"):
        new_command = execute_history_command(command_line)
        if new_command:
            process_command(new_command)
        return

    update_history(command_line)

    if '|' in command_line:
        segments = [seg.strip() for seg in command_line.split('|')]
        background = segments[-1].endswith('&')
        if background:
            segments[-1] = segments[-1][:-1].strip()
        execute_pipeline(segments, background)
        return

    tokens = parse_command(command_line)
    if not tokens:
        return

    if tokens[0] == 'cd':
        change_directory(tokens[1] if len(tokens) > 1 else os.path.expanduser("~"))
    elif tokens[0] == 'history':
        show_history()
    elif tokens[0] == 'jobs':
        list_jobs()
    elif tokens[0] == 'fg':
        bring_fg()
    elif '>' in tokens or '>>' in tokens or '<' in tokens:
        redirect_input_output(tokens)
    elif tokens[-1] == '&':
        run_in_background(tokens[:-1])
    else:
        try:

            proc = subprocess.run(tokens, stdout=subprocess.PIPE, text=True)
            if proc.stdout:
                print(proc.stdout.strip())
        except FileNotFoundError:
            print(f"{tokens[0]}: command not found")

def main():
    while True:
        try:
            print_prompt()
            command = sys.stdin.readline()
            if not command:
                break
            command = command.strip()
            if command in ["exit", "quit"]:
                break
            process_command(command)
        except KeyboardInterrupt:
            if sys.stdin.isatty():
                print()  
            break

if __name__ == "__main__":
    main()