import os
import re
import subprocess


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
        self.next_jobs = 0

    def add_stack(self, command):
        if len(self.pila) > 0:
            if self.pila.tail.valor != " ".join(command).strip():
                self.pila.add(" ".join(command).strip())
        else:
            self.pila.add(" ".join(command).strip())

    def parse_command(self, _command):
        __command = re.sub(r"\s+", " ", _command).strip()
        return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', __command)

    def sub(self, command, shell=False, background=False):
        if shell and isinstance(command, list):
            command = " ".join(command)
        try:
            if background:
                return subprocess.Popen(
                    command,
                    shell=shell,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
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
        except Exception as e:
            print(f"{e.stderr}", end="", flush=True)
            return

    def execute(self, command):
        if not command:
            return

        background = False
        if "&" == command[-1]:
            background = True
            command = command[:-1]

        if command[0] == "cd":
            try:
                os.chdir(command[1] if len(command) > 1 else os.path.expanduser("~"))
            except Exception as e:
                print(f"cd: {e.args[1]}: {command[1]}", flush=True)
            return

        if command[0] == "history":
            print(self.pila, flush=True)
            return

        result = self.sub(command, True, background)
        if result and not background:
            print(result.stdout.strip(), end="\n", flush=True)
        elif background:
            self.next_jobs += 1
            print(f"[{self.next_jobs}]\t{result.pid}", flush=True)

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

    @property
    def run(self):
        while True:
            try:
                print("$ ", end="", flush=True)
                input_line = input()
                self.process_input(input_line)
            except KeyboardInterrupt:
                print()
                continue


if __name__ == "__main__":
    Shell().run
