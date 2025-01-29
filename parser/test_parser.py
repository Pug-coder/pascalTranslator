from lexer.lexer import Lexer
from parser import Parser


lexer = Lexer(filename='../tests/lexer_tests/test_programm_block.pas')
tokens = lexer.tokenize()

for elem in tokens:
    print(elem)

parser = Parser(tokens)

ast = parser.parse_program()
print(ast.children[0].declarations)

