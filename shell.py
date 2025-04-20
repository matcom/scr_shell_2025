import os
import subprocess
import shlex
import sys
import re
import io

history = []
background_jobs = []
HISTORY_MAX_SIZE = 50

def print_prompt():
    cwd = os.getcwd()
    sys.stdout.write(f'{cwd}$ ')
    sys.stdout.flush()

def update_history(command):
    stripped = command.strip()
    if not stripped or stripped.startswith(" "):
        return
    if history and history[-1] == stripped:
        return
    history.append(stripped)
    if len(history) > HISTORY_MAX_SIZE:
        del history[0]

def show_history():
    for i, cmd in enumerate(history, 1):
        print(f"{i:3}  {cmd}")

def execute_history_command(token):
    if token == "!!":
        return history[-1] if history else None
    if token.startswith("!"):
        try:
            index = int(token[1:]) - 1
            if 0 <= index < len(history):
                return history[index]
            print("No such command in history")
            return None
        except ValueError:
            for cmd in reversed(history):
                if cmd.startswith(token[1:]):
                    return cmd
            print("No such command in history")
            return None
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

def parse_redirections(tokens):
    input_file = None
    output_file = None
    append = False
    cmd = []
    i = 0

    while i < len(tokens):
        if tokens[i] == '<':
            if i + 1 < len(tokens):
                input_file = tokens[i + 1]
                i += 2
        elif tokens[i] == '>':
            if i + 1 < len(tokens):
                output_file = tokens[i + 1]
                i += 2
        elif tokens[i] == '>>':
            if i + 1 < len(tokens):
                output_file = tokens[i + 1]
                append = True
                i += 2
        else:
            cmd.append(tokens[i])
            i += 1

    return cmd, output_file, input_file, append

def execute_command(tokens):
    if not tokens:
        return
    
    cmd, output_file, input_file, append = parse_redirections(tokens)
    if not cmd:
        print("Error: comando vacío")
        return
    
    stdin_file = None
    stdout_file = None
    
    try:
        if input_file:
            stdin_file = open(input_file, 'r')
        if output_file:
            mode = 'a' if append else 'w'
            stdout_file = open(output_file, mode)

        proceso = subprocess.run(
            cmd,
            stdin=stdin_file,
            stdout=stdout_file if output_file else None,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if proceso.returncode != 0 and proceso.stderr:
            print(proceso.stderr.strip(), file=sys.stderr)
            
    except FileNotFoundError:
        print(f"{cmd[0]}: command not found", file=sys.stderr)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        if stdin_file and not stdin_file.closed:
            stdin_file.close()
        if stdout_file and not stdout_file.closed:
            stdout_file.close()

def execute_pipeline(segments, background=False):
    processes = []
    prev_out = None
    last_output_redir = None

    if segments:
        last_segment = segments[-1]
        tokens = parse_command(last_segment)
        if tokens:
            cmd, output_file, _, append = parse_redirections(tokens)
            if output_file:
                last_output_redir = (output_file, append)
                segments[-1] = ' '.join(cmd)

    for i, segment in enumerate(segments):
        tokens = parse_command(segment)
        if not tokens:
            return

        stdin = prev_out if prev_out else None
        stdout = subprocess.PIPE if i < len(segments)-1 else None

        if i == len(segments)-1 and last_output_redir:
            output_file, append = last_output_redir
            try:
                mode = 'a' if append else 'w'
                stdout = open(output_file, mode)
            except IOError as e:
                print(f"Error opening file: {e}")
                return

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
        prev_out = proc.stdout if stdout == subprocess.PIPE else None
        processes.append(proc)

    if background:
        background_jobs.append(processes[-1])
    else:
        for p in processes:
            p.wait()
        if last_output_redir and isinstance(stdout, io.TextIOWrapper):
            stdout.close()

def process_command(command_line):
    command_line = normalize_command(command_line.strip())
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
    elif tokens[-1] == '&':
        run_background(tokens[:-1])
    else:
        execute_command(tokens)

def normalize_command(command):
    command = re.sub(r'(\S)(>>?|<)', r'\1 \2', command)
    command = re.sub(r'(>>?|<)(\S)', r'\1 \2', command)
    return command

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
    interactive = sys.stdin.isatty()
    
    while True:
        try:
            cmd_lines = []
            if interactive:
                print_prompt()
                
            while True:
                line = sys.stdin.readline()
                if not line:
                    raise EOFError
                cmd_lines.append(line.strip())
                full_cmd = ' '.join(cmd_lines)
                
                if is_balanced(full_cmd):
                    break
                    
                if interactive:
                    sys.stdout.write('> ')
                    sys.stdout.flush()

            command = normalize_command(' '.join(cmd_lines))
            if command.lower() in ('exit', 'quit'):
                break
                
            process_command(command)
            
        except EOFError:
            if interactive:
                print()
            break
        except KeyboardInterrupt:
            if interactive:
                print("\nUse 'exit' to quit")
            else:
                break

if __name__ == "__main__":
    main()