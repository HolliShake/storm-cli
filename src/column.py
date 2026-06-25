


PRIMITIVE_TYPES = {'int', 'long', 'float', 'double', 'string', 'bool', 'uuid', 'datetime'}


class ColumnType:
    def __init__(self, name: str, attrs=None, is_nullable=False, default_value=None):
        self.name = name
        self.is_nullable = is_nullable
        self.attributes = attrs or {}
        self.is_fk = False
        self.ref_table = None
        self.default_value = default_value
        self.default_value_node = None

    def to_csharp(self):
        raise Exception("override")

    def to_php(self):
        raise Exception("override")

    @classmethod
    def from_ast(cls, type_node, table_names=None):
        table_names = table_names or set()
        type_name = type_node.value
        attrs_node = type_node.a

        attrs = {}
        if attrs_node:
            cur = attrs_node.a
            while cur:
                val = cur.b.value
                try:
                    val = int(val)
                except ValueError:
                    pass
                attrs[cur.a.value] = val
                cur = cur.next

        is_nullable = type_name.endswith('?')
        base_name = type_name[:-1] if is_nullable else type_name

        if base_name in PRIMITIVE_TYPES:
            return ColumnType(base_name, attrs, is_nullable)

        col = cls(base_name, attrs, is_nullable)
        if base_name in table_names:
            col.is_fk = True
            col.ref_table = base_name
        return col


class Int(ColumnType):
    def __init__(self, min=None, max=None):
        super().__init__("int", {"min": min or -2147483648, "max": max or 2147483647})