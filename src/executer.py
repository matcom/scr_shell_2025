import os
import signal
import subprocess
import sys
from typing import Dict, List, Optional, Tuple,Deque
from collections import deque
from src.ast_tree import Command, Pipe, Job
import glob

COLORS = {
    "RESET": "\033[0m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "BRIGHT_CYAN": "\033[1;96m",
}
class CommandExecutor:
    """
    Clase que representa el ejecutor de comandos.
    """
    def __init__(self) -> None:
        self.env = os.environ.copy()
        self.last_return_code = 0
        self.jobs: Dict[int, Job] = {}
        self.current_job_id = 1
        self.history: Deque[str] = deque(maxlen=50)
        self.alias: Dict[str, str] = {}
        signal.signal(signal.SIGCHLD, self._handle_sigchld)

    def _handle_sigchld(self, signum, frame) -> None:
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
                            print(f"\r{COLORS['GREEN']}$:{COLORS['RESET']} ", end="")
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

    def execute(self, node) -> int:
        try:
            if isinstance(node, (Command, Pipe)):
                cmd_str = self._ast_to_string(node)

            if isinstance(node, Command):
                return self._execute_command(node)
            elif isinstance(node, Pipe):
                return self._execute_pipe(node)
            else:
                raise ValueError(f"Unknown node type: {type(node)}")
        except Exception as e:
            self.last_return_code = 1
            return 1

    def _ast_to_string(self, node) -> str:
        if isinstance(node, Command):
            parts = []
            for arg in node.args:
                if " " in arg:
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
        if not cmd.args:
            return 0

        if cmd.args[0] == "cd":
            return self._builtin_cd(cmd.args[1:])
        elif cmd.args[0] == "exit":
            sys.exit(0)
        elif cmd.args[0] == "jobs":
            return self._builtin_jobs()
        elif cmd.args[0] == "fg":
            return self._builtin_fg(cmd.args[1:] if len(cmd.args) > 1 else None)
        elif cmd.args[0] == "history":
            return self._builtin_history(cmd.args[1:] if len(cmd.args) > 1 else None)

        return self._spawn_process(cmd.args, cmd.redirects, cmd.background)

    def _spawn_process(
        self, args: List[str], redirects: List[Tuple[str, str]], background: bool
    ) -> int:
        expanded_args = []
        for arg in args:
            if '*' in arg or '?' in arg:
                matches = glob.glob(arg)
                if matches:
                    expanded_args.extend(matches)
                else:
                  
                    expanded_args.append(arg)
            else:
                expanded_args.append(arg)
        
        args = expanded_args

        if not args:
            return 0

        stdin = None
        stdout = None
        stderr = None

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
                    f"{COLORS['RED']}Cannot open file: {e}{COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1

        try:
            final_stdout = stdout or sys.stdout

            process = subprocess.Popen(
                args,
                stdin=stdin or sys.stdin,
                stdout=final_stdout,
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
                return 0
            else:
                try:
                    process.wait()
                    self.last_return_code = process.returncode
                    return process.returncode
                except KeyboardInterrupt:
                    os.killpg(os.getpgid(process.pid), signal.SIGINT)
                    process.wait()
                    self.last_return_code = 128 + signal.SIGINT
                    return self.last_return_code
        except FileNotFoundError:
            print(
                f"{COLORS['RED']}{args[0]}: command not found{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return 127
        except Exception as e:
            print(
                f"{COLORS['RED']}Error executing command: {e}{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return 1
        finally:
            for f in [stdin, stdout]:
                if f and f not in [sys.stdin, sys.stdout, sys.stderr]:
                    f.close()

    def _execute_pipe(self, pipe_node: Pipe) -> int:
        commands = []
        self._flatten_pipes(pipe_node, commands)

        background = False
        if commands and commands[-1].background:
            background = True
            for cmd in commands:
                cmd.background = False

        processes = []
        prev_stdout = None

        for i, cmd in enumerate(commands):
            try:
               
                expanded_args = []
                for arg in cmd.args:
                    if '*' in arg or '?' in arg:
                        matches = glob.glob(arg)
                        if matches:
                            expanded_args.extend(matches)
                        else:
                            
                            expanded_args.append(arg)
                    else:
                        expanded_args.append(arg)
                
                cmd.args = expanded_args

                if not cmd.args:
                    continue

               
                if not cmd.args:
                    print(f"{COLORS['RED']}Warning: Empty command in pipe at position {i}{COLORS['RESET']}", file=sys.stderr)
                    continue

                stdin = prev_stdout
                
                stdout = subprocess.PIPE if i < len(commands) - 1 else None
                stderr = None

                stdin_redir = None
                stdout_redir = None

                for r_type, filename in cmd.redirects:
                    try:
                        if r_type == "IN" and i == 0:
                            stdin_redir = open(filename, "r")
                        elif r_type == "OUT" and i == len(commands) - 1:
                            stdout_redir = open(filename, "w")
                        elif r_type == "APPEND" and i == len(commands) - 1:
                            stdout_redir = open(filename, "a")
                    except IOError as e:
                        print(
                            f"{COLORS['RED']}Cannot open file: {e}{COLORS['RESET']}",
                            file=sys.stderr,
                            flush=True,
                        )
                        return 1

                
                final_stdout = stdout_redir or stdout
                if i == len(commands) - 1 and final_stdout is None:
                    final_stdout = sys.stdout

                process = subprocess.Popen(
                    cmd.args,
                    stdin=stdin_redir or stdin,
                    stdout=final_stdout,
                    stderr=stderr,
                    env=self.env,
                    universal_newlines=True,
                    preexec_fn=os.setsid,
                )

                processes.append(process)

                if prev_stdout and prev_stdout not in (sys.stdin, None):
                    prev_stdout.close()

                prev_stdout = process.stdout

            except FileNotFoundError:
                print(
                    f"{COLORS['RED']}{cmd.args[0]}: command not found {COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
                for p in processes:
                    p.terminate()
                return 127

        if background:
            job_id = self.current_job_id
            self.jobs[job_id] = Job(processes[-1].pid, self._ast_to_string(pipe_node))
            self.current_job_id += 1
            print(
                f"{COLORS['CYAN']}[{job_id}] {processes[-1].pid}{COLORS['RESET']}",
                flush=True,
            )
            return 0
        else:
            try:
                for p in processes:
                    p.wait()
              
                if processes:
                    return_code = processes[-1].returncode
                    self.last_return_code = return_code
                    return return_code
                return 0
            except KeyboardInterrupt:
                for p in processes:
                    try:
                        os.killpg(os.getpgid(p.pid), signal.SIGINT)
                        p.wait()
                    except (ProcessLookupError, OSError):
                        pass
                self.last_return_code = 128 + signal.SIGINT
                return self.last_return_code

    def _flatten_pipes(self, node, result: List[Command]) -> None:
        if isinstance(node, Pipe):
            self._flatten_pipes(node.left, result)
            self._flatten_pipes(node.right, result)
        elif isinstance(node, Command):
            result.append(node)
        else:
            raise ValueError("Invalid node in pipe")

    def _builtin_cd(self, args: List[str]) -> int:

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
                    return 1
                new_dir = self._prev_dir
                print(f"move to => {COLORS['GREEN']}{new_dir}{COLORS['RESET']}")
            else:
                new_dir = args[0]

            current_dir = os.getcwd()
            os.chdir(new_dir)

            self._prev_dir = current_dir

            return 0
        except Exception as e:
            print(
                f"{COLORS['RED']}cd: {e}{COLORS['RESET']}", file=sys.stderr, flush=True
            )
            return 1

    def _builtin_jobs(self) -> int:
        if not self.jobs:
            print("No background jobs", file=sys.stderr)
            return 0

        for job_id, job in self.jobs.items():
            print(
                f"{COLORS['CYAN']}[{job_id}] {job.pid} {job.status} {job.cmd}{COLORS['RESET']}",
                flush=True,
            )
        return 0

    def _builtin_fg(self, args: Optional[List[str]]) -> int:
        if not self.jobs:
            print(
                f"{COLORS['MAGENTA']}fg: no current job{COLORS['RESET']}",
                file=sys.stderr,
                flush=True,
            )
            return 1

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
                    f"{COLORS['RED']}fg: {job_id}: no such job{COLORS['RESET']}",
                    file=sys.stderr,
                    flush=True,
                )
                return 1

            try:

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
                    print(f"\r{COLORS['GREEN']}$:{COLORS['RESET']} ",flush=True)
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
                    job.status = "stopped"
                return 0

            except ProcessLookupError:
                print(
                    f"{COLORS['MAGENTA']}fg: job {job_id} has terminated{COLORS['RESET']}",
                    flush=True,
                    file=sys.stderr,
                )
                del self.jobs[job_id]
                return 1
        except ValueError:
            print(
                f"{COLORS['RED']}fg: job ID must be a number{COLORS['RESET']}",
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
                cmd_base = command.split()[0]
                if cmd_base not in self.alias:
                    self.alias[cmd_base] = command

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
       