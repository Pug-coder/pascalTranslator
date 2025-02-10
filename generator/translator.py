import ast
import re


import re
import ast

class Translator:
    def __init__(self, glob_sym_table, semantic_json, statements):
        """
        :param glob_sym_table: глобальная таблица символов с методом lookup(name)
        :param semantic_json: словарь, содержащий, например, "GLOBAL Symbol_Table": { symbol: details_str, ... }
        :param statements: список AST-узлов операторов (например, sem.code_generator['statements'])
        """
        self.glob_sym_table = glob_sym_table
        self.semantic_json = semantic_json
        self.symbol_table = semantic_json.get("GLOBAL Symbol_Table", {})
        self.statements = statements
        self.output_lines = []
        self.global_var_decl = []
        self.local_var_decl = []

    # ========================================================
    # Основной метод трансляции
    # ========================================================
    def translate(self):
        # 1. Обрабатываем глобальные объявления из таблицы символов.
        for symbol, details_str in self.symbol_table.items():
            info = self._parse_info(details_str)
            print(info)  # отладочный вывод
            if info.get("type") == "const":
                self.output_lines.append(self.translate_constant(symbol, info))
            elif info.get("type") == "record":
                self.output_lines.append(self.translate_record(symbol, info))
            elif info.get("type") == "var":
                self.global_var_decl.append(self.translate_variable(symbol, info))
            elif "kind" in info:
                self.output_lines.append(self.translate_function(symbol, info))

        if self.global_var_decl:
            var_block = "(var\n  " + "\n  ".join(self.global_var_decl) + "\n)"
            self.output_lines.append(var_block)

        # 2. Обрабатываем операторы.
        for stmt in self.statements:
            self.output_lines.append(self.translate_statement(stmt))

        return "\n".join(self.output_lines)

    # ========================================================
    # Вспомогательные функции для формирования кода
    # ========================================================
    def _wrap(self, code):
        """Оборачивает строку в скобки."""
        return f"({code})"

    def _load(self, code):
        """Генерирует загрузку значения (оператор L)."""
        return f"(L {code})"

    def _call_memcpy(self, target, source, type_spec=None):
        """Генерирует вызов memcpy_ с необязательным указанием типа."""
        if type_spec:
            return f"(call memcpy_ {target} {source} {type_spec})"
        else:
            return f"(call memcpy_ {target} {source})"

    def _lookup_symbol(self, name):
        """Вспомогательный метод для поиска информации о символе."""
        return self.glob_sym_table.lookup(name)

    # ========================================================
    # Обработка таблицы символов (глобальных объявлений)
    # ========================================================
    def _parse_info(self, info_str):
        """
        Преобразует строковое представление словаря в настоящий словарь.
        Например, оборачивает нестроковые идентификаторы в кавычки.
        """
        info_str = re.sub(r":\s*([a-zA-Z_]\w*)(\s*[,}])", r': "\1"\2', info_str)

        def symbol_table_replacer(match):
            text = match.group(0)
            return f'"{text}"' if "SymbolTable" in text else "None"

        cleaned = re.sub(r"<(?!>)[^>]+>", symbol_table_replacer, info_str)
        try:
            return ast.literal_eval(cleaned)
        except Exception as e:
            print(f"Ошибка при парсинге: {info_str}\n{e}")
            return {}

    def translate_record(self, name, info):
        """
        Перевод описания record’а в конструкцию вида:
          (struct RecordName
             (RecordName_field1 type1)
             (RecordName_field2 type2)
             ...)
        """
        fields = info.get("fields_info", [])

        def map_type_val(field):
            mapping = {"integer": 1, "boolean": 1}
            return mapping.get(field['field_type'], field['field_type'])

        fields_code = " ".join(
            f"\n ({name}_{field['field_name']} {map_type_val(field)})"
            for field in fields
        )
        return f"(struct {name} {fields_code}\n)"

    def translate_array_type(self, name, info, ttype):
        """
        Перевод описания типа массива.
        Например, генерируется конструкция вида:
          (const subarray (array element_type size))
        """
        element_type = info.get("element_type")
        size = info.get("size")
        return f"({ttype} {name} (array {element_type} {size}))"

    def translate_constant(self, name, info):
        """
        Обрабатывает константное объявление.
        Если это запись, генерируется блочное копирование полей.
        """
        inner = info.get("info", {})
        if inner.get("type") == "record":
            record_type = inner.get("record_type")
            fields = inner.get("fields", {})
            field_inits = []
            for field, value in fields.items():
                value_repr = f"\"{value}\"" if isinstance(value, str) else str(value)
                field_inits.append(f"({record_type}_{field} {value_repr})")
            fields_code = " ".join(field_inits)
            return f"(const {name} (struct {record_type} {fields_code}))"
        else:
            value = inner.get("value", "0")
            return f'(const {name} "=" {value})'

    def process_fields(self, prefix, fields):
        """
        Рекурсивно обходит словарь полей и формирует список инициализаций.
        Например, для:
          process_fields("TPerson", {'name': 'John', 'age': 30})
        вернёт:
          ['(TPerson_name "John")', '(TPerson_age 30)']
        """
        inits = []
        if isinstance(fields, list):
            fields = {key: value for key, value in fields}
        for key, value in fields.items():
            if isinstance(value, dict):
                new_prefix = f"{prefix}_{key}"
                inits.extend(self.process_fields(new_prefix, value))
            else:
                value_repr = f"\"{value}\"" if isinstance(value, str) else str(value)
                inits.append(f"({prefix}_{key} {value_repr})")
        return inits

    def translate_variable(self, name, info):
        """
        Перевод объявления переменной.
        Выбирается обработчик для простых переменных, массивов или записей.
        """
        var_info = info.get("info", {})
        vtype = var_info.get("type")
        if vtype == "array":
            return self.translate_glob_var_array(name, info)
        elif vtype == "record":
            return self.translate_global_var_struct(name, info)
        else:
            return self.translate_global_simple_var(name, info)

    def translate_global_simple_var(self, name, info):
        """
        Перевод простых переменных (например, integer, boolean).
        """
        var_info = info.get("info", {})
        vtype = var_info.get("type")
        # Для integer и boolean размер считается равным 1.
        if vtype in ['integer', 'boolean']:
            return f'({name} 1)'
        return f'({name} 1)'

    def translate_global_var_struct(self, name, info):
        """
        Перевод объявления переменной-структуры.
        """
        var_info = info.get("info", {})
        record_type = var_info.get("record_type")
        return f"({name} {record_type})"

    def translate_glob_var_array(self, name, info):
        """
        Перевод объявления переменной-массива.
        Для integer не используется умножение на размер.
        """
        var_info = info.get("info", {})
        element_type = var_info.get("element_type")
        dims = var_info.get("dimensions")[0]
        low, high = dims[0], dims[1]
        if element_type == 'integer':
            return f'({name} (({high} "-" {low}) "+" 1))'
        elif element_type != 'string':
            return f'({name} ((({high} "-" {low}) "+" 1) "*" {element_type}))'
        else:
            return f'({name} ((({high} "-" {low}) "+" 1)))'

    def translate_function(self, name, info):
        """
        Перевод функции или процедуры.
        Пример результата:
          (function Sum (a b)
            ( ; локальные переменные )
            ; тело функции
            (return Sum)
          )
        """
        params = info.get("parameters", [])
        params_list = " ".join(param["name"] for param in params)
        local_sym_table = info.get("local_symbol_table", {})
        non_parameters = {
            key: value
            for key, value in local_sym_table.items()
            if value.get("kind") != "parameter"
        }
        header = f"(function {name} ({params_list})"
        local_vars_lines = []
        if non_parameters:
            local_vars_lines.append("  (")
            for var_name, var_info in non_parameters.items():
                var_value = var_info.get("info", {}).get("value", "")
                vtype = var_info.get("type")
                local_vars_lines.append(f"    ({vtype} {var_name} \"=\" {var_value})")
            local_vars_lines.append("  )")
        else:
            local_vars_lines.append("  ;; нет локальных переменных")
        body_lines = []
        block = info.get("block_code", {})
        if block.get("type") in ("block", "Block"):
            body_lines.extend(self.translate_block(block, indent="  ").split("\n"))
        if info.get("kind") == "function":
            body_lines.append(f"  (return {name})")
        all_lines = [header] + local_vars_lines + body_lines + [")"]
        return "\n".join(all_lines)

    # ========================================================
    # Перевод операторов
    # ========================================================
    def translate_statement(self, stmt):
        stype = stmt.get("type")
        if stype == "Assignment":
            return self._translate_assignment(stmt)
        elif stype == "ProcedureCall":
            return self._translate_procedure_call(stmt)
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

    def _translate_assignment(self, stmt):
        # Получаем левую и правую части с учетом lvalue/rvalue.
        target_code = self.translate_expr(stmt.get("target"), lvalue=True)
        value_code = self.translate_expr(stmt.get("value"), lvalue=False)
        target_expr = stmt.get("target")

        # Если переменная имеет специальный тип (record или массив), вызываем memcpy_.
        var = self._lookup_symbol(target_expr.get("name")) if "name" in target_expr else None
        if var:
            vinfo = var.get("info")
            if vinfo.get("type") == "record":
                return f"{target_code} {value_code}"
            if vinfo.get("type") == "array":
                if vinfo.get("element_type") not in ['integer', "string"]:
                    return self._call_memcpy(target_code, value_code, vinfo.get('element_type'))
                return self._call_memcpy(target_code, value_code)
        if target_expr.get("type") == 'ArrayAccess':
            var = self._lookup_symbol(target_expr.get("array"))
            vinfo = var.get("info")
            if vinfo.get("element_type") not in ['integer', "string"]:
                return self._call_memcpy(target_code, value_code, vinfo.get('element_type'))
        return f"({target_code} \"=\" {value_code})"

    def _translate_procedure_call(self, stmt):
        name = stmt.get("name")
        args = stmt.get("arguments", [])
        args_code = " ".join(self.translate_expr(arg) for arg in args)
        return f"({name} {args_code})"

    # ========================================================
    # Перевод выражений с разбиением по типам
    # ========================================================
    def translate_expr(self, expr, lvalue=False, sym_table=None):
        etype = expr.get("type")
        if etype == "Integer":
            return self._translate_integer(expr)
        elif etype == "String":
            return self._translate_string(expr)
        elif etype == "Variable":
            return self._translate_variable(expr, lvalue)
        elif etype in ("BinaryOperation", "BinaryExpression"):
            return self._translate_binary(expr, lvalue)
        elif etype == "FunctionCall":
            return self._translate_function_call(expr, lvalue)
        elif etype == "ArrayAccess":
            return self._translate_array_access(expr, lvalue)
        elif etype == "RecordFieldAccess":
            return self._translate_record_field_access(expr, lvalue)
        else:
            return "UNKNOWN_EXPR"

    def _translate_integer(self, expr):
        val = expr.get("value")
        # Если число представлено в виде bool, возвращаем "1" или "0".
        if isinstance(val, bool):
            return "1" if val else "0"
        return str(val)

    def _translate_string(self, expr):
        return f"\"{expr.get('value')}\""

    def _translate_variable(self, expr, lvalue):
        var_name = expr.get("name")
        var = self._lookup_symbol(var_name)
        vinfo = var.get("info")
        vtype = vinfo.get("type")
        if vtype in ['integer', 'boolean']:
            return var_name
        if vtype == 'record':
            rec_type = vinfo.get("record_type")
            tmp = f"{var_name} * {rec_type}"
            if lvalue:
                # Формируем строку для lvalue с вызовом memcpy_ с загрузкой адреса
                return f"(call memcpy_ {self._load(tmp)})"
            else:
                # Формируем строку для rvalue, где добавляем тип структуры
                return f"({self._load(tmp)} {rec_type})"
        if vtype == 'array':
            return self._load(var_name)
        return var_name
    def _translate_binary(self, expr, lvalue):
        op = expr.get("operator")
        left = self.translate_expr(expr.get("left"), lvalue)
        right = self.translate_expr(expr.get("right"), lvalue)
        return f'({left} "{op}" {right})'

    def _translate_function_call(self, expr, lvalue):
        name = expr.get("name")
        args = expr.get("arguments", [])
        args_code = " ".join(self.translate_expr(arg, lvalue) for arg in args)
        return f"({name} {args_code})"

    def _translate_array_access(self, expr, lvalue):
        array_name = expr.get("array")
        arr_info = self._lookup_symbol(array_name)
        element_type = arr_info.get('info').get("element_type")
        dims = arr_info.get('info').get("dimensions")[0]
        low = dims[0]
        indices = expr.get("indices", [])
        # Предположим, что используется один индекс.
        index_code = self.translate_expr(indices[0], lvalue) if indices else "0"
        if lvalue:
            if element_type == 'integer':
                return f'({array_name} "+" (({self._load(index_code)} "-" {low})))'
            elif element_type != 'string':
                return f'({array_name} "+" (({self._load(index_code)} "-" {low}) "*" {element_type}))'
            else:
                return f'(({array_name} "+" {self._load(index_code)} "-" {low}))'
        else:
            if element_type == 'integer':
                return f'({self._load(f"{array_name} + (({self._load(index_code)} - {low}))")})'
            elif element_type != 'string':
                return f'{array_name} + ((({self._load(index_code)} - {low}) * {element_type}))'
            else:
                return f'(({array_name} + ({self._load(index_code)} - {low})))'

    def _translate_record_field_access(self, expr, lvalue):
        record_expr = self.translate_expr(expr.get("record"), lvalue)
        field = expr.get("field")
        rec = expr.get("record")
        if "name" in rec:
            var = self._lookup_symbol(rec["name"])
            vinfo = var.get("info")
            rec_name = rec["name"]
            rec_type = vinfo.get("record_type")
            if lvalue:
                return f'({rec_name} "+" {rec_type}_{field})'
            else:
                tmp = f"{rec_name} + {rec_type}_{field}"
                return f'({self._load(tmp)})'
        elif "array" in rec:
            var = self._lookup_symbol(rec["array"])
            vinfo = var.get("info")
            elem_type = vinfo.get("element_type")
            if lvalue:
                return f'({record_expr} "+" {elem_type}_{field})'
            else:
                tmp = f"{record_expr} + {elem_type}_{field}"
                return f'({self._load(tmp)})'
        return "UNKNOWN_FIELD_ACCESS"

    # ========================================================
    # Перевод блоков и циклов
    # ========================================================
    def translate_block(self, block, indent=""):
        """
        Перевод блока операторов вида:
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
          {'type': 'For', 'loop_variable': 'i', 'start': {...}, 'direction': 'to', 'end': {...}, 'body': {...}}
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
        """
        condition = self.translate_expr(stmt.get("condition"))
        body = self.translate_block(stmt.get("body"), indent="  ")
        return f"(while {condition}\n{body}\n)"

    def translate_if(self, stmt):
        """
        Перевод оператора If.
        """
        condition = self.translate_expr(stmt.get("condition"))
        then_part = self.translate_block(stmt.get("then"), indent="  ")
        if stmt.get("else"):
            else_part = self.translate_block(stmt.get("else"), indent="  ")
            return f"(if {condition}\n  {then_part}\n  {else_part}\n)"
        else:
            return f"(if {condition}\n  {then_part}\n)"



