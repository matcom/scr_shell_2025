#!/usr/bin/env python3
"""
A custom Unix-like shell implementation with support for:
- Command execution
- Pipes and I/O redirection
- Job control (background processes, fg, bg, stop)
- Command history with expansion (!!, !n, !prefix)
"""
import os
import sys
import subprocess
import signal
from collections import deque
from typing import List, Dict, Optional, Tuple, Deque, Union, Any, NoReturn


COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m", 
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
}


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_COMMAND_NOT_FOUND = 127
EXIT_INTERRUPTED = 128 + signal.SIGINT


class Command:
    def __init__(
        self,
        args: List[str],
        redirects: List[Tuple[str, str]] = None,
        background: bool = False,
    ) -> None:
        self.args = args
        self.redirects = redirects if redirects else []
        self.background = background

    def __repr__(self) -> str:
        return f"Command({self.args}, {self.redirects}, {self.background})"


class Pipe:
    def __init__(self, left, right) -> None:
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"Pipe({self.left}, {self.right})"


class ShellLexer:

    def __init__(self) -> None:
        self.tokens: List[str] = []
        self.current_token = ""
        self.in_quote = False
        self.quote_char = ""

    def tokenize(self, line: str) -> List[str]:
     
        self.tokens = []
        self.current_token = ""
        self.in_quote = False
        self.quote_char = ""
        
        i = 0
        while i < len(line):
            char = line[i]

          
            if char in ('"', "'"):
                if not self.in_quote:
                    self.in_quote = True
                    self.quote_char = char
                    i += 1
                    continue
                elif char == self.quote_char:
                    self.in_quote = False
                    self.add_token()
                    self.quote_char = ""
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

    def add_token(self) -> None:
        
        if self.current_token:
            self.tokens.append(self.current_token)
            self.current_token = ""


class ShellParser:

    def __init__(self, tokens: List[str]) -> None:
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Union[Command, Pipe]:

        cmd = self.parse_pipe()

  
        if self.peek() == "&":
            self.consume("&")
            if isinstance(cmd, Command):
                cmd.background = True
            elif isinstance(cmd, Pipe):
                self._mark_pipe_background(cmd)
                
     
        if self.pos < len(self.tokens):
            raise SyntaxError(f"Unexpected token: {self.peek()}")
            
        return cmd

    def _mark_pipe_background(self, pipe_node: Pipe) -> None:
        """Mark the rightmost command in a pipe chain as background."""
        if isinstance(pipe_node.right, Pipe):
            self._mark_pipe_background(pipe_node.right)
        else:
            pipe_node.right.background = True

    def parse_pipe(self) -> Union[Command, Pipe]:
        left = self.parse_redirect()

        while self.peek() == "|":
            self.consume("|")
            right = self.parse_redirect()
            left = Pipe(left, right)

        return left

    def parse_redirect(self) -> Command:
        
        args = []
        redirects = []

        while self.pos < len(self.tokens):
            token = self.peek()

            if token == "<":
                self.consume("<")
                file = self.consume_any()
                redirects.append(("IN", file))
            elif token == ">":
                self.consume(">")
                file = self.consume_any()
                redirects.append(("OUT", file))
            elif token == ">>":
                self.consume(">>")
                file = self.consume_any()
                redirects.append(("APPEND", file))
            elif token in ("|", "&"):
                break
            else:
                args.append(self.consume_any())

        if not args:
            raise SyntaxError("Empty command")
            
        return Command(args, redirects, False)

    def peek(self) -> str:
        """Return current token without advancing position."""
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ""

    def consume(self, expected: str) -> str:
        """
        Consume the current token if it matches expected token.
        
        Args:
            expected: The expected token
            
        Returns:
            The consumed token
            
        Raises:
            SyntaxError: If current token doesn't match expected
        """
        if self.peek() == expected:
            self.pos += 1
            return expected
        raise SyntaxError(f"Expected '{expected}', got '{self.peek()}'")

    def consume_any(self) -> str:
        """
        Consume the current token regardless of value.
        
        Returns:
            The consumed token
            
        Raises:
            SyntaxError: If there are no more tokens
        """
        if self.pos >= len(self.tokens):
            raise SyntaxError("Unexpected end of input")
        token = self.tokens[self.pos]
        self.pos += 1
        return token


