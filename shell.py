from parser import ShellParser, CommandExecutor
from lexer import ShellLexer
import sys


def main_loop():
    executor = CommandExecutor()

    while True:
        try:

            try:
                line = input("$ ").strip()
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue

            if not line:
                continue

            lexer = ShellLexer()

            tokens = lexer.tokenize(line)

            parser = ShellParser(tokens)
            ast = parser.parse()

            executor.execute(ast)

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main_loop()
