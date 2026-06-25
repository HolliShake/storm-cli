



from src.column import ColumnType


PRIMITIVE_TYPES = {'int', 'long', 'float', 'double', 'string', 'bool', 'uuid', 'datetime'}


class Table:
    def __init__(self, name, columns=[]):
        self.name = name
        self.columns: list[tuple[str, ColumnType]] = columns

    @classmethod
    def from_ast(cls, node, table_names=None):
        table_names = table_names or set()
        name = node.a.value
        columns = []
        cur = node.b
        while cur:
            col_name = cur.a.value
            type_node = cur.b
            col_type = ColumnType.from_ast(type_node, table_names)
            if cur.d is not None:
                col_type.default_value_node = cur.d
            columns.append((col_name, col_type))
            cur = cur.next
        return cls(name, columns)

    def dependencies(self):
        deps = set()
        for _, col_type in self.columns:
            if col_type.is_fk and col_type.ref_table:
                deps.add(col_type.ref_table)
        return deps