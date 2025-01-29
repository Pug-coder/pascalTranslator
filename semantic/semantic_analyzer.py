from semantic.symbol_table import SymbolTable
from parser.ast_node import *


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()

    def visit_program(self, node: ProgramNode):
        self.visit_block(node.children[0])

    def visit_block(self, node: BlockNode):
        print(node)
        if node.declarations:
            self.visit_declarations(node.declarations)
        self.visit_compound_statement(node.compound_statement)

    def visit_declarations(self, node: DeclarationNode):
        for declaration in node:
            if isinstance(declaration, ConstDeclarationNode):
                self.visit_const_declaration(declaration)
            elif isinstance(declaration, TypeDeclarationNode):
                self.visit_type_declaration(declaration)
            elif isinstance(declaration, VarDeclarationNode):
                self.visit_var_declaration(declaration)
            elif isinstance(declaration, ProcedureOrFunctionDeclarationNode):
                self.visit_proc_or_func_declaration()

    def visit_compound_statement(self, node: CompoundStatementNode):
        ...

    def visit_proc_or_func_declaration(self):
        ...

    def create_array_info(self, node: ArrayTypeNode, declaration_place):
        """
        Эта функция проверяет, что размеры массива и его вложенности соответствуют
        указанным в декларации. Также проверяет соответствие типов данных в массиве.
        """

        type_checks = {
            "integer": int,
            "string": str,
        }

        def check_array_size_and_types(dimensions, values, level=0):
            if level == len(dimensions):

                if isinstance(values, RecordInitializerNode):
                    record_type = self.symbol_table.lookup(node.element_type)
                    if not record_type:
                        raise Exception(f"Record type '{node.record_type_name}' not found in symbol table")
                    self.validate_record_initializer(record_type, values)
                    return 1

                elif isinstance(values, list) and all(isinstance(v, RecordInitializerNode) for v in values):
                    record_type = self.symbol_table.lookup(node.record_type_name)
                    if not record_type:
                        raise Exception(f"Record type '{node.record_type_name}' not found in symbol table")
                    for record_instance in values:
                        self.validate_record_initializer(record_type, record_instance)
                    return len(values)

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

                elif expected_type is None:
                    record_type = self.symbol_table.lookup(node.element_type)
                    #print('a', record_type)
                    if record_type:
                        if isinstance(values, RecordInitializerNode):
                            # Вызываем отдельную функцию для проверки записи
                            return self.validate_record_initializer(record_type, values)
                        else:
                            raise Exception(f"Invalid initializer for record type '{record_type}'")


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

        # Получаем размеры из dimensions
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
                    "element_type": node.element_type,
                    "size": size,
                    "dimensions": node.dimensions,
                    "initial_values": node.initial_values
                }
                return arr_info

        elif declaration_place in ('var', 'record'):
            # Обработка для массива в записи
            arr_info = {
                "element_type": node.element_type,
                "size": size,
                "dimensions": node.dimensions,
                "initial_values": node.initial_values
            }

            if node.element_type == "record":
                arr_info["record_type_name"] = node.record_type_name

            # Проверяем типы начальных значений, если они заданы

            if node.initial_values is not None:

                total_elements = check_array_size_and_types(node.dimensions, node.initial_values)

                if total_elements != size:
                    raise ValueError(f'Array size is incorrect. Expected {size} elements, got {total_elements}')

            return arr_info

        return None

    def visit_type_declaration(self, node: TypeDeclarationNode):
        name = node.name
        type_node = node.type_node

        if isinstance(type_node, RecordTypeNode):
            fields = []
            for field_name, field in type_node.fields:
                print(field)
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

            print(fields)
            info = {
                "name": name,
                "type": 'record',
                "fields_info": fields
            }
            self.symbol_table.declare(name, info)

        elif isinstance(type_node, ArrayTypeNode):
            arr_info = self.create_array_info(type_node, "record")
            self.symbol_table.declare(name, arr_info)

    def validate_record_initializer(self, record_type_info, initializer_node):
        """
        Проверяет инициализацию записи RecordInitializerNode
        на соответствие информации о типе записи из record_type_info.
        """
        # Получаем список информации о полях из record_type_info
        fields_info = record_type_info.get("fields_info")
        if not fields_info:
            raise Exception(f"Record type '{record_type_info.get('name')}' has no fields information")

        initializer_fields = initializer_node.fields  # Это список пар (field_name, field_value)

        # Проверяем, совпадает ли количество полей
        if len(fields_info) != len(initializer_fields):
            raise Exception(
                f"Record initializer has incorrect number of fields for type '{record_type_info.get('name')}'")

        # Сравниваем каждое поле
        for field_info, (init_name, init_value) in zip(fields_info, initializer_fields):
            field_name = field_info["field_name"]
            field_type = field_info["field_type"]

            # Проверяем совпадение имен полей
            if field_name != init_name:
                raise Exception(f"Field name mismatch: expected '{field_name}', got '{init_name}'")

            # Проверяем тип значения
            type_checks = {
                "integer": int,
                "string": str,
            }

            if field_type in type_checks:
                expected_type = type_checks[field_type]
                if not isinstance(init_value, expected_type):
                    raise Exception(
                        f"Field '{field_name}' expected type '{field_type}', got '{type(init_value).__name__}'")

            elif field_type == "array":
                # Если тип — массив, вызываем функцию обработки массива
                arr_info = field_info.get("arr_info")
                if not arr_info:
                    raise Exception(f"Array field '{field_name}' has no array info")

                # Проверяем массив, создавая его информацию через create_array_info
                array_type_node = ArrayTypeNode(
                    element_type=arr_info["element_type"],
                    dimensions=arr_info["dimensions"],
                    initial_values=init_value  # Значение массива для проверки
                )

                # Проверяем массив как часть записи
                self.create_array_info(array_type_node, declaration_place="record")

            else:
                raise Exception(f"Unsupported field type '{field_type}' in record '{record_type_info.get('name')}'")

        # Если все проверки прошли успешно, возвращаем информацию
        return {
            "type": "record",
            "record_type": record_type_info["name"],
            "fields": {init_name: init_value for init_name, init_value in initializer_fields},
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
        print('a', record_type)
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
                        "type": var_type,
                        "value": init_value
                    }
                else:
                    # Создаём пустой RecordInitializerNode по умолчанию
                    default_record = self.create_default_record_initializer(record_type_info)
                    return {
                        "type": var_type,
                        "value": default_record
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
            "string": ""
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

        return RecordInitializerNode(fields=initializer_fields)

