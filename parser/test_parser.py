from lexer.lexer import Lexer
from parser import Parser


lexer = Lexer(filename='../tests/lexer_tests/test_declarations.pas')
tokens = lexer.tokenize()

for elem in tokens:
    print(elem)

parser = Parser(tokens)

ast = parser.parse_program()
print(ast.children)

