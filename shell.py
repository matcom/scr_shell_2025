import os
import subprocess
import shlex
import sys
import io

history = []
background_jobs = []
HISTORY_MAX = 50

def print_prompt():
    if sys.stdin.isatty():
        cwd = os.getcwd()
        sys.stdout.write(f'{cwd}$ ')
        sys.stdout.flush()

def update_history(command):
    cmd = command.strip()
    if cmd and (not history or history[-1] != cmd):
        history.append(cmd)
        if len(history) > HISTORY_MAX:
            del history[0]

def show_history():
    for i, cmd in enumerate(history, 1):
        print(f"{i} {cmd}")

def execute_history_command(token):
    if token == "!!":
        return history[-1] if history else None
    if token.startswith("!"):
        ref = token[1:]
        if ref.isdigit():
            idx = int(ref) - 1
            return history[idx] if 0 <= idx < len(history) else None
        else:
            return next((c for c in reversed(history) if c.startswith(ref)), None)
    return None

def change_directory(path):
    try:
        os.chdir(path if path else os.path.expanduser("~"))
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

def bring_fg():
    for i, proc in enumerate(background_jobs):
        if proc.poll() is None:
            proc.wait()
            background_jobs.pop(i)
            return
    print("No background jobs")

def parse_command(command):
    try:
        return shlex.split(command)
    except ValueError as e:
        print(f"Syntax error: {e}")
        return None

def execute_redirection(tokens):
    cmd = []
    input_file = output_file = None
    append = False
    i = 0

    while i < len(tokens):
        if tokens[i] == '<':
            input_file = tokens[i+1] if i+1 < len(tokens) else None
            i += 2
        elif tokens[i] in ('>', '>>'):
            append = tokens[i] == '>>'
            output_file = tokens[i+1] if i+1 < len(tokens) else None
            i += 2
        else:
            cmd.append(tokens[i])
            i += 1

    stdin = open(input_file, 'r') if input_file else None
    stdout = open(output_file, 'a' if append else 'w') if output_file else None

    try:
        if cmd:
            proc = subprocess.run(
                cmd,
                stdin=stdin,
                stdout=stdout,
                stderr=subprocess.PIPE,
                text=True
            )
            if proc.stderr:
                print(proc.stderr.strip(), file=sys.stderr)
    except FileNotFoundError:
        print(f"{cmd[0]}: command not found", file=sys.stderr)
    finally:
        for f in (stdin, stdout):
            if f: f.close()

def execute_pipeline(segments, background=False):
    processes = []
    prev_out = None

    for i, segment in enumerate(segments):
        tokens = parse_command(segment)
        if not tokens:
            continue

        if tokens[0] == 'jobs':
            output = io.StringIO()
            sys.stdout = output
            list_jobs()
            sys.stdout = sys.__stdout__
            output = output.getvalue().encode()
            if i == len(segments)-1:
                sys.stdout.buffer.write(output)
            else:
                next_proc = subprocess.Popen(parse_command(segments[i+1]), stdin=subprocess.PIPE)
                next_proc.communicate(input=output)
            break
        else:
            stdin = prev_out
            stdout = subprocess.PIPE if i < len(segments)-1 else None

            try:
                proc = subprocess.Popen(
                    tokens,
                    stdin=stdin,
                    stdout=stdout,
                    text=True
                )
                if prev_out:
                    prev_out.close()
                prev_out = proc.stdout if stdout else None
                processes.append(proc)
            except FileNotFoundError:
                print(f"{tokens[0]}: command not found")
                return

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
        segments = [s.strip().rstrip('&') for s in command_line.split('|')]
        background = '&' in command_line
        execute_pipeline(segments, background)
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
        bring_fg()
    elif tokens[-1] == '&':
        run_background(tokens[:-1])
    elif any(r in tokens for r in ('>', '>>', '<')):
        execute_redirection(tokens)
    else:
        try:
            proc = subprocess.run(
                tokens,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if proc.stdout:
                print(proc.stdout.strip())
            if proc.stderr:
                print(proc.stderr.strip(), file=sys.stderr)
        except FileNotFoundError:
            print(f"{tokens[0]}: command not found")
        except BrokenPipeError:
            pass

def main():
    while True:
        try:
            cmd_lines = []
            print_prompt()
            while True:
                line = sys.stdin.readline()
                if not line:
                    raise EOFError
                cmd_lines.append(line.rstrip('\n'))
                full_cmd = ' '.join(cmd_lines)
                if is_balanced(full_cmd):
                    break
                if sys.stdin.isatty():
                    sys.stdout.write('> ')
                    sys.stdout.flush()

            command = ' '.join(cmd_lines)
            if command.strip().lower() in ('exit', 'quit'):
                break
            process_command(command)
            
        except EOFError:
            break
        except KeyboardInterrupt:
            if sys.stdin.isatty():
                print("\n")
            break

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

if __name__ == "__main__":
    main()