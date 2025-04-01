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

    def add(self, valor):
        new_nodo = Nodo(valor)
        new_nodo.back = self.tail
        self.tail = new_nodo
        self.size += 1
        self._cache = None

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
            return "Pila vacía"

        if self._cache and len(self._cache) == self.size:
            elementos = self._cache
        else:
            elementos = list(self)

        return "\n".join(f"{i+1}: {elem}" for i, elem in enumerate(elementos[::-1]))

    def __contains__(self, valor):
        return any(item == valor for item in self)
