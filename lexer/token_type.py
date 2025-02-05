from enum import Enum, auto


class TokenType(Enum):
    BEGIN = auto()
    END = auto()

    IF = auto()
    THEN = auto()
    ELSE = auto()

    FOR = auto()
    WHILE = auto()
    DO = auto()
    TO = auto()

    CONST = auto()
    VAR = auto()

    FUNCTION = auto()
    PROCEDURE = auto()

    TRUE = auto()
    FALSE = auto()

    OR = auto()
    AND = auto()
    NOT = auto()

    EQ = auto()  # ==
    NEQ = auto()  # <>
    LT = auto()  # <
    GT = auto()  # >
    LTE = auto()  # <=
    GTE = auto()  # >=

    PLUS = auto()
    MINUS = auto()
    ASTERISK = auto()
    SLASH = auto()
    DIV = auto()
    MOD = auto()

    SEMICOLON = auto() # ;
    COLON = auto()  # :
    ASSIGN = auto()  # :=
    DOT = auto()
    COMMA = auto()
    # для массивов
    TWODOTS = auto()


    RECORD = auto()
    TYPE = auto()
    ARRAY = auto()
    OF = auto()

    LPAREN = auto()
    RPAREN = auto()
    LBRACKET = auto()
    RBRACKET = auto()

    STRING = auto()
    NUMBER = auto()
    IDENTIFIER = auto()

    EOF = auto()