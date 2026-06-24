import sys
import pytest

sys.path.insert(0, 'src')
from src.pos import Pos
from src.error_handler import raise_error


class TestErrorHandler:
    def test_raises_system_exit(self):
        with pytest.raises(SystemExit) as exc:
            raise_error('test.storm', 'line one\nline two\n  target', 'test error', Pos(3, 3))
        assert exc.value.code == 1

    def test_shows_message_and_location(self, capsys):
        with pytest.raises(SystemExit):
            raise_error('f.storm', 'a\nb\nc', 'msg', Pos(2, 1))
        out = capsys.readouterr().out
        assert 'Error: msg' in out
        assert 'f.storm:2:1' in out

    def test_shows_context_lines(self, capsys):
        data = 'a\nb\nc\nd\ne'
        with pytest.raises(SystemExit):
            raise_error('f', data, 'err', Pos(3, 1))
        out = capsys.readouterr().out
        assert '1 | a' in out
        assert '2 | b' in out
        assert '3 | c' in out
        assert '4 | d' in out

    def test_caret_at_error_column(self, capsys):
        with pytest.raises(SystemExit):
            raise_error('f', 'abc\ndef\nghi', 'err', Pos(2, 2))
        out = capsys.readouterr().out
        assert 'def' in out
        assert ' ^' in out

    def test_nullable_column(self, capsys):
        with pytest.raises(SystemExit):
            raise_error('f', 'x', 'err', Pos(1, 1))
        out = capsys.readouterr().out
        assert '1 | x' in out
        assert '^' in out
