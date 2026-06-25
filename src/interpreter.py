




from collections import deque

from src.ast import AstType
from src.enum import Enum
from src.error_handler import raise_error
from src.parser import Parser
from src.table import Table


class Interpreter(Parser):
    def __init__(self, filename):
        super().__init__(filename)
        ast = self.parse()
        self.tables = {}
        self.enums = {}
        self.deps = {}
        self._ordered = []
        self._collect(ast)

    def _collect(self, ast):
        cur = ast.next
        while cur:
            if cur.node_type == AstType.TABLE_DECL:
                name = cur.a.value
                self.tables[name] = cur
            elif cur.node_type == AstType.ENUM_DECL:
                name = cur.a.value
                self.enums[name] = cur
            cur = cur.next

        table_names = set(self.tables.keys())

        for name, table_node in self.tables.items():
            deps = set()
            field = table_node.b
            while field:
                type_node = field.b
                type_name = type_node.value.rstrip('?')
                if type_name in table_names and type_name != name:
                    deps.add(type_name)
                field = field.next
            self.deps[name] = deps

        self._ordered = self._topological_sort()

    def _topological_sort(self):
        indegree = {name: 0 for name in self.tables}
        for name, deps in self.deps.items():
            indegree[name] = len(deps)

        queue = deque(name for name, deg in indegree.items() if deg == 0)
        ordered = []

        while queue:
            current = queue.popleft()
            ordered.append(current)
            for name, deps in self.deps.items():
                if current in deps:
                    indegree[name] -= 1
                    if indegree[name] == 0:
                        queue.append(name)

        if len(ordered) != len(self.tables):
            remaining = set(self.tables.keys()) - set(ordered)
            ordered.extend(remaining)

        return ordered

    def _try_op(self, node, op_fn, zero_fn=None):
        try:
            return op_fn()
        except TypeError as e:
            raise_error(self.file_path, self.file_data, f"type error: {e}", node.position)
        except ZeroDivisionError:
            if zero_fn:
                return zero_fn()
            raise_error(self.file_path, self.file_data, "division by zero", node.position)

    def _evaluate_expression(self, node):
        if node is None:
            return None

        nt = node.node_type

        if nt == AstType.INT_LITERAL:
            return int(node.value)
        if nt == AstType.STR_LITERAL:
            return node.value
        if nt == AstType.BOOL_LITERAL:
            return node.value == 'true'
        if nt == AstType.IDENTIFIER:
            return None

        l = self._evaluate_expression(node.a)
        r = self._evaluate_expression(node.b)

        if nt == AstType.BINARY_ADD:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l + r)
        if nt == AstType.BINARY_SUB:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l - r)
        if nt == AstType.BINARY_MUL:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l * r)
        if nt == AstType.BINARY_DIV:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l / r)
        if nt == AstType.BINARY_MOD:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l % r)

        if nt == AstType.UNARY_MINUS:
            if l is None:
                return None
            return self._try_op(node, lambda: -l)
        if nt == AstType.UNARY_PLUS:
            if l is None:
                return None
            return self._try_op(node, lambda: +l)
        if nt == AstType.UNARY_NOT:
            if l is None:
                return None
            return self._try_op(node, lambda: not l)
        if nt == AstType.UNARY_BITWISE_NOT:
            if l is None:
                return None
            return self._try_op(node, lambda: ~l)

        if nt == AstType.BINARY_EQ:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l == r)
        if nt == AstType.BINARY_NE:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l != r)
        if nt == AstType.BINARY_LT:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l < r)
        if nt == AstType.BINARY_LTE:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l <= r)
        if nt == AstType.BINARY_GT:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l > r)
        if nt == AstType.BINARY_GTE:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l >= r)

        if nt == AstType.BINARY_SHL:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l << r)
        if nt == AstType.BINARY_SHR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l >> r)
        if nt == AstType.BINARY_BITWISE_AND:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l & r)
        if nt == AstType.BINARY_BITWISE_XOR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l ^ r)
        if nt == AstType.BINARY_BITWISE_OR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l | r)

        if nt == AstType.BINARY_LOGICAL_AND:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l and r)
        if nt == AstType.BINARY_LOGICAL_OR:
            if l is None or r is None:
                return None
            return self._try_op(node, lambda: l or r)

        return None

    def get_tables(self):
        table_names = set(self.tables.keys())
        result = []
        for name in self._ordered:
            node = self.tables[name]
            table = Table.from_ast(node, table_names)
            for _, ct in table.columns:
                if ct.default_value_node is not None:
                    ct.default_value = self._evaluate_expression(ct.default_value_node)
            result.append(table)
        return result

    def get_enums(self):
        return [Enum.from_ast(node) for node in self.enums.values()]

    def get_table_order(self):
        return list(self._ordered)



