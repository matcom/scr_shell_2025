from enum import Enum, auto
from collections import namedtuple, deque
import subprocess
import os
import sys
import signal
from typing import List, Dict, Optional, Tuple, NamedTuple, Deque
import re
import readline


class ShellTokenType(Enum):
    ARGUMENT = auto()
    PIPE = auto()
    SEMICOLON = auto()
    AND = auto()
    OR = auto()
    REDIRECT_IN = auto()
    REDIRECT_STDOUT = auto()
    REDIRECT_APPEND = auto()
    REDIRECT_STDERR = auto()
    REDIRECT_STDOUT_ERR = auto()
    REDIRECT_APPEND_ERR = auto()
    REDIRECT_APPEND_OUT_ERR = auto()
    BACKGROUND = auto()
    EOF = auto()


class ShellToken(NamedTuple):
    token_type: ShellTokenType
    lex: str


class ShellLexer:
    TOKEN_REGEX = [
        (ShellTokenType.PIPE, r"\|"),
        (ShellTokenType.SEMICOLON, r";"),
        (ShellTokenType.AND, r"&&"),
        (ShellTokenType.OR, r"\|\|"),
        (ShellTokenType.REDIRECT_APPEND_OUT_ERR, r"&>>"),
        (ShellTokenType.REDIRECT_STDOUT_ERR, r"&>"),
        (ShellTokenType.REDIRECT_APPEND_ERR, r"2>>"),
        (ShellTokenType.REDIRECT_STDERR, r"2>"),
        (ShellTokenType.REDIRECT_APPEND, r">>"),
        (ShellTokenType.REDIRECT_STDOUT, r">"),
        (ShellTokenType.REDIRECT_IN, r"<"),
        (ShellTokenType.BACKGROUND, r"&"),
        (ShellTokenType.ARGUMENT, r"[^\s|;&><]+"),
    ]

    def tokenize(self, line: str) -> List[ShellToken]:
        tokens = []
        while line:
            line = line.lstrip()
            matched = False
            for token_type, regex in self.TOKEN_REGEX:
                match = re.match(regex, line)
                if match:
                    lexeme = match.group(0)
                    tokens.append(ShellToken(token_type, lexeme))
                    line = line[len(lexeme) :]
                    matched = True
                    break
            if not matched:
                raise SyntaxError(f"Token no reconocido en: {line}")
        tokens.append(ShellToken(ShellTokenType.EOF, "EOF"))
        return tokens


Command = namedtuple("Command", ["args", "redirects", "background"])
Pipe = namedtuple("Pipe", ["left", "right"])
LogicalOp = namedtuple("LogicalOp", ["left", "right", "op"])
Sequence = namedtuple("Sequence", ["left", "right"])


