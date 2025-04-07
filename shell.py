import os
import re
import subprocess
import threading
from collections import defaultdict
import signal


COLORS = {
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "MAGENTA": "\033[95m",
    "CYAN": "\033[96m",
    "WHITE": "\033[97m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
}


class Nodo:
    def __init__(self, valor):
        self.valor = valor
        self.back = None

    def __str__(self):
        return str(self.valor)


class Pila:
    def __init__(self):
        self.tail = None
        self.size = 0
        self._cache = None
        self.max_size = 50

    def search(self, comando):
        if self._cache and len(self._cache) == self.size:
            elementos = self._cache
        else:
            elementos = list(self)
        ultimos_elementos = (
            elementos[-self.max_size :]
            if len(elementos) >= self.max_size
            else elementos
        )
        for i, elem in enumerate(reversed(ultimos_elementos)):
            if i + 1 == int(comando.strip()):
                return elem
        raise IndexError()

    def search_comand(self, comand):
        if self._cache and len(self._cache) == self.size:
            elementos = self._cache
        else:
            elementos = list(self)

        ultimos_elementos = (
            elementos[-self.max_size :]
            if len(elementos) >= self.max_size
            else elementos
        )
        for i in ultimos_elementos:
            if i.split()[0] == comand:
                return i
        raise IndexError()

    def add(self, valor):
        new_nodo = Nodo(valor)
        new_nodo.back = self.tail
        self.tail = new_nodo
        self.size += 1

        if self.size > self.max_size:
            self._eliminar_mas_antiguo()

        self._cache = None

    def _eliminar_mas_antiguo(self):
        if self.size <= 1:
            self.tail = None
            self.size = 0
            return
        actual = self.tail
        while actual.back and actual.back.back:
            actual = actual.back
        actual.back = None
        self.size -= 1

    def __iter__(self):
        actual = self.tail
        while actual:
            yield actual.valor
            actual = actual.back

    def __getitem__(self, index):
        if index < 0 or index >= self.size:
            raise IndexError("Índice fuera de rango")

        if self._cache and len(self._cache) == self.size:
            return self._cache[index]

        self._cache = list(self)
        return self._cache[index]

    def __len__(self):
        return self.size

    def __str__(self):
        if not self.tail:
            return f"{COLORS['YELLOW']}Historial vacío{COLORS['RESET']}"

        if self._cache and len(self._cache) == self.size:
            elementos = self._cache
        else:
            elementos = list(self)

        ultimos_elementos = (
            elementos[-self.max_size :]
            if len(elementos) >= self.max_size
            else elementos
        )

        return "\n".join(
            f"{COLORS['CYAN']}{i+1}:{COLORS['RESET']} {elem}"
            for i, elem in enumerate(reversed(ultimos_elementos))
        )

    def __contains__(self, valor):
        return any(item == valor for item in self)


