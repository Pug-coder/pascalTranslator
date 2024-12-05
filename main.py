from lexer.lexer import Lexer

lexer = Lexer(filename='tests/lexer_tests/test_array.pas')
tokens = lexer.tokenize()
for token in tokens:
    print(token)


