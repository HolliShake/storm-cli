import sys
import os
import pytest

sys.path.insert(0, 'src')
from src.parser import Parser
from src.ast import AstType


@pytest.fixture
def storm_path():
    return os.path.join(os.path.dirname(__file__), '..', 'src', 'test.storm')


class TestIntegration:
    def test_parse_test_storm(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        assert ast.node_type == AstType.PROGRAM

    def test_has_enum_decl(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        enum_node = ast.next
        assert enum_node.node_type == AstType.ENUM_DECL
        assert enum_node.a.value == 'Options'

    def test_enum_has_item(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        item = ast.next.b
        assert item.node_type == AstType.ENUM_ITEM
        assert item.a.value == 'ITEM'
        assert item.b.value == 'DOG'

    def test_has_product_table(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        product = ast.next.next
        assert product.node_type == AstType.TABLE_DECL
        assert product.a.value == 'Product'

    def test_product_has_fields(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        product = ast.next.next

        id_field = product.b
        assert id_field.a.value == 'id'
        assert id_field.b.value == 'int?'
        assert id_field.value == 'pk'

        name_field = id_field.next
        assert name_field.a.value == 'name'
        assert name_field.b.value == 'string'
        assert name_field.b.a is not None

        amout_field = name_field.next
        assert amout_field.a.value == 'amout'
        assert amout_field.b.value == 'double'
        assert amout_field.d.value == '0'

        qty_field = amout_field.next
        assert qty_field.a.value == 'qty'
        assert qty_field.b.value == 'int'
        assert qty_field.b.a is not None

        owner_field = qty_field.next
        assert owner_field.a.value == 'owner'
        assert owner_field.b.value == 'User'

    def test_has_user_table(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        user = ast.next.next.next
        assert user.node_type == AstType.TABLE_DECL
        assert user.a.value == 'User'
        assert user.b is None

    def test_track_positions(self, storm_path):
        p = Parser(storm_path)
        ast = p.parse()
        assert ast.position.line == 4 and ast.position.column == 1