class Shell:
    def __init__(self):
        self.pila = Pila()
        self.jobs = {}
        self.next_job_id = 1
        self.current_fg_job = None
        self.prompt_ready = True
        self.original_sigint = signal.getsignal(signal.SIGINT)

    def add_stack(self, command):
        if len(self.pila) > 0:
            if self.pila.tail.valor != " ".join(command).strip():
                self.pila.add(" ".join(command).strip())
        else:
            self.pila.add(" ".join(command).strip())

    def parse_command(self, _command):
        tokens = []
        current_token = []
        in_quote = None

        for char in _command:
            if char in ('"', "'"):
                if in_quote == char:
                    in_quote = None
                    if current_token:
                        tokens.append("".join(current_token))
                        current_token = []
                elif in_quote is None:
                    in_quote = char
                else:
                    current_token.append(char)
            elif in_quote is not None:
                current_token.append(char)
            elif char in (">", "<", "|", "&"):
                if current_token:
                    tokens.append("".join(current_token).strip())
                    current_token = []
                tokens.append(char)
            elif char.isspace():
                if current_token:
                    tokens.append("".join(current_token).strip())
                    current_token = []
            else:
                current_token.append(char)

        if current_token:
            tokens.append("".join(current_token).strip())

        i = 0
        while i < len(tokens) - 1:
            if tokens[i] in (">", "<") and tokens[i + 1] == tokens[i]:
                tokens[i] += tokens[i + 1]
                del tokens[i + 1]
            else:
                i += 1

        tokens = [t for t in tokens if t]

        return tokens

    def execute_in_bg(self, comando):
        proceso = subprocess.Popen(
            comando,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        return proceso

    def wait_and_notify(self, proceso, comando_str, job_id):
        proceso.wait()
        self.prompt_ready = True
        codigo_retorno = proceso.returncode
        if codigo_retorno == 0:
            print(
                f"\n{COLORS['GREEN']}[{job_id}] '{comando_str}' finalizó con éxito.{COLORS['RESET']}",
                flush=True,
            )
            print("$ ", end="")
        else:
            print(
                f"\n{COLORS['RED']}[{job_id}] '{comando_str}' falló con código {codigo_retorno}.{COLORS['RESET']}",
                flush=True,
            )
            print("$ ", end="")
            return
        self.jobs.pop(job_id, None)

    def sub(self, command, shell=False, background=False):
        if shell and isinstance(command, list):
            command = " ".join(command)
        try:
            if background:
                self.prompt_ready = False
                proceso = self.execute_in_bg(command)
                job_id = self.next_job_id
                self.next_job_id += 1
                self.jobs[job_id] = {
                    "pid": proceso.pid,
                    "command": command,
                    "process": proceso,
                    "status": "running",
                }
                threading.Thread(
                    target=self.wait_and_notify,
                    args=(proceso, command, job_id),
                    daemon=True,
                ).start()
                return job_id, proceso
            else:
                signal.signal(signal.SIGINT, self.original_sigint)
                result = subprocess.run(
                    command,
                    check=True,
                    shell=shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                signal.signal(signal.SIGINT, self.handle_sigint)
                return result
        except subprocess.CalledProcessError as e:
            print(f"{COLORS['RED']}{e.stderr}{COLORS['RESET']}", end="", flush=True)
            return None
        except Exception as e:
            print(f"{COLORS['RED']}Error: {str(e)}{COLORS['RESET']}", flush=True)
            return None

    def handle_sigint(self, signum, frame):
        if self.current_fg_job:
            job = self.jobs.get(self.current_fg_job)
            if job:
                try:
                    os.kill(job["pid"], signal.SIGINT)
                    print()
                except ProcessLookupError:
                    pass
        else:
            print(
                f"\n{COLORS['YELLOW']}Para salir use 'exit' o Ctrl+D{COLORS['RESET']}"
            )
            print("$ ", end="", flush=True)

    def execute(self, command):
        if not command:
            return

        background = False
        if command[-1] == "&":
            background = True
            command = command[:-1]

        if command[0] == "cd":
            try:
                os.chdir(command[1] if len(command) > 1 else os.path.expanduser("~"))
            except Exception as e:
                print(
                    f"{COLORS['RED']}cd: {e.args[1]}: {command[1]}{COLORS['RESET']}",
                    flush=True,
                )
            return

        if command[0] == "history" and len(command) == 1:
            print(self.pila, flush=True)
            return

        if command[0] == "jobs":
            self.list_jobs()
            return

        if command[0] == "fg" and len(command) <= 2:
            self.foreground_job(command[1] if len(command) > 1 else None)
            return

        if command[0] == "bg" and len(command) <= 2:
            self.background_job(command[1] if len(command) > 1 else None)
            return

        if command[0] == "exit":
            raise EOFError()

        result = self.sub(command, True, background)
        if result and not background:
            if isinstance(result, subprocess.CompletedProcess):
                print(result.stdout, end="", flush=True)
        elif background and result:
            job_id, proceso = result
            print(
                f"{COLORS['CYAN']}[{job_id}] {proceso.pid}{COLORS['RESET']}", flush=True
            )

    def list_jobs(self):
        if not self.jobs:
            print(
                f"{COLORS['YELLOW']}No hay trabajos en segundo plano{COLORS['RESET']}",
                flush=True,
            )
            return

        for job_id, job_info in self.jobs.items():
            status_color = (
                COLORS["YELLOW"] if job_info["status"] == "stopped" else COLORS["GREEN"]
            )
            status = "Detenido" if job_info["status"] == "stopped" else "Ejecutando"
            print(
                f"{COLORS['CYAN']}[{job_id}]{COLORS['RESET']} {job_info['pid']} {status_color}{status}{COLORS['RESET']}\t{job_info['command']}",
                flush=True,
            )

    def foreground_job(self, job_spec=None):
        if not job_spec:
            if not self.jobs:
                print(
                    f"{COLORS['RED']}fg: no hay trabajos actuales{COLORS['RESET']}",
                    flush=True,
                )
                return
            job_id = max(self.jobs.keys())
        else:
            try:
                job_id = int(job_spec)
            except ValueError:
                print(
                    f"{COLORS['RED']}fg: argumento debe ser un ID de trabajo{COLORS['RESET']}",
                    flush=True,
                )
                return

        job = self.jobs.get(job_id)
        if not job:
            print(
                f"{COLORS['RED']}fg: {job_id}: no existe ese trabajo{COLORS['RESET']}",
                flush=True,
            )
            return

        self.current_fg_job = job_id
        try:
            os.kill(job["pid"], signal.SIGCONT)
            job["status"] = "running"

            print(
                f"{COLORS['BLUE']}Reanudando: {job['command']}{COLORS['RESET']}",
                flush=True,
            )
            job["process"].wait()
            self.jobs.pop(job_id, None)
            self.current_fg_job = None
            # print("$ ", end="", flush=True)
        except KeyboardInterrupt:
            self.current_fg_job = None
            # print("$ ", end="", flush=True)
        except Exception as e:
            print(f"{COLORS['RED']}fg: error: {str(e)}{COLORS['RESET']}", flush=True)
            print("$ ", end="", flush=True)

    def background_job(self, job_spec=None):
        if not job_spec:
            stopped_jobs = [
                jid for jid, job in self.jobs.items() if job["status"] == "stopped"
            ]
            if not stopped_jobs:
                print(
                    f"{COLORS['RED']}bg: no hay trabajos detenidos{COLORS['RESET']}",
                    flush=True,
                )
                return
            job_id = max(stopped_jobs)
        else:
            try:
                job_id = int(job_spec)
            except ValueError:
                print(
                    f"{COLORS['RED']}bg: argumento debe ser un ID de trabajo{COLORS['RESET']}",
                    flush=True,
                )
                return

        job = self.jobs.get(job_id)
        if not job:
            print(
                f"{COLORS['RED']}bg: {job_id}: no existe ese trabajo{COLORS['RESET']}",
                flush=True,
            )
            return
        try:
            os.kill(job["pid"], signal.SIGCONT)
            job["status"] = "running"
            print(
                f"{COLORS['CYAN']}[{job_id}] {job['command']} &{COLORS['RESET']}",
                flush=True,
            )
        except Exception as e:
            print(f"{COLORS['RED']}bg: error: {str(e)}{COLORS['RESET']}", flush=True)

    def search_history(self, comando):
        if len(comando) == 1:
            return ["!"]
        elif comando == "!!":
            if self.pila.size > 0:
                ultimo_comando = self.pila.tail.valor
                command = self.parse_command(ultimo_comando)
                self.execute(command)
                return command
            else:
                print(
                    f"{COLORS['MAGENTA']}No hay comandos en el historial{COLORS['RESET']}",
                    flush=True,
                )
                return -1
        elif comando.startswith("!") and comando[1:].isdigit():
            try:
                comand = self.pila.search(comando[1:])
                result = self.parse_command(comand)
                self.execute(result)
                return result
            except IndexError:
                print(
                    f"{COLORS['RED']}No existe el comando en la posición {comando[1:]}{COLORS['RESET']}",
                    flush=True,
                )
                return -1
        else:
            try:
                comand = self.pila.search_comand(comando[1:])
                result = self.parse_command(comand)
                self.execute(result)
                return result
            except IndexError:
                print(
                    f"{COLORS['RED']}No existe el comando: {comando[1:]}{COLORS['RESET']}",
                    flush=True,
                )
                return -1

    def process_input(self, input_line):
        if input_line.strip() == "":
            return

        command = self.parse_command(input_line)
        if command[0].startswith("!"):
            result = self.search_history(command[0])
            if result != -1 and input_line[0] != " ":
                self.add_stack(result)
            return

        if input_line[0] != " ":
            self.add_stack(command)

        self.execute(command)

    @property
    def run(self):
        signal.signal(signal.SIGINT, self.handle_sigint)
        while True:
            try:
                # print("$ ", end="", flush=True)
                input_line = input("$ ")
                self.process_input(input_line)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print(f"{COLORS['GREEN']}Saliendo...{COLORS['RESET']}", flush=True)
                break


if __name__ == "__main__":
    Shell().run
