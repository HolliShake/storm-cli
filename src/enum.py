



class Enum:
    def __init__(self, name, keyValue):
        self.name = name
        self.keyValue = keyValue

    @classmethod
    def from_ast(cls, node):
        name = node.a.value
        items = []
        cur = node.b
        while cur:
            value = cur.b.value if cur.b else None
            items.append((cur.a.value, value))
            cur = cur.next
        return cls(name, items)


