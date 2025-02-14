import json

from custom_exceptions.lexer_error import LexerError
from custom_exceptions.parse_error import ParseError
from custom_exceptions.semantic_error import SemanticError
from generator.codegen import CodeGenerator
from generator.valid_structure import ValidStructure
from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.semantic_analyzer import SemanticAnalyzer
from generator.translator import Translator

files = [
    '../../tests/semantic_tests/test_decl.pas',

    '../../tests/lexer_tests/test_programm_block.pas',
]

# Файлы для логов
parser_log_file = 'parser_log.json'
semantic_log_file = 'semantic_log.json'
generated_code_file = 'generated_code2.txt'


with open(parser_log_file, 'w', encoding='utf-8') as parser_log, \
     open(semantic_log_file, 'w', encoding='utf-8') as semantic_log:

    try:
        # Лексический анализ
        lexer = Lexer(filename=files[0])
        tokens = lexer.tokenize()

        # Парсинг
        parser = Parser(tokens)
        ast = parser.parse_program()
        ast_json = {
            "AST_Nodes": [str(child) for child in ast.children]
        }

        json.dump(ast_json, parser_log, indent=4, ensure_ascii=False)
        print(json.dumps(ast_json, indent=4, ensure_ascii=False))

        # Семантический анализ
        sem = SemanticAnalyzer()
        sem.visit_program(ast)

        for symbol, details in sem.symbol_table.parent.symbols.items():
            if details.get('local_symbol_table'):
                print('details', details.get('local_symbol_table').symbols)
                details['local_symbol_table'] = {
                    sym: det
                    for sym, det in details.get('local_symbol_table').symbols.items()
                }

        semantic_json = {
            "GLOBAL Symbol_Table": {
                symbol: str(details)
                for symbol, details in sem.symbol_table.parent.symbols.items()
            }
        }

        for elem in sem.code_generator['statements']:
            print(elem)

        json.dump(semantic_json, semantic_log, indent=4, ensure_ascii=False)
        print(json.dumps(semantic_json, indent=4, ensure_ascii=False))

        # Теперь генерируем код на основе таблицы символов и списка операторов.
        # Создаём экземпляр класса Translator, передавая ему semantic_json и список операторов.
        translator = Translator(sem.symbol_table, semantic_json, sem.code_generator['statements'])
        generated_code = translator.translate()

        # Сохраняем сгенерированный код в отдельный файл
        with open(generated_code_file, 'w', encoding='utf-8') as code_file:
            code_file.write(generated_code)
    except ParseError as e:
        e.display()
    except LexerError as e:
        e.display()
    except SemanticError as e:
        e.display()

