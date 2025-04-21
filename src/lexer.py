from typing import List


class ShellLexer:
    """
    Clase que representa el lexer de la shell.
    """

    def __init__(self) -> None:
        self.tokens = []
        self.current_token = ""
        self.in_quote = False
        self.quote_char = ""
        self.token_was_quoted = False

    def tokenize(self, line: str) -> List[str]:

        i = 0
        while i < len(line):
            char = line[i]

            if char in ('"', "'"):
                if not self.in_quote:
                    self.in_quote = True
                    self.quote_char = char
                    self.token_was_quoted = True
                    i += 1
                    continue
                elif char == self.quote_char:
                    self.in_quote = False
                    self.add_token()
                    self.quote_char = ""
                    self.token_was_quoted = False
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
            if self.token_was_quoted and self.current_token in [">", "<", ">>", "|", "&"]:

                self.tokens.append(f"__QUOTED__{self.current_token}")
            else:
                self.tokens.append(self.current_token)
            self.current_token = ""
