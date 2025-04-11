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
import fcntl, termios, struct
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
        """Handle SIGTSTP (Ctrl+Z) to stop the current foreground process."""
        if self._current_foreground_pid > 0:
            try:
                os.killpg(os.getpgid(self._current_foreground_pid), signal.SIGTSTP)
                
                for job_id, job in self.jobs.items():
                    if job.pid == self._current_foreground_pid:
                        job.status = "stopped"
                        print(f"\r\n[{job_id}] Stopped\t{job.cmd}")
                        break
                else:
                    job_id = self.current_job_id
                    cmd_str = self._current_foreground_cmd
                    self.jobs[job_id] = Job(self._current_foreground_pid, cmd_str, "stopped")
                    self.current_job_id += 1
                    print(f"\r\n[{job_id}] Stopped\t{cmd_str}")
                
                self._current_foreground_pid = -1
                
                print(f"\r{COLORS['GREEN']}$:{COLORS['RESET']} ", end="", flush=True)
            except ProcessLookupError:
                self._current_foreground_pid = -1
            except OSError as e:
                if e.errno == 3:
                    self._current_foreground_pid = -1
                else:
                    print(f"\r\nError stopping process: {e}")
            except Exception as e:
                print(f"\r\nError stopping process: {e}")
                
    def _handle_sigchld(self, signum: int, frame: Any) -> None:
        """Handle SIGCHLD to reap zombie processes and update job status."""
        output_shown = False
        
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
                if pid == 0:
                    break

                was_foreground = (pid == self._current_foreground_pid)
                if was_foreground:
                    self._current_foreground_pid = -1
                
                for job_id, job in list(self.jobs.items()):
                    if job.pid == pid:
                        if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                            if (job.status != "running" or os.WIFSIGNALED(status)) and not (was_foreground and os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGINT):
                                print(f"\r\n[{job_id}] Done\t{job.cmd}")
                                output_shown = True
                            del self.jobs[job_id]
                        elif os.WIFSTOPPED(status):
                            job.status = "stopped"
                            print(f"\r\n[{job_id}] Stopped\t{job.cmd}")
                            output_shown = True
                        break
            except ChildProcessError:
                break
            except OSError as e:
                if e.errno == 10:
                    break
                print(f"\r\nError handling child process: {e}")
                break
                
        try:
            for job_id, job in list(self.jobs.items()):
                try:
                    os.kill(job.pid, 0)
                except ProcessLookupError:
                    print(f"\r\n[{job_id}] Terminated\t{job.cmd}")
                    del self.jobs[job_id]
                    output_shown = True
                except OSError:
                    pass
        except Exception as e:
            print(f"\r\nError cleaning up jobs: {e}")
                
        if output_shown:
            print(f"\r{COLORS['GREEN']}$:{COLORS['RESET']} ", end="", flush=True)

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
        except ChildProcessError:
            pass
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
            for r_type, filename in redirects:
                try:
                    if r_type == "IN":
                        try:
                            stdin = open(filename, "r")
                        except (IOError, FileNotFoundError) as e:
                            print(f"{args[0]}: {filename}: {e.strerror}")
                            return EXIT_FAILURE
                    elif r_type == "OUT":
                        try:
                            stdout = open(filename, "w")
                        except (IOError, PermissionError) as e:
                            print(f"{args[0]}: {filename}: {e.strerror}")
                            return EXIT_FAILURE
                    elif r_type == "APPEND":
                        try:
                            stdout = open(filename, "a")
                        except (IOError, PermissionError) as e:
                            print(f"{args[0]}: {filename}: {e.strerror}")
                            return EXIT_FAILURE
                except Exception as e:
                    print(f"Error with redirection: {e}")
                    return EXIT_FAILURE

            try:
                process = subprocess.Popen(
                    args,
                    stdin=stdin or sys.stdin,
                    stdout=stdout or sys.stdout,
                    stderr=stderr or sys.stderr,
                    env=self.env,
                    preexec_fn=os.setsid,
                    universal_newlines=True,
                )
            except FileNotFoundError:
                print(f"{args[0]}: command not found")
                return EXIT_COMMAND_NOT_FOUND

            if background:
                job_id = self.current_job_id
                self.jobs[job_id] = Job(process.pid, " ".join(args))
                self.current_job_id += 1
                
                all_jobs = sorted(self.jobs.keys())
                current_job = max(all_jobs) if all_jobs else None
                current_mark = "+" if job_id == current_job else ""
                
                print(f"[{job_id}]{current_mark} {process.pid}")
                return EXIT_SUCCESS
            
            else:
                self._current_foreground_pid = process.pid
                self._current_foreground_cmd = " ".join(args)
                
                try:
                    process.wait()
                    self._current_foreground_pid = -1
                    self.last_return_code = process.returncode
                    
                    if not stdout and not stderr and sys.stdout.isatty():
                        try:
                            import fcntl, termios, struct
                            buf = fcntl.ioctl(1, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))
                            _, col, _, _ = struct.unpack('HHHH', buf)
                            if col > 0:
                                print()
                        except:
                            print()
                    
                    return process.returncode
                except KeyboardInterrupt:
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGINT)
                        process.wait()
                    except (ProcessLookupError, OSError):
                        pass
                    self._current_foreground_pid = -1
                    self.last_return_code = EXIT_INTERRUPTED
                    return self.last_return_code
                
        except Exception as e:
            print(f"Error executing command: {e}")
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

        background = any(cmd.background for cmd in commands)
        if background:
            for cmd in commands:
                cmd.background = False

        processes = []
        prev_stdout = None
        cmd_str = self._ast_to_string(pipe_node)

        try:
            for i, cmd in enumerate(commands):
                is_last = (i == len(commands) - 1)
                
                stdin = prev_stdout
                stdout = subprocess.PIPE if not is_last else None
                
                stdin_redir = None
                stdout_redir = None

                for r_type, filename in cmd.redirects:
                    try:
                        if r_type == "IN" and i == 0:
                            try:
                                stdin_redir = open(filename, "r")
                            except (IOError, FileNotFoundError) as e:
                                print(f"{cmd.args[0]}: {filename}: {e.strerror}")
                                self._cleanup_processes(processes)
                                return EXIT_FAILURE
                                
                        elif (r_type == "OUT" or r_type == "APPEND") and is_last:
                            try:
                                mode = "w" if r_type == "OUT" else "a"
                                stdout_redir = open(filename, mode)
                            except (IOError, PermissionError) as e:
                                print(f"{cmd.args[0]}: {filename}: {e.strerror}")
                                self._cleanup_processes(processes)
                                return EXIT_FAILURE
                    except Exception as e:
                        print(f"Error setting up redirection: {e}")
                        self._cleanup_processes(processes)
                        return EXIT_FAILURE

                try:
                    process = subprocess.Popen(
                        cmd.args,
                        stdin=stdin_redir or stdin,
                        stdout=stdout_redir or stdout,
                        stderr=None,
                        env=self.env,
                        universal_newlines=True,
                        preexec_fn=os.setsid,
                    )
                    processes.append(process)
                except FileNotFoundError:
                    if i == 0:
                        print(f"{cmd.args[0]}: command not found")
                    self._cleanup_processes(processes)
                    return EXIT_COMMAND_NOT_FOUND
                except Exception as e:
                    print(f"Error starting process: {e}")
                    self._cleanup_processes(processes)
                    return EXIT_FAILURE

                if prev_stdout and prev_stdout not in (sys.stdin, None):
                    prev_stdout.close()

                prev_stdout = process.stdout if not is_last else None

            if background and processes:
                last_process = processes[-1]
                job_id = self.current_job_id
                self.jobs[job_id] = Job(last_process.pid, cmd_str)
                self.current_job_id += 1
                
                all_jobs = sorted(self.jobs.keys())
                current_job = max(all_jobs) if all_jobs else None
                current_mark = "+" if job_id == current_job else ""
                
                print(f"[{job_id}]{current_mark} {last_process.pid}")
                return EXIT_SUCCESS
            
            else:
                if processes:
                    last_process = processes[-1]
                    self._current_foreground_pid = last_process.pid
                    self._current_foreground_cmd = cmd_str
                
                try:
                    processes_exited = set()
                    exit_code = EXIT_SUCCESS
                    
                    for i, proc in enumerate(processes):
                        try:
                            proc.wait()
                            processes_exited.add(proc.pid)
                            if i == len(processes) - 1:
                                exit_code = proc.returncode
                        except KeyboardInterrupt:
                            try:
                                os.killpg(os.getpgid(proc.pid), signal.SIGINT)
                            except OSError:
                                pass
                                
                    self._current_foreground_pid = -1
                    
                    if not any(cmd.redirects for cmd in commands) and sys.stdout.isatty():
                        try:
                           
                            buf = fcntl.ioctl(1, termios.TIOCGWINSZ, struct.pack('HHHH', 0, 0, 0, 0))
                            _, col, _, _ = struct.unpack('HHHH', buf)
                            if col > 0:
                                print()
                        except:
                            print()
                    
                    self.last_return_code = exit_code
                    return exit_code
                    
                except KeyboardInterrupt:
                    self._cleanup_processes(processes, signal.SIGINT)
                    self._current_foreground_pid = -1
                    self.last_return_code = EXIT_INTERRUPTED
                    return self.last_return_code
        finally:
            if prev_stdout and prev_stdout not in (sys.stdin, None):
                prev_stdout.close()
                
    def _cleanup_processes(self, processes, sig=signal.SIGTERM):
        """Helper to clean up a list of processes with the given signal."""
        for proc in processes:
            try:
                os.killpg(os.getpgid(proc.pid), sig)
                proc.wait()
            except Exception:
                pass

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

    def _builtin_jobs(self, args: Optional[List[str]]) -> int:
        """
        List active jobs with their status.
        
        Format is similar to bash:
        [job_id]+ state     command
        
        The + indicates the current job (that would be selected by fg with no args).
        The - indicates the previous job.
        """
        if not self.jobs:
            return EXIT_SUCCESS

        job_ids = sorted(self.jobs.keys())
        if not job_ids:
            return EXIT_SUCCESS
            
        current_job = max(job_ids)
        previous_job = None
        
        if len(job_ids) > 1:
            for jid in sorted(job_ids, reverse=True):
                if jid != current_job and self.jobs[jid].status == "stopped":
                    previous_job = jid
                    break
            
            if previous_job is None:
                job_ids.remove(current_job)
                previous_job = max(job_ids)

        for job_id in sorted(self.jobs.keys()):
            job = self.jobs[job_id]
            
            if job_id == current_job:
                marker = '+'
            elif job_id == previous_job:
                marker = '-'
            else:
                marker = ' '
                
            if job.status == "running":
                status_text = "Running"
            else:
                status_text = "Stopped"
                
            print(f"[{job_id}]{marker} {status_text}\t{job.cmd}")
            
        return EXIT_SUCCESS

    def _builtin_fg(self, args: Optional[List[str]]) -> int:
        """
        Bring a background job to the foreground.
        
        Usage: fg [%jobid]
        If no jobid is specified, brings the current job to the foreground.
        """
        if not self.jobs:
            print("fg: current: no such job")
            return EXIT_FAILURE

        try:
            if not args:
                job_id = None
                
                for jid in sorted(self.jobs.keys(), reverse=True):
                    if self.jobs[jid].status == "stopped":
                        job_id = jid
                        break
                        
                if job_id is None:
                    job_id = max(self.jobs.keys())
            else:
                arg = args[0]
                if arg.startswith("%"):
                    arg = arg[1:]
                try:
                    job_id = int(arg)
                except ValueError:
                    print(f"fg: {arg}: no such job")
                    return EXIT_FAILURE

            job = self.jobs.get(job_id)
            if not job:
                print(f"fg: %{job_id}: no such job")
                return EXIT_FAILURE

            try:
                try:
                    os.kill(job.pid, 0)
                except ProcessLookupError:
                    print(f"fg: job %{job_id} has terminated")
                    del self.jobs[job_id]
                    return EXIT_FAILURE
                
                print(job.cmd)
                
                process_terminated = False
                
                def handle_sigint(signum, frame):
                    try:
                        os.killpg(os.getpgid(job.pid), signal.SIGINT)
                        nonlocal process_terminated
                        process_terminated = True
                    except (ProcessLookupError, OSError):
                        process_terminated = True

                original_sigint = signal.signal(signal.SIGINT, handle_sigint)

                self._current_foreground_pid = job.pid
                self._current_foreground_cmd = job.cmd
                
                if job.status == "stopped":
                    try:
                        os.kill(job.pid, signal.SIGCONT)
                    except (ProcessLookupError, OSError):
                        print(f"fg: job %{job_id} has terminated")
                        del self.jobs[job_id]
                        signal.signal(signal.SIGINT, original_sigint)
                        self._current_foreground_pid = -1
                        return EXIT_FAILURE
                
                try:
                    if not process_terminated:
                        _, status = os.waitpid(job.pid, 0)
                except OSError as e:
                    if process_terminated and e.errno == 10:
                        signal.signal(signal.SIGINT, original_sigint)
                        self._current_foreground_pid = -1
                        if job_id in self.jobs:
                            del self.jobs[job_id]
                        return EXIT_INTERRUPTED
                    else:
                        signal.signal(signal.SIGINT, original_sigint)
                        self._current_foreground_pid = -1
                        print(f"fg: error waiting for job %{job_id}: {e}")
                        if job_id in self.jobs:
                            del self.jobs[job_id]
                        return EXIT_FAILURE
                        
                signal.signal(signal.SIGINT, original_sigint)
                
                self._current_foreground_pid = -1
                
                if not process_terminated and job_id in self.jobs:
                    if os.WIFEXITED(status):
                        del self.jobs[job_id]
                        return os.WEXITSTATUS(status)
                    elif os.WIFSIGNALED(status):
                        del self.jobs[job_id]
                        return 128 + os.WTERMSIG(status)
                    elif os.WIFSTOPPED(status):
                        return EXIT_SUCCESS
                
                return EXIT_SUCCESS
                
            except ProcessLookupError:
                print(f"fg: job %{job_id} has terminated")
                del self.jobs[job_id]
                return EXIT_FAILURE
            except OSError as e:
                print(f"fg: error bringing job %{job_id} to foreground: {e}")
                return EXIT_FAILURE
                
        except ValueError:
            print(f"fg: {args[0]}: no such job")
            return EXIT_FAILURE

    def _builtin_bg(self, args: Optional[List[str]]) -> int:
        """
        Resume a stopped job in the background.
        
        Usage: bg [%jobid]
        If no jobid is specified, resumes the current stopped job.
        """
        if not self.jobs:
            print("bg: current: no such job")
            return EXIT_FAILURE

        try:
            if not args:
                job_id = None
                for jid in sorted(self.jobs.keys(), reverse=True):
                    if self.jobs[jid].status == "stopped":
                        job_id = jid
                        break
                
                if job_id is None:
                    print("bg: current: no such job")
                    return EXIT_FAILURE
            else:
                arg = args[0]
                if arg.startswith("%"):
                    arg = arg[1:]
                try:
                    job_id = int(arg)
                except ValueError:
                    print(f"bg: {arg}: no such job")
                    return EXIT_FAILURE

            job = self.jobs.get(job_id)
            if not job:
                print(f"bg: %{job_id}: no such job")
                return EXIT_FAILURE

            if job.status != "stopped":
                print(f"bg: job %{job_id} already in background")
                return EXIT_FAILURE

            try:
                try:
                    os.kill(job.pid, 0)
                except ProcessLookupError:
                    print(f"bg: job %{job_id} has terminated")
                    del self.jobs[job_id]
                    return EXIT_FAILURE
                    
                try:
                    os.kill(job.pid, signal.SIGCONT)
                    job.status = "running"
                    
                    all_jobs = sorted(self.jobs.keys())
                    current_job = max(all_jobs) if all_jobs else None
                    current_mark = "+" if job_id == current_job else ""
                    
                    print(f"[{job_id}]{current_mark} {job.cmd} &")
                    
                    return EXIT_SUCCESS
                except (ProcessLookupError, OSError) as e:
                    print(f"bg: failed to continue job %{job_id}: {e}")
                    del self.jobs[job_id]
                    return EXIT_FAILURE
            except OSError as e:
                print(f"bg: error accessing job %{job_id}: {e}")
                return EXIT_FAILURE
                
        except ValueError:
            print(f"bg: {args[0]}: no such job")
            return EXIT_FAILURE

    def _builtin_history(self, args: Optional[List[str]]) -> int:
        """
        Display command history.
        
        Usage: history [n]
        Shows the last n commands (or all commands if n is not specified).
        """
        limit = None
        
        if args and args[0].isdigit():
            limit = min(int(args[0]), len(self.history))

        for i, cmd in enumerate(self.history[-limit:] if limit else self.history, 1):
            print(f"{i} {cmd}")
            
        return EXIT_SUCCESS

    def add_to_history(self, command: str) -> None:
        """
        Add command to history unless it meets certain exclusion criteria:
        1. If the command is empty
        2. If the command starts with a space
        3. If the command is identical to the previous command
        """
        if command.startswith(" "):
            return

        command = command.strip()
        
        if not command:
            return
            
        if self.history and command == self.history[-1]:
            return
            
        self.history.append(command)
        
        while len(self.history) > 50:
            self.history.popleft()

    def get_history_command(self, arg: str) -> Optional[str]:
        """
        Expands history references similar to Bash.
        
        Supports:
        - !! - Last command
        - !n - Command by number
        - !prefix - Most recent command starting with prefix
        - !?pattern? - Most recent command containing pattern
        
        If a pipe is added after the history reference, it's appended to the expanded command.
        """
        if not arg:
            return None

        pipe_parts = arg.split('|', 1)
        history_part = pipe_parts[0].strip()
        pipe_suffix = ''
        
        if len(pipe_parts) > 1:
            pipe_suffix = f" | {pipe_parts[1].strip()}"

        if history_part == "!!":
            if not self.history:
                print("!!: event not found")
                return None
            base_cmd = self.history[-1]
            return f"{base_cmd}{pipe_suffix}"

        if history_part.startswith("!") and history_part[1:].isdigit():
            index = int(history_part[1:]) - 1
            if index < 0:
                print(f"!{history_part[1:]}: event not found")
                return None
            if index < len(self.history):
                base_cmd = self.history[index]
                return f"{base_cmd}{pipe_suffix}"
            print(f"!{history_part[1:]}: event not found")
            return None

        if history_part.startswith("!"):
            cmd_prefix = history_part[1:]
            
            if not cmd_prefix:
                print("!: event not found")
                return None

            for cmd in reversed(self.history):
                if cmd.startswith(cmd_prefix):
                    return f"{cmd}{pipe_suffix}"
            
            print(f"!{cmd_prefix}: event not found")
            return None

        return None

    def _builtin_stop(self, args: Optional[List[str]]) -> int:
        """Stop a job or process (send SIGSTOP)."""        
        if not args or len(args) < 1:
            print("stop: missing job or process ID", file=sys.stderr)
            return EXIT_FAILURE
            
        try:
            target = args[0]
            pid = None
            
            if target.startswith("%"):
                try:
                    job_id = int(target[1:])
                    job = self.jobs.get(job_id)
                    if not job:
                        print(f"stop: %{job_id}: no such job", file=sys.stderr)
                        return EXIT_FAILURE
                    pid = job.pid
                except ValueError:
                    print(f"stop: {target}: invalid job ID", file=sys.stderr)
                    return EXIT_FAILURE
            else:
                try:
                    pid = int(target)
                    found = False
                    for job_id, job in self.jobs.items():
                        if job.pid == pid:
                            found = True
                            break
                    if not found:
                        print(f"Warning: PID {pid} is not a known job", file=sys.stderr)
                except ValueError:
                    print(f"stop: {target}: argument must be PID or %jobID", file=sys.stderr)
                    return EXIT_FAILURE
            
            try:
                os.kill(pid, signal.SIGSTOP)
                
                for job_id, job in self.jobs.items():
                    if job.pid == pid:
                        job.status = "stopped"
                        print(f"[{job_id}] Stopped\t{job.cmd}")
                        break
                else:
                    print(f"Process {pid} stopped")
                return EXIT_SUCCESS
                
            except ProcessLookupError:
                print(f"stop: ({pid}) - No such process", file=sys.stderr)
                for job_id, job in list(self.jobs.items()):
                    if job.pid == pid:
                        del self.jobs[job_id]
                        break
                return EXIT_FAILURE
                
            except PermissionError:
                print(f"stop: ({pid}) - Operation not permitted", file=sys.stderr)
                return EXIT_FAILURE
                
        except Exception as e:
            print(f"stop: Unexpected error: {e}", file=sys.stderr)
            return EXIT_FAILURE

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
        """Handle Ctrl+C in the main shell loop."""
        if executor._current_foreground_pid <= 0:
            print("\r")
            print("$: ", end="", flush=True)
    
    original_sigint = signal.signal(signal.SIGINT, handle_sigint)
    original_sigtstp = signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    try:
        while True:
            try:
                print("$: ", end="", flush=True)
                try:
                    line = input()
                except EOFError:
                    print("\nexit")
                    break
                except KeyboardInterrupt:
                    print()
                    continue
                
                if not line:
                    continue
                    
                line2 = line.strip()
                if line2.startswith("!"):
                    history_cmd = executor.get_history_command(line2)
                    if history_cmd:
                        line = history_cmd
                    else:
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
                    print(f"{e}", file=sys.stderr)
                    executor.last_return_code = EXIT_FAILURE
                except Exception as e:
                    print(f"Error: {e}", flush=True, file=sys.stderr)
                    executor.last_return_code = EXIT_FAILURE

            except KeyboardInterrupt:
                if executor._current_foreground_pid <= 0:
                    print("\r")
                continue
            except Exception as e:
                print(f"Unexpected error: {e}", file=sys.stderr)
                executor.last_return_code = EXIT_FAILURE
    finally:
        signal.signal(signal.SIGINT, original_sigint)
        signal.signal(signal.SIGTSTP, original_sigtstp)
        
        sys.exit(executor.last_return_code)


if __name__ == "__main__":
    try:
        main_loop()
    except Exception as e:
        print(f"{COLORS['RED']}Fatal error: {e}{COLORS['RESET']}", file=sys.stderr)
        sys.exit(EXIT_FAILURE)  