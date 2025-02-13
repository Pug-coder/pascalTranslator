from parser.ast_node import *


class CodeGenerator:
    def __init__(self):
        self.result = []

    def generate(self, node):
        """Основная функция генерации кода. Определяет тип узла и вызывает соответствующий генератор."""
        if isinstance(node, CompoundStatementNode):
            return self.generate_compound_statement(node)
        elif isinstance(node, AssignStatementNode):
            return self.generate_assign_statement(node)
        elif isinstance(node, ForStatementNode):
            return self.generate_for_statement(node)
        elif isinstance(node, WhileStatementNode):
            return self.generate_while_statement(node)
        elif isinstance(node, ExpressionNode):
            return self.generate_expression(node)
        elif isinstance(node, SimpleExpressionNode):
            return self.generate_simple_expression(node)
        elif isinstance(node, FactorNode):
            return self.generate_factor(node)
        elif isinstance(node, ArrayAccessNode):
            return self.generate_array_access(node)
        elif isinstance(node, RecordFieldAccessNode):
            return self.generate_record_field_access(node)
        elif isinstance(node, IfStatementNode):
            return self.generate_if_statement(node)
        # Новые узлы для функций и процедур:
        elif isinstance(node, ProcedureOrFunctionDeclarationNode):
            return self.generate_proc_or_func_decl(node)
        elif isinstance(node, ProcedureCallNode):
            return self.generate_proc_call(node)
        elif isinstance(node, FunctionCallNode):
            return self.generate_func_call(node)
        return None

    def generate_compound_statement(self, node: CompoundStatementNode):
        """Генерирует блок операторов."""
        return {
            "type": "Block",
            "statements": [self.generate(stmt) for stmt in node.statements]
        }

    def generate_assign_statement(self, node: AssignStatementNode):
        """Генерирует присваивание.

        Если target (идентификатор) не является строкой (например, обращение к массиву
        или к полю записи), генерируется специальная структура.
        """
        if isinstance(node.identifier, (ArrayAccessNode, RecordFieldAccessNode)):
            target = self.generate(node.identifier)
        else:
            target = {"type": "Variable", "name": node.identifier}

        return {
            "type": "Assignment",
            "target": target,
            "value": self.generate(node.expression)
        }

    def generate_expression(self, node: ExpressionNode):
        # Если узел содержит реляционный оператор, генерируем код для обоих операндов
        if getattr(node, "relational_operator", None):
            left_code = self.generate(node.left)
            right_code = self.generate(node.right)
            return {
                "type": "BinaryExpression",
                "operator": node.relational_operator,
                "left": left_code,
                "right": right_code
            }
        # Иначе (если оператора нет) — обрабатываем только левую часть
        return self.generate(node.left)

    def generate_simple_expression(self, node: SimpleExpressionNode):
        """Генерирует сложное (инфиксное) выражение, например: a + b + c."""
        if len(node.terms) == 1:
            return self.generate(node.terms[0])

        left = self.generate(node.terms[0])
        for i in range(1, len(node.terms), 2):
            operator = node.terms[i]
            right = self.generate(node.terms[i + 1])
            left = {
                "type": "BinaryOperation",
                "operator": operator,
                "left": left,
                "right": right
            }
        return left

    def generate_factor(self, node: FactorNode):
        """Генерирует отдельные факторы (переменные, литералы, подвыражения)."""
        if node.sub_expression:
            return self.generate(node.sub_expression)

        if node.identifier:
            return {"type": "Variable", "name": node.identifier}

        if isinstance(node.value, int):
            return {"type": "Integer", "value": node.value}
        if isinstance(node.value, str):
            if len(node.value) == 1:  # Если строка длины 1 - это char
                return {"type": "Char", "value": ord(node.value)}  # Преобразуем в ASCII код
            return {"type": "String", "value": node.value}
        if isinstance(node.value, str):
            return {"type": "String", "value": node.value}

        raise Exception(f"Неизвестный фактор: {node.to_dict()}")

    def generate_for_statement(self, node: ForStatementNode):
        """
        Преобразует for-цикл вида:
          for j := i + 1 to n do <body>
        в эквивалентный код с предварительной инициализацией переменной цикла,
        циклом while и оператором обновления.
        Итоговая структура:
          Block {
              statements: [
                  <инициализация: j := i + 1>,
                  While {
                      condition: (j <= n)  (или j >= n для downto),
                      body: Block {
                          statements: [
                              <тело цикла>,
                              <обновление: j := j + 1>  (или j := j - 1 для downto)
                          ]
                      }
                  }
              ]
          }
        """
        # 1. Инициализация переменной цикла: j := i + 1
        init_assignment = {
            "type": "Assignment",
            "target": {"type": "Variable", "name": node.identifier},  # j
            "value": self.generate(node.start_expr)  # генерирует выражение i + 1
        }

        # 2. В зависимости от направления цикла формируем условие и оператор обновления
        if node.direction.lower() == "to":
            condition = {
                "type": "BinaryExpression",
                "operator": "<=",
                "left": {"type": "Variable", "name": node.identifier},  # j
                "right": self.generate(node.end_expr)  # генерирует n
            }
            update = {
                "type": "Assignment",
                "target": {"type": "Variable", "name": node.identifier},  # j
                "value": {
                    "type": "BinaryOperation",
                    "operator": "+",
                    "left": {"type": "Variable", "name": node.identifier},  # j
                    "right": {"type": "Integer", "value": 1}  # + 1
                }
            }
        elif node.direction.lower() == "downto":
            condition = {
                "type": "BinaryExpression",
                "operator": ">=",
                "left": {"type": "Variable", "name": node.identifier},
                "right": self.generate(node.end_expr)
            }
            update = {
                "type": "Assignment",
                "target": {"type": "Variable", "name": node.identifier},
                "value": {
                    "type": "BinaryOperation",
                    "operator": "-",
                    "left": {"type": "Variable", "name": node.identifier},
                    "right": {"type": "Integer", "value": 1}
                }
            }
        else:
            raise Exception(f"Неподдерживаемое направление цикла: {node.direction}")

        # 3. Генерируем цикл while, тело которого состоит из:
        #    - тела исходного for-цикла
        #    - оператора обновления переменной цикла
        while_node = {
            "type": "While",
            "condition": condition,
            "body": {
                "type": "Block",
                "statements": [
                    self.generate(node.body),
                    update
                ]
            }
        }

        # 4. Возвращаем блок (Block), содержащий сначала инициализацию, затем цикл while
        return {
            "type": "Block",
            "statements": [
                init_assignment,
                while_node
            ]
        }

    def generate_while_statement(self, node: WhileStatementNode):
        """Генерирует WHILE-цикл.

        Ожидается, что узел содержит:
          - condition: условие цикла (выражение)
          - body: тело цикла (оператор или составной оператор)
        """
        return {
            "type": "While",
            "condition": self.generate(node.condition),
            "body": self.generate(node.body)
        }

    def generate_array_access(self, node: ArrayAccessNode):
        """Генерирует обращение к массиву с поддержкой вложенных обращений."""
        base, indices = self.flatten_array_access(node)
        return {
            "type": "ArrayAccess",
            "array": base,
            "indices": [self.generate(index) for index in indices]
        }

    def flatten_array_access(self, node: ArrayAccessNode):
        """Вспомогательная функция для разворачивания вложенных обращений к массиву.

        Например, для arr[i][j] возвращает ('arr', [i, j]).
        """
        indices = []
        current = node
        while isinstance(current, ArrayAccessNode):
            if isinstance(current.index_expr, list):
                indices = current.index_expr + indices
            else:
                indices = [current.index_expr] + indices
            current = current.array_name
        if not isinstance(current, str):
            raise Exception("Ошибка: не распознано имя массива при обращении")
        return current, indices

    def generate_record_field_access(self, node: RecordFieldAccessNode):
        """Генерирует обращение к полю записи."""
        if isinstance(node.record_obj, str):
            record_expr = {"type": "Variable", "name": node.record_obj}
        else:
            record_expr = self.generate(node.record_obj)

        return {
            "type": "RecordFieldAccess",
            "record": record_expr,
            "field": node.field_name
        }

    def generate_if_statement(self, node: IfStatementNode):
        """
        Генерирует код для оператора IF.

        Структура генерируемого кода:
        {
            "type": "If",
            "condition": <код условия>,
            "then": <код then-ветки>,
            "else": <код else-ветки>  # Если ветка else отсутствует, то может быть None
        }
        """
        condition_code = self.generate(node.condition)
        then_code = self.generate(node.then_statement)
        else_code = self.generate(node.else_statement) if node.else_statement is not None else None

        return {
            "type": "If",
            "condition": condition_code,
            "then": then_code,
            "else": else_code
        }

    # ===== Новые методы для функций и процедур =====

    def generate_proc_or_func_decl(self, node: ProcedureOrFunctionDeclarationNode):
        """
        Генерирует код для объявления процедуры или функции.

        Для процедуры генерируется структура:
        {
            "type": "ProcedureDeclaration",
            "name": <имя процедуры>,
            "parameters": [<список параметров>],
            "block": <код тела процедуры>
        }

        Для функции – аналогично, но дополнительно добавляется "return_type":
        {
            "type": "FunctionDeclaration",
            "name": <имя функции>,
            "parameters": [<список параметров>],
            "block": <код тела функции>,
            "return_type": <тип возвращаемого значения>
        }
        """
        node_type = "ProcedureDeclaration" if node.kind.lower() == "procedure" else "FunctionDeclaration"
        return {
            "type": node_type,
            "name": node.identifier,
            "parameters": [str(param) for param in node.parameters] if node.parameters else [],
            "block": self.generate(node.block) if node.block else None,
            "return_type": node.return_type if node.kind.lower() == "function" else None

        }

    def generate_proc_call(self, node: ProcedureCallNode):
        """
        Генерирует вызов процедуры.

        Результирующая структура:
        {
            "type": "ProcedureCall",
            "name": <имя процедуры>,
            "arguments": [<аргументы вызова>]
        }
        """
        return {
            "type": "ProcedureCall",
            "name": node.identifier,
            "arguments": [self.generate(arg) for arg in node.arguments] if node.arguments else []
        }

    def generate_func_call(self, node: FunctionCallNode):
        """
        Генерирует вызов функции.

        Результирующая структура:
        {
            "type": "FunctionCall",
            "name": <имя функции>,
            "arguments": [<аргументы вызова>]
        }
        """
        return {
            "type": "FunctionCall",
            "name": node.identifier,
            "arguments": [self.generate(arg) for arg in node.arguments] if node.arguments else []
        }
