#!/usr/bin/env python3

import sys
import os
from src.lexer import ShellLexer
from src.parser import ShellParser
from src.executer import CommandExecutor, COLORS, safe_print

"""def sms():
    def get_system_info():
        try:
            if os.uname().sysname =="Darwin":
                return "macOS"
            elif os.uname().sysname =="Linux":
                return "Linux"
        except Exception as e:
            return "Windows"
    sistema = get_system_info()
    term_width = os.get_terminal_size().columns
    python_version = sys.version.split()[0]
    user = os.getenv('USER', 'usuario')
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

    box_width = 46  
    system_info = []
    
    system_info.append(f"{COLORS['GREEN']}╭{'─' * (box_width - 2)}╮")
    system_info.append(f"{COLORS['GREEN']}│{' ' * (box_width - 2)}│")
    
    title = "INFORMACIÓN DEL SISTEMA"
    left_padding = (box_width - 2 - len(title)) // 2
    right_padding = box_width - 2 - len(title) - left_padding
    system_info.append(f"{COLORS['GREEN']}│{' ' * left_padding}{COLORS['YELLOW']}{title}{COLORS['GREEN']}{' ' * right_padding}│")
    

    system_info.append(f"{COLORS['GREEN']}│{' ' * (box_width - 2)}│")
    
    items = [
        ("Versión:", "Shell 1.0.0"),
        ("Python:", python_version),
        ("Sistema:", sistema),
        ("Usuario:", user),
    ]
    
    for label, value in items:
    
        content_length = len(f"  ▶ {label} {value}")
        right_spaces = box_width - 2 - content_length
        
        line = f"{COLORS['GREEN']}│  {COLORS['WHITE']}▶ {label}{COLORS['GREEN']} {COLORS['YELLOW']}{value}{' ' * right_spaces}{COLORS['GREEN']}│"
        system_info.append(line)
    
 
    system_info.append(f"{COLORS['GREEN']}│{' ' * (box_width - 2)}│")
    
    system_info.append(f"{COLORS['GREEN']}╰{'─' * (box_width - 2)}╯{COLORS['RESET']}")
    

    for line in system_info:
        clean_line = ""
        i = 0
        while i < len(line):
            if line[i] == '\033':
              
                while i < len(line) and line[i] != 'm':
                    i += 1
                i += 1  
            else:
                clean_line += line[i]
                i += 1
        
        padding = (term_width - len(clean_line)) // 2
        print(" " * padding + line)
    
  
    inspirational_msg = f"{COLORS['MAGENTA']}✨ Bienvenido  ✨{COLORS['RESET']}"
    padding = (term_width - len(inspirational_msg) + len(COLORS['MAGENTA']) + len(COLORS['RESET'])) // 2
    print("\n" + " " * padding + inspirational_msg + "\n")"""


def main_loop() -> None:
    executor = CommandExecutor()
    # sms()

    while True:
        try:
            prompt = f"\r{COLORS['GREEN']}$:{COLORS['RESET']} "
            try:
                line = input(prompt)
                """line1= line.strip()
                if line1 == 'home':
                    sms()
                    continue"""
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
                if not history_cmd:
                    safe_print(
                        f"{COLORS['MAGENTA']}Command not found in history: {line} {COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    continue
                line = history_cmd
                safe_print(line, flush=True)

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
                safe_print(
                    f"{COLORS['RED']}Syntax error: {e} {COLORS['RESET']}",
                    flush=True,
                    file=sys.stderr,
                )
                executor.last_return_code = 1
            except Exception as e:
                safe_print(
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
