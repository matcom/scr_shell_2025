from typing import List, Tuple


class Command:
    """
    Clase que representa un comando en el AST.
    """
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
    """
    Clase que representa un pipe en el AST.
    """
    def __init__(self, left:Command, right:Command) -> None:
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"Pipe(izq=({self.left}), der=({self.right}))"


class Job:
    """
    Clase que representa un job en el AST.
    """
    def __init__(self, pid: int, cmd: str, status: str = "running") -> None:
        self.pid = pid  
        self.cmd = cmd  
        self.status = status  
        self.pids = [pid] 

    def __repr__(self) -> str:
        return f"Job(pid=({self.pid}), cmd=({self.cmd}), status=({self.status}), pids=({self.pids}))"
