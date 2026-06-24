import unicodedata

from src.tok import Tok
from src.pos import Pos
from src.tok_type import TokenType
from src.keyword import Keyword
from src.error_handler import raise_error


class Tokenizer:
    def __init__(self, fpath: str, fdata: str):
        self.file_path = fpath
        self.file_data = fdata
        self.pos = 0
        self.line = 1
        self.column = 1

        self.keywords = {k.value for k in Keyword}

        self._two_char = {
            '++', '--', '==', '!=', '<=', '>=', '&&', '||',
            '<<', '>>', '->', '+=', '-=', '*=', '/=', '%=',
            '&=', '|=', '^=', '##',
        }

        self._three_char = {'<<=', '>>='}

    def _pos(self) -> Pos:
        return Pos(self.line, self.column)

    def _advance(self) -> str:
        ch = self.file_data[self.pos]
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        self.pos += 1
        return ch

    def _peek(self, n: int = 0) -> str:
        idx = self.pos + n
        if idx < len(self.file_data):
            return self.file_data[idx]
        return ''

    def _skip_whitespace(self):
        while self.pos < len(self.file_data):
            ch = self.file_data[self.pos]
            if ch in ' \t\r\n':
                self._advance()
            else:
                break

    def _skip_line_comment(self):
        while self.pos < len(self.file_data) and self.file_data[self.pos] != '\n':
            self._advance()

    def _skip_block_comment(self):
        self._advance()
        self._advance()
        while self.pos < len(self.file_data):
            if self.file_data[self.pos] == '*' and self._peek(1) == '/':
                self._advance()
                self._advance()
                return
            self._advance()
        raise_error(self.file_path, self.file_data, 'unterminated block comment', self._pos())

    def _read_string(self, quote: str) -> Tok:
        start = self._pos()
        self._advance()
        chars = []
        while self.pos < len(self.file_data):
            ch = self.file_data[self.pos]
            if ch == '\\':
                self._advance()
                if self.pos >= len(self.file_data):
                    raise_error(self.file_path, self.file_data, 'unterminated string', start)
                esc = self._advance()
                if esc == 'n':
                    chars.append('\n')
                elif esc == 't':
                    chars.append('\t')
                elif esc == 'r':
                    chars.append('\r')
                elif esc == '0':
                    chars.append('\0')
                elif esc == '\\':
                    chars.append('\\')
                elif esc == '\'':
                    chars.append('\'')
                elif esc == '"':
                    chars.append('"')
                elif esc == 'x':
                    hex_digits = []
                    while self.pos < len(self.file_data):
                        c = self.file_data[self.pos]
                        if c.isdigit() or c.lower() in 'abcdef':
                            hex_digits.append(self._advance())
                        else:
                            break
                    if hex_digits:
                        chars.append(chr(int(''.join(hex_digits), 16)))
                else:
                    chars.append(esc)
            elif ch == quote:
                self._advance()
                return Tok(TokenType.STRING, ''.join(chars), start)
            elif ch == '\n':
                raise_error(self.file_path, self.file_data, 'unterminated string', start)
            else:
                chars.append(self._advance())
        raise_error(self.file_path, self.file_data, 'unterminated string', start)

    def _read_number(self) -> Tok:
        start = self._pos()
        result = [self._advance()]

        if result[0] == '0' and self.pos < len(self.file_data):
            nxt = self.file_data[self.pos].lower()
            if nxt == 'x':
                result.append(self._advance())
                if self.pos >= len(self.file_data) or not (self.file_data[self.pos].isdigit() or self.file_data[self.pos].lower() in 'abcdef'):
                    raise_error(self.file_path, self.file_data, 'invalid hex literal', start)
                while self.pos < len(self.file_data):
                    c = self.file_data[self.pos]
                    if c.isdigit() or c.lower() in 'abcdef':
                        result.append(self._advance())
                    else:
                        break
                return Tok(TokenType.HEX, ''.join(result), start)
            elif nxt == 'o':
                result.append(self._advance())
                if self.pos >= len(self.file_data) or self.file_data[self.pos] not in '01234567':
                    raise_error(self.file_path, self.file_data, 'invalid octal literal', start)
                while self.pos < len(self.file_data):
                    c = self.file_data[self.pos]
                    if c in '01234567':
                        result.append(self._advance())
                    else:
                        break
                return Tok(TokenType.OCT, ''.join(result), start)
            elif nxt == 'b':
                result.append(self._advance())
                if self.pos >= len(self.file_data) or self.file_data[self.pos] not in '01':
                    raise_error(self.file_path, self.file_data, 'invalid binary literal', start)
                while self.pos < len(self.file_data):
                    c = self.file_data[self.pos]
                    if c in '01':
                        result.append(self._advance())
                    else:
                        break
                return Tok(TokenType.BIN, ''.join(result), start)

        while self.pos < len(self.file_data):
            c = self.file_data[self.pos]
            if c.isdigit():
                result.append(self._advance())
            else:
                break
        return Tok(TokenType.INT, ''.join(result), start)

    def _read_identifier(self) -> Tok:
        start = self._pos()
        result = []
        while self.pos < len(self.file_data):
            ch = self.file_data[self.pos]
            cat = unicodedata.category(ch)
            if not result:
                if ch == '_' or ch.isalpha() or cat.startswith('L'):
                    result.append(self._advance())
                else:
                    break
            else:
                if ch == '_' or ch.isalnum():
                    result.append(self._advance())
                elif cat in ('Nd', 'Pc', 'Mn', 'Mc'):
                    result.append(self._advance())
                else:
                    break
        word = ''.join(result)
        if word in self.keywords:
            return Tok(TokenType.KEYWORD, word, start)
        return Tok(TokenType.IDENTIFIER, word, start)

    def _read_symbol(self) -> Tok:
        start = self._pos()

        if self._peek(2) and self.file_data[self.pos:self.pos + 3] in self._three_char:
            val = self.file_data[self.pos:self.pos + 3]
            self._advance()
            self._advance()
            self._advance()
            return Tok(TokenType.SYMBOL, val, start)

        if self._peek(1) and self.file_data[self.pos:self.pos + 2] in self._two_char:
            val = self.file_data[self.pos:self.pos + 2]
            self._advance()
            self._advance()
            return Tok(TokenType.SYMBOL, val, start)

        ch = self._advance()
        if ch == '.' and self._peek() == '.':
            raise_error(self.file_path, self.file_data, 'unexpected token', start)
        return Tok(TokenType.SYMBOL, ch, start)

    def nextToken(self) -> Tok:
        while self.pos < len(self.file_data):
            self._skip_whitespace()
            if self.pos >= len(self.file_data):
                break

            ch = self.file_data[self.pos]

            if ch == '/' and self._peek(1) == '/':
                self._skip_line_comment()
                continue

            if ch == '/' and self._peek(1) == '*':
                self._skip_block_comment()
                continue

            if ch in '"\'':
                return self._read_string(ch)

            if ch.isdigit():
                return self._read_number()

            if ch == '_' or ch.isalpha() or unicodedata.category(ch).startswith('L'):
                return self._read_identifier()

            if ch in '+-*/%&|^~!<>=.,;:{}[]()?#\\':
                return self._read_symbol()

            raise_error(self.file_path, self.file_data, f"unexpected character '{ch}'", self._pos())

        return Tok(TokenType.EOF, '', self._pos())
