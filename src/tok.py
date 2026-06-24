from src.pos import Pos
from src.tok_type import TokenType


class Tok:
    def __init__(self, tok_type: TokenType, value, position: Pos):
        self.tok_type = tok_type
        self.value = value
        self.position = position

    def __repr__(self):
        return f"Tok({self.tok_type.value}, {self.value}, {self.position})"