class ShellParser:
    def __init__(self, tokens: List[ShellToken]):
        self.tokens = tokens
        self.current = 0

    def parse(self):
        return self._sequence()

    def _sequence(self):
        left = self._logical_expression()
        while self._match(ShellTokenType.SEMICOLON):
            right = self._logical_expression()
            left = Sequence(left, right)
        return left

    def _logical_expression(self):
        left = self._pipeline()
        while self._match(ShellTokenType.AND, ShellTokenType.OR):
            op = self._previous().lex
            right = self._pipeline()
            left = LogicalOp(left, right, op)
        return left

    def _pipeline(self):
        left = self._command()

        while self._match(ShellTokenType.PIPE):
            right = self._command()
            left = Pipe(left, right)

        if self._match(ShellTokenType.BACKGROUND):
            if isinstance(left, Command):
                left = Command(left.args, left.redirects, True)
            else:
                left = Command([self._node_to_string(left)], [], True)
        return left

    def _command(self):
        args = []
        redirects = []

        while not self._is_at_end() and not self._is_command_terminator():
            if self._match(ShellTokenType.REDIRECT_IN):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de <"
                ).lex
                redirects.append(("IN", file))
            elif self._match(ShellTokenType.REDIRECT_STDOUT):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de >"
                ).lex
                redirects.append(("OUT", file))
            elif self._match(ShellTokenType.REDIRECT_APPEND):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de >>"
                ).lex
                redirects.append(("APPEND", file))
            elif self._match(ShellTokenType.REDIRECT_STDERR):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de 2>"
                ).lex
                redirects.append(("ERR", file))
            elif self._match(ShellTokenType.REDIRECT_STDOUT_ERR):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de &>"
                ).lex
                redirects.append(("OUT_ERR", file))
            elif self._match(ShellTokenType.REDIRECT_APPEND_ERR):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de 2>>"
                ).lex
                redirects.append(("APPEND_ERR", file))
            elif self._match(ShellTokenType.REDIRECT_APPEND_OUT_ERR):
                file = self._consume(
                    ShellTokenType.ARGUMENT, "Archivo esperado después de &>>"
                ).lex
                redirects.append(("APPEND_OUT_ERR", file))
            else:
                args.append(self._advance().lex)

        return Command(args, redirects, False)

    def _match(self, *token_types):
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type):
        return (
            not self._is_at_end() and self.tokens[self.current].token_type == token_type
        )

    def _advance(self):
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _previous(self):
        return self.tokens[self.current - 1]

    def _consume(self, token_type, message):
        if self._check(token_type):
            return self._advance()
        raise SyntaxError(message)

    def _is_at_end(self):
        return (
            self.current >= len(self.tokens)
            or self.tokens[self.current].token_type == ShellTokenType.EOF
        )

    def _is_command_terminator(self):
        return (
            self._check(ShellTokenType.SEMICOLON)
            or self._check(ShellTokenType.AND)
            or self._check(ShellTokenType.OR)
            or self._check(ShellTokenType.PIPE)
            or self._check(ShellTokenType.BACKGROUND)
        )

    def _node_to_string(self, node) -> str:
        if isinstance(node, Command):
            return " ".join(node.args)
        elif isinstance(node, Pipe):
            return f"{self._node_to_string(node.left)} | {self._node_to_string(node.right)}"
        elif isinstance(node, LogicalOp):
            return f"{self._node_to_string(node.left)} {node.op} {self._node_to_string(node.right)}"
        elif isinstance(node, Sequence):
            return f"{self._node_to_string(node.left)} ; {self._node_to_string(node.right)}"
        return str(node)


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
                            job.status = f"terminated ({os.WEXITSTATUS(status)})"
                        elif os.WIFSIGNALED(status):
                            job.status = f"killed ({os.WTERMSIG(status)})"
                        elif os.WIFSTOPPED(status):
                            job.status = "stopped"
            except ChildProcessError:
                break

    def execute(self, node):
        try:
            if isinstance(node, (Command, Pipe, LogicalOp, Sequence)):
                cmd_str = self._ast_to_string(node)
                self.add_to_history(cmd_str)
            if isinstance(node, Command):
                return self._execute_command(node)
            elif isinstance(node, Pipe):
                return self._execute_pipe(node)
            elif isinstance(node, LogicalOp):
                return self._execute_logical(node)
            elif isinstance(node, Sequence):
                self.execute(node.left)
                return self.execute(node.right)
            else:
                raise ValueError(f"Tipo de nodo desconocido: {type(node)}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            self.last_return_code = 1
            return 1

    def _ast_to_string(self, node) -> str:
        if isinstance(node, Command):
            return " ".join(node.args)
        elif isinstance(node, Pipe):
            return (
                f"{self._ast_to_string(node.left)} | {self._ast_to_string(node.right)}"
            )
        elif isinstance(node, LogicalOp):
            return f"{self._ast_to_string(node.left)} {node.op} {self._ast_to_string(node.right)}"
        elif isinstance(node, Sequence):
            return (
                f"{self._ast_to_string(node.left)} ; {self._ast_to_string(node.right)}"
            )
        return str(node)

    def _execute_command(self, cmd: Command):
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

    def _spawn_process(self, args, redirects, background):
        stdin = stdout = stderr = None
        for r_type, file in redirects:
            try:
                if r_type == "IN":
                    stdin = open(file, "r")
                elif r_type == "OUT":
                    stdout = open(file, "w")
                elif r_type == "APPEND":
                    stdout = open(file, "a")
                elif r_type == "ERR":
                    stderr = open(file, "w")
                elif r_type == "OUT_ERR":
                    stdout = stderr = open(file, "w")
                elif r_type == "APPEND_ERR":
                    stderr = open(file, "a")
                elif r_type == "APPEND_OUT_ERR":
                    stdout = stderr = open(file, "a")
            except IOError as e:
                print(f"No se puede abrir archivo: {e}", file=sys.stderr)
                return 1

        try:
            process = subprocess.Popen(
                args,
                stdin=stdin or None,
                stdout=stdout or None,
                stderr=stderr or None,
                env=self.env,
                start_new_session=True,
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
            print(f"{args[0]}: comando no encontrado", file=sys.stderr)
            return 127
        except Exception as e:
            print(f"Error al ejecutar comando: {e}", file=sys.stderr)
            return 1
        finally:
            for f in [stdin, stdout, stderr]:
                if f and f not in [sys.stdin, sys.stdout, sys.stderr]:
                    f.close()

    def _execute_pipe(self, pipe_node):
        commands = []
        self._flatten_pipes(pipe_node, commands)

        processes = []
        prev_stdout = None

        for i, cmd in enumerate(commands):
            try:
                # Configurar stdin (salida del comando anterior o redirección)
                stdin = prev_stdout

                # Configurar stdout (pipe si no es el último comando)
                stdout = subprocess.PIPE if i < len(commands) - 1 else None

                # Configurar stderr (solo para el último comando)
                stderr = None if i < len(commands) - 1 else subprocess.PIPE

                # Solo aplicar redirecciones de archivo al primer y último comando
                stdin_redir = None
                stdout_redir = None
                stderr_redir = None

                if i == 0 or i == len(commands) - 1:
                    for r_type, file in cmd.redirects:
                        if r_type == "IN":
                            stdin_redir = open(file, "r")
                        elif r_type == "OUT":
                            stdout_redir = open(file, "w")
                        elif r_type == "APPEND":
                            stdout_redir = open(file, "a")
                        elif r_type == "ERR":
                            stderr_redir = open(file, "w")

                process = subprocess.Popen(
                    cmd.args,
                    stdin=stdin_redir or stdin,
                    stdout=stdout_redir or stdout,
                    stderr=stderr_redir or stderr,
                    env=self.env,
                    text=True,
                    universal_newlines=True,
                )

                processes.append(process)

                # Cerrar el stdout del proceso anterior si no lo necesitamos más
                if prev_stdout and prev_stdout != sys.stdin:
                    prev_stdout.close()

                # Guardar el stdout de este proceso para el siguiente
                prev_stdout = process.stdout if i < len(commands) - 1 else None

            except FileNotFoundError as e:
                print(f"{cmd.args[0]}: comando no encontrado", file=sys.stderr)
                # Cerrar todos los file descriptors abiertos
                for p in processes:
                    if p.stdout and p.stdout != sys.stdout:
                        p.stdout.close()
                return 127

        # Esperar a que todos los procesos terminen
        for p in processes:
            p.wait()

        # El código de retorno es del último proceso
        self.last_return_code = processes[-1].returncode

        # Mostrar salida del último proceso si no fue redirigida
        if processes[-1].stdout and processes[-1].stdout != sys.stdout:
            output = processes[-1].stdout.read()
            if output:
                print(output, end="")

        return self.last_return_code

    def _get_redirected_stream(self, kind, redirects, fallback):
        for r_type, file in redirects:
            if r_type == kind or (kind == "OUT" and r_type.startswith("OUT")):
                mode = "a" if "APPEND" in r_type else "w"
                return open(file, mode)
        return fallback

    def _flatten_pipes(self, node, result):
        if isinstance(node, Pipe):
            self._flatten_pipes(node.left, result)
            self._flatten_pipes(node.right, result)
        elif isinstance(node, Command):
            result.append(node)
        else:
            raise ValueError("Nodo inválido en tubería")

    def _execute_logical(self, logical):
        left_code = self.execute(logical.left)

        if logical.op == "&&" and left_code != 0:
            return left_code
        if logical.op == "||" and left_code == 0:
            return left_code

        return self.execute(logical.right)

    def _builtin_cd(self, args):
        try:
            new_dir = args[0] if args else os.path.expanduser("~")
            os.chdir(new_dir)
            return 0
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return 1

    def _builtin_jobs(self) -> int:
        if not self.jobs:
            print("No hay trabajos en segundo plano")
            return 0

        for job_id, job in self.jobs.items():
            print(f"[{job_id}] {job.pid} {job.status} {job.cmd}")
        return 0

    def _builtin_fg(self, args: Optional[List[str]]) -> int:
        if not self.jobs:
            print("fg: no hay trabajos", file=sys.stderr)
            return 1

        try:
            job_id = max(self.jobs.keys()) if not args else int(args[0].lstrip("%"))
        except ValueError:
            print("fg: argumento debe ser un ID de trabajo", file=sys.stderr)
            return 1

        job = self.jobs.get(job_id)
        if not job:
            print(f"fg: {job_id}: no existe ese trabajo", file=sys.stderr)
            return 1

        try:
            os.setpgid(job.pid, os.getpgid(0))
            os.kill(job.pid, signal.SIGCONT)

            _, status = os.waitpid(job.pid, 0)

            if os.WIFEXITED(status):
                job.status = f"terminated ({os.WEXITSTATUS(status)})"
            elif os.WIFSIGNALED(status):
                job.status = f"killed ({os.WTERMSIG(status)})"

            del self.jobs[job_id]
            return 0
        except ProcessLookupError:
            print(f"fg: proceso {job.pid} no existe", file=sys.stderr)
            del self.jobs[job_id]
            return 1

    def _builtin_bg(self, args: Optional[List[str]]) -> int:
        if not self.jobs:
            print("bg: no hay trabajos", file=sys.stderr)
            return 1

        job_id = max(self.jobs.keys()) if not args else int(args[0].lstrip("%"))
        job = self.jobs.get(job_id)

        if not job:
            print(f"bg: {job_id}: no existe ese trabajo", file=sys.stderr)
            return 1

        try:
            os.kill(job.pid, signal.SIGCONT)
            job.status = "running"
            print(f"[{job_id}] {job.pid} {job.cmd}")
            return 0
        except ProcessLookupError:
            print(f"bg: proceso {job.pid} no existe", file=sys.stderr)
            del self.jobs[job_id]
            return 1

    def _builtin_history(self, args: Optional[List[str]]) -> int:
        limit = None
        if args and args[0].isdigit():
            limit = int(args[0])

        for i, cmd in enumerate(self.history[-limit:] if limit else self.history, 1):
            print(f"{i:4}  {cmd}")
        return 0

    def add_to_history(self, command: str):
        command = command.strip()
        if (
            command
            and not command.startswith(" ")
            and (not self.history or command != self.history[-1])
        ):
            self.history.append(command)

    def get_history_command(self, arg: str) -> Optional[str]:
        if not arg:
            return None
        if arg == "!!":
            return self.history[-1] if self.history else None
        if arg.startswith("!"):
            try:
                index = int(arg[1:]) - 1
                if 0 <= index < len(self.history):
                    return self.history[index]
            except ValueError:
                prefix = arg[1:]
                for cmd in reversed(self.history):
                    if cmd.startswith(prefix):
                        return cmd
        return None


def main_loop():
    executor = CommandExecutor()
    while True:
        try:
            cwd = os.getcwd()
            prompt = f"\033[1;32m{cwd}\033[0m$ "
            line = input(prompt).strip()

            # Manejar comandos de historial antes de procesar
            if line.startswith("!"):
                history_cmd = executor.get_history_command(line)
                if history_cmd:
                    print(f"Ejecutando: {history_cmd}")
                    line = history_cmd
                else:
                    print(
                        f"Comando no encontrado en historial: {line}", file=sys.stderr
                    )
                    continue

            if not line:
                continue

            if not line.startswith(" "):
                executor.add_to_history(line)

            lexer = ShellLexer()
            tokens = lexer.tokenize(line)

            parser = ShellParser(tokens)
            ast = parser.parse()

            print("AST:", ast)
            executor.execute(ast)
        except EOFError:
            break
        except KeyboardInterrupt:
            print()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main_loop()
