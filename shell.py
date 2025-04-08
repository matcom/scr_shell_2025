#!/usr/bin/env python3
import os
import sys
import subprocess
import signal
from collections import deque
from typing import List, Dict, Optional, Tuple, Deque


class Command:
    def __init__(
        self,
        args: List[str],
        redirects: List[Tuple[str, str]] = None,
        background: bool = False,
    ):
        self.args = args
        self.redirects = redirects if redirects else []
        self.background = background

    def __repr__(self):
        return f"Command({self.args}, {self.redirects}, {self.background})"


class Pipe:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"Pipe({self.left}, {self.right})"


class ShellLexer:
    def __init__(self):
        self.tokens = []
        self.current_token = ""
        self.in_quote = False
        self.quote_char = ""

    def tokenize(self, line: str) -> List[str]:
        self.tokens = []
        self.current_token = ""
        self.in_quote = False
        self.quote_char = ""

        i = 0
        while i < len(line):
            char = line[i]

            if char in ('"', "'"):
                if not self.in_quote:
                    self.in_quote = True
                    self.quote_char = char
                    i += 1
                    continue
                elif char == self.quote_char:
                    self.in_quote = False
                    self.add_token()
                    self.quote_char = ""
                    i += 1
                    continue

            if self.in_quote:
                self.current_token += char
                i += 1
                continue

            if char in ("|", "<", ">", "&"):
                self.add_token()

                if char == ">" and i + 1 < len(line) and line[i + 1] == ">":
                    self.tokens.append(">>")
                    i += 2
                    continue

                self.tokens.append(char)
                i += 1
                continue

            if char in (" ", "\t"):
                self.add_token()
                i += 1
                continue

            self.current_token += char
            i += 1

        self.add_token()
        return [t for t in self.tokens if t]

    def add_token(self):
        if self.current_token:
            self.tokens.append(self.current_token)
            self.current_token = ""


class ShellParser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def parse(self):
        """Parsea el comando y aplica & al pipeline completo."""
        cmd = self.parse_pipe()

        # Si hay un & al final, lo aplicamos a TODO el pipeline
        if self.peek() == "&":
            self.consume("&")
            if isinstance(cmd, Command):
                cmd.background = True
            elif isinstance(cmd, Pipe):
                # Marcamos todo el pipeline como background
                self._mark_pipe_background(cmd)
        return cmd

    def _mark_pipe_background(self, pipe_node):
        """Marca todo el pipeline como background."""
        if isinstance(pipe_node.right, Pipe):
            self._mark_pipe_background(pipe_node.right)
        else:
            pipe_node.right.background = True

    def parse_pipe(self):
        """Maneja pipes (|)."""
        left = self.parse_redirect()

        while self.peek() == "|":
            self.consume("|")
            right = self.parse_redirect()
            left = Pipe(left, right)

        return left

    def parse_redirect(self) -> Command:
        """Maneja redirecciones (<, >, >>)."""
        args = []
        redirects = []

        while self.pos < len(self.tokens):
            token = self.peek()

            if token == "<":
                self.consume("<")
                file = self.consume_any()
                redirects.append(("IN", file))
            elif token == ">":
                self.consume(">")
                file = self.consume_any()
                redirects.append(("OUT", file))
            elif token == ">>":
                self.consume(">>")
                file = self.consume_any()
                redirects.append(("APPEND", file))
            elif token in ("|", "&"):  # Cortar si encontramos un pipe o &
                break
            else:
                args.append(self.consume_any())

        return Command(args, redirects, False)

    def peek(self) -> str:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ""

    def consume(self, expected: str) -> str:
        if self.peek() == expected:
            self.pos += 1
            return expected
        raise SyntaxError(f"Expected '{expected}', got '{self.peek()}'")

    def consume_any(self) -> str:
        if self.pos >= len(self.tokens):
            raise SyntaxError("Unexpected end of input")
        token = self.tokens[self.pos]
        self.pos += 1
        return token


class Job:
    def __init__(self, pid: int, cmd: str, status: str = "running"):
        self.pid = pid
        self.cmd = cmd
        self.status = status


