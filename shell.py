#!/usr/bin/env python3
import os
import sys
import re
import shlex
import subprocess
from typing import List, Deque, Optional, Dict, Tuple, Union
from collections import deque
from enum import Enum, auto


class TokenType(Enum):
    COMMAND = auto()
    ARGUMENT = auto()
    PIPE = auto()
    REDIRECT_IN = auto()
    REDIRECT_OUT = auto()
    REDIRECT_APPEND = auto()
    BACKGROUND = auto()


class Token:
    def __init__(self, type: TokenType, value: str = ""):
        self.type = type
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, '{self.value}')"


class Command:
    def __init__(self):
        self.command: str = ""
        self.args: List[str] = []
        self.stdin: Optional[str] = None
        self.stdout: Optional[str] = None
        self.append: bool = False
        self.background: bool = False
        self.pipe_to: Optional["Command"] = None


class Shell:
    def __init__(self) -> None:
        self.prompt = "$ "
        self.paths: List[str] = [os.path.expanduser("~"), os.getcwd()]
        self.max_dir_history = 5
        self.command_history: Deque[str] = deque(maxlen=50)
        self.last_command: Optional[str] = None
        self.command_dict: Dict[int, str] = {}
        self.background_processes: Dict[int, str] = {}
        self.last_return_code = 0

    def _update_path_history(self, new_path: str) -> None:
        if not self.paths or self.paths[-1] != new_path:
            self.paths.append(new_path)
            if len(self.paths) > self.max_dir_history:
                self.paths.pop(0)

    def _add_to_command_history(self, command: str) -> None:
        command = command.strip()
        if not command or command.startswith(" "):
            return
        self.command_history.append(command)
        self.command_dict[len(self.command_history)] = command
        self.last_command = command

    def _tokenize(self, input_line: str) -> List[Token]:
        tokens = []
        lexer = shlex.shlex(input_line, posix=True)
        lexer.whitespace_split = True
        lexer.whitespace = " \t\n"

        for word in lexer:
            if word == "|":
                tokens.append(Token(TokenType.PIPE))
            elif word == "<":
                tokens.append(Token(TokenType.REDIRECT_IN))
            elif word == ">":
                tokens.append(Token(TokenType.REDIRECT_OUT))
            elif word == ">>":
                tokens.append(Token(TokenType.REDIRECT_APPEND))
            elif word == "&":
                tokens.append(Token(TokenType.BACKGROUND))

            else:
                if tokens and tokens[-1].type in [
                    TokenType.REDIRECT_IN,
                    TokenType.REDIRECT_OUT,
                    TokenType.REDIRECT_APPEND,
                ]:
                    tokens.append(Token(TokenType.ARGUMENT, word))
                else:
                    tokens.append(
                        Token(
                            TokenType.COMMAND if not tokens else TokenType.ARGUMENT,
                            word,
                        )
                    )

        return tokens

    def _parse_commands(self, tokens: List[Token]) -> List[Command]:
        commands = []
        current = Command()
        i = 0
        n = len(tokens)

        while i < n:
            token = tokens[i]

            if token.type == TokenType.COMMAND:
                current.command = token.value
            elif token.type == TokenType.ARGUMENT:
                current.args.append(token.value)
            elif token.type == TokenType.REDIRECT_IN:
                if i + 1 < n and tokens[i + 1].type == TokenType.ARGUMENT:
                    current.stdin = tokens[i + 1].value
                    i += 1
            elif token.type == TokenType.REDIRECT_OUT:
                if i + 1 < n and tokens[i + 1].type == TokenType.ARGUMENT:
                    current.stdout = tokens[i + 1].value
                    i += 1
            elif token.type == TokenType.REDIRECT_APPEND:
                if i + 1 < n and tokens[i + 1].type == TokenType.ARGUMENT:
                    current.stdout = tokens[i + 1].value
                    current.append = True
                    i += 1
            elif token.type == TokenType.BACKGROUND:
                current.background = True
            elif token.type == TokenType.PIPE:
                commands.append(current)
                current = Command()

            i += 1

        if current.command or current.args:
            commands.append(current)

        for i in range(len(commands) - 1):
            commands[i].pipe_to = commands[i + 1]

        return commands

    def _expand_special_commands(self, input_line: str) -> str:
        parts = input_line.split("|")
        expanded_parts = []

        for part in parts:
            part = part.strip()
            if part.startswith("!"):
                expanded = self._handle_special_commands(part)
                if expanded:
                    if "|" in expanded:
                        expanded_parts.extend([p.strip() for p in expanded.split("|")])
                    else:
                        expanded_parts.append(expanded)
                else:
                    expanded_parts.append(part)
            else:
                expanded_parts.append(part)

        return " | ".join(expanded_parts)

    def _handle_special_commands(self, command: str) -> Optional[str]:
        if command == "!!":
            return self.last_command if self.last_command else None

        if command.startswith("!"):
            if command[1:].isdigit():
                num = int(command[1:])
                return self.command_dict.get(num, None)
            else:
                prefix = command[1:]
                return self._get_command_by_prefix(prefix)
        return None

    def _get_command_by_prefix(self, prefix: str) -> Optional[str]:
        for cmd in reversed(self.command_history):
            cmd_first_part = cmd.split()[0] if cmd else ""
            if cmd_first_part.startswith(prefix):
                return cmd
        return None

    def _handle_cd(self, tokens: List[str]) -> bool:
        try:
            if len(tokens) > 1 and tokens[1] == "-":
                if len(self.paths) < 2:
                    print("cd: no previous directory", file=sys.stderr)
                    return False
                prev_dir = self.paths[-2]
                os.chdir(prev_dir)
                self._update_path_history(prev_dir)
                print(prev_dir)
                return True

            target_dir = os.path.expanduser("~") if len(tokens) == 1 else tokens[1]
            target_dir = (
                os.path.expanduser(target_dir)
                if target_dir.startswith("~")
                else target_dir
            )
            target_dir = os.path.expandvars(target_dir)

            if not os.path.exists(target_dir):
                print(f"cd: no such file or directory: {target_dir}", file=sys.stderr)
                return False

            os.chdir(target_dir)
            self._update_path_history(os.getcwd())
            return True

        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return False

    def _show_command_history(self) -> None:
        for i, cmd in enumerate(self.command_history, 1):
            print(f"{i:4d}  {cmd}")
            self.command_dict[i] = cmd

    def _execute_command(self, cmd: Command) -> int:

        if cmd.command == "cd":
            return 0 if self._handle_cd([cmd.command] + cmd.args) else 1
        elif cmd.command == "history":
            self._show_command_history()
            return 0
        elif cmd.command == "jobs":
            self._show_background_jobs()
            return 0
        elif cmd.command == "fg":
            return self._bring_to_foreground(cmd.args[0] if cmd.args else None)

        stdin_file = None
        stdout_file = None

        try:

            if cmd.stdin:
                try:
                    stdin_file = open(cmd.stdin, "r")
                except IOError as e:
                    print(f"{cmd.command}: {e}", file=sys.stderr)
                    return 1

            if cmd.stdout:
                try:
                    mode = "a" if cmd.append else "w"
                    stdout_file = open(cmd.stdout, mode)
                except IOError as e:
                    print(f"{cmd.command}: {e}", file=sys.stderr)
                    if stdin_file:
                        stdin_file.close()
                    return 1

            if cmd.background:
                try:
                    process = subprocess.Popen(
                        [cmd.command] + cmd.args,
                        stdin=stdin_file or subprocess.DEVNULL,
                        stdout=stdout_file or subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                    )
                    self.background_processes[process.pid] = " ".join(
                        [cmd.command] + cmd.args
                    )
                    print(f"[{process.pid}] {process.pid}")
                    return 0
                except Exception as e:
                    print(f"{cmd.command}: {e}", file=sys.stderr)
                    return 1
            else:
                try:
                    process = subprocess.run(
                        [cmd.command] + cmd.args,
                        stdin=stdin_file or sys.stdin,
                        stdout=stdout_file or sys.stdout,
                        stderr=sys.stderr,
                        text=True,
                    )
                    return process.returncode
                except FileNotFoundError:
                    print(f"{cmd.command}: command not found", file=sys.stderr)
                    return 127
                except Exception as e:
                    print(f"{cmd.command}: {e}", file=sys.stderr)
                    return 1
        finally:

            if stdin_file and not stdin_file.closed:
                stdin_file.close()
            if stdout_file and not stdout_file.closed:
                stdout_file.close()

    def _execute_pipeline(self, commands: List[Command]) -> int:
        if not commands:
            return 0

        processes = []
        prev_pipe = None

        try:
            for i, cmd in enumerate(commands):

                stdin = None
                if i == 0 and cmd.stdin:
                    try:
                        stdin = open(cmd.stdin, "r")
                    except IOError as e:
                        print(f"{cmd.command}: {e}", file=sys.stderr)
                        return 1
                elif prev_pipe:
                    stdin = os.fdopen(prev_pipe[0], "r")

                stdout = None
                if i == len(commands) - 1:
                    if cmd.stdout:
                        try:
                            mode = "a" if cmd.append else "w"
                            stdout = open(cmd.stdout, mode)
                        except IOError as e:
                            print(f"{cmd.command}: {e}", file=sys.stderr)
                            if stdin:
                                stdin.close()
                            return 1
                else:
                    next_pipe = os.pipe()
                    stdout = os.fdopen(next_pipe[1], "w")

                try:
                    process = subprocess.Popen(
                        [cmd.command] + cmd.args,
                        stdin=stdin or (None if i == 0 else subprocess.PIPE),
                        stdout=stdout
                        or (None if i == len(commands) - 1 else subprocess.PIPE),
                        stderr=sys.stderr,
                        text=True,
                    )
                    processes.append(process)
                except FileNotFoundError:
                    print(f"{cmd.command}: command not found", file=sys.stderr)
                    return 127
                except Exception as e:
                    print(f"{cmd.command}: {e}", file=sys.stderr)
                    return 1

                if stdin and stdin != sys.stdin:
                    stdin.close()
                if stdout and stdout != sys.stdout:
                    stdout.close()

                prev_pipe = next_pipe if i != len(commands) - 1 else None

            for process in processes:
                process.wait()

            return processes[-1].returncode

        except Exception as e:
            print(f"Pipeline error: {e}", file=sys.stderr)
            return 1
        finally:
            if prev_pipe:
                os.close(prev_pipe[0])
                os.close(prev_pipe[1])
            for process in processes:
                if process.poll() is None:
                    process.terminate()

    def _show_background_jobs(self) -> None:
        if not self.background_processes:
            print("No background jobs running")
            return

        for pid, cmd in self.background_processes.items():
            print(f"[{pid}] {pid}\t{cmd}")

    def _bring_to_foreground(self, job_spec: Optional[str] = None) -> int:
        if not self.background_processes:
            print("fg: no current jobs", file=sys.stderr)
            return 1

        if job_spec is None:

            pid = next(reversed(self.background_processes.keys()))
        elif job_spec.isdigit():
            pid = int(job_spec)
            if pid not in self.background_processes:
                print(f"fg: {pid}: no such job", file=sys.stderr)
                return 1
        else:

            matching = [
                p
                for p, cmd in self.background_processes.items()
                if cmd.startswith(job_spec)
            ]
            if not matching:
                print(f"fg: {job_spec}: no such job", file=sys.stderr)
                return 1
            pid = matching[0]

        try:
            cmd = self.background_processes.pop(pid)
            print(cmd)
            os.waitpid(pid, 0)
            return 0
        except ChildProcessError:
            print(f"fg: job {pid} already terminated", file=sys.stderr)
            self.background_processes.pop(pid, None)
            return 1

    def _check_background_processes(self) -> None:
        finished = []
        for pid in list(self.background_processes.keys()):
            try:

                if os.waitpid(pid, os.WNOHANG)[0] == pid:
                    finished.append(pid)
            except ChildProcessError:
                finished.append(pid)

        for pid in finished:
            self.background_processes.pop(pid, None)

    def process_input(self, input_line: str) -> None:
        input_line = input_line.strip()
        if not input_line:
            return

        self._check_background_processes()

        expanded_line = self._expand_special_commands(input_line)
        if expanded_line != input_line:
            print(f"$ {expanded_line}")

        if not input_line.startswith("!"):
            self._add_to_command_history(
                expanded_line if expanded_line != input_line else input_line
            )

        try:
            tokens = self._tokenize(expanded_line)
            commands = self._parse_commands(tokens)
        except ValueError as e:
            print(f"Parse error: {e}", file=sys.stderr)
            return
        if not commands:
            return

        if len(commands) > 1:
            return_code = self._execute_pipeline(commands)
        else:
            return_code = self._execute_command(commands[0])

        self.last_return_code = return_code

    def run(self) -> None:
        while True:
            try:
                input_line = input(self.prompt)
                self.process_input(input_line)
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    Shell().run()
