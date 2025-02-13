import ast
import re

from semantic.symbol_table import SymbolTable


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

        self.output_lines.append('( function main_')
        # 2. Обрабатываем операторы.
        for stmt in self.statements:
            self.output_lines.append("  " + self.translate_statement(stmt))

        self.output_lines.append(')')

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
            return f"(call memcpy_ {target} {source}"

    def _lookup_symbol(self, name, sym_table=None):
        """
        Ищет символ в таблице символов.
        Если sym_table не передан, используется глобальная таблица.
        """
        if sym_table is None:
            sym_table = self.glob_sym_table
        return sym_table.lookup(name)

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
        inner = info.get("info", {})
        print('inner', info)
        # Если inner не является словарём, трактуем его как литеральное значение
        if not isinstance(inner, dict):
            return f'(const {name} "=" {inner})'

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
        if element_type in ['integer', 'char']:
            return f'({name} (({high} "-" {low}) "+" 1))'
        elif element_type != 'string':
            return f'({name} ((({high} "-" {low}) "+" 1) "*" {element_type}))'
        else:
            return f'({name} ((({high} "-" {low}) "+" 1)))'

    def translate_function(self, name, info):
        """
        Перевод функции или процедуры.
        Здесь обрабатываются параметры, затем локальные объявления (из local_symbol_table)
        так же, как в методе translate для глобальных объявлений, и затем тело функции.
        """
        # 1. Обработка параметров.
        params = info.get("parameters", [])
        params_list = " ".join(param["name"] for param in params)

        # 2. Обработка локальной таблицы символов.
        # Если локальная таблица представлена как dict, преобразуем её в SymbolTable.
        local_sym_table = info.get("local_symbol_table", {})
        if not hasattr(local_sym_table, "lookup"):
            tmp = SymbolTable()
            tmp.symbols = local_sym_table
            local_sym_table = tmp

        # Создаём список локальных объявлений, аналогично глобальным.
        local_decls = []
        # Проходим по всем символам локальной таблицы.
        # При этом параметры (kind == "parameter") мы пропускаем, так как они уже перечислены в header.
        for symbol, details in local_sym_table.symbols.items():
            if details.get("kind") == "parameter":
                continue
            # Обрабатываем объявление в зависимости от типа (const, record, var, или даже функция).
            if details.get("type") == "const":
                local_decls.append(self.translate_constant(symbol, details))
            elif details.get("type") == "record":
                local_decls.append(self.translate_record(symbol, details))
            elif details.get("type") == "var":
                local_decls.append(self.translate_variable(symbol, details))
            elif "kind" in details:
                local_decls.append(self.translate_function(symbol, details))

        # Формируем блок локальных переменных.
        if local_decls:
            local_decl_block = "(var\n  " + "\n  ".join(local_decls) + "\n)"
        else:
            local_decl_block = ";; нет локальных переменных"

        # 3. Обработка тела функции.
        block = info.get("block_code", {})
        if block.get("type") in ("block", "Block"):
            print('loc', local_sym_table.symbols)
            body_code = self.translate_block(block, indent="  ", sym_table=local_sym_table)
        else:
            body_code = ";; тело функции отсутствует"

        # Если это функция (а не процедура), добавляем оператор возврата.
        ret_line = ""
        if info.get("kind") == "function":
            ret_line = f"  (return {name})"

        # 4. Собираем всё вместе.
        func_code = (
            f"(function {name} ({params_list})\n"
            f"{local_decl_block}\n"
            f"{body_code}\n"
            f"{ret_line}\n)"
        )
        return func_code

    # ========================================================
    # Перевод операторов
    # ========================================================
    def translate_statement(self, stmt, sym_table=None):
        stype = stmt.get("type")
        if stype == "Assignment":
            return self._translate_assignment(stmt, sym_table)
        elif stype == "ProcedureCall":
            return self._translate_procedure_call(stmt, sym_table)
        elif stype == "For":
            return self.translate_for(stmt, sym_table)
        elif stype == "While":
            return self.translate_while(stmt, sym_table)
        elif stype == "If":
            return self.translate_if(stmt, sym_table)
        elif stype in ("Block", "block"):
            return self.translate_block(stmt, sym_table)
        else:
            return f";;; Неизвестный оператор: {stype}"

    def _translate_assignment(self, stmt, sym_table):
        # Получаем левую и правую части с учетом lvalue/rvalue.
        target_code = self.translate_expr(stmt.get("target"), lvalue=True, sym_table=sym_table)
        value_code = self.translate_expr(stmt.get("value"), lvalue=False, sym_table=sym_table)
        target_expr = stmt.get("target")

        # Если в target присутствует имя, ищем его в таблице символов.
        var = self._lookup_symbol(target_expr.get("name"), sym_table=sym_table) if "name" in target_expr else None
        if var:
            # Если ключ "info" отсутствует или равен None, используем сам var как информацию о типе.
            vinfo = var.get("info") if var.get("info") is not None else var
            if vinfo.get("type") == "record":
                return f"{target_code} {value_code}"
            if vinfo.get("type") == "array":
                elem_type = vinfo.get("element_type")
                dims = vinfo.get("dimensions")[0]
                low, high = dims[0], dims[1]

                if vinfo.get("element_type") not in ['integer', "string", "char"]:
                    return f'({self._call_memcpy(target_code, value_code, vinfo.get("element_type"))}({elem_type}) "*" (({high} - {low}) "+" 1)))'
                return f'{self._call_memcpy(target_code, value_code)} (({high} - {low}) "+" 1))'
        if target_expr.get("type") == 'ArrayAccess':
            var = self._lookup_symbol(target_expr.get("array"), sym_table=sym_table)
            # Аналогично, проверяем наличие информации о типе.
            vinfo = var.get("info") if var.get("info") is not None else var
            if vinfo.get("element_type") not in ['integer', "string", "char"]:
                return f'({self._call_memcpy(target_code, value_code, vinfo.get("element_type"))}))'
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
        elif etype == "Char":
            return self._translate_char(expr)
        elif etype == "Variable":
            return self._translate_variable(expr, lvalue, sym_table)
        elif etype in ("BinaryOperation", "BinaryExpression"):
            return self._translate_binary(expr, lvalue, sym_table)
        elif etype == "FunctionCall":
            return self._translate_function_call(expr, lvalue, sym_table)
        elif etype == "ArrayAccess":
            return self._translate_array_access(expr, lvalue, sym_table)
        elif etype == "RecordFieldAccess":
            return self._translate_record_field_access(expr, lvalue, sym_table)
        else:
            return "UNKNOWN_EXPR"

    def _translate_integer(self, expr):
        val = expr.get("value")
        # Если число представлено в виде bool, возвращаем "1" или "0".
        if isinstance(val, bool):
            return "1" if val else "0"
        return str(val)

    def _translate_char(self, expr):
        # Возвращаем ASCII код символа
        return str(expr.get('value'))
    def _translate_string(self, expr):
        return f"\"{expr.get('value')}\""

    def _translate_variable(self, expr, lvalue, sym_table=None):
        """
        Перевод переменной с использованием переданной таблицы символов.
        Если для переменной отсутствует ключ "info" (например, для параметра),
        то обрабатываем её как параметр и возвращаем (L var_name).
        """
        var_name = expr.get("name")
        var = self._lookup_symbol(var_name, sym_table)
        if var is None:
            return var_name

        # Если это параметр функции, оборачиваем в (L ...)
        if var.get("kind") == "parameter":
            if lvalue:
                return self._load(var_name)
            elif not lvalue:
                return self._load(self._load(var_name))

        # Если ключ "info" отсутствует или равен None, используем сам var как информацию о типе
        if "info" in var and var["info"] is not None:
            vinfo = var["info"]
        else:
            vinfo = var

        vtype = vinfo.get("type")
        if vtype in ['integer', 'boolean']:
            if lvalue:
                return var_name
            elif not lvalue:
                return self._load(var_name)
        if vtype == 'record':
            rec_type = vinfo.get("record_type")
            #tmp = f'({var_name} "*" {rec_type})'

            if lvalue:
                return f"(call memcpy_ {var_name}"
            else:
                return f"{var_name} {rec_type})"
        if vtype == 'array':
            return f'{var_name}'
        return var_name

    def _translate_binary(self, expr, lvalue, sym_table=None):
        op = expr.get("operator")
        left = self.translate_expr(expr.get("left"), lvalue, sym_table)
        right = self.translate_expr(expr.get("right"), lvalue, sym_table)
        return f'({left} "{op}" {right})'

    def _translate_function_call(self, expr, lvalue, sym_table=None):
        name = expr.get("name")
        args = expr.get("arguments", [])
        args_code = " ".join(self.translate_expr(arg, lvalue, sym_table) for arg in args)
        return f"({name} {args_code})"

    def _translate_index(self, expr, sym_table=None):
        """
        Перевод индексного выражения для массива.
        Если выражение представляет собой целочисленный литерал, возвращает его.
        Если выражение – переменная, возвращает (L var_name).
        Для остальных типов использует стандартный перевод с lvalue=True.
        """
        etype = expr.get("type")
        if etype == "Integer":
            return self._translate_integer(expr)
        elif etype == "Variable":
            # Для индексного выражения переменной всегда оборачиваем в _load
            # чтобы получить (L var_name)
            return self._load(expr.get("name"))
        else:
            # Для составных выражений используем перевод с lvalue=True
            return self.translate_expr(expr, lvalue=True, sym_table=sym_table)
    def _translate_array_access(self, expr, lvalue, sym_table=None):
        array_name = expr.get("array")
        arr_info = self._lookup_symbol(array_name, sym_table)
        # Если для массива описана информация через "info", используем её, иначе сам объект
        info = arr_info.get("info") if arr_info.get("info") is not None else arr_info
        element_type = info.get("element_type")
        dims = info.get("dimensions")[0]
        low = dims[0]
        indices = expr.get("indices", [])
        # Предположим, что используется один индекс.
        if indices:
            index_code = self._translate_index(indices[0], sym_table)
        else:
            index_code = "0"

        # Если массив является параметром, оборачиваем базу в _load
        if arr_info.get("kind") == "parameter":
            base = self._load(array_name)
        else:
            base = array_name

        if lvalue:
            # В lvalue-контексте просто формируем адрес элемента
            if element_type in ['integer', 'char']:
                return f'({base} "+" (({index_code} "-" {low})))'
            elif element_type != 'string':
                return f'({base} "+" (({index_code} "-" {low}) "*" {element_type}))'
            else:
                return f'(({base} "+" {index_code} "-" {low}))'
        else:
            # В rvalue-контексте сначала формируем lvalue-выражение для элемента,
            # а затем оборачиваем его в _load для извлечения значения
            if element_type in ['integer', 'char']:
                temp = f'({base} + (({index_code} "-" {low})))'
                return f'({self._load(temp)})'
            elif element_type != 'string':
                temp = f'({base} + ((({index_code} "-" {low}) "*" {element_type}))'
                return f'({self._load(temp)})'
            else:
                temp = f'({base} + ({index_code} "-" {low}))'
                return f'({self._load(temp)})'

    def _translate_record_field_access(self, expr, lvalue, sym_table=None):
        # Предполагаем, что для обращения к полю записи базовый оператор задаётся как { "name": "p" }
        rec = expr.get("record")
        field = expr.get("field")
        # Если базовая запись задана по имени, то используем его напрямую
        if "name" in rec:
            record_expr = rec["name"]
            var = self._lookup_symbol(record_expr, sym_table)
            # Если для символа нет вложенного "info", используем сам var как информацию о типе.
            if var.get("info") is not None:
                vinfo = var.get("info")
            else:
                vinfo = var
            # Если это параметр и нет record_type, берём тип из "type"
            if vinfo.get("kind") == "parameter" and not vinfo.get("record_type"):
                rec_type = vinfo.get("type", "")
            else:
                rec_type = vinfo.get("record_type", "")
            # Формируем выражение для доступа к полю.
            # Форматируем оператор плюс как литерал: " + "
            if lvalue:
                # Для lvalue оставляем базовый адрес без загрузки
                return f'({record_expr} \"+\" {rec_type}_{field})'
            else:
                # Для rvalue оборачиваем итоговое выражение в (L ...)
                temp = self._load(f'({record_expr} \"+\" {rec_type}_{field})')
                return f"({temp})"
        # Если запись задаётся через массив, аналогично обрабатываем
        elif "array" in rec:
            record_expr = rec["array"]
            var = self._lookup_symbol(record_expr, sym_table)
            if var.get("info") is not None:
                vinfo = var.get("info")
            else:
                vinfo = var
            elem_type = vinfo.get("element_type", "")
            if lvalue:
                return f'({record_expr} \"+\" {elem_type}_{field})'
            else:
                temp = self._load(f'{record_expr} \"+\" {elem_type}_{field}')
                return f"({temp})"
        return "UNKNOWN_FIELD_ACCESS"

    # ========================================================
    # Перевод блоков и циклов
    # ========================================================
    def translate_block(self, block, indent="", sym_table=None):
        """
        Перевод блока операторов без дополнительного оборачивания в скобки.
        Генерируется просто список операторов с отступами.
        """
        if block.get("type") not in ("Block", "block"):
            return self.translate_statement(block, sym_table)
        stmts = block.get("statements", [])
        if indent is None:
            indent = ""
        lines = []
        for stmt in stmts:
            stmt_code = self.translate_statement(stmt, sym_table)
            lines.append(f"{indent}{stmt_code}")
        return "\n  ".join(lines)

    def translate_for(self, stmt, sym_table=None):
        """
        Перевод цикла For.
        Исходный вид:
          {'type': 'For', 'loop_variable': 'i', 'start': {...}, 'direction': 'to', 'end': {...}, 'body': {...}}
        """
        loop_var = stmt.get("loop_variable")
        start_expr = self.translate_expr(stmt.get("start"), sym_table)
        end_expr = self.translate_expr(stmt.get("end"), sym_table)
        direction = stmt.get("direction")
        body = self.translate_block(stmt.get("body"), indent="  ", sym_table=sym_table)
        return f"(for {loop_var} {start_expr} {direction} {end_expr}\n{body}\n)"


    def translate_while(self, stmt, sym_table):
        """
        Перевод цикла While.
        """
        condition = self.translate_expr(stmt.get("condition"), sym_table=sym_table)
        print('body', stmt.get('body'))
        body = self.translate_block(stmt.get("body"), indent="  ", sym_table=sym_table)
        return f"(while {condition}\n  {body}\n  )"

    def translate_if(self, stmt, sym_table=None, indent=""):
        """
        Перевод оператора If согласно грамматике:
          (if t.BoolExpr e.Code else e.Code)
        Если ветка else пуста, то она не выводится.
        """
        condition = self.translate_expr(stmt.get("condition"), sym_table=sym_table)
        # Переводим then-часть с увеличенным отступом
        then_part = self.translate_block(stmt.get("then"), indent=indent + "  ", sym_table=sym_table)

        # Получаем ветку else
        else_stmt = stmt.get("else")
        else_part = ""
        # Если ветка else существует
        if else_stmt:
            # Если это блок, проверяем, содержит ли он непустой список операторов
            if else_stmt.get("type") in ("Block", "block"):
                stmts = else_stmt.get("statements", [])
                if stmts:  # Если список операторов не пустой
                    else_part = self.translate_block(else_stmt, indent=indent + "  ", sym_table=sym_table)
            else:
                # Если это не блок, просто переводим его
                else_part = self.translate_statement(else_stmt, sym_table)

        # Формируем итоговую строку. Если ветка else не пуста, включаем её
        if else_part:
            return f"(if {condition}\n  {indent}{then_part}\n{indent}    else\n  {indent}  {else_part}\n    )"
        else:
            return f"(if {condition}\n{indent}    {then_part}\n{6*' '})"

