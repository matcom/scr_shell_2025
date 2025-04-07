from enum import Enum, auto
import re
from typing import List, NamedTuple, Tuple, Pattern, Optional


class ShellTokenType(Enum):
    # Comandos y argumentos
    COMMAND = auto()
    ARGUMENT = auto()

    # Operadores de control
    PIPE = auto()  # |
    SEMICOLON = auto()  # ;
    AND = auto()  # &&
    OR = auto()  # ||
    BACKGROUND = auto()  # &

    # Agrupación
    SUBSHELL_START = auto()  # (
    SUBSHELL_END = auto()  # )

    # Redirecciones
    REDIRECT_IN = auto()  # <
    REDIRECT_STDOUT = auto()  # >
    REDIRECT_STDERR = auto()  # 2>
    REDIRECT_STDOUT_ERR = auto()  # &>
    REDIRECT_APPEND = auto()  # >>
    REDIRECT_APPEND_ERR = auto()  # 2>>
    REDIRECT_APPEND_OUT_ERR = auto()  # &>>
    REDIRECT_HEREDOC = auto()  # <<
    REDIRECT_HERE_STRING = auto()  # <<<

    # Variables y strings
    VARIABLE = auto()  # $VAR o ${VAR}
    SINGLE_QUOTE_STRING = auto()  # 'texto'
    DOUBLE_QUOTE_STRING = auto()  # "texto"

    # Asignación
    ASSIGNMENT = auto()  # =

    # Fin de entrada
    EOF = auto()


class ShellToken(NamedTuple):
    lex: str
    token_type: ShellTokenType

    def __str__(self) -> str:
        return f"ShellToken('{self.lex}', {self.token_type})"


class ShellLexer:
    def __init__(self) -> None:
        # Patrones ordenados por prioridad (más específicos primero)
        self.patterns: List[Tuple[Pattern, ShellTokenType]] = [
            # Redirecciones compuestas
            (re.compile(r"&>>"), ShellTokenType.REDIRECT_APPEND_OUT_ERR),
            (re.compile(r"2>>"), ShellTokenType.REDIRECT_APPEND_ERR),
            (re.compile(r"&>"), ShellTokenType.REDIRECT_STDOUT_ERR),
            (re.compile(r"<<<"), ShellTokenType.REDIRECT_HERE_STRING),
            (re.compile(r"<<"), ShellTokenType.REDIRECT_HEREDOC),
            (re.compile(r">>"), ShellTokenType.REDIRECT_APPEND),
            (re.compile(r"2>"), ShellTokenType.REDIRECT_STDERR),
            # Operadores compuestos
            (re.compile(r"&&"), ShellTokenType.AND),
            (re.compile(r"\|\|"), ShellTokenType.OR),
            # Strings entre comillas (con soporte para escapes)
            (re.compile(r"'((?:[^']|\\')*)'"), ShellTokenType.SINGLE_QUOTE_STRING),
            (re.compile(r'"((?:[^"]|\\")*)"'), ShellTokenType.DOUBLE_QUOTE_STRING),
            # Variables
            (re.compile(r"\$\{[a-zA-Z_][a-zA-Z0-9_]*\}"), ShellTokenType.VARIABLE),
            (re.compile(r"\$[a-zA-Z_][a-zA-Z0-9_]*"), ShellTokenType.VARIABLE),
            # Operadores y símbolos simples
            (re.compile(r"\|"), ShellTokenType.PIPE),
            (re.compile(r"<"), ShellTokenType.REDIRECT_IN),
            (re.compile(r">"), ShellTokenType.REDIRECT_STDOUT),
            (re.compile(r"&(?!&)"), ShellTokenType.BACKGROUND),
            (re.compile(r";"), ShellTokenType.SEMICOLON),
            (re.compile(r"\("), ShellTokenType.SUBSHELL_START),
            (re.compile(r"\)"), ShellTokenType.SUBSHELL_END),
            (re.compile(r"="), ShellTokenType.ASSIGNMENT),
            # Palabras (comandos y argumentos)
            (re.compile(r"[^|\s&;<>()=]+"), ShellTokenType.ARGUMENT),
        ]

    def tokenize(self, input_text: str) -> List[ShellToken]:
        tokens: List[ShellToken] = []
        pos = 0
        length = len(input_text)

        while pos < length:
            # Saltamos espacios en blanco
            if input_text[pos].isspace():
                pos += 1
                continue

            matched = False

            for pattern, token_type in self.patterns:
                match = pattern.match(input_text, pos)
                if match:
                    token_value = match.group()

                    # Para strings, capturamos el contenido sin las comillas
                    if token_type in [
                        ShellTokenType.SINGLE_QUOTE_STRING,
                        ShellTokenType.DOUBLE_QUOTE_STRING,
                    ]:
                        token_value = match.group(1)

                    # Determinar si es COMMAND o ARGUMENT
                    if token_type == ShellTokenType.ARGUMENT:
                        if not tokens or self._is_command_delimiter(tokens[-1]):
                            token_type = ShellTokenType.COMMAND

                    tokens.append(ShellToken(token_value, token_type))
                    pos = match.end()
                    matched = True
                    break

            if not matched:
                raise ValueError(
                    f"Carácter inesperado en la posición {pos}: '{input_text[pos]}'"
                )

        tokens.append(ShellToken("", ShellTokenType.EOF))
        return tokens

    def _is_command_delimiter(self, token: ShellToken) -> bool:
        # Delimitadores básicos
        basic_delimiters = [
            ShellTokenType.PIPE,
            ShellTokenType.SEMICOLON,
            ShellTokenType.AND,
            ShellTokenType.OR,
            ShellTokenType.BACKGROUND,
            ShellTokenType.SUBSHELL_START,
            ShellTokenType.SUBSHELL_END,
            ShellTokenType.ASSIGNMENT,
        ]

        command_indicators = [
            "-exec",
            "exec",
            "-ok",
            "-I",
            "--replace",
            "xargs",
            "find",
            "time",
            "command",
            "builtin",
        ]

        # Combinar las condiciones
        return token.token_type in basic_delimiters or (
            token.token_type == ShellTokenType.ARGUMENT
            and token.lex in command_indicators
        )
