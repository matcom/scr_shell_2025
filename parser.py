from enum import Enum, auto
from collections import namedtuple
import subprocess
import os
import sys


class NodeType(Enum):
    COMMAND = auto()
    PIPE = auto()
    REDIRECT = auto()
    BACKGROUND = auto()
    LOGICAL_AND = auto()
    LOGICAL_OR = auto()


Command = namedtuple("Command", ["args", "redirects", "background"])
Pipe = namedtuple("Pipe", ["left", "right"])
Redirect = namedtuple("Redirect", ["command", "type", "file"])
LogicalOp = namedtuple("LogicalOp", ["left", "right", "op"])


class ShellParser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0

    def parse(self):
        return self._logical_expression()

    def _logical_expression(self):
        left = self._pipeline()

        while self._match("AND", "OR"):
            op = self._previous().lex
            right = self._pipeline()
            left = LogicalOp(left, right, op)

        return left

    def _pipeline(self):
        left = self._command()

        while self._match("PIPE"):
            right = self._command()
            left = Pipe(left, right)

        return left

    def _command(self):
        args = []
        redirects = []
        background = False

        while not self._is_at_end() and not self._is_command_terminator():
            if self._match("REDIRECT_IN"):
                file = self._consume("ARGUMENT", "Expected filename after <").lex
                redirects.append(("IN", file))
            elif self._match("REDIRECT_OUT"):
                file = self._consume("ARGUMENT", "Expected filename after >").lex
                redirects.append(("OUT", file))
            elif self._match("REDIRECT_APPEND"):
                file = self._consume("ARGUMENT", "Expected filename after >>").lex
                redirects.append(("APPEND", file))
            elif self._match("REDIRECT_STDERR"):
                file = self._consume("ARGUMENT", "Expected filename after 2>").lex
                redirects.append(("ERR", file))
            elif self._match("BACKGROUND"):
                background = True
                break
            else:
                args.append(self._advance().lex)

        return Command(args, redirects, background)

    def _match(self, *token_types):
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _check(self, token_type):
        if self._is_at_end():
            return False
        return self.tokens[self.current].token_type.name == token_type

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
            or self.tokens[self.current].token_type.name == "EOF"
        )

    def _is_command_terminator(self):
        return (
            self._check("SEMICOLON")
            or self._check("AND")
            or self._check("OR")
            or self._check("PIPE")
            or self._check("BACKGROUND")
        )


class CommandExecutor:
    def __init__(self):
        self.env = os.environ.copy()
        self.last_return_code = 0

    def execute(self, node):
        if isinstance(node, Command):
            return self._execute_command(node)
        elif isinstance(node, Pipe):
            return self._execute_pipe(node)
        elif isinstance(node, LogicalOp):
            return self._execute_logical(node)
        else:
            raise ValueError(f"Unknown node type: {type(node)}")

    def _execute_command(self, cmd):
        if not cmd.args:
            return 0

        # Comandos built-in
        if cmd.args[0] == "cd":
            return self._builtin_cd(cmd.args[1:])
        elif cmd.args[0] == "exit":
            sys.exit(0)

        # Configurar redirecciones
        stdin = stdout = stderr = None
        for r_type, file in cmd.redirects:
            if r_type == "IN":
                stdin = open(file, "r")
            elif r_type == "OUT":
                stdout = open(file, "w")
            elif r_type == "APPEND":
                stdout = open(file, "a")
            elif r_type == "ERR":
                stderr = open(file, "w")

        try:
            process = subprocess.Popen(
                cmd.args,
                stdin=stdin or sys.stdin,
                stdout=stdout or sys.stdout,
                stderr=stderr or sys.stderr,
                env=self.env,
                shell=False,
            )

            if not cmd.background:
                process.wait()
                self.last_return_code = process.returncode
                return process.returncode
            else:
                print(f"[{process.pid}]")
                return 0
        except FileNotFoundError:
            print(f"{cmd.args[0]}: command not found", file=sys.stderr)
            self.last_return_code = 127
            return 127
        finally:
            for f in [stdin, stdout, stderr]:
                if f and f not in [sys.stdin, sys.stdout, sys.stderr]:
                    f.close()

    def _execute_pipe(self, pipe):
        # Implementación básica de pipes
        try:
            p1 = subprocess.Popen(
                pipe.left.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
            p2 = subprocess.Popen(
                pipe.right.args,
                stdin=p1.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )

            p1.stdout.close()
            output, error = p2.communicate()

            if output:
                sys.stdout.write(output.decode())
            if error:
                sys.stderr.write(error.decode())

            self.last_return_code = p2.returncode
            return p2.returncode
        except FileNotFoundError as e:
            print(f"{e.filename}: command not found", file=sys.stderr)
            self.last_return_code = 127
            return 127

    def _execute_logical(self, logical):
        left_code = self.execute(logical.left)

        if logical.op == "&&" and left_code != 0:
            return left_code
        if logical.op == "||" and left_code == 0:
            return left_code

        return self.execute(logical.right)

    def _builtin_cd(self, args):
        try:
            if not args:
                new_dir = os.path.expanduser("~")
            else:
                new_dir = args[0]
            os.chdir(new_dir)
            self.last_return_code = 0
            return 0
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            self.last_return_code = 1
            return 1
