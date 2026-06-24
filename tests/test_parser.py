import sys
import tempfile
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.parser import Parser
from src.ast import AstType


def parse(src):
    fp = tempfile.NamedTemporaryFile(mode='w', suffix='.storm', delete=False)
    fp.write(src)
    fp.close()
    p = Parser(fp.name)
    ast = p.parse()
    os.unlink(fp.name)
    return ast


def collect(node):
    items = []
    cur = node
    while cur:
        items.append((cur.node_type, cur.value))
        cur = cur.next
    return items


class TestParserEnum:
    def test_empty_enum(self):
        ast = parse('enum E {}')
        decls = collect(ast.next)
        assert len(decls) == 1
        assert decls[0] == (AstType.ENUM_DECL, '')
        assert ast.next.a.value == 'E'

    def test_enum_with_item(self):
        ast = parse('enum E { A = "x" }')
        enum = ast.next
        assert enum.a.value == 'E'
        item = enum.b
        assert item.node_type == AstType.ENUM_ITEM
        assert item.a.value == 'A'
        assert item.b.value == 'x'

    def test_enum_multiple_items(self):
        ast = parse('enum E { A = "x" B = "y" }')
        enum = ast.next
        first = enum.b
        second = first.next
        assert first.a.value == 'A'
        assert second.a.value == 'B'


class TestParserTable:
    def test_empty_table(self):
        ast = parse('table T {}')
        t = ast.next
        assert t.node_type == AstType.TABLE_DECL
        assert t.a.value == 'T'
        assert t.b is None

    def test_simple_field(self):
        ast = parse('table T { name:string; }')
        t = ast.next
        f = t.b
        assert f.a.value == 'name'
        assert f.b.value == 'string'

    def test_field_with_pk(self):
        ast = parse('table T { id:int pk; }')
        f = ast.next.b
        assert f.a.value == 'id'
        assert f.b.value == 'int'
        assert f.value == 'pk'

    def test_field_with_unique(self):
        ast = parse('table T { email:string unique; }')
        f = ast.next.b
        assert f.value == 'unique'

    def test_field_nullable(self):
        ast = parse('table T { id:int?; }')
        f = ast.next.b
        assert f.b.value == 'int?'

    def test_field_with_default(self):
        ast = parse('table T { x:int = 42; }')
        f = ast.next.b
        assert f.d.node_type == AstType.INT_LITERAL
        assert f.d.value == '42'

    def test_field_with_attrs(self):
        ast = parse('table T { x:string(min=0,max=100); }')
        f = ast.next.b
        type_node = f.b
        attrs = type_node.a
        assert attrs.node_type == AstType.FIELD_ATTRS
        a1 = attrs.a
        assert a1.a.value == 'min'
        assert a1.b.value == '0'
        a2 = a1.next
        assert a2.a.value == 'max'
        assert a2.b.value == '100'

    def test_multiple_fields(self):
        ast = parse('table T { a:int; b:string; }')
        t = ast.next
        f1 = t.b
        f2 = f1.next
        assert f1.a.value == 'a'
        assert f2.a.value == 'b'

    def test_field_type_from_keyword(self):
        ast = parse('table T { x:uuid; }')
        assert ast.next.b.b.value == 'uuid'

    def test_field_type_from_identifier(self):
        ast = parse('table T { owner:User; }')
        assert ast.next.b.b.value == 'User'


class TestParserExpressions:
    def test_literal_int(self):
        ast = parse('table T { x:int = 42; }')
        assert ast.next.b.d.value == '42'

    def test_binary_add(self):
        ast = parse('table T { x:int = 1 + 2; }')
        expr = ast.next.b.d
        assert expr.node_type == AstType.BINARY_ADD
        assert expr.a.value == '1'
        assert expr.b.value == '2'

    def test_precedence_mul_over_add(self):
        ast = parse('table T { x:int = 1 + 2 * 3; }')
        expr = ast.next.b.d
        assert expr.node_type == AstType.BINARY_ADD
        assert expr.a.value == '1'
        assert expr.b.node_type == AstType.BINARY_MUL
        assert expr.b.a.value == '2'
        assert expr.b.b.value == '3'

    def test_parentheses(self):
        ast = parse('table T { x:int = (1 + 2) * 3; }')
        expr = ast.next.b.d
        assert expr.node_type == AstType.BINARY_MUL
        assert expr.a.node_type == AstType.BINARY_ADD
        assert expr.a.a.value == '1'
        assert expr.a.b.value == '2'
        assert expr.b.value == '3'

    def test_unary_minus(self):
        ast = parse('table T { x:int = -5; }')
        expr = ast.next.b.d
        assert expr.node_type == AstType.UNARY_MINUS
        assert expr.a.value == '5'

    def test_unary_not(self):
        ast = parse('table T { x:bool = !true; }')
        expr = ast.next.b.d
        assert expr.node_type == AstType.UNARY_NOT
        assert expr.a.value == 'true'

    def test_logical_or(self):
        ast = parse('table T { x:bool = a || b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_LOGICAL_OR

    def test_logical_and(self):
        ast = parse('table T { x:bool = a && b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_LOGICAL_AND

    def test_equality(self):
        ast = parse('table T { x:bool = a == b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_EQ

    def test_inequality(self):
        ast = parse('table T { x:bool = a != b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_NE

    def test_relational(self):
        ast = parse('table T { x:bool = a < b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_LT

    def test_shift(self):
        ast = parse('table T { x:int = 1 << 2; }')
        assert ast.next.b.d.node_type == AstType.BINARY_SHL

    def test_bitwise_and(self):
        ast = parse('table T { x:int = a & b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_BITWISE_AND

    def test_bitwise_or(self):
        ast = parse('table T { x:int = a | b; }')
        assert ast.next.b.d.node_type == AstType.BINARY_BITWISE_OR


class TestParserProgram:
    def test_empty_source(self):
        ast = parse('')
        assert ast.node_type == AstType.PROGRAM

    def test_enum_then_table(self):
        ast = parse('enum E {}\ntable T {}')
        decls = collect(ast.next)
        assert decls[0] == (AstType.ENUM_DECL, '')
        assert decls[1] == (AstType.TABLE_DECL, '')

    def test_multiple_tables(self):
        ast = parse('table A {}\ntable B {}')
        decls = collect(ast.next)
        assert len(decls) == 2


class TestParserErrors:
    def test_unexpected_token(self):
        with pytest.raises(SystemExit):
            parse('???')

    def test_invalid_decl(self):
        with pytest.raises(SystemExit):
            parse('123')

    def test_missing_brace(self):
        with pytest.raises(SystemExit):
            parse('table T {')
