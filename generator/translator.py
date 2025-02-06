import ast
import re


class Translator:
    def __init__(self, semantic_json, statements):
        """
        semantic_json: словарь вида
          {
            "GLOBAL Symbol_Table": {
                symbol: str(details), ...
            }
          }
        statements: список операторов (AST-узлов), полученных после семантического анализа,
                    например: sem.code_generator['statements']
        """
        self.semantic_json = semantic_json
        self.symbol_table = semantic_json.get("GLOBAL Symbol_Table", {})
        self.statements = statements
        self.output_lines = []

    def translate(self):
        # Сначала обрабатываем объявления из таблицы символов.
        for symbol, details_str in self.symbol_table.items():
            info = self._parse_info(details_str)
            print(info)  # отладочный вывод
            if info.get("type") == "const":
                self.output_lines.append(self.translate_constant(symbol, info))
            # Если это структура
            elif info.get("type") == "record":
                self.output_lines.append(self.translate_record(symbol, info))
            # Если это объявление типа, записанного в "info" (например, массив)
            elif "info" in info and isinstance(info["info"], dict):
                ttype = info.get("type")
                nested_type = info["info"].get("type")
                # Если тип во вложенном словаре – array, то обрабатываем как тип-массив
                if nested_type == "array":
                    self.output_lines.append(self.translate_array_type(symbol, info["info"], ttype))
                else:
                    # Если вдруг что-то ещё – можно обрабатывать как переменную
                    self.output_lines.append(self.translate_variable(symbol, info))
            # Если это переменная (например, var), которая может иметь вложенный info
            elif info.get("type") == "var":
                # В данном случае может быть как обычная переменная, так и переменная-массив, если тип записан во вложенном info
                if "info" in info and isinstance(info["info"], dict):
                    nested_type = info["info"].get("type")
                    if nested_type == "array":
                        self.output_lines.append(self.translate_variable(symbol, info))
                    else:
                        self.output_lines.append(self.translate_variable(symbol, info))
                else:
                    self.output_lines.append(self.translate_variable(symbol, info))
            elif "kind" in info:
                self.output_lines.append(self.translate_function(symbol, info))

        # Затем обрабатываем операторы из сгенерированного списка.
        for stmt in self.statements:
            self.output_lines.append(self.translate_statement(stmt))

        return "\n".join(self.output_lines)

    def _parse_info(self, info_str):
        """
        Преобразует строковое представление словаря в настоящий словарь.
        Для этого предварительно оборачивает нестроковые идентификаторы (например, integer)
        в кавычки.
        """
        # Пример регулярного выражения, которое ищет случаи вида: : integer, : boolean и т.д.
        # и заменяет их на : "integer", : "boolean" и т.п.
        info_str = re.sub(r":\s*([a-zA-Z_]\w*)(\s*[,}])", r': "\1"\2', info_str)
        # Заменяем подстроки вида <...> на None
        cleaned = re.sub(r"<(?!>)[^>]+>", "None", info_str)
        try:
            return ast.literal_eval(cleaned)
        except Exception as e:
            print(f"Ошибка при парсинге: {info_str}\n{e}")
            return {}

    def translate_record(self, name, info):
        """
        Перевод описания record’а в конструкцию вида:
          (struct TPerson (name string) (age integer))
        """
        fields = info.get("fields_info", [])
        fields_code = " ".join(f"({field['field_name']} {field['field_type']})" for field in fields)
        return f"(struct {name} {fields_code})"

    def translate_array_type(self, name, info, ttype):
        """
        Перевод описания типа массива.
        Например, генерируется конструкция вида:
          (const subarray (array integer 4))
        """
        element_type = info.get("element_type")
        size = info.get("size")
        return f"({ttype} {name} (array {element_type} {size}))"

    def translate_constant(self, name, info):
        """
        Обрабатывает константное объявление.
        Если info содержит инициализатор записи, то генерирует код вида:
          (const <name> (record <record_type>) (fields (<record_type>_field1 value1) (<record_type>_field2 value2) ...))
        """
        inner = info.get("info", {})
        if inner.get("type") == "record":
            record_type = inner.get("record_type")
            fields = inner.get("fields", {})
            # Формируем список инициализаторов для полей записи.
            # Например, для 'name': 'John' и 'age': 30 будет: (TPerson_name "John") (TPerson_age 30)
            field_inits = []
            for field, value in fields.items():
                # Если значение строковое, то его оборачиваем в кавычки
                if isinstance(value, str):
                    value_repr = f"\"{value}\""
                else:
                    value_repr = str(value)
                field_inits.append(f"({record_type}_{field} {value_repr})")
            fields_code = " ".join(field_inits)
            # Генерируем итоговое объявление константы
            return f"(const {name} (struct {record_type} {fields_code}))"
        # Если константа не является записью, можно обработать другие варианты (например, числовые константы)
        else:
            # Предположим, что value у нас содержится прямо в inner под ключом 'value'
            value = inner.get("value", "0")
            return f"(const {name} {value})"

    def process_fields(self, prefix, fields):
        """
        Рекурсивно обходит словарь fields и формирует список инициализаций полей.
        Для простого поля (не словаря) генерируется строка:
          (prefix_field value)
        Если значение является словарём, то вызывается рекурсия с новым префиксом:
          prefix_new = prefix + "_" + key
        Пример:
          process_fields("TPerson", {'p': {'name': 'John', 'age': 30}})
          вернёт: ['(TPerson_p_name "John")', '(TPerson_p_age 30)']
        """
        inits = []
        #print(fields)
        if isinstance(fields, list):
            fields = {key: value for key, value in fields}
        for key, value in fields.items():
            if isinstance(value, dict):
                new_prefix = f"{prefix}_{key}"
                inits.extend(self.process_fields(new_prefix, value))
            else:
                # Если значение строковое, оборачиваем в кавычки
                if isinstance(value, str):
                    value_repr = f"\"{value}\""
                else:
                    value_repr = str(value)
                inits.append(f"({prefix}_{key} {value_repr})")
        return inits

    def translate_variable(self, name, info):
        """
        Перевод объявления переменной.
        Примеры:
          (var a string)
          (var arr2 (array integer "*" 3))
          (var person TPerson)
          (var person (record TPerson) (fields (TPerson_name "John") (TPerson_age 30)))
        """
        var_info = info.get("info", {})
        vtype = var_info.get("type")

        if vtype == "array":
            element_type = var_info.get("element_type")
            size = var_info.get("size")
            type_expr = f"(array {element_type} \"*\" {size})"
            return f"(var {name} {type_expr})"

        elif vtype == "record":
            record_type = var_info.get("record_type")
            fields = var_info.get("fields", {})
            # Рекурсивно обрабатываем поля, чтобы корректно учесть вложенные структуры
            field_inits = self.process_fields(record_type, fields)
            fields_code = " ".join(field_inits)
            return f"(var {name} (struct {record_type} {fields_code}))"

        else:
            # Если это простой тип (например, string, integer и т.д.)
            type_expr = vtype
            return f"(var {name} {type_expr})"

    def translate_function(self, name, info):
        """
        Перевод функции/процедуры.
        Пример результата:
          (function Sum (a b)
             ...тело...
             (return Sum)
          )
        """
        params = info.get("parameters", [])
        params_list = " ".join(param["name"] for param in params)
        header = f"(function {name} ({params_list})"
        body_lines = []
        block = info.get("block_code", {})
        if block.get("type") in ("block", "Block"):
            body_lines.extend(self.translate_block(block, indent="  ").split("\n"))
        if info.get("kind") == "function":
            # Добавляем возврат результата (если требуется)
            body_lines.append(f"  (return {name})")
        body = "\n".join(body_lines)
        return f"{header}\n{body}\n)"

    # --------------- Перевод операторов и выражений ---------------

    def translate_statement(self, stmt):
        stype = stmt.get("type")
        if stype == "Assignment":
            target_code = self.translate_expr(stmt.get("target"))
            value_code = self.translate_expr(stmt.get("value"))
            return f"({target_code} \"=\" {value_code})"
        elif stype == "ProcedureCall":
            name = stmt.get("name")
            args = stmt.get("arguments", [])
            args_code = " ".join(self.translate_expr(arg) for arg in args)
            return f"({name} {args_code})"
        elif stype == "For":
            return self.translate_for(stmt)
        elif stype == "While":
            return self.translate_while(stmt)
        elif stype == "If":
            return self.translate_if(stmt)
        elif stype in ("Block", "block"):
            return self.translate_block(stmt)
        else:
            return f";;; Неизвестный оператор: {stype}"

    def translate_expr(self, expr):
        etype = expr.get("type")
        if etype == "Variable":
            return expr.get("name")
        elif etype == "Integer":
            val = expr.get("value")
            if isinstance(val, bool):
                return "true" if val else "false"
            return str(val)
        elif etype == "String":
            return f"\"{expr.get('value')}\""
        # Объединяем обработку для BinaryOperation и BinaryExpression
        elif etype in ("BinaryOperation", "BinaryExpression"):
            op = expr.get("operator")
            left = self.translate_expr(expr.get("left", {}))
            right = self.translate_expr(expr.get("right", {}))
            return f"({left} {op} {right})"
        elif etype == "FunctionCall":
            name = expr.get("name")
            args = expr.get("arguments", [])
            args_code = " ".join(self.translate_expr(arg) for arg in args)
            return f"({name} {args_code})"
        elif etype == "ArrayAccess":
            array_name = expr.get("array")
            indices = expr.get("indices", [])
            indices_code = " ".join(self.translate_expr(ind) for ind in indices)
            return f"(L {array_name} {indices_code})"
        elif etype == "RecordFieldAccess":
            record_expr = self.translate_expr(expr.get("record"))
            field = expr.get("field")
            return f"{record_expr}_{field}"
        return "UNKNOWN_EXPR"

    def translate_block(self, block, indent=""):
        """
        Перевод блока операторов в виде:
          (block stmt1 stmt2 ...)
        """
        if block.get("type") not in ("Block", "block"):
            return self.translate_statement(block)
        stmts = block.get("statements", [])
        lines = [f"{indent}("]
        for stmt in stmts:
            stmt_code = self.translate_statement(stmt)
            lines.append(f"{indent}  {stmt_code}")
        lines.append(f"{indent})")
        return "\n".join(lines)

    def translate_for(self, stmt):
        """
        Перевод цикла For.
        Исходный вид:
          {'type': 'For',
           'loop_variable': 'i',
           'start': {...},
           'direction': 'to',
           'end': {...},
           'body': {...}}
        Пример генерируемого кода:
          (for i <start> to <end>
            <body>)
        """
        loop_var = stmt.get("loop_variable")
        start_expr = self.translate_expr(stmt.get("start"))
        end_expr = self.translate_expr(stmt.get("end"))
        direction = stmt.get("direction")
        body = self.translate_block(stmt.get("body"), indent="  ")
        return f"(for {loop_var} {start_expr} {direction} {end_expr}\n{body}\n)"

    def translate_while(self, stmt):
        """
        Перевод цикла While.
        Исходный вид:
          {'type': 'While', 'condition': {...}, 'body': {...}}
        Пример:
          (while <condition>
            <body>)
        """
        condition = self.translate_expr(stmt.get("condition"))
        body = self.translate_block(stmt.get("body"), indent="  ")
        return f"(while {condition}\n{body}\n)"

    def translate_if(self, stmt):
        """
        Перевод оператора If.
        Исходный вид:
          {'type': 'If', 'condition': {...}, 'then': {...}, 'else': {...}}
        Пример:
          (if <condition>
              <then>
              <else>)
        """
        condition = self.translate_expr(stmt.get("condition"))
        then_part = self.translate_block(stmt.get("then"), indent="  ")
        else_part = ""
        if stmt.get("else"):
            else_part = self.translate_block(stmt.get("else"), indent="  ")
            return f"(if {condition}\n  {then_part}\n  {else_part}\n)"
        else:
            return f"(if {condition}\n  {then_part}\n)"


