from enum import Enum


class Keyword(Enum):
    ENUM = 'enum'
    TABLE = 'table'
    UUID = 'uuid'
    INT = 'int'
    LONG = 'long'
    FLOAT = 'float'
    DOUBLE = 'double'
    DATETIME = 'datetime'
    STRING = 'string'
    BOOL = 'bool'
    PK = 'pk'
    UNIQUE = 'unique'
    TRUE = 'true'
    FALSE = 'false'
