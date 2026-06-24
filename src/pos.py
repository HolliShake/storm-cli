


class Pos:
    def __init__(self, line, column):
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Pos({self.line}, {self.column})"

