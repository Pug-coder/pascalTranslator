import json
import re

from semantic.symbol_table import SymbolTable
from parser.ast_node import *
from generator.codegen import CodeGenerator

GLOBAL_TYPE_CHECKS = {
    "integer": int,
    "string": str,
    "boolean": bool
}

class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.code_generator = CodeGenerator()

    def visit_program(self, node: ProgramNode):
        self.visit_block(node.children[0])

    def visit_block(self, node: BlockNode):
        if node.declarations:
            self.visit_declarations(node.declarations)

        outer_scope = self.symbol_table
        self.symbol_table = SymbolTable(parent=outer_scope)
        self.code_generator = self.visit_compound_statement(node.compound_statement)
        block = self.code_generator
        return block
        #self.symbol_table = outer_scope

    def visit_declarations(self, node: DeclarationNode):
        for declaration in node:
            if isinstance(declaration, ConstDeclarationNode):
                self.visit_const_declaration(declaration)
            elif isinstance(declaration, TypeDeclarationNode):
                self.visit_type_declaration(declaration)
            elif isinstance(declaration, VarDeclarationNode):
                self.visit_var_declaration(declaration)
            elif isinstance(declaration, ProcedureOrFunctionDeclarationNode):
                self.visit_proc_or_func_declaration(declaration)

    def create_array_info(self, node: ArrayTypeNode, declaration_place):
        """
        Эта функция проверяет, что размеры массива и его вложенности соответствуют
        указанным в декларации. Также проверяет соответствие типов данных в массиве.
        """
        type_checks = {
            "integer": int,
            "string": str,
            "boolean": bool,
            "char": str
        }

        def check_array_size_and_types(dimensions, values, level=0):
            if level == len(dimensions):
                # Обработка для базового уровня (одиночный элемент или список элементов)
                # Если элемент — инициализатор записи, который может быть задан как RecordInitializerNode или dict
                if isinstance(values, (RecordInitializerNode, dict)):
                    record_type = self.symbol_table.lookup(node.element_type)
                    if not record_type:
                        raise Exception(f"Record type '{node.element_type}' not found in symbol table")
                    self.validate_record_initializer(record_type, values)
                    return 1
                # Если список содержит только инициализаторы записей (RecordInitializerNode или dict)
                elif isinstance(values, list) and all(isinstance(v, (RecordInitializerNode, dict)) for v in values):
                    record_type = self.symbol_table.lookup(node.element_type)
                    if not record_type:
                        raise Exception(f"Record type '{node.element_type}' not found in symbol table")
                    for record_instance in values:
                        self.validate_record_initializer(record_type, record_instance)
                    return len(values)
                # Если элемент относится к базовому типу (integer, string, boolean)
                expected_type = type_checks.get(node.element_type)
                if expected_type:
                    if isinstance(values, list):
                        if not all(isinstance(value, expected_type) for value in values):
                            raise ValueError(f"Expected elements of type {expected_type} at level {level}")
                        return len(values)
                    else:
                        if isinstance(values, expected_type):
                            return 1
                        else:
                            raise ValueError(
                                f"Expected element of type {expected_type} at level {level}, but got {type(values)}")
                # Если ни базовый тип, ни запись найдены – ошибка
                raise Exception(f"Invalid initializer for type '{node.element_type}'")

            # Рекурсивно обрабатываем вложенные списки
            dim_lower, dim_upper = dimensions[level]
            expected_size = dim_upper - dim_lower + 1

            if isinstance(values, list):
                if len(values) != expected_size:
                    raise ValueError(f"At level {level}, expected {expected_size} elements, got {len(values)}")
                total_size = 0
                for sub_values in values:
                    total_size += check_array_size_and_types(dimensions, sub_values, level + 1)
                return total_size
            else:
                raise ValueError(f"Expected list of values at level {level}, but got {type(values)}")

        # Вычисляем общий размер массива по измерениям
        size = 1
        for dim in node.dimensions:
            lower_bound, upper_bound = dim
            size *= (upper_bound - lower_bound + 1)

        if declaration_place == 'const':
            if node.initial_values is None:
                raise ValueError(f'{declaration_place} declaration array cannot be empty, enter values')

            total_elements = check_array_size_and_types(node.dimensions, node.initial_values)
            if total_elements != size:
                raise ValueError(f'Array size is incorrect. Expected {size} elements, got {total_elements}')
            else:
                arr_info = {
                    "type": "array",
                    "element_type": node.element_type,
                    "size": size,
                    "dimensions": node.dimensions,
                    "initial_values": node.initial_values
                }
                # Если element_type соответствует записи, преобразуем инициализаторы в словари
                record_type_info = self.symbol_table.lookup(node.element_type)
                if record_type_info and record_type_info.get("type") == "record":
                    arr_info["initial_values"] = self.transform_record_array_values(
                        node.initial_values, node.dimensions, record_type_info
                    )
                return arr_info

        elif declaration_place in ('var', 'record'):
            arr_info = {
                "type": "array",
                "element_type": node.element_type,
                "size": size,
                "dimensions": node.dimensions,
                "initial_values": node.initial_values
            }
            record_type_info = self.symbol_table.lookup(node.element_type)
            if record_type_info and record_type_info.get("type") == "record":
                # Если для массива записей заданы начальные значения, преобразуем их
                if node.initial_values is not None:
                    arr_info["initial_values"] = self.transform_record_array_values(
                        node.initial_values, node.dimensions, record_type_info
                    )
            if node.initial_values is not None:
                total_elements = check_array_size_and_types(node.dimensions, node.initial_values)
                if total_elements != size:
                    raise ValueError(f'Array size is incorrect. Expected {size} elements, got {total_elements}')
            return arr_info

        return None

    def transform_record_array_values(self, values, dimensions, record_type_info, level=0):
        """
        Рекурсивно проходит по структуре initial_values массива.
        Если на базовом уровне обнаруживается RecordInitializerNode,
        то он преобразуется в словарь с полями, используя validate_record_initializer.
        """
        print(values)
        if level == len(dimensions):
            if isinstance(values, RecordInitializerNode) or isinstance(values, dict):
                return self.validate_record_initializer(record_type_info, values)
            elif isinstance(values, list):
                return [self.validate_record_initializer(record_type_info, v) for v in values]
            else:
                raise Exception(f"Unexpected value type {type(values)} at record array base level")
        return [
            self.transform_record_array_values(sub_value, dimensions, record_type_info, level + 1)
            for sub_value in values
        ]

    def visit_type_declaration(self, node: TypeDeclarationNode):
        name = node.name
        type_node = node.type_node

        if isinstance(type_node, RecordTypeNode):
            fields = []
            for field_name, field in type_node.fields:
                #print(field)
                if isinstance(field, TypeNode):
                    if field.identifier_type in ("integer", "string") or \
                            self.symbol_table.lookup(field.identifier_type):
                        field_info = {
                            "field_name": field_name,
                            "field_type": field.identifier_type
                        }
                        fields.append(field_info)
                    else:
                        # если не в symbol_table, значит не запись
                        raise Exception(f'Wrong type {field.identifier_type} in field {field_name}')

                elif isinstance(field, ArrayTypeNode):
                    arr_info = self.create_array_info(field, "record")
                    field_info = {
                        "field_name": field_name,
                        "field_type": 'array',
                        "arr_info": arr_info
                    }
                    fields.append(field_info)

            #print(fields)
            info = {
                "name": name,
                "type": 'record',
                "fields_info": fields
            }
            self.symbol_table.declare(name, info)

        elif isinstance(type_node, ArrayTypeNode):
            arr_info = self.create_array_info(type_node, "record")
            info = {'info': arr_info}
            self.symbol_table.declare(name, info)

    def validate_record_initializer(self, record_type_info, initializer):
        """
        Проверяет инициализацию записи на соответствие информации о типе записи из record_type_info.
        Параметр initializer может быть либо объектом RecordInitializerNode, либо словарём вида
        {'name': value, 'age': value, ...}.
        """
        # Получаем список информации о полях из record_type_info
        fields_info = record_type_info.get("fields_info")
        if not fields_info:
            raise Exception(f"Record type '{record_type_info.get('name')}' has no fields information")

        type_checks = {
            "integer": int,
            "string": str,
            "boolean": bool
        }

        validated_fields = {}

        if isinstance(initializer, RecordInitializerNode):
            # Получаем список полей в виде списка пар (field_name, field_value)
            initializer_fields = initializer.fields

            if len(fields_info) != len(initializer_fields):
                raise Exception(
                    f"Record initializer has incorrect number of fields for type '{record_type_info.get('name')}'"
                )

            for field_info, (init_name, init_value) in zip(fields_info, initializer_fields):
                expected_name = field_info["field_name"]
                field_type = field_info["field_type"]

                # Проверяем совпадение имён полей
                if expected_name != init_name:
                    raise Exception(f"Field name mismatch: expected '{expected_name}', got '{init_name}'")

                # Проверяем тип значения
                if field_type in type_checks:
                    expected_type = type_checks[field_type]
                    if not isinstance(init_value, expected_type):
                        raise Exception(
                            f"Field '{init_name}' expected type '{field_type}', got '{type(init_value).__name__}'"
                        )
                elif field_type == "array":
                    # Если тип — массив, вызываем функцию обработки массива
                    arr_info = field_info.get("arr_info")
                    if not arr_info:
                        raise Exception(f"Array field '{init_name}' has no array info")
                    array_type_node = ArrayTypeNode(
                        element_type=arr_info["element_type"],
                        dimensions=arr_info["dimensions"],
                        initial_values=init_value  # Значение массива для проверки
                    )
                    self.create_array_info(array_type_node, declaration_place="record")
                else:
                    raise Exception(f"Unsupported field type '{field_type}' in record '{record_type_info.get('name')}'")

                validated_fields[init_name] = init_value

        elif isinstance(initializer, dict):
            # Проверяем, что набор ключей в словаре совпадает с ожидаемым набором имён полей
            expected_field_names = {field_info["field_name"] for field_info in fields_info}
            if set(initializer.keys()) != expected_field_names:
                raise Exception(
                    f"Record initializer has incorrect set of fields for type '{record_type_info.get('name')}'. "
                    f"Expected fields: {expected_field_names}, got: {set(initializer.keys())}"
                )
            for field_info in fields_info:
                field_name = field_info["field_name"]
                field_type = field_info["field_type"]
                init_value = initializer[field_name]

                if field_type in type_checks:
                    expected_type = type_checks[field_type]
                    if not isinstance(init_value, expected_type):
                        raise Exception(
                            f"Field '{field_name}' expected type '{field_type}', got '{type(init_value).__name__}'"
                        )
                elif field_type == "array":
                    arr_info = field_info.get("arr_info")
                    if not arr_info:
                        raise Exception(f"Array field '{field_name}' has no array info")
                    array_type_node = ArrayTypeNode(
                        element_type=arr_info["element_type"],
                        dimensions=arr_info["dimensions"],
                        initial_values=init_value  # Значение массива для проверки
                    )
                    self.create_array_info(array_type_node, declaration_place="record")
                # record
                elif self.symbol_table.lookup(field_type):
                    validated_fields[field_name] = init_value
                    return {
                        "type": "record",
                        "record_type": record_type_info["name"],
                        "fields": validated_fields,
                    }
                else:
                    raise Exception(f"Unsupported field type '{field_type}' in record '{record_type_info.get('name')}'")

                validated_fields[field_name] = init_value

        else:
            raise Exception("Record initializer must be a RecordInitializerNode or a dictionary")

        # Если все проверки прошли успешно, возвращаем информацию о записи
        return {
            "type": "record",
            "record_type": record_type_info["name"],
            "fields": validated_fields,
        }

    def visit_const_declaration(self, node: ConstDeclarationNode):
        name = node.identifier
        const_value = node.value

        info = self.look_const_type(const_value)

        const_info = {"type": "const", "info": info}
        self.symbol_table.declare(name, const_info)

    def look_const_type(self, value):
        const_type = None
        const_value = None

        type_checks = {
            "integer": int,
            "string": str,
            "boolean": bool
        }

        const_type = value[0]
        const_value = value[1]

        if const_type in type_checks:
            expected_type = type_checks[const_type]
            if isinstance(const_value, expected_type):
                info = {
                    "type": const_type,
                    "value": const_value,
                }
                return info
            else:
                raise Exception(f"Value is not {const_type.capitalize()}")

        elif isinstance(value[0], ArrayTypeNode):
            info = self.create_array_info(const_type, declaration_place="const")
            return info

        record_type = self.symbol_table.lookup(const_type)
        #print('a', record_type)
        if record_type:
            if isinstance(const_value, RecordInitializerNode):
                # Вызываем отдельную функцию для проверки записи
                return self.validate_record_initializer(record_type, const_value)
            else:
                raise Exception(f"Invalid initializer for record type '{const_type}'")

        elif self.symbol_table.lookup(value[0]):
            pass

    def visit_var_declaration(self, node: VarDeclarationNode):
        name = node.identifier
        init_value = node.init_value
        var_type = node.var_type

        info = self.look_var_type(var_type, init_value)

        var_info = {"type": "var", "info": info}
        self.symbol_table.declare(name, var_info)

    def look_var_type(self, var_type, init_value):
        """
        var_type может быть:
          - строка "integer" или "string"
          - ArrayTypeNode(...)
          - имя записи (например, "TPerson")
        init_value: фактическое значение (список, RecordInitializerNode, ...) или None,
                    если не инициализировано явно при объявлении.
        """
        type_checks = {
            "integer": int,
            "string": str,
            "boolean": bool,
            "char": str,
        }

        # 1) Базовые типы
        if var_type in type_checks:
            expected_type = type_checks[var_type]
            if init_value is not None:
                if isinstance(init_value, expected_type):
                    return {"type": var_type, "value": init_value}
                else:
                    raise Exception(f"Value is not {var_type.capitalize()}")
            else:
                # Значение не задано, проставим дефолт (0 или "")
                default_val = 0 if expected_type is int else ""
                return {"type": var_type, "value": default_val}

        # 2) ArrayTypeNode
        elif isinstance(var_type, ArrayTypeNode):

            # Если init_value не задан, заполним массив дефолтными значениями
            """
            """
            if var_type.initial_values is None:
                init_value = self.fill_array_with_defaults(
                    dimensions=var_type.dimensions,
                    element_type=var_type.element_type
                )
                var_type.initial_values = init_value
            # Вызываем create_array_info
            info = self.create_array_info(var_type, declaration_place="var")
            return info

        # 3) Проверка: вдруг var_type — это имя записи (например, "TPerson")
        else:
            record_type_info = self.symbol_table.lookup(var_type)
            if record_type_info and record_type_info.get("type") == "record":
                # Если есть init_value, проверим через validate_record_initializer
                if init_value is not None:
                    if not isinstance(init_value, RecordInitializerNode):
                        raise Exception(
                            f"Expected RecordInitializerNode for record '{var_type}', "
                            f"got {type(init_value).__name__}."
                        )
                    self.validate_record_initializer(record_type_info, init_value)
                    return {
                        "type": "record",
                        "record_type": var_type,
                        "fields": [field for field in init_value.fields]
                    }
                else:
                    # Создаём пустой RecordInitializerNode по умолчанию
                    default_record = self.create_default_record_initializer(record_type_info)

                    return {
                        "type": "record",
                        "record_type": var_type,
                        "fields": default_record
                    }

            # 4) Иначе тип неизвестен
            raise Exception(f"Unsupported variable type: {var_type}")

    def create_default_value(self, type_name, extra_info=None):
        """
        Возвращает дефолтное (пустое) значение для заданного типа:
          - integer -> 0
          - string  -> ""
          - record  -> RecordInitializerNode(...) со всеми полями по умолчанию
          - массив  -> заполненный вложенный список (через fill_array_with_defaults)

        Параметр extra_info может понадобиться для массивов или записей:
          - Для массива: {"dimensions": [...], "element_type": ...}
          - Для записи: словарь record_type_info (впрочем, можно получить его через symbol_table)
        """
        type_checks = {
            "integer": 0,
            "string": "",
            "boolean": False,
            "char": chr(0),
        }

        # 1) Базовые типы: integer/string
        if type_name in type_checks:
            return type_checks[type_name]

        # 2) Массив
        if type_name == "array":
            if not extra_info:
                raise Exception("Array type requires extra_info with dimensions and element_type.")
            return self.fill_array_with_defaults(
                dimensions=extra_info["dimensions"],
                element_type=extra_info["element_type"]
            )

        # 3) Попробуем найти запись (record) в таблице символов
        record_type_info = self.symbol_table.lookup(type_name)
        if record_type_info and record_type_info.get("type") == "record":
            return self.create_default_record_initializer(record_type_info)

        # 4) Иначе не знаем, что это
        raise Exception(f"Unsupported or unknown type: {type_name}")

    def fill_array_with_defaults(self, dimensions, element_type, level=0):
        """
        Рекурсивно создаёт многомерный массив с дефолтными значениями.
        dimensions: список [(lower, upper), (lower, upper), ...]
        element_type: строка типа (например, "integer", "string", "TPerson")
                      или "array" (если вложенные массивы), и т. п.
        """
        if level == len(dimensions):
            # Базовый случай: вернуть дефолтное значение для элемента
            return self.create_default_value(element_type)

        dim_lower, dim_upper = dimensions[level]
        size = dim_upper - dim_lower + 1

        return [
            self.fill_array_with_defaults(dimensions, element_type, level + 1)
            for _ in range(size)
        ]

    def create_default_record_initializer(self, record_type_info):
        """
        Создаёт RecordInitializerNode с полями по умолчанию на основе record_type_info.
        Предполагается, что record_type_info содержит:
          {
            "name": "TPerson",
            "type": "record",
            "fields_info": [
                {"field_name": "name", "field_type": "string"},
                {"field_name": "age",  "field_type": "integer"},
                ...
            ]
          }
        """
        if record_type_info.get("type") != "record":
            raise Exception(
                f"Type '{record_type_info.get('name')}' is not a record, got '{record_type_info.get('type')}' instead."
            )

        fields_info = record_type_info.get("fields_info")
        if not fields_info:
            raise Exception(f"Record '{record_type_info.get('name')}' has no fields info.")

        initializer_fields = []
        for field in fields_info:
            field_name = field["field_name"]
            field_type = field["field_type"]

            if field_type == "array":
                arr_info = field.get("arr_info")
                if not arr_info:
                    raise Exception(
                        f"Field '{field_name}' in record '{record_type_info['name']}' is array but has no arr_info."
                    )
                default_val = self.fill_array_with_defaults(
                    dimensions=arr_info["dimensions"],
                    element_type=arr_info["element_type"]
                )
            else:
                # Используем универсальную create_default_value
                default_val = self.create_default_value(field_type)
            initializer_fields.append((field_name, default_val))
            print(initializer_fields)
        fields = {init_name: init_value for init_name, init_value in RecordInitializerNode(fields=initializer_fields).fields}
        return fields

    def visit_compound_statement(self, node: CompoundStatementNode):
        """Обход составного оператора (Compound Statement)"""
        generated_statements = []
        for statement_node in node.statements:
            if isinstance(statement_node, AssignStatementNode):
                generated_statements.append(self.visit_assign_statement_node(statement_node))
            elif isinstance(statement_node, ForStatementNode):
                generated_statements.append(self.visit_for_statement_node(statement_node))
            elif isinstance(statement_node, WhileStatementNode):
                generated_statements.append(self.visit_while_statement_node(statement_node))
            elif isinstance(statement_node, IfStatementNode):
                generated_statements.append(self.visit_if_statement_node(statement_node))
            elif isinstance(statement_node, ProcedureCallNode):
                generated_statements.append(self.visit_procedure_call_node(statement_node))

        return {"type": "block", "statements": generated_statements}

    def visit_expression_node(self, node, stmt_type=None):
        """
        Обходит выражение и выполняет семантическую проверку.

        Если node является ExpressionNode, то проверяются реляционные операторы.
        Если node — FactorNode или SimpleExpressionNode, то вызывается соответствующий метод.
        """
        # Если node является ExpressionNode, обрабатываем его отдельно.
        if isinstance(node, ExpressionNode):
            # Если в узле присутствует реляционный оператор, результат считается boolean.
            if getattr(node, "relational_operator", None):
                left_type = self.get_expression_type(node.left)
                right_type = self.get_expression_type(node.right)
                if left_type != right_type:
                    raise Exception(
                        f"Ошибка типов: {left_type} != {right_type} в сравнении {node.relational_operator}"
                    )
                # Обходим подвыражения без ожидания конкретного типа.
                self.visit_expression_node(node.left, None)
                self.visit_expression_node(node.right, None)
                result = self.code_generator.generate(node)
                # Если сверху ожидался не boolean, сообщаем об ошибке.
                if stmt_type is not None and stmt_type != "boolean":
                    raise Exception(
                        f"Ошибка типов: ожидаемый тип {stmt_type}, но выражение возвращает boolean"
                    )
                return result
            else:
                # Если реляционного оператора нет, обрабатываем левую часть.
                # Здесь предполагается, что node.left является либо FactorNode, либо SimpleExpressionNode.
                return self.visit_expression_node(node.left, stmt_type)

        # Если node уже является FactorNode, передаем его в visit_factor_node.
        elif isinstance(node, FactorNode):
            return self.visit_factor_node(node, stmt_type)

        # Если node является SimpleExpressionNode, передаем его в visit_simple_expr_node.
        elif isinstance(node, SimpleExpressionNode):
            return self.visit_simple_expr_node(node, stmt_type)

        elif isinstance(node, ArrayAccessNode):
            return self.visit_array_access_node(node, stmt_type)
        elif isinstance(node, FunctionCallNode):
            return self.visit_function_call_node(node)
        elif isinstance(node, RecordFieldAccessNode):
            return self.visit_record_field_access_node(node)
        else:
            raise Exception(f"Unsupported node type in visit_expression_node: {type(node)}")

    def visit_simple_expr_node(self, node: SimpleExpressionNode, stmt_type):
        """Обход простого выражения (например, a + b)"""
        print("Проверяем простое выражение:", node.to_dict())

        for i, term in enumerate(node.terms):
            if isinstance(term, FactorNode):
                self.visit_factor_node(term, stmt_type)
            elif term in {"+", "-", "or", "*", "div", "mod", "and"}:
                continue  # Это оператор, его проверять не нужно
            elif isinstance(term, SimpleExpressionNode):
                self.visit_simple_expr_node(term, stmt_type)
            elif isinstance(term, TermNode):
                self.visit_term_node(term, stmt_type)
            elif isinstance(term, ArrayAccessNode):
                self.visit_array_access_node(term, stmt_type)
            elif isinstance(term, RecordFieldAccessNode):
                self.visit_record_field_access_node(term, stmt_type)
            else:
                print(type(term))
                raise Exception(f"Некорректный элемент в terms: {term}")

        return self.code_generator.generate(node)

    def visit_factor_node(self, node: FactorNode, stmt_type):
        """Обход отдельных факторов (чисел, переменных, подвыражений)"""
        print("Проверяем фактор:", node.to_dict())

        # Если фактор – это подвыражение, обходим его.
        if node.sub_expression:
            if isinstance(node.sub_expression, FactorNode):
                return self.visit_factor_node(node.sub_expression, stmt_type)
            elif isinstance(node.sub_expression, ExpressionNode):
                return self.visit_expression_node(node.sub_expression, stmt_type)

        # Если фактор – идентификатор переменной, проверяем его тип.
        elif node.identifier:
            var_info = self.symbol_table.lookup(node.identifier)
            if not var_info:
                raise Exception(f"Ошибка: переменная {node.identifier} не объявлена")
            var_type = var_info.get('info', {}).get('type')
            print('inf',var_info)
            if var_info.get('kind') == 'parameter':
                var_type = var_info.get('type')
            print("Тип переменной:", var_info)
            # Only check if an expected type was given
            if stmt_type is not None and str(var_type) != str(stmt_type):
                if var_type != 'record':
                    raise Exception(f"Ошибка типов: {var_type} != {stmt_type} для {node.identifier}")
                elif var_type == 'record':
                    var_type = var_info.get('info', {}).get('record_type')
                    if stmt_type is not None and var_type != stmt_type:
                        raise Exception(f"Ошибка типов: {var_type} != {stmt_type} для {node.identifier}")
            print(self.code_generator)
            return self.code_generator.generate(node)

        elif node.value is not None:
            expected_python_type = self.map_type(stmt_type)
            print('expected_python_type', expected_python_type)
            if not isinstance(node.value, expected_python_type):
                raise Exception(f"Ошибка типов: {node.value} ({type(node.value).__name__}) != {stmt_type}")
            return self.code_generator.generate(node)
        # Если фактор – литерал (например, число или строка)
        else:
            # Сначала проверяем, ожидается ли составной тип (например, массив)
            type_info = self.symbol_table.lookup(stmt_type)

            if type_info and type_info.get('info', {}).get('type') == 'array':
                # Если ожидается массив, нельзя назначать ему простой литерал.
                raise Exception(f"Ошибка типов: нельзя присвоить литерал {node.value} массиву типа {stmt_type}")

            # Если ожидается простой тип, проверяем соответствие типов.
            expected_python_type = self.map_type(stmt_type)
            if not isinstance(node.value, expected_python_type):
                raise Exception(f"Ошибка типов: {node.value} ({type(node.value).__name__}) != {stmt_type}")

            return self.code_generator.generate(node)

    def get_expression_type(self, node, detailed=False):
        """Определяет тип выражения. Если detailed=True, возвращает подробную информацию."""
        if isinstance(node, FunctionCallNode):
            func_info = self.symbol_table.lookup(node.identifier)
            if not func_info:
                raise Exception(f"Ошибка: функция '{node.identifier}' не объявлена")
            return func_info.get('return_type')
        elif isinstance(node, ExpressionNode):
            if node.relational_operator:
                left_type = self.get_expression_type(node.left, detailed)

                right_type = self.get_expression_type(node.right, detailed)
                if left_type != right_type:
                    raise Exception(
                        f"Ошибка типов: {left_type} != {right_type} в сравнении {node.relational_operator}"
                    )
                return "boolean"
            else:
                if isinstance(node.left, FactorNode):
                    return self.get_factor_type(node.left, detailed)
                elif isinstance(node.left, SimpleExpressionNode):
                    return self.get_simple_expr_type(node.left)
                elif isinstance(node.left, ArrayAccessNode):
                    return self.get_array_access_type(node.left)
                else:
                    return None
        elif isinstance(node, FactorNode):
            return self.get_factor_type(node, detailed)
        elif isinstance(node, SimpleExpressionNode):
            return self.get_simple_expr_type(node, detailed)
        elif isinstance(node, ArrayAccessNode):
            return self.get_array_access_type(node)
        return None

    def get_factor_type(self, node: FactorNode, detailed=False):
        """Определяет тип фактора (число, переменная, вложенное выражение)"""
        if node.identifier:
            var_info = self.symbol_table.lookup(node.identifier)
            if not detailed:
                if var_info.get('kind') == 'parameter':
                    return str(var_info.get('type'))
                return var_info.get('info', {}).get('type') if var_info else None
            else:
                return var_info.get('info', {})
        elif node.value is not None:
            return self.get_python_type_name(node.value)
        return None

    def get_simple_expr_type(self, node: SimpleExpressionNode):
        """Определяет тип простого выражения (например, a + b)"""
        first_term = node.terms[0]
        if isinstance(first_term, FactorNode):
            return self.get_factor_type(first_term)
        elif isinstance(first_term, ArrayAccessNode):
            return self.get_array_access_type(first_term)
        elif isinstance(first_term, SimpleExpressionNode):
            return self.get_simple_expr_type(first_term)
        elif isinstance(first_term, TermNode):
            return self.get_term_type(first_term)
        return None

    def get_array_access_type(self, node):
        """
        Определяет тип выражения для обращения к массиву.
        Например, для узла, представляющего niz[i], возвращает тип элементов массива 'niz'
        """
        base_array_name, indices = self.flatten_array_access(node)
        array_info = self.symbol_table.lookup(base_array_name)
        if not array_info:
            raise Exception(f"Ошибка: массив '{base_array_name}' не объявлен")
        if array_info.get('info', {}).get('type') != 'array':
            raise Exception(f"Ошибка: '{base_array_name}' не является массивом")

        # Можно также добавить проверку количества индексов и границ,
        # но для определения типа достаточно вернуть тип элемента
        element_type = array_info['info'].get('element_type')
        return element_type

    def flatten_array_access(self, node: ArrayAccessNode):
        """
        Разворачивает вложенные обращения к массиву.
        Например, для arr[i][j] возвращает: ("arr", [i, j])
        """
        indices = []
        current = node
        # Walk backward through nested ArrayAccessNodes.
        while isinstance(current, ArrayAccessNode):
            # If the index_expr is a list, extend; otherwise, wrap in a list.
            if isinstance(current.index_expr, list):
                # Prepend the indices so that the innermost index comes first.
                indices = current.index_expr + indices
            else:
                indices = [current.index_expr] + indices
            current = current.array_name  # Move to the next (inner) node.
        # At the end, current should be the base array name (a string)
        if not isinstance(current, str):
            raise Exception("Ошибка: не распознано имя массива при обращении")
        return current, indices

    def get_array_identifier_from_expression(self, node):
        """Получает идентификатор массива из выражения."""
        if isinstance(node, FactorNode):
            return node.identifier
        elif isinstance(node, ExpressionNode):
            if isinstance(node.left, FactorNode):
                return node.left.identifier
            return self.get_array_identifier_from_expression(node.left)
        return None

    def visit_assign_statement_node(self, node: AssignStatementNode):
        """Обход оператора присваивания (Assignment) с поддержкой вложенных обращений к массивам."""
        # Если идентификатор — обычная переменная (строка)
        if isinstance(node.identifier, str):
            stmt = self.symbol_table.lookup(node.identifier)
            if stmt:
                stmt_info = stmt.get('info', {})
                stmt_type = stmt_info.get('type')

                # Проверка для массива
                if stmt_type == 'array':
                    # Получаем тип элементов массива
                    element_type = stmt_info.get('element_type')

                    # Получаем тип выражения справа
                    expr_type = self.get_expression_type(node.expression)
                    if expr_type != 'array':
                        raise Exception(
                            f"Ошибка: массиву нельзя присвоить значение типа {expr_type}"
                        )

                    # Для ExpressionNode получаем тип элементов массива
                    other_array_name = self.get_array_identifier_from_expression(node.expression)
                    other_array = self.symbol_table.lookup(other_array_name)
                    other_element_type = other_array.get('info', {}).get('element_type')

                    # Проверяем совпадение типов элементов
                    if element_type != other_element_type:
                        raise Exception(
                            f"Ошибка: несовпадение типов элементов массивов ({element_type} != {other_element_type})"
                        )
                    # Проверяем совпадение размерностей
                    if stmt_info.get('dimensions') != other_array.get('info', {}).get('dimensions'):
                        raise Exception("Ошибка: несовпадение размерностей массивов")

                self.visit_expression_node(node.expression, stmt_type)
                return self.code_generator.generate(node)
            else:
                raise Exception(f"Ошибка: переменная {node.identifier} не объявлена")

            # Если идентификатор представляет собой обращение к массиву
        elif isinstance(node.identifier, ArrayAccessNode):
            base_array_name, indices = self.flatten_array_access(node.identifier)
            array_info = self.symbol_table.lookup(base_array_name)

            if not array_info:
                raise Exception(f"Ошибка: массив '{base_array_name}' не объявлен")
            if array_info.get('info', {}).get('type') != 'array':
                raise Exception(f"Ошибка: '{base_array_name}' не является массивом")

            # Проверяем индексы
            dimensions = array_info['info'].get('dimensions', [])
            if len(indices) != len(dimensions):
                raise Exception(
                    f"Ошибка: массив '{base_array_name}' имеет {len(dimensions)} измерений, но передано {len(indices)} индексов"
                )

            # Проверяем границы индексов
            for i, (index_expr, (lower_bound, upper_bound)) in enumerate(zip(indices, dimensions)):
                index_value = self.evaluate_expression(index_expr)
                if index_value is not None and not (lower_bound <= index_value <= upper_bound):
                    raise Exception(
                        f"Ошибка: индекс {index_value} выходит за границы [{lower_bound}, {upper_bound}] для измерения {i + 1}"
                    )

            # Получаем тип элемента массива, которому присваиваем
            element_type = array_info['info'].get('element_type')

            # Получаем тип выражения справа
            expr_type = self.get_expression_type(node.expression)
            print(f"Debug: array element type = {element_type}, expression type = {expr_type}")

            if element_type != expr_type:
                raise Exception(
                    f"Ошибка типов: нельзя присвоить значение типа {expr_type} элементу типа {element_type}"
                )

            self.visit_expression_node(node.expression, element_type)
            return self.code_generator.generate(node)
        elif isinstance(node.identifier, RecordFieldAccessNode):
            # Здесь вызываем специализированную функцию для проверки обращения к полю записи.
            # Этот метод выполнит необходимые проверки, например, что запись существует, поле определено,
            # и тип поля совпадает с ожидаемым типом для оператора присваивания.
            self.visit_record_field_access_node(node.identifier, None)
            # Теперь, определяем тип поля, чтобы проверить правую часть присваивания.
            field_type = self.get_record_field_type(node.identifier)
            if field_type is None:
                raise Exception(f"Ошибка: не удалось определить тип для {node.identifier}")
            self.visit_expression_node(node.expression, field_type)
            return self.code_generator.generate(node)

        else:
            raise Exception("Ошибка: неверный тип идентификатора в операторе присваивания")

    def visit_array_access_node(self, node: ArrayAccessNode, stmt):
        # Разворачиваем вложенные обращения: получаем базовое имя массива и список индексов
        base_array_name, indices = self.flatten_array_access(node)
        array_info = self.symbol_table.lookup(base_array_name)
        if not array_info:
            raise Exception(f"Ошибка: массив '{base_array_name}' не объявлен")
        if array_info.get('info', {}).get('type') != 'array':
            raise Exception(f"Ошибка: '{base_array_name}' не является массивом")

        dimensions = array_info['info'].get('dimensions', [])
        if len(indices) != len(dimensions):
            raise Exception(
                f"Ошибка: массив '{base_array_name}' имеет {len(dimensions)} измерений, но передано {len(indices)} индексов"
            )

        # Проверяем каждый индекс (пытаемся вычислить константное значение, если возможно)
        for i, (index_expr, (lower_bound, upper_bound)) in enumerate(zip(indices, dimensions)):
            index_value = self.evaluate_expression(index_expr)
            if index_value is None:
                # Если индекс не константный, можно либо пропустить проверку, либо предупредить о невозможности проверки на этапе компиляции.
                print(
                    f"Предупреждение: индекс для измерения {i + 1} не является константой – проверка границ выполняется в рантайме")
            else:
                print(f"Индекс {i + 1}: {index_value} (допустимый диапазон: [{lower_bound}, {upper_bound}])")
                if not (lower_bound <= index_value <= upper_bound):
                    raise Exception(
                        f"Ошибка: индекс {index_value} выходит за границы [{lower_bound}, {upper_bound}] для измерения {i + 1}"
                    )

        print(f"Доступ к массиву {base_array_name} с индексами {indices} - ОК!")
        # Если нужно вернуть какое-либо значение, можно добавить return здесь.

    def evaluate_expression(self, expr):
        """Попытка вычислить выражение индекса (если оно константное)"""
        if isinstance(expr, FactorNode) and isinstance(expr.value, int):
            return expr.value  # Простое число — возвращаем его
        elif isinstance(expr, ExpressionNode):

            expression_result = self.visit_expression_node(expr, "integer")
            # Если возможно, вы могли бы сразу вернуть число, но если нет —
            # извлекаем значение из результата (в примере используется JSON и regex, что не очень надёжно)
            if expression_result and expression_result.get("type") == "constant":
                return expression_result["value"]
            else:
                # Альтернативный вариант: пробуем найти все числовые значения и суммировать их

                json_str = json.dumps(expression_result)

                values = list(map(int, re.findall(r'"value": (\d+)', json_str)))
                if values:
                    return sum(values)
        else:raise Exception(f"Ошибка: не удалось вычислить индексное выражение: {expr}")

    def visit_record_field_access_node(self, node: RecordFieldAccessNode, stmt_type=None):
        """Обход обращения к полю записи (Record Field Access) с учетом структуры таблицы символов."""
        print("Проверяем доступ к полю записи:", node)

        # Determine the record definition based on the type of node.record_obj.
        if isinstance(node.record_obj, str):
            # Если record_obj – это простой идентификатор.
            var_info = self.symbol_table.lookup(node.record_obj)
            if not var_info:
                raise Exception(f"Ошибка: переменная/запись '{node.record_obj}' не объявлена")
            # Из переменной получаем имя типа записи.
            record_type = var_info.get("info", {}).get("record_type")
            if var_info.get('kind') == 'parameter':
                record_type = str(var_info.get('type'))
            if not record_type:
                raise Exception(f"Ошибка: переменная '{node.record_obj}' не является записью")
            # Ищем определение записи по record_type.
            print(record_type)

            record_def = self.symbol_table.lookup(record_type)

            if not record_def or record_def.get("type") != "record":
                raise Exception(f"Ошибка: '{record_type}' не является корректной записью")
            # Извлекаем информацию о полях.
            fields = record_def.get("fields_info", [])
            field_entry = next((f for f in fields if f["field_name"] == node.field_name), None)
            if not field_entry:
                raise Exception(f"Ошибка: поле '{node.field_name}' отсутствует в записи '{record_type}'")
            field_type = field_entry["field_type"]

        elif isinstance(node.record_obj, ArrayAccessNode):
            # Если record_obj – это обращение к элементу массива, предполагаем, что тип элемента – запись.
            self.visit_array_access_node(node.record_obj, stmt_type)
            base_array_name, indices = self.flatten_array_access(node.record_obj)
            array_info = self.symbol_table.lookup(base_array_name)
            if not array_info:
                raise Exception(f"Ошибка: массив '{base_array_name}' не объявлен")
            if array_info.get("info", {}).get("type") != "array":
                raise Exception(f"Ошибка: '{base_array_name}' не является массивом")
            element_type = array_info.get("info", {}).get("element_type")
            if not element_type:
                raise Exception(f"Ошибка: тип элемента массива '{base_array_name}' не указан")
            record_def = self.symbol_table.lookup(element_type)
            if not record_def or record_def.get("type") != "record":
                raise Exception(f"Ошибка: элемент массива '{base_array_name}' не является записью")
            fields = record_def.get("fields_info", [])
            field_entry = next((f for f in fields if f["field_name"] == node.field_name), None)
            if not field_entry:
                raise Exception(f"Ошибка: поле '{node.field_name}' отсутствует в записи '{element_type}'")
            field_type = field_entry["field_type"]

        elif isinstance(node.record_obj, RecordFieldAccessNode):
            # Если record_obj – это вложенное обращение к полю записи, обрабатываем рекурсивно.
            print(type(node.record_obj))
            inner_field_type = self.get_record_field_type(node.record_obj)
            print(inner_field_type)
            if not inner_field_type:
                #self.visit_record_field_access_node(node.record_obj)
                raise Exception(f"Ошибка: не удалось определить тип вложенной записи в {node.record_obj}")
            record_def = self.symbol_table.lookup(inner_field_type)
            if not record_def or record_def.get("type") != "record":
                raise Exception(f"Ошибка: {node.record_obj} не является записью")
            fields = record_def.get("fields_info", [])
            field_entry = next((f for f in fields if f["field_name"] == node.field_name), None)
            if not field_entry:
                raise Exception(f"Ошибка: поле '{node.field_name}' отсутствует в записи {node.record_obj}")
            field_type = field_entry["field_type"]

        else:
            raise Exception("Ошибка: неверный тип объекта записи при обращении к полю")

        # Если задан ожидаемый тип (например, в контексте присваивания), проверяем соответствие.
        if stmt_type and field_type != stmt_type:
            raise Exception(
                f"Ошибка типов: ожидаемый тип '{stmt_type}', а получен '{field_type}' для поля '{node.field_name}'"
            )

        # Если все проверки прошли, передаем узел в генератор кода.
        return self.code_generator.generate(node)

    def get_record_field_type(self, node: RecordFieldAccessNode):
        """
        Вспомогательная функция, которая определяет тип поля записи.
        Например, для выражения person.address.street возвращает тип поля 'street',
        если 'address' является полем типа записи в 'person'.
        """
        print("node", node.record_obj)
        if isinstance(node.record_obj, str):
            var_info = self.symbol_table.lookup(node.record_obj)

            if not var_info:
                return None
            record_type = var_info.get("info", {}).get("record_type")
            if var_info.get('kind') == 'parameter':
                record_type = str(var_info.get('type'))
            if not record_type:
                return None
            record_def = self.symbol_table.lookup(record_type)
            if not record_def or record_def.get("type") != "record":
                return None
            fields = record_def.get("fields_info", [])
            field_entry = next((f for f in fields if f["field_name"] == node.field_name), None)
            return field_entry["field_type"] if field_entry else None

        elif isinstance(node.record_obj, RecordFieldAccessNode):

            inner_field_type = self.get_record_field_type(node.record_obj)
            if not inner_field_type:
                return None
            record_def = self.symbol_table.lookup(inner_field_type)
            if not record_def or record_def.get("type") != "record":
                return None
            fields = record_def.get("fields_info", [])
            field_entry = next((f for f in fields if f["field_name"] == node.field_name), None)
            return field_entry["field_type"] if field_entry else None

        elif isinstance(node.record_obj, ArrayAccessNode):
            base_array_name, indices = self.flatten_array_access(node.record_obj)
            array_info = self.symbol_table.lookup(base_array_name)
            if not array_info:
                return None
            if array_info.get("info", {}).get("type") != "array":
                return None
            element_type = array_info.get("info", {}).get("element_type")
            record_def = self.symbol_table.lookup(element_type)
            if not record_def or record_def.get("type") != "record":
                return None
            fields = record_def.get("fields_info", [])
            field_entry = next((f for f in fields if f["field_name"] == node.field_name), None)
            return field_entry["field_type"] if field_entry else None

        else:
            return None

    def visit_for_statement_node(self, node: ForStatementNode):
        """
        Semantic checking for a FOR statement.

        AST node structure:
          identifier: the loop variable (expected to be a string)
          start_expr: the expression for the initial value
          direction: either "TO" or "DOWNTO"
          end_expr: the expression for the end value
          body: the loop body (which can be a compound statement or a single statement)
        """
        # Check that the loop variable is declared.
        loop_var = node.identifier
        var_info = self.symbol_table.lookup(loop_var)
        if var_info is None:
            raise Exception(f"Ошибка: переменная цикла '{loop_var}' не объявлена")

        # Verify that the loop variable is of type integer.
        var_type = var_info.get("info", {}).get("type")
        if var_type != "integer":
            raise Exception(f"Ошибка: переменная цикла '{loop_var}' должна быть типа integer, а не {var_type}")

        # Check that the start expression evaluates to an integer.
        start_type = self.get_expression_type(node.start_expr)
        if start_type != "integer":
            raise Exception(f"Ошибка: начальное значение цикла FOR должно быть целого типа, получено {start_type}")
        # Visit the start expression.
        self.visit_expression_node(node.start_expr, "integer")

        # Check that the end expression evaluates to an integer.
        end_type = self.get_expression_type(node.end_expr)
        if end_type != "integer":
            raise Exception(f"Ошибка: конечное значение цикла FOR должно быть целого типа, получено {end_type}")
        # Visit the end expression.
        self.visit_expression_node(node.end_expr, "integer")

        # Check that the direction is either "TO" or "DOWNTO".
        if node.direction not in ("to", "downto"):
            raise Exception(f"Ошибка: направление цикла должно быть TO или DOWNTO, получено {node.direction}")

        # Optionally, you might mark the loop variable as read-only within the loop body,
        # or create a new scope for the loop body here.

        # Visit the body of the loop (it can be a compound statement or any other statement).
        self.visit_compound_statement(node.body)

        # Finally, generate code for the FOR loop.
        return self.code_generator.generate(node)

    def visit_while_statement_node(self, node: WhileStatementNode):
        """
        Обходит оператор WHILE с семантической проверкой.

        Ожидается, что:
          - node.condition – условие цикла, результат которого должен быть булевого типа.
          - node.body – тело цикла, которое будет рекурсивно обработано.
        """
        # Определяем тип выражения условия.
        cond_type = self.get_expression_type(node.condition)
        if cond_type != "boolean":
            raise Exception(f"Ошибка: условие WHILE должно быть булевого типа, получено {cond_type}")

        # Посещаем условие с ожидаемым типом "boolean"
        self.visit_expression_node(node.condition, "boolean")

        # Посещаем тело цикла (оно может быть составным оператором или одиночным оператором)
        self.visit_compound_statement(node.body)

        # После семантической проверки возвращаем сгенерированный код для WHILE-цикла.
        return self.code_generator.generate(node)

    def visit_if_statement_node(self, node: IfStatementNode):
        """
        Семантический анализ оператора IF.

        - Проверяется, что условие (node.condition) возвращает булев тип.
        - Обрабатываются then- и else-ветки.
        - Возвращается сгенерированный код для оператора IF.
        """
        # Проверяем тип условия
        cond_type = self.get_expression_type(node.condition)
        if cond_type != "boolean":
            raise Exception(f"Ошибка: условие IF должно быть булевого типа, получено {cond_type}")

        # Посещаем условие с ожидаемым типом "boolean"
        self.visit_expression_node(node.condition, "boolean")

        # Обрабатываем ветку then и сохраняем результат в узле
        self.visit_compound_statement(node.then_statement)

        # Если есть ветка else, обрабатываем и её и сохраняем результат в узле
        if node.else_statement:
            print(node.else_statement)
            self.visit_compound_statement(node.else_statement)

        # Генерируем и возвращаем код для оператора IF
        return self.code_generator.generate(node)

    def visit_procedure_call_node(self, node: ProcedureCallNode):
        """
        Обрабатывает вызов процедуры.
        Проверяет, что процедура объявлена, и что число/типы аргументов соответствуют параметрам.
        """
        proc_info = self.symbol_table.lookup(node.identifier)
        if not proc_info:
            raise Exception(f"Ошибка: процедура '{node.identifier}' не объявлена")
        if proc_info.get('kind') != 'procedure':
            raise Exception(f"Ошибка: '{node.identifier}' не является процедурой")

        expected_params = proc_info.get('parameters', [])
        if len(expected_params) != len(node.arguments):
            raise Exception(
                f"Ошибка: процедура '{node.identifier}' ожидает {len(expected_params)} аргументов, получено {len(node.arguments)}")

        for param, arg in zip(expected_params, node.arguments):
            expected_type = param['type']
            print('arg',arg)
            print(param)
            print(expected_type)

            if isinstance(expected_type, ArrayTypeNode):
                arg_type = self.get_expression_type(arg, True)
                dim = expected_type.dimensions
                elem_type = expected_type.element_type
                if dim != arg_type['dimensions']:
                    raise Exception (
                        f'Ошибка размерностей {dim} != {arg_type["dimensions"]}'
                    )
                if elem_type != arg_type['element_type']:
                    raise Exception(
                        f'Ошибка типов {elem_type} != { arg_type["element_type"]}'
                    )
                return self.code_generator.generate(node)
            arg_type = self.get_expression_type(arg)
            if arg_type != expected_type:
                raise Exception(
                    f"Ошибка типов в вызове процедуры '{node.identifier}': для параметра '{param['name']}' ожидается {expected_type}, получено {arg_type}")
        return self.code_generator.generate(node)

    # Обработка вызова функции
    def visit_function_call_node(self, node: FunctionCallNode):
        """
        Обрабатывает вызов функции.
        Проверяет, что функция объявлена, число и типы аргументов соответствуют параметрам,
        и возвращает тип результата, равный возвращаемому типу функции.
        """
        func_info = self.symbol_table.lookup(node.identifier)
        if not func_info:
            raise Exception(f"Ошибка: функция '{node.identifier}' не объявлена")
        if func_info.get('kind') != 'function':
            raise Exception(f"Ошибка: '{node.identifier}' не является функцией")

        expected_params = func_info.get('parameters', [])
        if len(expected_params) != len(node.arguments):
            raise Exception(
                f"Ошибка: функция '{node.identifier}' ожидает {len(expected_params)} аргументов, получено {len(node.arguments)}")

        for param, arg in zip(expected_params, node.arguments):
            print(param)
            expected_type = param['type']
            arg_type = self.get_expression_type(arg)
            if str(arg_type).lower().strip() != str(expected_type).lower().strip():
                raise Exception(
                    f"Ошибка типов в вызове функции '{node.identifier}': для параметра '{param['name']}' ожидается {expected_type}, получено {arg_type}")
        # Генерация кода для вызова функции. Можно также вернуть ожидаемый тип.
        generated_code = self.code_generator.generate(node)
        return self.code_generator.generate(node)

    def visit_parameters(self, parameters):
        """
        Обходит список параметров процедуры/функции.

        Для каждого параметра:
          - Если параметр задан через составной узел (например, массив или запись),
            вызывается look_var_type для разрешения типа.
          - Поскольку для параметров не задаётся явное значение (init_value),
            передаём None в качестве инициализирующего значения.
          - Регистрируем параметр в локальной таблице символов с разрешённой информацией о типе.
        """
        for param in parameters:
            # Здесь param.type_node может быть объектом типа TypeNode, ArrayTypeNode, или даже строкой
            resolved_type = self.look_var_type(param.type_node, None)
            # Регистрируем параметр в текущей таблице символов.
            self.symbol_table.declare(param.identifier, {"kind": "parameter", "type": resolved_type})

    def visit_proc_or_func_declaration(self, node: ProcedureOrFunctionDeclarationNode):
        """
        Обрабатывает объявление процедуры или функции:
          1. Регистрирует объявление в глобальной таблице символов.
          2. Создает отдельные экземпляры SymbolTable и CodeGenerator для обработки тела.
          3. Обрабатывает блок (тело) процедуры/функции с использованием локальных объектов.
          4. Сохраняет полученные результаты в записи объявления.
        """
        # Проверяем, что такое имя ещё не объявлено
        if self.symbol_table.lookup(node.identifier):
            raise Exception(f"Ошибка: {node.kind} '{node.identifier}' уже объявлена")

        # Создаем запись для объявления с базовой информацией
        proc_info = {
            "kind": node.kind,  # "procedure" или "function"
            "parameters": [],  # Заполним ниже
            "return_type": node.return_type,  # Для функции; для процедуры может быть None
            "block_code": None,  # Сюда позже запишем сгенерированный код
            "local_symbol_table": None  # При необходимости сохраним локальную таблицу
        }

        # Обработка параметров (предполагается, что у каждого параметра есть identifier и param_type)
        if node.parameters:
            for param in node.parameters:

                if isinstance(param.type_node, ArrayTypeNode):
                    array_info = self.create_array_info(param.type_node, 'var')
                    param.type_node = 'array'

                proc_info["parameters"].append({
                    "name": param.identifier,
                    "type": param.type_node
                })

        # Регистрируем объявление в глобальной таблице символов
        self.symbol_table.declare(node.identifier, proc_info)

        # Сохраняем текущие объекты (глобальные)
        old_symbol_table = self.symbol_table
        old_code_generator = self.code_generator

        # Создаем новые (локальные) объекты для обработки тела функции/процедуры
        local_symbol_table = SymbolTable(parent=old_symbol_table)
        local_code_generator = CodeGenerator()

        # Добавляем параметры в локальную таблицу
        if node.parameters:
            for param in node.parameters:
                if param.type_node == 'array':
                    local_symbol_table.declare(param.identifier, {"kind": "parameter", "info": array_info})
                else:
                    local_symbol_table.declare(param.identifier, {"kind": "parameter", "type": param.type_node})


        # Переключаемся на локальные объекты
        self.symbol_table = local_symbol_table
        self.code_generator = local_code_generator

        # Обрабатываем блок (тело) функции/процедуры и получаем сгенерированный код
        block_code = self.visit_block(node.block)

        # Сохраняем сгенерированный код и локальную таблицу в записи объявления

        proc_info["block_code"] = block_code
        proc_info["local_symbol_table"] = local_symbol_table

        # Возвращаемся к исходным (глобальным) объектам
        self.symbol_table = old_symbol_table
        self.code_generator = old_code_generator

        return proc_info

    def get_python_type_name(self, value):
        if isinstance(value, int):
            return "integer"
        if isinstance(value, str):
            if len(value) == 1:  # Если строка длины 1 - это char
                return "char"
            return "string"
        if isinstance(value, bool):
            return "boolean"
        return "unknown"
    def map_type(self, stmt_type):
        """Сопоставляет строковое представление типа с Python-типом"""
        mapping = {
            "integer": int,
            "string": str,
            "boolean": bool,
            "char": str,
        }
        return mapping.get(stmt_type, object)