class Job:

    def __init__(self, pid: int, cmd: str, status: str = "running") -> None:
        if not isinstance(pid, int) or pid <= 0:
            raise ValueError(f"Invalid process ID: {pid}")
        
        if status not in ("running", "stopped"):
            raise ValueError(f"Invalid job status: {status}")
            
        self.pid = pid
        self.cmd = cmd
        self.status = status
        
    def __repr__(self) -> str:
        return f"Job(pid={self.pid}, status={self.status}, cmd={self.cmd})"


class CommandExecutor:

    def __init__(self) -> None:
        
        self.env = os.environ.copy()
        self.last_return_code = EXIT_SUCCESS
        self.jobs: Dict[int, Job] = {}
        self.current_job_id = 1
        self.history: Deque[str] = deque(maxlen=50)
        
        
        self._current_foreground_pid = -1
        self._current_foreground_cmd = ""
        self._prev_dir = os.getcwd()  
        
       
        signal.signal(signal.SIGCHLD, self._handle_sigchld)
        signal.signal(signal.SIGTSTP, self._handle_sigtstp)
        
    def _handle_sigtstp(self, signum: int, frame: Any) -> None:
 
        if hasattr(self, '_current_foreground_pid') and self._current_foreground_pid > 0:
            try:
              
                os.killpg(os.getpgid(self._current_foreground_pid), signal.SIGTSTP)
                
             
                for job_id, job in self.jobs.items():
                    if job.pid == self._current_foreground_pid:
                        job.status = "stopped"
                        print(f"\n{COLORS['CYAN']}[{job_id}] Detenido    {job.cmd}{COLORS['RESET']}")
                        break
                else:
                 
                    job_id = self.current_job_id
                    if hasattr(self, '_current_foreground_cmd'):
                        cmd_str = self._current_foreground_cmd
                    else:
                        cmd_str = "unknown command"
                    self.jobs[job_id] = Job(self._current_foreground_pid, cmd_str, "stopped")
                    self.current_job_id += 1
                    print(f"\n{COLORS['CYAN']}[{job_id}] Detenido    {cmd_str}{COLORS['RESET']}")
                
                
                self._current_foreground_pid = -1
                
                
                print(f"{COLORS['GREEN']}$:{COLORS['RESET']} ", end="", flush=True)
            except Exception as e:
                print(f"\n{COLORS['RED']}Error deteniendo proceso: {e}{COLORS['RESET']}")
                
    def _handle_sigchld(self, signum: int, frame: Any) -> None:
       
        printed_prompt = False
        
        
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break  

              
                for job_id, job in list(self.jobs.items()):
                    if job.pid == pid:
                        
                        if os.WIFEXITED(status):
                            print(
                                f"{COLORS['GREEN']}[{job_id}]    done       {job.cmd}{COLORS['RESET']}"
                            )
                            del self.jobs[job_id]
                            if not printed_prompt:
                                sys.stdout.write(f"{COLORS['GREEN']}$:{COLORS['RESET']} ")
                                sys.stdout.flush()
                                printed_prompt = True
                        
                        elif os.WIFSIGNALED(status):
                            sig = os.WTERMSIG(status)
                            if sig == signal.SIGINT:
                                print(f"\n[{job_id}]    interrupted    {job.cmd}")
                            else:
                                print(
                                    f"\n[{job_id}]    terminated by signal {sig}    {job.cmd}"
                                )
                            del self.jobs[job_id]
                     
                        elif os.WIFSTOPPED(status):
                            job.status = "stopped"
                            print(f"\n{COLORS['CYAN']}[{job_id}] Detenido    {job.cmd}{COLORS['RESET']}")
                            if hasattr(self, '_current_foreground_pid') and self._current_foreground_pid == pid:
                                self._current_foreground_pid = -1
                                printed_prompt = True
                                print(f"{COLORS['GREEN']}$:{COLORS['RESET']} ", end="", flush=True)
            except ChildProcessError:
                break  

        
        for job_id, job in list(self.jobs.items()):
            try:
                os.kill(job.pid, 0)  
            except ProcessLookupError:
                print(
                    f"{COLORS['GREEN']}[{job_id}]    terminated    {job.cmd}{COLORS['RESET']}",
                    flush=True,
                )
                del self.jobs[job_id]
                if not printed_prompt:
                    sys.stdout.write(f"{COLORS['GREEN']}$:{COLORS['RESET']} ")
                    sys.stdout.flush()
                    printed_prompt = True

    def execute(self, node: Union[Command, Pipe]) -> int:
        """
        Execute a command or pipeline.
        
        Args:
            node: The command tree node to execute
            
        Returns:
            The exit code of the command execution
        """
        try:
            if not isinstance(node, (Command, Pipe)):
                raise ValueError(f"Cannot execute node of type: {type(node)}")

            
            cmd_str = self._ast_to_string(node)

            if isinstance(node, Command):
                return self._execute_command(node)
            elif isinstance(node, Pipe):
                return self._execute_pipe(node)
        except Exception as e:
            print(
                f"{COLORS['RED']}Error executing command: {e}{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            self.last_return_code = EXIT_FAILURE
            return EXIT_FAILURE

    def _ast_to_string(self, node: Union[Command, Pipe]) -> str:
        """
        Convert an AST node to a command string.
        
        Args:
            node: Command or Pipe object
            
        Returns:
            String representation of the command
        """
        if isinstance(node, Command):
            parts = []
            
            for arg in node.args:
                if " " in arg or any(c in arg for c in ['"', "'", '|', '&', '<', '>']):
                    parts.append(f'"{arg}"')
                else:
                    parts.append(arg)

           
            for r_type, file in node.redirects:
                if r_type == "IN":
                    parts.append(f"< {file}")
                elif r_type == "OUT":
                    parts.append(f"> {file}")
                elif r_type == "APPEND":
                    parts.append(f">> {file}")

       
            if node.background:
                parts.append("&")

            return " ".join(parts)
        elif isinstance(node, Pipe):
            return (
                f"{self._ast_to_string(node.left)} | {self._ast_to_string(node.right)}"
            )
        return str(node)

    def _execute_command(self, cmd: Command) -> int:
        """
        Execute a single command.
        
        Args:
            cmd: The command to execute
            
        Returns:
            The exit code of the command
        """
        if not cmd.args:
            return EXIT_SUCCESS

       
        builtin_handlers = {
            "cd": self._builtin_cd,
            "exit": self._builtin_exit,
            "jobs": self._builtin_jobs,
            "fg": self._builtin_fg,
            "bg": self._builtin_bg,
            "history": self._builtin_history,
            "stop": self._builtin_stop,
        }
        
        command_name = cmd.args[0]
        
       
        if command_name in builtin_handlers:
            args = cmd.args[1:] if len(cmd.args) > 1 else None
            return builtin_handlers[command_name](args)
            
        if command_name == "kill" and len(cmd.args) >= 3 and cmd.args[1] == "-STOP":
            return self._builtin_stop(cmd.args[2:])
           
       
        return self._spawn_process(cmd.args, cmd.redirects, cmd.background)

    def _spawn_process(
        self, args: List[str], redirects: List[Tuple[str, str]], background: bool
    ) -> int:
        """
        Spawn a new process to execute a command.
        
        Args:
            args: Command arguments
            redirects: List of I/O redirections
            background: Whether to run in background
            
        Returns:
            Exit code of the process
        """
        stdin = None
        stdout = None
        stderr = None
        
        try:
            # Set up redirections
            for r_type, filename in redirects:
                try:
                    if r_type == "IN":
                        stdin = open(filename, "r")
                    elif r_type == "OUT":
                        stdout = open(filename, "w")
                    elif r_type == "APPEND":
                        stdout = open(filename, "a")
                except IOError as e:
                    print(
                        f"{COLORS['RED']}Cannot open file {filename}: {e}{COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    return EXIT_FAILURE

            
            process = subprocess.Popen(
                args,
                stdin=stdin or sys.stdin,
                stdout=stdout or sys.stdout,
                stderr=stderr or sys.stderr,
                env=self.env,
                preexec_fn=os.setsid, 
                universal_newlines=True,
            )

            
            if background:
                job_id = self.current_job_id
                self.jobs[job_id] = Job(process.pid, " ".join(args))
                self.current_job_id += 1
                print(
                    f"{COLORS['CYAN']}[{job_id}] {process.pid}{COLORS['RESET']}",
                    flush=True,
                )
                return EXIT_SUCCESS
            
            
            else:
               
                self._current_foreground_pid = process.pid
                self._current_foreground_cmd = " ".join(args)
                
                try:
                   
                    process.wait()
                except KeyboardInterrupt:
                    #  Ctrl+C 
                    os.killpg(os.getpgid(process.pid), signal.SIGINT)
                    process.wait()
                    self._current_foreground_pid = -1
                    self.last_return_code = 128 + signal.SIGINT
                    return self.last_return_code
                
                # Process completed normally
                self._current_foreground_pid = -1
                self.last_return_code = process.returncode
                return process.returncode
                
        except FileNotFoundError:
            print(
                f"{COLORS['RED']}{args[0]}: command not found{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return EXIT_COMMAND_NOT_FOUND
        except Exception as e:
            print(
                f"{COLORS['RED']}Error executing command: {e}{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return EXIT_FAILURE
        finally:
            
            for file_handle in [f for f in [stdin, stdout, stderr] if f and f not in [sys.stdin, sys.stdout, sys.stderr]]:
                try:
                    file_handle.close()
                except Exception:
                    pass  

    def _execute_pipe(self, pipe_node: Pipe) -> int:
        """
        Execute a pipeline of commands.
        
        Args:
            pipe_node: The pipe node to execute
            
        Returns:
            The exit code of the last command in the pipeline
        """
        
        commands = []
        self._flatten_pipes(pipe_node, commands)
        
        if not commands:
            return EXIT_FAILURE

     
        background = False
        if commands and commands[-1].background:
            background = True
           
            for cmd in commands:
                cmd.background = False

        processes = []
        prev_stdout = None

        try:
           
            for i, cmd in enumerate(commands):
                is_last = (i == len(commands) - 1)
                
              
                stdin = prev_stdout
                stdout = subprocess.PIPE if not is_last else None
                stderr = None

                stdin_redir = None
                stdout_redir = None

               
                for r_type, filename in cmd.redirects:
                    try:
                   
                        if r_type == "IN" and i == 0:
                            stdin_redir = open(filename, "r")
                        
                        elif (r_type == "OUT" or r_type == "APPEND") and is_last:
                            mode = "w" if r_type == "OUT" else "a"
                            stdout_redir = open(filename, mode)
                    except IOError as e:
                        print(
                            f"{COLORS['RED']}Cannot open file {filename}: {e}{COLORS['RESET']}",
                            file=sys.stderr,
                            flush=True,
                        )
                       
                        for proc in processes:
                            try:
                                proc.terminate()
                            except Exception:
                                pass
                        return EXIT_FAILURE

                # Start the process
                try:
                    process = subprocess.Popen(
                        cmd.args,
                        stdin=stdin_redir or stdin,
                        stdout=stdout_redir or stdout,
                        stderr=stderr,
                        env=self.env,
                        universal_newlines=True,
                        preexec_fn=os.setsid,
                    )
                    processes.append(process)
                except FileNotFoundError:
                    print(
                        f"{COLORS['RED']}{cmd.args[0]}: command not found{COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    
                    for proc in processes:
                        try:
                            proc.terminate()
                        except Exception:
                            pass
                    return EXIT_COMMAND_NOT_FOUND

                # 
                if prev_stdout and prev_stdout not in (sys.stdin, None):
                    prev_stdout.close()

                
                prev_stdout = process.stdout if not is_last else None

        
            if background and processes:
                job_id = self.current_job_id
                self.jobs[job_id] = Job(processes[-1].pid, self._ast_to_string(pipe_node))
                self.current_job_id += 1
                print(
                    f"{COLORS['CYAN']}[{job_id}] {processes[-1].pid}{COLORS['RESET']}",
                    flush=True,
                )
                return EXIT_SUCCESS
            
          
            else:
                try:
                   
                    for proc in processes:
                        proc.wait()
                    
                    
                    if processes:
                        self.last_return_code = processes[-1].returncode
                        return self.last_return_code
                    return EXIT_SUCCESS
                    
                except KeyboardInterrupt:
                    #  Ctrl+C
                    for proc in processes:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                            proc.wait()
                        except Exception:
                            pass
                    self.last_return_code = 128 + signal.SIGINT
                    return self.last_return_code
        finally:
           
            if prev_stdout and prev_stdout not in (sys.stdin, None):
                prev_stdout.close()

    def _flatten_pipes(self, node: Union[Pipe, Command], result: List[Command]) -> None:
        """
        Recursively flatten a pipe tree into a list of commands.
        
        Args:
            node: The root node to flatten
            result: The list to store flattened commands
        """
        if isinstance(node, Pipe):
            self._flatten_pipes(node.left, result)
            self._flatten_pipes(node.right, result)
        elif isinstance(node, Command):
            result.append(node)
        else:
            raise ValueError(f"Invalid node type in pipe: {type(node)}")

    def _builtin_cd(self, args: Optional[List[str]]) -> int:
    
   
        try:
            
            if not args:
                
                new_dir = os.path.expanduser("~")
            elif args[0] == "-":
                
                if not hasattr(self, "_prev_dir"):
                    print(
                        f"{COLORS['RED']}cd: no previous directory{COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    return EXIT_FAILURE
                new_dir = self._prev_dir
                print(f"{COLORS['GREEN']}cd to: {new_dir}{COLORS['RESET']}")
            else:
                new_dir = args[0]

            
            current_dir = os.getcwd()
            
          
            os.chdir(new_dir)
            
            self._prev_dir = current_dir
            return EXIT_SUCCESS
            
        except Exception as e:
            print(
                f"{COLORS['RED']}cd: {e}{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return EXIT_FAILURE

    def _builtin_jobs(self) -> int:
    
        if not self.jobs:
            print("No background jobs", file=sys.stderr)
            return EXIT_SUCCESS

        for job_id, job in sorted(self.jobs.items()):
            print(
                f"{COLORS['CYAN']}[{job_id}] {job.pid} {job.status} {job.cmd}{COLORS['RESET']}",
                flush=True,
            )
        return EXIT_SUCCESS

    def _builtin_fg(self, args: Optional[List[str]]) -> int:

        if not self.jobs:
            print(
                f"{COLORS['MAGENTA']}fg: no current job{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return EXIT_FAILURE

        try:
           
            if not args:
                
                job_id = max(self.jobs.keys())
            else:
              
                arg = args[0]
                if arg.startswith("%"):
                    arg = arg[1:]  
                job_id = int(arg)

    
            job = self.jobs.get(job_id)
            if not job:
                print(
                    f"{COLORS['RED']}fg: %{job_id}: no such job{COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
                return EXIT_FAILURE

            try:
                #  Ctrl+C 
                def handle_sigint(signum, frame):
                    os.killpg(os.getpgid(job.pid), signal.SIGINT)

                original_sigint = signal.signal(signal.SIGINT, handle_sigint)

                
                os.kill(job.pid, signal.SIGCONT)
                
                
                _, status = os.waitpid(job.pid, 0)
                
                
                signal.signal(signal.SIGINT, original_sigint)
                
               
                if os.WIFEXITED(status):
            
                    print(
                        f"{COLORS['GREEN']}[{job_id}]    done       {job.cmd}{COLORS['RESET']}",
                        flush=True,
                    )
                    del self.jobs[job_id]
                elif os.WIFSIGNALED(status):
                    
                    sig = os.WTERMSIG(status)
                    if sig == signal.SIGINT:
                        print(
                            f"{COLORS['MAGENTA']}[{job_id}]    interrupted    {job.cmd}{COLORS['RESET']}",
                            flush=True,
                        )
                    else:
                        print(
                            f"{COLORS['RED']}[{job_id}]    terminated by signal {sig}    {job.cmd} {COLORS['RESET']}",
                            flush=True,
                        )
                    del self.jobs[job_id]
                elif os.WIFSTOPPED(status):
                    # Ctrl+Z
                    job.status = "stopped"
                    print(
                        f"{COLORS['CYAN']}[{job_id}] Detenido    {job.cmd}{COLORS['RESET']}",
                        flush=True,
                    )
                
                return EXIT_SUCCESS
                
            except ProcessLookupError:
                
                print(
                    f"{COLORS['MAGENTA']}fg: job {job_id} has terminated{COLORS['RESET']}",
                    flush=True,
                    file=sys.stderr,
                )
                del self.jobs[job_id]
                return EXIT_FAILURE
        except ValueError:
            
            print(
                f"{COLORS['RED']}fg: job ID must be a number{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return EXIT_FAILURE

    def _builtin_bg(self, args: Optional[List[str]]) -> int:
        if not self.jobs:
            print(
                f"{COLORS['RED']}bg: no current job{COLORS['RESET']}",
                flush=True,
                file=sys.stderr,
            )
            return 1

        try:
            if not args:
                job_id = None
                for jid in sorted(self.jobs.keys(), reverse=True):
                    if self.jobs[jid].status == "stopped":
                        job_id = jid
                        break
                
                if job_id is None:
                    print(
                        f"{COLORS['RED']}bg: no stopped jobs{COLORS['RESET']}",
                        flush=True,
                        file=sys.stderr,
                    )
                    return 1
            else:
                arg = args[0]
                if arg.startswith("%"):
                    arg = arg[1:]
                job_id = int(arg)

            job = self.jobs.get(job_id)
            if not job:
                print(
                    f"{COLORS['RED']}bg: {job_id}: no such job{COLORS['RESET']}",
                    flush=True,
                    file=sys.stderr,
                )
                return 1

            try:
                os.kill(job.pid, signal.SIGCONT)
                job.status = "running"
                print(
                    f"{COLORS['CYAN']}[{job_id}] {job.pid} {job.cmd}{COLORS['RESET']}",
                    flush=True,
                )
                return 0
            except ProcessLookupError:
                print(
                    f"{COLORS['CYAN']}bg: job {job_id} has terminated{COLORS["RESET"]}",
                    file=sys.stderr,
                    flush=True,
                )
                del self.jobs[job_id]
                return 1
        except ValueError:
            print(
                f"{COLORS["RED"]}bg: job ID must be a number{COLORS["RESET"]}",
                file=sys.stderr,
                flush=True,
            )
            return 1

    def _builtin_history(self, args: Optional[List[str]]) -> int:
        limit = None
        if args and args[0].isdigit():
            limit = min(int(args[0]), len(self.history))

        for i, cmd in enumerate(self.history[-limit:] if limit else self.history, 1):
            print(f"{COLORS['CYAN']}{i:4} {cmd}{COLORS['RESET']} ", flush=True)
        return 0

    def add_to_history(self, command: str) -> None:
        if command.startswith(" "):
            return

        command = command.strip()
        if command:
            if not self.history or command != self.history[-1]:
                self.history.append(command)

    def get_history_command(self, arg: str) -> Optional[str]:
        if not arg:
            return None

       
        pipe_parts = arg.split('|', 1)
        history_part = pipe_parts[0].strip()
        pipe_suffix = ''
        
        if len(pipe_parts) > 1:
            pipe_suffix = f" | {pipe_parts[1].strip()}"

  
        if history_part == "!!":
            if not self.history:
                return None
            base_cmd = self.history[-1]
            return f"{base_cmd}{pipe_suffix}"


        if history_part.startswith("!") and history_part[1:].isdigit():
            index = int(history_part[1:]) - 1
            if 0 <= index < len(self.history):
                base_cmd = self.history[index]
                return f"{base_cmd}{pipe_suffix}"
            return None


        if history_part.startswith("!"):
            cmd_prefix = history_part[1:]

          
            for cmd in reversed(self.history):
                if cmd.startswith(cmd_prefix):
                    return f"{cmd}{pipe_suffix}"

        return None

    def _builtin_stop(self, args: Optional[List[str]]) -> int:
        
        if not args or len(args) < 1:
            print(
                f"{COLORS['RED']}stop: falta PID o ID de trabajo{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return 1
            
        try:
            
            target = args[0]
            if target.startswith("%"):
             
                job_id = int(target[1:])
                job = self.jobs.get(job_id)
                if not job:
                    print(
                        f"{COLORS['RED']}stop: %{job_id}: no existe ese trabajo{COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    return 1
                pid = job.pid
            else:
                
                try:
                    pid = int(target)
                    
                    found = False
                    for job_id, job in self.jobs.items():
                        if job.pid == pid:
                            found = True
                            break
                    if not found:
                        print(
                            f"{COLORS['MAGENTA']}Advertencia: El PID {pid} no corresponde a ningún trabajo conocido{COLORS['RESET']}",
                            file=sys.stderr,
                            flush=True,
                        )
                except ValueError:
                    print(
                        f"{COLORS['RED']}stop: {target}: argumento debe ser PID o %jobID{COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    return 1
            
            
            try:
                os.kill(pid, signal.SIGSTOP)
                
            
                for job_id, job in self.jobs.items():
                    if job.pid == pid:
                        job.status = "stopped"
                        print(
                            f"{COLORS['CYAN']}[{job_id}] Detenido    {job.cmd}{COLORS['RESET']}",
                            flush=True,
                        )
                        break
                else:
                    print(
                        f"{COLORS['CYAN']}Proceso {pid} detenido{COLORS['RESET']}",
                        flush=True,
                    )
                return 0
            except ProcessLookupError:
                print(
                    f"{COLORS['RED']}stop: ({pid}) - No existe ese proceso{COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
               
                for job_id, job in list(self.jobs.items()):
                    if job.pid == pid:
                        del self.jobs[job_id]
                        break
                return 1
            except PermissionError:
                print(
                    f"{COLORS['RED']}stop: ({pid}) - Permiso denegado{COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1
        except Exception as e:
            print(
                f"{COLORS['RED']}stop: Error inesperado: {e}{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return 1

    def _builtin_exit(self, args: Optional[List[str]] = None) -> NoReturn:
        """Exit the shell with the specified code or last return code."""
        exit_code = EXIT_SUCCESS
        if args and args[0].isdigit():
            exit_code = int(args[0])
        sys.exit(exit_code)


def main_loop() -> None:
    """
    Main shell loop that processes user input and executes commands.
    """
    executor = CommandExecutor()

    
    def handle_sigint(sig, frame):
        """ Ctrl+C """
        print()  
        print(f"{COLORS['GREEN']}$:{COLORS['RESET']} ", end="", flush=True)
        return
    
    
    original_sigint = signal.signal(signal.SIGINT, handle_sigint)
    original_sigtstp = signal.signal(signal.SIGTSTP, signal.SIG_IGN)  # Ignore Ctrl+Z 

    try:
        while True:
            try:
               
                prompt = f"{COLORS['GREEN']}$:{COLORS['RESET']} "
                try:
                    line = input(prompt)
                except EOFError:  # Ctrl+D
                    print("\nExiting shell")
                    break
                except KeyboardInterrupt:  # Ctrl+C 
                    print()
                    continue

             
                if not line:
                    continue
                    
          
                line2 = line.strip()
                if line2.startswith("!"):
                    history_cmd = executor.get_history_command(line2)
                    if history_cmd:
                        line = history_cmd
                        print(f"{COLORS['CYAN']}Executing: {line}{COLORS['RESET']}")
                    else:
                        print(
                            f"{COLORS['MAGENTA']}Command not found in history: {line2}{COLORS['RESET']}",
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
                        f"{COLORS['RED']}Syntax error: {e}{COLORS['RESET']}",
                        file=sys.stderr,
                        flush=True,
                    )
                    executor.last_return_code = EXIT_FAILURE
                except Exception as e:
                    print(
                        f"{COLORS['RED']}Error: {e}{COLORS['RESET']}",
                        flush=True,
                        file=sys.stderr,
                    )
                    executor.last_return_code = EXIT_FAILURE

            except Exception as e:
                print(
                    f"{COLORS['RED']}Unexpected error: {e}{COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
                executor.last_return_code = EXIT_FAILURE
    finally:
      
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTSTP, original_sigtstp)


if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        print(f"{COLORS['RED']}Fatal error: {e}{COLORS['RESET']}", file=sys.stderr)
        sys.exit(EXIT_FAILURE)  