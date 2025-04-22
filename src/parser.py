from typing import List
from src.ast_tree import Command, Pipe


class ShellParser:
    """
    Clase que representa el parser de la shell.
    """

    def __init__(self, tokens: List[str]) -> None:
       
        self.tokens = []
        for token in tokens:
            if token.startswith("__QUOTED__"):
                self.tokens.append(token[10:])  # Quitar "__QUOTED__"
            else:
                self.tokens.append(token)
        
        self.pos = 0
        self.quoted_tokens = []
        
        for i, token in enumerate(tokens):
            if token.startswith("__QUOTED__"):
                self.quoted_tokens.append(i)

        if self.tokens:
            self._validate_token(tokens)

    def _validate_token(self,tokens) -> None:
        if not self.tokens:
            return

        for i, token in enumerate(tokens):
            if token == "&" and i < len(tokens) - 1:
                raise SyntaxError(f"Token '&' solo puede aparecer al final del comando")

        if self.tokens[0] in ("<", ">", ">>", "|"):
            raise SyntaxError(
                f"No se puede comenzar un comando con el token '{self.tokens[0]}'"
            )

        if self.tokens[-1] == "|":
            raise SyntaxError("No se puede terminar un comando con el token '|'")

        for i in range(len(self.tokens) - 1):
            if self.tokens[i] == "|" and self.tokens[i + 1] == "|":
                raise SyntaxError("No se permiten tokens '|' consecutivos")

    def parse(self) -> Command:

        cmd = self.parse_pipe()

        if self.peek() == "&" and self.pos not in self.quoted_tokens:
            self.consume("&")
            if isinstance(cmd, Command):
                cmd.background = True
            elif isinstance(cmd, Pipe):
                self._mark_pipe_background(cmd)
        return cmd

    def _mark_pipe_background(self, pipe_node) -> None:

        if isinstance(pipe_node.left, Pipe):
            self._mark_pipe_background(pipe_node.left)
        else:
            pipe_node.left.background = True

        if isinstance(pipe_node.right, Pipe):
            self._mark_pipe_background(pipe_node.right)
        else:
            pipe_node.right.background = True

    def parse_pipe(self) -> Command:
        left = self.parse_redirect()

        while self.peek() == "|" and self.pos not in self.quoted_tokens:
            self.consume("|")
            if self.pos >= len(self.tokens) or self.peek() in ("|", "&"):
                raise SyntaxError("Comando incompleto después del pipe '|'")
            right = self.parse_redirect()
            if not right.args:
                raise SyntaxError("Comando vacío después del pipe '|'")
            left = Pipe(left, right)

        return left

    def parse_redirect(self) -> Command:
        args = []
        redirects = []

        while self.pos < len(self.tokens):
            token = self.peek()
            current_pos = self.pos

            if token == "<" and current_pos not in self.quoted_tokens:
                if not args and not redirects:
                    raise SyntaxError("Redirección de entrada '<' sin comando previo")

                self.consume("<")
                if self.pos >= len(self.tokens) or self.peek() in (
                    "|",
                    "&",
                    "<",
                    ">",
                    ">>",
                ):
                    raise SyntaxError("Falta archivo de entrada después de '<'")
                file = self.consume_any()
                redirects.append(("IN", file))
            elif token == ">" and current_pos not in self.quoted_tokens:
                if not args and not redirects:
                    raise SyntaxError("Redirección de salida '>' sin comando previo")

                self.consume(">")
                if self.pos >= len(self.tokens) or self.peek() in (
                    "|",
                    "&",
                    "<",
                    ">",
                    ">>",
                ):
                    raise SyntaxError("Falta archivo de salida después de '>'")
                file = self.consume_any()
                redirects.append(("OUT", file))
            elif token == ">>" and current_pos not in self.quoted_tokens:
                if not args and not redirects:
                    raise SyntaxError("Redirección de append '>>' sin comando previo")

                self.consume(">>")
                if self.pos >= len(self.tokens) or self.peek() in (
                    "|",
                    "&",
                    "<",
                    ">",
                    ">>",
                ):
                    raise SyntaxError("Falta archivo de salida después de '>>'")
                file = self.consume_any()
                redirects.append(("APPEND", file))
            elif token in ("|", "&") and current_pos not in self.quoted_tokens:
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
