#!/usr/bin/env python3

import sys
from Lexer import ShellLexer
from Parser import ShellParser  
from executer import CommandExecutor, COLORS

def main_loop() -> None:
    executor = CommandExecutor()

    while True:
        try:
            prompt = f"\r{COLORS['GREEN']}$:{COLORS["RESET"]} "
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
                    print(
                        f"{COLORS['MAGENTA']}Command not found in history: {line} {COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue

            executor.add_to_history(line)

            try:
                lexer = ShellLexer()
                tokens = lexer.tokenize(line)

                parser = ShellParser(tokens)
                ast = parser.parse()
                executor.execute(ast)
            except KeyboardInterrupt:
                print()
                continue
            except Exception as e:
                print(
                    f"{COLORS['RED']}Error: {e} {COLORS["RESET"]}",
                    flush=True,
                    file=sys.stderr,
                )
                executor.last_return_code = 1

        except Exception as e:
            print(
                f"{COLORS["RED"]}Unexpected error: {e} {COLORS["RESET"]}",
                file=sys.stderr,
                flush=True,
            )
            executor.last_return_code = 1


if __name__ == "__main__":
    main_loop()