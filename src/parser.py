from src.ast import AstType, ASTNode
from src.tokenizer import Tokenizer
from src.tok_type import TokenType
from src.keyword import Keyword
from src.error_handler import raise_error


class Parser(Tokenizer):
    def __init__(self, fpath):
        with open(fpath) as f:
            fdata = f.read()
        super().__init__(fpath, fdata)
        self.current_token = None

    def next_token(self):
        self.current_token = self.nextToken()

    def __check_type(self, expected_type):
        if self.current_token is None:
            raise_error(self.file_path, self.file_data, f"Expected token of type {expected_type.value}, but got None", self._pos())
        return self.current_token.tok_type == expected_type

    def __check_value(self, expected_value):
        if self.current_token is None:
            raise_error(self.file_path, self.file_data, f"Expected token with value '{expected_value}', but got None", self._pos())
        return self.current_token.value == expected_value and (
            self.__check_type(TokenType.KEYWORD) or self.__check_type(TokenType.SYMBOL)
        )

    def __consume_type(self, expected_type):
        if self.current_token is None:
            raise_error(self.file_path, self.file_data, f"Expected token of type {expected_type.value}, but got None", self._pos())
        if self.current_token.tok_type != expected_type:
            raise_error(self.file_path, self.file_data, f"Expected token of type {expected_type.value}, but got {self.current_token.tok_type.value}", self.current_token.position)
        self.next_token()

    def __consume_value(self, expected_value):
        if self.current_token is None:
            raise_error(self.file_path, self.file_data, f"Expected token with value '{expected_value}', but got None", self._pos())
        if self.current_token.value != expected_value:
            raise_error(self.file_path, self.file_data, f"Expected token with value '{expected_value}', but got '{self.current_token.value}'", self.current_token.position)
        self.next_token()

    def _parse_primary(self):
        if self.__check_type(TokenType.STRING):
            node = ASTNode.create_terminal_node(AstType.STR_LITERAL, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.STRING)
            return node
        if self.current_token.tok_type in (TokenType.INT, TokenType.HEX, TokenType.OCT, TokenType.BIN):
            node = ASTNode.create_terminal_node(AstType.INT_LITERAL, self.current_token.value, self.current_token.position)
            self.next_token()
            return node
        if self.__check_type(TokenType.KEYWORD) and self.current_token.value in (Keyword.TRUE.value, Keyword.FALSE.value):
            node = ASTNode.create_terminal_node(AstType.BOOL_LITERAL, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.KEYWORD)
            return node
        if self.__check_type(TokenType.IDENTIFIER):
            node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.IDENTIFIER)
            return node
        if self.__check_value('('):
            self.__consume_value('(')
            node = self._parse_expression()
            self.__consume_value(')')
            return node
        raise_error(self.file_path, self.file_data, f"unexpected token in expression", self.current_token.position)

    def _parse_unary(self):
        if self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value in ('+', '-', '!', '~'):
            pos = self.current_token.position
            op = self.current_token.value
            self.__consume_value(op)
            operand = self._parse_unary()
            if operand is None:
                raise_error(self.file_path, self.file_data, "expected expression after unary operator", pos)
            ast_type = {
                '+': AstType.UNARY_PLUS,
                '-': AstType.UNARY_MINUS,
                '!': AstType.UNARY_NOT,
                '~': AstType.UNARY_BITWISE_NOT,
            }[op]
            return ASTNode.create_unary(ast_type, operand, pos)
        return self._parse_primary()

    def _parse_multiplicative(self):
        left = self._parse_unary()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value in ('*', '/', '%'):
            pos = self.current_token.position
            op = self.current_token.value
            self.__consume_value(op)
            right = self._parse_unary()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            ast_type = {
                '*': AstType.BINARY_MUL,
                '/': AstType.BINARY_DIV,
                '%': AstType.BINARY_MOD,
            }[op]
            left = ASTNode.create_binary(ast_type, left, right, pos)
        return left

    def _parse_additive(self):
        left = self._parse_multiplicative()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value in ('+', '-'):
            pos = self.current_token.position
            op = self.current_token.value
            self.__consume_value(op)
            right = self._parse_multiplicative()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            ast_type = AstType.BINARY_ADD if op == '+' else AstType.BINARY_SUB
            left = ASTNode.create_binary(ast_type, left, right, pos)
        return left

    def _parse_shift(self):
        left = self._parse_additive()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value in ('<<', '>>'):
            pos = self.current_token.position
            op = self.current_token.value
            self.__consume_value(op)
            right = self._parse_additive()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            ast_type = AstType.BINARY_SHL if op == '<<' else AstType.BINARY_SHR
            left = ASTNode.create_binary(ast_type, left, right, pos)
        return left

    def _parse_relational(self):
        left = self._parse_shift()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value in ('<', '<=', '>', '>='):
            pos = self.current_token.position
            op = self.current_token.value
            self.__consume_value(op)
            right = self._parse_shift()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            ast_type = {
                '<': AstType.BINARY_LT,
                '<=': AstType.BINARY_LTE,
                '>': AstType.BINARY_GT,
                '>=': AstType.BINARY_GTE,
            }[op]
            left = ASTNode.create_binary(ast_type, left, right, pos)
        return left

    def _parse_equality(self):
        left = self._parse_relational()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value in ('==', '!='):
            pos = self.current_token.position
            op = self.current_token.value
            self.__consume_value(op)
            right = self._parse_relational()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            ast_type = AstType.BINARY_EQ if op == '==' else AstType.BINARY_NE
            left = ASTNode.create_binary(ast_type, left, right, pos)
        return left

    def _parse_bitwise_and(self):
        left = self._parse_equality()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value == '&':
            pos = self.current_token.position
            self.__consume_value('&')
            right = self._parse_equality()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            left = ASTNode.create_binary(AstType.BINARY_BITWISE_AND, left, right, pos)
        return left

    def _parse_bitwise_xor(self):
        left = self._parse_bitwise_and()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value == '^':
            pos = self.current_token.position
            self.__consume_value('^')
            right = self._parse_bitwise_and()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            left = ASTNode.create_binary(AstType.BINARY_BITWISE_XOR, left, right, pos)
        return left

    def _parse_bitwise_or(self):
        left = self._parse_bitwise_xor()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value == '|':
            pos = self.current_token.position
            self.__consume_value('|')
            right = self._parse_bitwise_xor()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            left = ASTNode.create_binary(AstType.BINARY_BITWISE_OR, left, right, pos)
        return left

    def _parse_logical_and(self):
        left = self._parse_bitwise_or()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value == '&&':
            pos = self.current_token.position
            self.__consume_value('&&')
            right = self._parse_bitwise_or()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            left = ASTNode.create_binary(AstType.BINARY_LOGICAL_AND, left, right, pos)
        return left

    def _parse_logical_or(self):
        left = self._parse_logical_and()
        while self.current_token and self.__check_type(TokenType.SYMBOL) and self.current_token.value == '||':
            pos = self.current_token.position
            self.__consume_value('||')
            right = self._parse_logical_and()
            if right is None:
                raise_error(self.file_path, self.file_data, "expected expression", pos)
            left = ASTNode.create_binary(AstType.BINARY_LOGICAL_OR, left, right, pos)
        return left

    def _parse_expression(self):
        return self._parse_logical_or()

    def _parse_value(self):
        if self.current_token.tok_type == TokenType.STRING:
            node = ASTNode.create_terminal_node(AstType.STR_LITERAL, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.STRING)
        elif self.current_token.tok_type in (TokenType.INT, TokenType.HEX, TokenType.OCT, TokenType.BIN):
            node = ASTNode.create_terminal_node(AstType.INT_LITERAL, self.current_token.value, self.current_token.position)
            self.next_token()
        elif self.current_token.tok_type == TokenType.KEYWORD and self.current_token.value in (Keyword.TRUE.value, Keyword.FALSE.value):
            node = ASTNode.create_terminal_node(AstType.BOOL_LITERAL, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.KEYWORD)
        elif self.current_token.tok_type == TokenType.IDENTIFIER:
            node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.IDENTIFIER)
        else:
            raise_error(self.file_path, self.file_data, f"unexpected token in value", self.current_token.position)
        return node

    def _parse_enum_item(self):
        pos = self.current_token.position
        name_node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
        self.__consume_type(TokenType.IDENTIFIER)

        node = ASTNode.create_enum_item(pos)
        node.a = name_node

        if self.__check_value('='):
            self.__consume_value('=')
            node.b = self._parse_expression()

        return node

    def _parse_enum(self):
        pos = self.current_token.position
        self.__consume_value(Keyword.ENUM.value)
        name_node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
        self.__consume_type(TokenType.IDENTIFIER)
        self.__consume_value('{')

        node = ASTNode.create_enum_decl(pos)
        node.a = name_node

        prev = None
        while not self.__check_value('}'):
            item = self._parse_enum_item()
            if prev:
                prev.next = item
            else:
                node.b = item
            prev = item
            if self.__check_value(','):
                self.__consume_value(',')

        self.__consume_value('}')
        return node

    def _parse_attr(self):
        pos = self.current_token.position
        name_node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
        self.__consume_type(TokenType.IDENTIFIER)
        self.__consume_value('=')

        node = ASTNode.create_field_attr(pos)
        node.a = name_node

        if self.current_token.tok_type == TokenType.STRING:
            val_node = ASTNode.create_terminal_node(AstType.STR_LITERAL, self.current_token.value, self.current_token.position)
            self.__consume_type(TokenType.STRING)
        elif self.current_token.tok_type in (TokenType.INT, TokenType.HEX, TokenType.OCT, TokenType.BIN):
            val_node = ASTNode.create_terminal_node(AstType.INT_LITERAL, self.current_token.value, self.current_token.position)
            self.next_token()
        else:
            raise_error(self.file_path, self.file_data, f"expected value in attribute", self.current_token.position)

        node.b = val_node
        return node

    def _parse_attrs(self):
        pos = self.current_token.position
        self.__consume_value('(')
        node = ASTNode.create_field_attrs(pos)

        prev = None
        while not self.__check_value(')'):
            attr = self._parse_attr()
            if prev:
                prev.next = attr
            else:
                node.a = attr
            prev = attr
            if self.__check_value(','):
                self.__consume_value(',')

        self.__consume_value(')')
        return node

    def _parse_type(self):
        pos = self.current_token.position
        if not (self.__check_type(TokenType.IDENTIFIER) or self.__check_type(TokenType.KEYWORD)):
            raise_error(self.file_path, self.file_data, f"expected type name, got '{self.current_token.value}'", self.current_token.position)
        type_name = self.current_token.value
        self.next_token()

        if self.__check_value('?'):
            self.__consume_value('?')
            type_name += '?'

        node = ASTNode.create_terminal_node(AstType.TYPE, type_name, pos)

        if self.__check_value('('):
            node.a = self._parse_attrs()

        return node

    def _parse_field(self):
        pos = self.current_token.position
        name_node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
        self.__consume_type(TokenType.IDENTIFIER)
        self.__consume_value(':')

        type_node = self._parse_type()

        node = ASTNode.create_field_decl(pos)
        node.a = name_node
        node.b = type_node

        if self.__check_value('='):
            self.__consume_value('=')
            val_node = self._parse_expression()
            node.d = val_node

        if self.__check_type(TokenType.KEYWORD) and self.current_token.value in (Keyword.PK.value, Keyword.UNIQUE.value):
            node.value = self.current_token.value
            self.__consume_type(TokenType.KEYWORD)

        if self.__check_value(';'):
            self.__consume_value(';')

        return node

    def _parse_table(self):
        pos = self.current_token.position
        self.__consume_value(Keyword.TABLE.value)
        name_node = ASTNode.create_terminal_node(AstType.IDENTIFIER, self.current_token.value, self.current_token.position)
        self.__consume_type(TokenType.IDENTIFIER)
        self.__consume_value('{')

        node = ASTNode.create_table_decl(pos)
        node.a = name_node

        prev = None
        while not self.__check_value('}'):
            field = self._parse_field()
            if prev:
                prev.next = field
            else:
                node.b = field
            prev = field

        self.__consume_value('}')
        return node

    def _parse_decl(self):
        if self.__check_type(TokenType.KEYWORD):
            if self.current_token.value == Keyword.ENUM.value:
                return self._parse_enum()
            if self.current_token.value == Keyword.TABLE.value:
                return self._parse_table()
        raise_error(self.file_path, self.file_data, f"unexpected token '{self.current_token.value}'", self.current_token.position)

    def _parse_program(self):
        node = ASTNode.create_program(self.current_token.position)
        last = node
        while self.current_token.tok_type != TokenType.EOF:
            decl = self._parse_decl()
            last.next = decl
            last = decl
        return node

    def parse(self):
        self.next_token()
        return self._parse_program()
