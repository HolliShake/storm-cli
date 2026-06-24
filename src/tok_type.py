from enum import Enum


class TokenType(Enum):
    IDENTIFIER = 'IDENTIFIER'
    KEYWORD = 'KEYWORD'
    STRING = 'STRING'
    INT = 'INT'
    HEX = 'HEX'
    OCT = 'OCT'
    BIN = 'BIN'
    SYMBOL = 'SYMBOL'
    EOF = 'EOF'
