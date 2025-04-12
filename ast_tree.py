from typing import List, Tuple


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


class Job:
    def __init__(self, pid: int, cmd: str, status: str = "running") -> None:
        self.pid = pid
        self.cmd = cmd
        self.status = status