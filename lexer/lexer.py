from lexer.token_type import TokenType
from lexer.token import Token


class Lexer:
    def __init__(self, filename=None, text=None):
        if filename:
            with open(filename) as f:
                self.text = f.read( )
        elif text:
            self.text = text
        else:
            raise ValueError("Either 'filename' or 'text' must be provided.")

        self.current_pos = 0
        self.line = 1
        self.column = 1

    def next_char(self):
        """Возвращает текущий символ и смещает указатель."""
        if self.current_pos < len(self.text):
            char = self.text[self.current_pos]
            self.current_pos += 1
            if char == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            return char
        return None

    def read_space(self):
        """Пропускает пробелы и символы новой строки."""
        while self.current_pos < len(self.text) and self.text[self.current_pos].isspace():
            self.next_char()

    def read_identifier_or_keyword(self):
        """Считывает идентификатор или ключевое слово."""
        start_pos = self.current_pos
        start_column = self.column

        while self.current_pos < len(self.text) and self.text[self.current_pos].isalnum():
            self.next_char()

        value = self.text[start_pos:self.current_pos]
        type_ = TokenType[value.upper()] if value.upper() in TokenType.__members__ else TokenType.IDENTIFIER
        return Token(type_, value, self.line, start_column)

    def read_string(self):
        """Читает строку, заключенную в кавычки."""
        start_pos = self.current_pos
        start_column = self.column
        string_value = ""

        # Пропускаем начальную кавычку
        self.next_char()

        while self.current_pos < len(self.text):
            char = self.next_char()

            if char == '"':
                break

            elif char == "\\":
                if self.current_pos < len(self.text):
                    next_char = self.text[self.current_pos]
                    string_value += next_char
                    self.next_char()
                else:
                    raise ValueError(f"Invalid escape sequence at line {self.line}, column {self.column}")

            else:
                string_value += char

        """
        if self.text[self.current_pos] != '"':
            raise ValueError(f"Unterminated string literal at line {self.line}, column {self.column}")
        """


        return Token(TokenType.STRING, string_value, self.line, start_column)

    def read_number(self):
        """Читает число."""
        start_pos = self.current_pos
        start_column = self.column
        number_value = ""

        while self.current_pos < len(self.text) and self.text[self.current_pos].isdigit():
            number_value += self.next_char()

        return Token(TokenType.NUMBER, number_value, self.line, start_column)

    def read_operator_or_punctuation(self):
        """Читает операторы и знаки препинания."""
        char = self.text[self.current_pos]
        if char == '+':
            self.next_char()
            return Token(TokenType.PLUS, '+', self.line, self.column)
        elif char == '-':
            self.next_char()
            return Token(TokenType.MINUS, '-', self.line, self.column)
        elif char == '*':
            self.next_char()
            return Token(TokenType.ASTERISK, '*', self.line, self.column)
        elif char == '/':
            self.next_char()
            return Token(TokenType.SLASH, '/', self.line, self.column)
        elif char == ';':
            self.next_char()
            return Token(TokenType.SEMICOLON, ';', self.line, self.column)
        elif char == '(':
            self.next_char()
            return Token(TokenType.LPAREN, '(', self.line, self.column)
        elif char == ')':
            self.next_char()
            return Token(TokenType.RPAREN, ')', self.line, self.column)
        elif char == '[':
            self.next_char()
            return Token(TokenType.LBRACKET, '[', self.line, self.column)
        elif char == ']':
            self.next_char()
            return Token(TokenType.RBRACKET, ']', self.line, self.column)
        elif char == ',':
            self.next_char()
            return Token(TokenType.COMMA, ',', self.line, self.column)
        elif char == '.':
            start_column = self.column  # Сохраняем начальный столбец
            self.next_char()  # Пропускаем текущую точку
            if self.current_pos < len(self.text) and self.text[self.current_pos] == '.':
                self.next_char()  # Пропускаем вторую точку
                return Token(TokenType.TWODOTS, '..', self.line, start_column)
            else:
                return Token(TokenType.DOT, '.', self.line, start_column)
        elif char == ':':
            self.next_char()
            if self.text[self.current_pos] == '=':
                self.next_char()
                return Token(TokenType.ASSIGN, ':=', self.line, self.column)
            return Token(TokenType.COLON, ':', self.line, self.column)
        elif char == '=':
            self.next_char()
            return Token(TokenType.EQ, '=', self.line, self.column)
        elif char == '<':
            self.next_char()
            if self.text[self.current_pos] == '>':
                self.next_char()
                return Token(TokenType.NEQ, '<>', self.line, self.column)
            return Token(TokenType.LT, '<', self.line, self.column)
        elif char == '>':
            self.next_char()
            return Token(TokenType.GT, '>', self.line, self.column)

        return None

    def tokenize(self):
        tokens = []

        while self.current_pos < len(self.text):
            char = self.text[self.current_pos]

            # Пропускаем пробелы
            if char.isspace():
                self.read_space()
                continue

            # Если строка
            if char == '"':
                tokens.append(self.read_string())
                continue

            # Если число
            if char.isdigit():
                tokens.append(self.read_number())
                continue

            # Если идентификатор или ключевое слово
            if char.isalpha():
                tokens.append(self.read_identifier_or_keyword())
                continue

            # Если оператор или знак препинания
            operator_token = self.read_operator_or_punctuation()
            if operator_token:
                tokens.append(operator_token)
                continue

            raise ValueError(f"Unexpected character '{char}' at line {self.line}, column {self.column}")

        tokens.append(Token(TokenType.EOF, "EOF", self.line, self.column))
        return tokens