class CommandExecutor:
    def __init__(self):
        self.env = os.environ.copy()
        self.last_return_code = 0
        self.jobs: Dict[int, Job] = {}
        self.current_job_id = 1
        self.history: Deque[str] = deque(maxlen=50)
        self.alias: Dict[str, str] = {}
        signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def _handle_sigchld(self, signum, frame):
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break

                for job_id, job in list(self.jobs.items()):
                    if job.pid == pid:
                        if os.WIFEXITED(status):
                            del self.jobs[job_id]
                        elif os.WIFSIGNALED(status):
                            del self.jobs[job_id]
                        elif os.WIFSTOPPED(status):
                            job.status = "stopped"
            except ChildProcessError:
                break

        for job_id, job in list(self.jobs.items()):
            try:
                os.kill(job.pid, 0)
            except ProcessLookupError:
                del self.jobs[job_id]

    def execute(self, node):
        try:
            if isinstance(node, (Command, Pipe)):
                cmd_str = self._ast_to_string(node)
                # self.add_to_history(cmd_str)

            if isinstance(node, Command):
                return self._execute_command(node)
            elif isinstance(node, Pipe):
                return self._execute_pipe(node)
            else:
                raise ValueError(f"Unknown node type: {type(node)}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            self.last_return_code = 1
            return 1

    def _ast_to_string(self, node) -> str:
        if isinstance(node, Command):
            parts = []
            for arg in node.args:
                if " " in arg:
                    parts.append(f'"{arg}"')
                else:
                    parts.append(arg)

            for r_type, file in node.redirects:
                if r_type == "IN":
                    parts.append(f"< {file}")
                elif r_type == "OUT":
                    parts.append(f"> {file}")
                elif r_type == "APPEND":
                    parts.append(f">> {file}")

            if node.background:
                parts.append("&")

            return " ".join(parts)
        elif isinstance(node, Pipe):
            return (
                f"{self._ast_to_string(node.left)} | {self._ast_to_string(node.right)}"
            )
        return str(node)

    def _execute_command(self, cmd: Command) -> int:
        if not cmd.args:
            return 0

        if cmd.args[0] == "cd":
            return self._builtin_cd(cmd.args[1:])
        elif cmd.args[0] == "exit":
            sys.exit(0)
        elif cmd.args[0] == "jobs":
            return self._builtin_jobs()
        elif cmd.args[0] == "fg":
            return self._builtin_fg(cmd.args[1:] if len(cmd.args) > 1 else None)
        elif cmd.args[0] == "bg":
            return self._builtin_bg(cmd.args[1:] if len(cmd.args) > 1 else None)
        elif cmd.args[0] == "history":
            return self._builtin_history(cmd.args[1:] if len(cmd.args) > 1 else None)

        return self._spawn_process(cmd.args, cmd.redirects, cmd.background)

    def _spawn_process(
        self, args: List[str], redirects: List[Tuple[str, str]], background: bool
    ) -> int:
        stdin = None
        stdout = None
        stderr = None

        for r_type, filename in redirects:
            try:
                if r_type == "IN":
                    stdin = open(filename, "r")
                elif r_type == "OUT":
                    stdout = open(filename, "w")
                elif r_type == "APPEND":
                    stdout = open(filename, "a")
            except IOError as e:
                print(f"Cannot open file: {e}", file=sys.stderr)
                return 1

        try:
            process = subprocess.Popen(
                args,
                stdin=stdin or sys.stdin,
                stdout=stdout or sys.stdout,
                stderr=sys.stderr,
                env=self.env,
                preexec_fn=os.setsid if background else None,
                universal_newlines=True,
            )

            if background:
                job_id = self.current_job_id
                self.jobs[job_id] = Job(process.pid, " ".join(args))
                self.current_job_id += 1
                print(f"[{job_id}] {process.pid}")
                return 0
            else:
                process.wait()
                self.last_return_code = process.returncode
                return process.returncode
        except FileNotFoundError:
            print(f"{args[0]}: command not found", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"Error executing command: {e}", file=sys.stderr)
            return 1
        finally:
            for f in [stdin, stdout]:
                if f and f not in [sys.stdin, sys.stdout, sys.stderr]:
                    f.close()

    def _execute_pipe(self, pipe_node: Pipe) -> int:
        commands = []
        self._flatten_pipes(pipe_node, commands)

        # Verificar si todo el pipeline debe ejecutarse en background
        background = False
        if commands and commands[-1].background:
            background = True
            for cmd in commands:
                cmd.background = False  # Quitar el flag para procesar el pipe

        processes = []
        prev_stdout = None

        for i, cmd in enumerate(commands):
            try:
                stdin = prev_stdout
                stdout = subprocess.PIPE if i < len(commands) - 1 else None
                stderr = None

                stdin_redir = None
                stdout_redir = None

                for r_type, filename in cmd.redirects:
                    try:
                        if r_type == "IN" and i == 0:
                            stdin_redir = open(filename, "r")
                        elif r_type == "OUT" and i == len(commands) - 1:
                            stdout_redir = open(filename, "w")
                        elif r_type == "APPEND" and i == len(commands) - 1:
                            stdout_redir = open(filename, "a")
                    except IOError as e:
                        print(f"Cannot open file: {e}", file=sys.stderr)
                        return 1

                process = subprocess.Popen(
                    cmd.args,
                    stdin=stdin_redir or stdin,
                    stdout=stdout_redir or stdout,
                    stderr=stderr,
                    env=self.env,
                    universal_newlines=True,
                    preexec_fn=os.setsid if background else None,
                )

                processes.append(process)

                if prev_stdout and prev_stdout not in (sys.stdin, None):
                    prev_stdout.close()

                prev_stdout = process.stdout if i < len(commands) - 1 else None

            except FileNotFoundError:
                print(f"{cmd.args[0]}: command not found", file=sys.stderr)
                for p in processes:
                    p.terminate()
                return 127

        if background:
            job_id = self.current_job_id
            self.jobs[job_id] = Job(processes[-1].pid, self._ast_to_string(pipe_node))
            self.current_job_id += 1
            print(f"[{job_id}] {processes[-1].pid}")
            return 0
        else:
            for p in processes:
                p.wait()
            self.last_return_code = processes[-1].returncode
            return self.last_return_code

    def _flatten_pipes(self, node, result: List[Command]):
        if isinstance(node, Pipe):
            self._flatten_pipes(node.left, result)
            self._flatten_pipes(node.right, result)
        elif isinstance(node, Command):
            result.append(node)
        else:
            raise ValueError("Invalid node in pipe")

    def _builtin_cd(self, args: List[str]) -> int:
        try:
            if not args:
                new_dir = os.path.expanduser("~")
            else:
                new_dir = args[0]

            os.chdir(new_dir)
            return 0
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return 1

    def _builtin_jobs(self) -> int:
        if not self.jobs:
            print("No background jobs", file=sys.stderr)
            return 0

        for job_id, job in self.jobs.items():
            print(f"[{job_id}] {job.pid} {job.status} {job.cmd}")
        return 0

    def _builtin_fg(self, args: Optional[List[str]]) -> int:
        if not self.jobs:
            print("fg: no current job", file=sys.stderr)
            return 1

        try:
            if not args:
                job_id = max(self.jobs.keys())
            else:
                arg = args[0]
                if arg.startswith("%"):
                    arg = arg[1:]
                job_id = int(arg)

            job = self.jobs.get(job_id)
            if not job:
                print(f"fg: {job_id}: no such job", file=sys.stderr)
                return 1

            try:
                os.kill(job.pid, signal.SIGCONT)
                _, status = os.waitpid(job.pid, 0)

                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    del self.jobs[job_id]
                elif os.WIFSTOPPED(status):
                    job.status = "stopped"

                return 0
            except ProcessLookupError:
                print(f"fg: job {job_id} has terminated", file=sys.stderr)
                del self.jobs[job_id]
                return 1
        except ValueError:
            print("fg: job ID must be a number", file=sys.stderr)
            return 1

    def _builtin_bg(self, args: Optional[List[str]]) -> int:
        if not self.jobs:
            print("bg: no current job", file=sys.stderr)
            return 1

        try:
            if not args:
                job_id = max(self.jobs.keys())
            else:
                arg = args[0]
                if arg.startswith("%"):
                    arg = arg[1:]
                job_id = int(arg)

            job = self.jobs.get(job_id)
            if not job:
                print(f"bg: {job_id}: no such job", file=sys.stderr)
                return 1

            try:
                os.kill(job.pid, signal.SIGCONT)
                job.status = "running"
                print(f"[{job_id}] {job.pid} {job.cmd}")
                return 0
            except ProcessLookupError:
                print(f"bg: job {job_id} has terminated", file=sys.stderr)
                del self.jobs[job_id]
                return 1
        except ValueError:
            print("bg: job ID must be a number", file=sys.stderr)
            return 1

    def _builtin_history(self, args: Optional[List[str]]) -> int:
        limit = None
        if args and args[0].isdigit():
            limit = min(int(args[0]), len(self.history))

        for i, cmd in enumerate(self.history[-limit:] if limit else self.history, 1):
            print(f"{i:4}  {cmd}")
        return 0

    def add_to_history(self, command: str) -> None:
        if command.startswith(" "):
            return

        command = command.strip()
        if command:
            if not self.history or command != self.history[-1]:
                self.history.append(command)
                cmd_base = command.split()[0]
                if cmd_base not in self.alias:
                    self.alias[cmd_base] = command

    def get_history_command(self, arg: str) -> Optional[str]:
        if not arg:
            return None

        if arg == "!!":
            return self.history[-1] if self.history else None

        if arg.startswith("!"):
            if arg[1:].isdigit():
                index = int(arg[1:]) - 1
                if 0 <= index < len(self.history):
                    return self.history[index]
                return None

            cmd_prefix = arg[1:]

            if cmd_prefix in self.alias:
                return self.alias[cmd_prefix]

            for cmd in reversed(self.history):
                if cmd.startswith(cmd_prefix):
                    self.alias[cmd_prefix] = cmd
                    return cmd

        return None


def main_loop() -> None:
    executor = CommandExecutor()

    while True:
        try:
            prompt = "$ "
            try:
                line = input(prompt)
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line:
                continue

            if line.startswith("!"):
                history_cmd = executor.get_history_command(line)
                if history_cmd:
                    line = history_cmd
                else:
                    print(f"Command not found in history: {line}", file=sys.stderr)
                    continue

            executor.add_to_history(line)

            try:
                lexer = ShellLexer()
                tokens = lexer.tokenize(line)

                parser = ShellParser(tokens)
                ast = parser.parse()
                executor.execute(ast)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                executor.last_return_code = 1

        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            executor.last_return_code = 1


if __name__ == "__main__":
    main_loop()
