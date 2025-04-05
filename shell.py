import os
import re
import subprocess
from collections import OrderedDict


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
            return "Historial vacío"

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
            f"{i+1}: {elem}" for i, elem in enumerate(reversed(ultimos_elementos))
        )

    def __contains__(self, valor):
        return any(item == valor for item in self)


class Shell:
    def __init__(self):
        self.pila = Pila()
        self.jobs = OrderedDict()
        self.next_job_id = 1
        self.last_bg_notification = None

    def add_stack(self, command):
        if len(self.pila) > 0:
            if self.pila.tail.valor != " ".join(command).strip():
                self.pila.add(" ".join(command).strip())
        else:
            self.pila.add(" ".join(command).strip())

    def parse_command(self, _command):
        __command = re.sub(r"\s+", " ", _command).strip()
        return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', __command)

    def _check_jobs(self):
        completed = []
        for job_id, (pid, proc, cmd) in list(self.jobs.items()):
            if proc.poll() is not None:
                status = proc.returncode
                notification = f"[{job_id}]  {'Done' if status == 0 else f'Exit {status}'}    {cmd}"

                if notification != self.last_bg_notification:
                    print(f"\n{notification}", file=sys.stderr, flush=True)
                    self.last_bg_notification = notification

                completed.append(job_id)

        for job_id in completed:
            self.jobs.pop(job_id)

    def sub(self, command, shell=False, background=False):
        if shell and isinstance(command, list):
            command = " ".join(command)
        try:
            if background:
                proc = subprocess.Popen(
                    command,
                    shell=shell,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                job_id = self.next_job_id
                self.jobs[job_id] = (proc.pid, proc, command)
                self.next_job_id += 1
                print(f"[{job_id}] {proc.pid}", flush=True)
                return proc
            else:
                return subprocess.run(
                    command,
                    check=True,
                    shell=shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
        except subprocess.CalledProcessError as e:
            print(f"Error: {e.stderr.strip()}", flush=True)
            return None
        except Exception as e:
            print(f"Error: {str(e)}", flush=True)
            return None

    def execute(self, command):
        if not command:
            return

        self._check_jobs()

        if command[0] == "jobs":
            for job_id, (pid, proc, cmd) in self.jobs.items():
                status = "Running" if proc.poll() is None else "Done"
                print(f"[{job_id}] {pid} {status}\t\t{cmd}", flush=True)
            return

        if command[0] == "fg":
            if not command[1:]:
                if not self.jobs:
                    print("fg: no current job", flush=True)
                    return
                job_id, (pid, proc, cmd) = next(reversed(self.jobs.items()))
            else:
                try:
                    job_id = int(command[1])
                    pid, proc, cmd = self.jobs[job_id]
                except (KeyError, ValueError):
                    print(f"fg: {command[1]}: no such job", flush=True)
                    return

            print(cmd, flush=True)
            try:
                return_code = proc.wait()
                if return_code == 0:
                    print(f"[{job_id}]+\tDone\t\t{cmd}", flush=True)
                else:
                    print(f"[{job_id}]+\tExit {return_code}\t\t{cmd}", flush=True)
                self.jobs.pop(job_id)
            except KeyboardInterrupt:
                print(f"[{job_id}]+\tStopped\t\t{cmd}", flush=True)
                proc.terminate()
                self.jobs.pop(job_id)
            return

        background = False
        if "&" in command[-1]:
            background = True
            command = command[:-1]

        if command[0] == "cd":
            try:
                os.chdir(command[1] if len(command) > 1 else os.path.expanduser("~"))
            except Exception as e:
                print(
                    f"cd: {e.args[1] if len(e.args) > 1 else str(e)}: {command[1] if len(command) > 1 else ''}",
                    flush=True,
                )
            return

        if command[0] == "history":
            print(self.pila, flush=True)
            return

        result = self.sub(command, True, background)
        if result and not background and hasattr(result, "stdout"):
            print(result.stdout.strip(), end="\n", flush=True)

    def search_history(self, comando):
        if len(comando) == 1:
            return
        elif comando == "!!":
            if self.pila.size > 0:
                ultimo_comando = self.pila.tail.valor
                command = self.parse_command(ultimo_comando)
                self.execute(command)
                return command
            else:
                print("No hay comandos en el historial", flush=True)
        elif comando.startswith("!") and comando[1:].isdigit():
            try:
                comand = self.pila.search(comando[1:])
                result = self.parse_command(comand)
                self.execute(result)
                return result
            except IndexError:
                print(f"No existe el comando en la posición {comando[1:]}", flush=True)
                return -1
        else:
            try:
                comand = self.pila.search_comand(comando[1:])
                result = self.parse_command(comand)
                self.execute(result)
                return result
            except IndexError:
                print(f"No existe el comando: {comando[1:]}", flush=True)
                return -1

    def process_input(self, input_line):
        if input_line.strip() == "":
            return

        command = self.parse_command(input_line)

        if input_line.startswith("!"):
            result = self.search_history(input_line)
            if result != -1 and input_line[0] != " ":
                self.add_stack(result)
            return

        if input_line[0] != " ":
            self.add_stack(command)

        self.execute(command)

    def run(self):
        while True:
            try:
                if not self.last_bg_notification:
                    print("$ ", end="", flush=True)
                else:
                    self.last_bg_notification = None
                    print("\n$ ", end="", flush=True)
                input_line = input()
                self.process_input(input_line)
            except KeyboardInterrupt:
                print("^C", flush=True)
                continue
            except EOFError:
                print("exit", flush=True)
                break


if __name__ == "__main__":
    shell = Shell()
    shell.run()
