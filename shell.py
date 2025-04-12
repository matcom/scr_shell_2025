#!/usr/bin/env python3

import sys
import os
from src.lexer import ShellLexer
from src.parser import ShellParser  
from src.executer import CommandExecutor, COLORS

def main_loop() -> None:
    executor = CommandExecutor()
    
    # Obtener ancho de terminal para centrado
    term_width = os.get_terminal_size().columns
    
    # Arte ASCII mejorado para Alberto
    print("\n")
    welcome_art = [
        f"{COLORS['BLUE']}╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮",
        f"{COLORS['BLUE']}    {COLORS['YELLOW']}    ███████╗██╗  ██╗███████╗██╗     ██╗         {COLORS['BLUE']}",
        f"{COLORS['BLUE']}    {COLORS['YELLOW']}    ██╔════╝██║  ██║██╔════╝██║     ██║         {COLORS['BLUE']}",
        f"{COLORS['BLUE']}    {COLORS['YELLOW']}    ███████╗███████║█████╗  ██║     ██║         {COLORS['BLUE']}",
        f"{COLORS['BLUE']}    {COLORS['YELLOW']}    ╚════██║██╔══██║██╔══╝  ██║     ██║         {COLORS['BLUE']}",
        f"{COLORS['BLUE']}    {COLORS['YELLOW']}    ███████║██║  ██║███████╗███████╗███████╗    {COLORS['BLUE']}",
        f"{COLORS['BLUE']}    {COLORS['YELLOW']}    ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝    {COLORS['BLUE']}",
        f"{COLORS['BLUE']}                                                      ",
        f"{COLORS['BLUE']}     {COLORS['CYAN']}█████╗ ██╗     ██████╗ ███████╗██████╗ ████████╗ ██████╗   {COLORS['BLUE']}",
        f"{COLORS['BLUE']}   {COLORS['CYAN']}██╔══██╗██║     ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██╔═══██╗  {COLORS['BLUE']}",
        f"{COLORS['BLUE']}   {COLORS['CYAN']}███████║██║     ██████╔╝█████╗  ██████╔╝   ██║   ██║   ██║  {COLORS['BLUE']}",
        f"{COLORS['BLUE']}   {COLORS['CYAN']}██╔══██║██║     ██╔══██╗██╔══╝  ██╔══██╗   ██║   ██║   ██║  {COLORS['BLUE']}",
        f"{COLORS['BLUE']}   {COLORS['BRIGHT_CYAN']}██║  ██║███████╗██████╔╝███████╗██║  ██║   ██║   ╚██████╔╝  {COLORS['BLUE']}",
        f"{COLORS['BLUE']}   {COLORS['BRIGHT_CYAN']}╚═╝  ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝    ╚═════╝   {COLORS['BLUE']}",
        f"{COLORS['BLUE']}╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    ]
    
  
    for line in welcome_art:
       
        clean_line = line.replace(COLORS['BLUE'], '').replace(COLORS['YELLOW'], '').replace(COLORS['CYAN'], '')
        clean_line = clean_line.replace(COLORS['MAGENTA'], '').replace(COLORS['BRIGHT_CYAN'], '')
        padding = (term_width - len(clean_line)) // 2
        print(" " * padding + line)
    
  
    print()
    system_info = [
        f"{COLORS['GREEN']}╭─────────────── {COLORS['YELLOW']}SISTEMA{COLORS['GREEN']} ───────────────╮",
        f"{COLORS['GREEN']}│                                      │",
        f"{COLORS['GREEN']}│  {COLORS['WHITE']}▶ Versión:  {COLORS['YELLOW']}Shell 1.0.0         {COLORS['GREEN']}│",
        f"{COLORS['GREEN']}│  {COLORS['WHITE']}▶ Python:   {COLORS['YELLOW']}{sys.version.split()[0]}           {COLORS['GREEN']}│",
        f"{COLORS['GREEN']}│  {COLORS['WHITE']}▶ Sistema:  {COLORS['YELLOW']}{os.uname().sysname}        {COLORS['GREEN']}│",
        f"{COLORS['GREEN']}│  {COLORS['WHITE']}▶ Usuario:  {COLORS['YELLOW']}{os.getenv('USER', 'usuario')}     {COLORS['GREEN']}│",
        f"{COLORS['GREEN']}│                                      │",
        f"{COLORS['GREEN']}╰──────────────────────────────────────╯{COLORS['RESET']}"
    ]
    
    
    for line in system_info:
        
        clean_line = line
        for color in [COLORS['GREEN'], COLORS['YELLOW'], COLORS['WHITE']]:
            clean_line = clean_line.replace(color, '')
        clean_line = clean_line.replace(COLORS['RESET'], '')
        padding = (term_width - len(clean_line)) // 2
        print(" " * padding + line)
    
  
    inspirational_msg = f"{COLORS['MAGENTA']}✨ Bienvenido  ✨{COLORS['RESET']}"
    padding = (term_width - len(inspirational_msg) + len(COLORS['MAGENTA']) + len(COLORS['RESET'])) // 2
    print("\n" + " " * padding + inspirational_msg + "\n")
    
    while True:
        try:
            prompt = f"\r{COLORS['GREEN']}$:{COLORS['RESET']} "
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
            line2 = line[:].strip()
            if line2.startswith("!"):
                history_cmd = executor.get_history_command(line2)
                if history_cmd:
                    line = history_cmd
                    print(line)
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
            except SyntaxError as e:
                print(
                    f"{COLORS['RED']}Syntax error: {e} {COLORS['RESET']}",
                    flush=True,
                    file=sys.stderr,
                )
                executor.last_return_code = 1
            except Exception as e:
                print(
                    f"{COLORS['RED']}Error: {e} {COLORS['RESET']}",
                    flush=True,
                    file=sys.stderr,
                )
                executor.last_return_code = 1

        except Exception as e:
            print(
                f"{COLORS['RED']}Unexpected error: {e} {COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            executor.last_return_code = 1


if __name__ == "__main__":
    main_loop()