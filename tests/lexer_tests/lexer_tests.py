import unittest
from lexer.lexer import Lexer
from lexer.token_type import TokenType
from lexer.token import Token


class TestLexer(unittest.TestCase):

    def test_tokenize_keywords(self):
        # Тестирование распознавания ключевых слов
        lexer = Lexer(text="begin end if then else")
        tokens = lexer.tokenize()

        expected_tokens = [
            Token(TokenType.BEGIN, "begin", 1, 1),
            Token(TokenType.END, "end", 1, 7),
            Token(TokenType.IF, "if", 1, 11),
            Token(TokenType.THEN, "then", 1, 14),
            Token(TokenType.ELSE, "else", 1, 19),
            Token(TokenType.EOF, "EOF", 1, 23)
        ]

        self.assertEqual(tokens, expected_tokens)

    def test_tokenize_identifiers(self):
        # Тестирование распознавания идентификаторов
        lexer = Lexer(text="var x y z")
        tokens = lexer.tokenize()

        expected_tokens = [
            Token(TokenType.VAR, "var", 1, 1),
            Token(TokenType.IDENTIFIER, "x", 1, 5),
            Token(TokenType.IDENTIFIER, "y", 1, 7),
            Token(TokenType.IDENTIFIER, "z", 1, 9),
            Token(TokenType.EOF, "EOF", 1, 10)
        ]

        self.assertEqual(tokens, expected_tokens)

    def test_tokenize_numbers(self):
        # Тестирование распознавания чисел
        lexer = Lexer(text="123 4567")
        tokens = lexer.tokenize()

        expected_tokens = [
            Token(TokenType.NUMBER, "123", 1, 1),
            Token(TokenType.NUMBER, "4567", 1, 5),
            Token(TokenType.EOF, "EOF", 1, 10)
        ]

        self.assertEqual(tokens, expected_tokens)

    def test_tokenize_operators(self):
        # Тестирование распознавания операторов
        lexer = Lexer(text="+ - * / := < > ; :")
        tokens = lexer.tokenize()

        expected_tokens = [
            Token(TokenType.PLUS, "+", 1, 1),
            Token(TokenType.MINUS, "-", 1, 3),
            Token(TokenType.ASTERISK, "*", 1, 5),
            Token(TokenType.SLASH, "/", 1, 7),
            Token(TokenType.ASSIGN, ":=", 1, 9),
            Token(TokenType.LT, "<", 1, 12),
            Token(TokenType.GT, ">", 1, 14),
            Token(TokenType.SEMICOLON, ";", 1, 16),
            Token(TokenType.COLON, ":", 1, 18),
            Token(TokenType.EOF, "EOF", 1, 19)
        ]

        self.assertEqual(tokens, expected_tokens)

    def test_tokenize_strings(self):
        # Тестирование распознавания строк
        lexer = Lexer(text='"hello" "world"')
        tokens = lexer.tokenize()

        expected_tokens = [
            Token(TokenType.STRING, "hello", 1, 1),
            Token(TokenType.STRING, "world", 1, 9),
            Token(TokenType.EOF, "EOF", 1, 15)
        ]

        self.assertEqual(tokens, expected_tokens)

    def test_tokenize_mixed(self):
        # Тестирование смешанных токенов (ключевые слова, операторы, числа, строки)
        lexer = Lexer(text="begin x := 123; end")
        tokens = lexer.tokenize()

        expected_tokens = [
            Token(TokenType.BEGIN, "begin", 1, 1),
            Token(TokenType.IDENTIFIER, "x", 1, 7),
            Token(TokenType.ASSIGN, ":=", 1, 9),
            Token(TokenType.NUMBER, "123", 1, 12),
            Token(TokenType.SEMICOLON, ";", 1, 15),
            Token(TokenType.END, "end", 1, 17),
            Token(TokenType.EOF, "EOF", 1, 20)
        ]

        self.assertEqual(tokens, expected_tokens)

    def test_unexpected_character(self):
        # Тестирование ситуации с неожиданным символом
        lexer = Lexer(text="begin $ end")
        with self.assertRaises(ValueError):
            lexer.tokenize()

    def test_unterminated_string(self):
        # Тестирование незавершенной строки
        lexer = Lexer(text='"hello world')
        with self.assertRaises(ValueError):
            lexer.tokenize()


if __name__ == '__main__':
    unittest.main()