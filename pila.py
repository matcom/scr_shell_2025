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

    def pop(self):
        if not self.tail:
            raise IndexError("No hay elementos en la pila")
        valor = self.tail.valor
        self.tail = self.tail.back
        self.size -= 1
        self._cache = None
        return valor

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

        ultimos_elementos = elementos[-50:] if len(elementos) > 50 else elementos

        return "\n".join(
            f"{i+1}: {elem}" for i, elem in enumerate(reversed(ultimos_elementos))
        )

    def __contains__(self, valor):
        return any(item == valor for item in self)
