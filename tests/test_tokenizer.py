import sys
import pytest

sys.path.insert(0, 'src')
from src.tokenizer import Tokenizer
from src.tok_type import TokenType
from src.keyword import Keyword


def tok(src):
    t = Tokenizer('<test>', src)
    tokens = []
    while True:
        tok = t.nextToken()
        tokens.append((tok.tok_type, tok.value))
        if tok.tok_type == TokenType.EOF:
            break
    return tokens


class TestTokenizerKeywords:
    def test_all_keywords(self):
        for k in Keyword:
            result = tok(k.value)
            assert len(result) == 2
            assert result[0] == (TokenType.KEYWORD, k.value)

    def test_keyword_distinct_from_identifier(self):
        result = tok('table User')
        assert result[0] == (TokenType.KEYWORD, 'table')
        assert result[1] == (TokenType.IDENTIFIER, 'User')


class TestTokenizerIdentifiers:
    def test_simple_identifier(self):
        assert tok('foo')[0] == (TokenType.IDENTIFIER, 'foo')

    def test_underscore_start(self):
        assert tok('_bar')[0] == (TokenType.IDENTIFIER, '_bar')

    def test_with_digits(self):
        assert tok('abc123')[0] == (TokenType.IDENTIFIER, 'abc123')

    def test_unicode_identifier(self):
        assert tok('var\u00e9')[0] == (TokenType.IDENTIFIER, 'var\u00e9')


class TestTokenizerLiterals:
    def test_int(self):
        assert tok('42')[0] == (TokenType.INT, '42')

    def test_zero(self):
        assert tok('0')[0] == (TokenType.INT, '0')

    def test_hex(self):
        assert tok('0xff')[0] == (TokenType.HEX, '0xff')

    def test_hex_uppercase(self):
        assert tok('0X1A')[0] == (TokenType.HEX, '0X1A')

    def test_octal(self):
        assert tok('0o77')[0] == (TokenType.OCT, '0o77')

    def test_octal_uppercase(self):
        assert tok('0O10')[0] == (TokenType.OCT, '0O10')

    def test_binary(self):
        assert tok('0b1010')[0] == (TokenType.BIN, '0b1010')

    def test_binary_uppercase(self):
        assert tok('0B1101')[0] == (TokenType.BIN, '0B1101')

    def test_string_double(self):
        assert tok('"hello"')[0] == (TokenType.STRING, 'hello')

    def test_string_single(self):
        assert tok("'world'")[0] == (TokenType.STRING, 'world')

    def test_string_escape_newline(self):
        assert tok('"a\\nb"')[0] == (TokenType.STRING, 'a\nb')

    def test_string_escape_tab(self):
        assert tok('"a\\tb"')[0] == (TokenType.STRING, 'a\tb')

    def test_string_escape_hex(self):
        assert tok('"\\x41"')[0] == (TokenType.STRING, 'A')


class TestTokenizerSymbols:
    def test_single_char_symbols(self):
        for sym in '+-*/%&|^~!<>=.,;:{}[]()?#\\':
            assert tok(sym)[0] == (TokenType.SYMBOL, sym)

    def test_two_char_symbols(self):
        pairs = ['++', '--', '==', '!=', '<=', '>=', '&&', '||',
                 '<<', '>>', '->', '+=', '-=', '*=', '/=', '%=',
                 '&=', '|=', '^=', '##']
        for sym in pairs:
            assert tok(sym)[0] == (TokenType.SYMBOL, sym)

    def test_three_char_symbols(self):
        assert tok('<<=')[0] == (TokenType.SYMBOL, '<<=')
        assert tok('>>=')[0] == (TokenType.SYMBOL, '>>=')

    def test_maximal_munch(self):
        result = tok('++')
        assert len(result) == 2
        assert result[0] == (TokenType.SYMBOL, '++')
        assert result[1] == (TokenType.EOF, '')


class TestTokenizerComments:
    def test_line_comment(self):
        result = tok('a // comment\nb')
        assert len([t for t in result if t[0] != TokenType.EOF]) == 2
        assert result[0] == (TokenType.IDENTIFIER, 'a')
        assert result[1] == (TokenType.IDENTIFIER, 'b')

    def test_block_comment(self):
        result = tok('a /* block */ b')
        assert result[0] == (TokenType.IDENTIFIER, 'a')
        assert result[1] == (TokenType.IDENTIFIER, 'b')

    def test_comment_in_string(self):
        result = tok('"hello // world"')
        assert result[0] == (TokenType.STRING, 'hello // world')


class TestTokenizerPositions:
    def test_tracks_line_column(self):
        t = Tokenizer('<test>', 'a\nbc')
        t1 = t.nextToken()
        assert t1.position.line == 1 and t1.position.column == 1
        t2 = t.nextToken()
        assert t2.position.line == 2 and t2.position.column == 1

    def test_eof_at_end(self):
        result = tok('')
        assert result[0] == (TokenType.EOF, '')
        assert result[0][0] == TokenType.EOF


class TestTokenizerErrors:
    def test_invalid_hex(self):
        t = Tokenizer('<test>', '0xg')
        with pytest.raises(SystemExit):
            while True:
                tok = t.nextToken()
                if tok.tok_type == TokenType.EOF:
                    break

    def test_unterminated_string(self):
        t = Tokenizer('<test>', '"hello')
        with pytest.raises(SystemExit):
            while True:
                tok = t.nextToken()
                if tok.tok_type == TokenType.EOF:
                    break

    def test_unexpected_character(self):
        t = Tokenizer('<test>', '@')
        with pytest.raises(SystemExit):
            while True:
                tok = t.nextToken()
                if tok.tok_type == TokenType.EOF:
                    break


class TestTokenizerComplex:
    def test_field_declaration(self):
        result = tok('id:int? pk')
        assert result[0] == (TokenType.IDENTIFIER, 'id')
        assert result[1] == (TokenType.SYMBOL, ':')
        assert result[2] == (TokenType.KEYWORD, 'int')
        assert result[3] == (TokenType.SYMBOL, '?')
        assert result[4] == (TokenType.KEYWORD, 'pk')

    def test_expression(self):
        result = tok('1 + 2 * 3')
        assert result[0] == (TokenType.INT, '1')
        assert result[1] == (TokenType.SYMBOL, '+')
        assert result[2] == (TokenType.INT, '2')
        assert result[3] == (TokenType.SYMBOL, '*')
        assert result[4] == (TokenType.INT, '3')
