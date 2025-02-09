import json

from generator.codegen import CodeGenerator
from generator.valid_structure import ValidStructure
from lexer.lexer import Lexer
from parser.parser import Parser
from semantic.semantic_analyzer import SemanticAnalyzer
from generator.translator import Translator  # Импортируем наш класс Translator

files = [
    '../../tests/semantic_tests/test_decl.pas',
    '../../tests/lexer_tests/test_programm_block.pas',
]

# Файлы для логов
parser_log_file = 'parser_log.json'
semantic_log_file = 'semantic_log.json'
generated_code_file = 'generated_code.txt'  # Файл для сгенерированного кода


with open(parser_log_file, 'w', encoding='utf-8') as parser_log, \
     open(semantic_log_file, 'w', encoding='utf-8') as semantic_log:
    # Лексический анализ
    lexer = Lexer(filename=files[0])
    tokens = lexer.tokenize()

    # Парсинг
    parser = Parser(tokens)
    ast = parser.parse_program()

    # Формируем структуру JSON для AST (преобразуем узлы в строки)
    ast_json = {
        "AST_Nodes": [str(child) for child in ast.children]
    }

    # Записываем AST в JSON файл
    json.dump(ast_json, parser_log, indent=4, ensure_ascii=False)
    print(json.dumps(ast_json, indent=4, ensure_ascii=False))

    # Семантический анализ
    sem = SemanticAnalyzer()
    sem.visit_program(ast)

    for symbol, details in sem.symbol_table.parent.symbols.items():
        if details.get('local_symbol_table'):
            print('details',details.get('local_symbol_table').symbols)
            details['local_symbol_table'] = {
                sym: det
                for sym, det in details.get('local_symbol_table').symbols.items()
        }

    # Формируем структуру JSON для таблицы символов
    semantic_json = {
        "GLOBAL Symbol_Table": {
            symbol: str(details)
            for symbol, details in sem.symbol_table.parent.symbols.items()
        }
    }

    # Выводим операторы, сгенерированные семантическим анализатором
    for elem in sem.code_generator['statements']:
        print(elem)

    # Записываем таблицу символов в JSON файл
    json.dump(semantic_json, semantic_log, indent=4, ensure_ascii=False)
    print(json.dumps(semantic_json, indent=4, ensure_ascii=False))

# Теперь генерируем код на основе таблицы символов и списка операторов.
# Создаём экземпляр класса Translator, передавая ему semantic_json и список операторов.
translator = Translator(sem.symbol_table, semantic_json, sem.code_generator['statements'])
generated_code = translator.translate()

# Сохраняем сгенерированный код в отдельный файл
with open(generated_code_file, 'w', encoding='utf-8') as code_file:
    code_file.write(generated_code)

#print("Сгенерированный код:")
#print(generated_code)

#generated_code = translator.translate()