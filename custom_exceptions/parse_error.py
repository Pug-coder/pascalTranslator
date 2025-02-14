class ParseError(Exception):
    def __init__(self, message, line, column):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"[Ошибка парсера] (строка {line}, позиция {column}): {message}")

    def __str__(self):
        return f"[Ошибка парсера] (строка {self.line}, позиция {self.column}): {self.message}"

    def display(self):
        print(self.__str__())