class Token:
    def __init__(self, type_, value, line, column):
        """
        type_ : str
            Тип токена (например, KEYWORD, OPERATOR, IDENTIFIER и т.д.)
        value : str
            Содержимое токена (например, 'begin', '+', 'x')
        line : int
           Номер строки в исходном коде, где находится токен.
        column : int
           Позиция начала токена в строке.
        """
        self.type_ = type_
        self.value = value
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token(type={self.type_}, value={self.value!r}, line={self.line}, column={self.column})"