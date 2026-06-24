import enum

from src.error_handler import raise_error


class AstType(enum.Enum):
    IDENTIFIER = "identifier"
    INT_LITERAL = "int_literal"
    NUM_LITERAL = "num_literal"
    STR_LITERAL = "str_literal"
    BOOL_LITERAL = "bool_literal"
    UNARY_NOT = "unary_not"
    UNARY_BITWISE_NOT = "unary_bitwise_not"
    UNARY_PLUS = "unary_plus"
    UNARY_MINUS = "unary_minus"
    BINARY_MUL = "binary_mul"
    BINARY_DIV = "binary_div"
    BINARY_MOD = "binary_mod"
    BINARY_ADD = "binary_add"
    BINARY_SUB = "binary_sub"
    BINARY_SHL = "binary_shl"
    BINARY_SHR = "binary_shr"
    BINARY_LT = "binary_lt"
    BINARY_LTE = "binary_lte"
    BINARY_GT = "binary_gt"
    BINARY_GTE = "binary_gte"
    BINARY_EQ = "binary_eq"
    BINARY_NE = "binary_ne"
    BINARY_BITWISE_AND = "binary_bitwise_and"
    BINARY_BITWISE_XOR = "binary_bitwise_xor"
    BINARY_BITWISE_OR = "binary_bitwise_or"
    BINARY_LOGICAL_AND = "binary_logical_and"
    BINARY_LOGICAL_OR = "binary_logical_or"
    PROGRAM = "program"
    ENUM_DECL = "enum_decl"
    ENUM_ITEM = "enum_item"
    TABLE_DECL = "table_decl"
    FIELD_DECL = "field_decl"
    TYPE = "type"
    FIELD_ATTRS = "field_attrs"
    FIELD_ATTR = "field_attr"


class ASTNode:
    def __init__(self, node_type, position):
        self.node_type = node_type
        self.position = position
        self.value: str = ""
        self.a = None
        self.b = None
        self.c = None
        self.d = None
        self.next = None

    @staticmethod
    def create_terminal_node(type: AstType, value: str, position):
        node = ASTNode(type, position)
        node.value = value
        return node

    @staticmethod
    def create_program(position):
        return ASTNode(AstType.PROGRAM, position)

    @staticmethod
    def create_enum_decl(position):
        return ASTNode(AstType.ENUM_DECL, position)

    @staticmethod
    def create_enum_item(position):
        return ASTNode(AstType.ENUM_ITEM, position)

    @staticmethod
    def create_table_decl(position):
        return ASTNode(AstType.TABLE_DECL, position)

    @staticmethod
    def create_field_decl(position):
        return ASTNode(AstType.FIELD_DECL, position)

    @staticmethod
    def create_field_attrs(position):
        return ASTNode(AstType.FIELD_ATTRS, position)

    @staticmethod
    def create_field_attr(position):
        return ASTNode(AstType.FIELD_ATTR, position)

    @staticmethod
    def create_binary(op_type: AstType, left, right, position):
        node = ASTNode(op_type, position)
        node.a = left
        node.b = right
        return node

    @staticmethod
    def create_unary(op_type: AstType, operand, position):
        node = ASTNode(op_type, position)
        node.a = operand
        return node
