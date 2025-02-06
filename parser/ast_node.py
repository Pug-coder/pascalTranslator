class AstNode:
    def __init__(self):
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def __repr__(self):
        return f"{self.__class__.__name__}({', '.join(map(str, self.children))})"


class ProgramNode(AstNode):
    def __init__(self, program_name, block):
        super().__init__()
        self.program_name = program_name
        self.add_child(block)


class BlockNode(AstNode):
    def __init__(self, declarations, compound_statement):
        super().__init__()
        self.declarations = declarations # список или None ?
        self.compound_statement = compound_statement

        if declarations:
            self.add_child(declarations)

        self.add_child(compound_statement)


# DECLARATIONS BLOCK
class DeclarationNode(AstNode):
    def __init__(self, declarations):
        super().__init__()
        self.declarations = declarations

        for declaration in declarations:
            self.add_child(declarations)


# CONST
class ConstDeclarationNode(AstNode):
    def __init__(self, identifier, value):
        super().__init__()
        self.identifier = identifier
        self.value = value


# VAR
class VarDeclarationNode(AstNode):
    def __init__(self, identifier, var_type, init_value):
        super().__init__()
        self.identifier = identifier
        self.var_type = var_type
        self.init_value = init_value


# TYPE
class TypeNode(AstNode):

    def __init__(self, identifier_type, array_range=None):
        # array ?
        super().__init__()
        self.identifier_type = identifier_type
        self.array_range = array_range

    def __repr__(self):
        if self.array_range:
            return f"{self.identifier_type}[{self.array_range}]"
        return self.identifier_type


class ParameterNode(AstNode):
    def __init__(self, identifier, type_node, pass_mode=None):
        super().__init__()
        self.identifier = identifier      # Имя параметра
        self.type_node = type_node        # Тип (TypeNode или строка)
        self.pass_mode = pass_mode        # Может быть None (по значению), 'var', 'const'

    def __repr__(self):
        if self.pass_mode:
            return f"{self.pass_mode} {self.identifier}: {self.type_node}"
        else:
            return f"{self.identifier}: {self.type_node}"


class ArrayTypeNode:
    def __init__(self, dimensions, element_type, initial_values=None):
        """
        Узел AST для массива.

        :param dimensions: Список пар (lower_bound, upper_bound) для каждого измерения.
        :param element_type: Тип элементов массива (например, integer, string).
        :param initial_values: Список значений для инициализации массива (опционально).
        """
        self.dimensions = dimensions
        self.element_type = element_type
        self.initial_values = initial_values

    def __repr__(self):
        return (
            f"ArrayTypeNode(dimensions={self.dimensions}, "
            f"element_type={self.element_type}, "
            f"initial_values={self.initial_values})"
        )


class ArrayAccessNode(AstNode):
    def __init__(self, array_name, index_expr):
        super().__init__()
        self.array_name = array_name     # str (имя массива)
        self.index_expr = index_expr     # ExpressionNode (индекс, который сам может быть выражением)

    def __repr__(self):
        return f"{self.array_name}[{self.index_expr}]"


class ProcedureOrFunctionDeclarationNode(AstNode):
    def __init__(self, kind, identifier, parameters=None, block=None, return_type=None):
        super().__init__()
        self.kind = kind
        self.identifier = identifier
        self.parameters = parameters
        self.block = block
        self.return_type = return_type

    def __repr__(self):
        params = ', '.join(map(str, self.parameters)) if self.parameters else ''
        return f"{self.kind} {self.identifier}({params}) {self.block}"


# OPERATORS
class CompoundStatementNode(AstNode):
    def __init__(self, statements):
        super().__init__()
        self.statements = statements  # Список операторов (список узлов StatementNode)

    def __repr__(self):
        return f"BEGIN {', '.join(map(str, self.statements))} END"


class StatementNode(AstNode):
    def __init__(self):
        super().__init__()

    def execute(self):
        pass  # В этой функции можно будет реализовать выполнение оператора, если необходимо


class AssignStatementNode(StatementNode):
    def __init__(self, identifier, expression):
        super().__init__()
        self.identifier = identifier  # Идентификатор (переменная)
        self.expression = expression  # Выражение (узел ExpressionNode)

    def __repr__(self):
        return f"{self.identifier} := {self.expression}"


class IfStatementNode(StatementNode):
    def __init__(self, condition, then_statement, else_statement=None):
        super().__init__()
        self.condition = condition  # Условие (выражение)
        self.then_statement = then_statement  # Оператор, выполняемый при истинности условия
        self.else_statement = else_statement  # Оператор, выполняемый при ложности условия (может быть None)

    def __repr__(self):
        else_part = f" ELSE {self.else_statement}" if self.else_statement else ""
        return f"IF {self.condition} THEN {self.then_statement}{else_part}"


class WhileStatementNode(StatementNode):
    def __init__(self, condition, body):
        super().__init__()
        self.condition = condition  # Условие цикла (выражение)
        self.body = body  # Тело цикла (оператор)

    def __repr__(self):
        return f"WHILE {self.condition} DO {self.body}"


class ForStatementNode(StatementNode):
    def __init__(self, identifier, start_expr, direction, end_expr, body):
        super().__init__()
        self.identifier = identifier  # Идентификатор переменной цикла
        self.start_expr = start_expr  # Начальное значение (выражение)
        self.direction = direction  # Направление цикла: 'TO' или 'DOWNTO'
        self.end_expr = end_expr  # Конечное значение (выражение)
        self.body = body  # Тело цикла (оператор)

    def __repr__(self):
        return f"FOR {self.identifier} := {self.start_expr} {self.direction} {self.end_expr} DO {self.body}"


class ProcedureCallNode(AstNode):
    def __init__(self, identifier, arguments=None):
        super().__init__()
        self.identifier = identifier  # Имя процедуры или функции
        self.arguments = arguments if arguments else []  # Список аргументов (список узлов ExpressionNode)

    def __repr__(self):
        args = ', '.join(map(str, self.arguments)) if self.arguments else ''
        return f"{self.identifier}({args})"


class FunctionCallNode(AstNode):
    def __init__(self, func_name, arguments=None):
        super().__init__()
        self.identifier = func_name        # строка, имя функции
        self.arguments = arguments or []

    def __repr__(self):
        args = ", ".join(map(str, self.arguments))
        return f"{self.identifier}({args})"


class ExpressionNode(AstNode):
    def __init__(self, left, relational_operator=None, right=None):
        super().__init__()
        self.left = left  # SimpleExpression (левая часть)
        self.relational_operator = relational_operator  # Реляционный оператор (например, "=", "<>")
        self.right = right  # Простое выражение (правая часть, если есть)

    def execute(self, context):
        left_value = self.left.execute(context)
        if self.right:  # Если есть правая часть
            right_value = self.right.execute(context)
            # Выполнение реляционного оператора
            if self.relational_operator == "=":
                return left_value == right_value
            elif self.relational_operator == "<>":
                return left_value != right_value
            elif self.relational_operator == "<":
                return left_value < right_value
            elif self.relational_operator == ">":
                return left_value > right_value
            elif self.relational_operator == "<=":
                return left_value <= right_value
            elif self.relational_operator == ">=":
                return left_value >= right_value
        return left_value

    def to_dict(self):
        # Рекурсивно получаем представление левого подвыражения
        left_repr = self.left.to_dict() if hasattr(self.left, 'to_dict') else str(self.left)
        result = {
            "node": "ExpressionNode",
            "left": left_repr
        }
        # Если задан реляционный оператор и правая часть, добавляем их
        if self.relational_operator and self.right:
            right_repr = self.right.to_dict() if hasattr(self.right, 'to_dict') else str(self.right)
            result["relational_operator"] = self.relational_operator
            result["right"] = right_repr
        return result


class SimpleExpressionNode(AstNode):
    def __init__(self, terms, additive_operator=None):
        super().__init__()
        self.terms = terms  # Список Terms (фактически это операция, связанная с термами)
        self.additive_operator = additive_operator  # Операторы сложения/вычитания/OR, если есть

    def execute(self, context):
        result = self.terms[0].execute(context)  # Первый терм
        for i in range(1, len(self.terms), 2):  # Перебираем операторы и термы
            operator = self.terms[i]
            term = self.terms[i + 1].execute(context)
            if operator == "+":
                result += term
            elif operator == "-":
                result -= term
            elif operator == "OR":
                result = bool(result) or bool(term)
        return result

    def to_dict(self):
        result = {"node": "SimpleExpressionNode", "terms": []}
        for item in self.terms:
            if hasattr(item, 'to_dict'):
                result["terms"].append(item.to_dict())
            else:
                # Если элемент является оператором-строкой или примитивом
                result["terms"].append(item)
        if self.additive_operator:
            result["additive_operator"] = self.additive_operator
        return result


class TermNode(AstNode):
    def __init__(self, factors, multiplicative_operator=None):
        super().__init__()
        self.factors = factors  # Список факторов (Factor)
        self.multiplicative_operator = multiplicative_operator  # Операторы умножения и деления

    def execute(self, context):
        result = self.factors[0].execute(context)  # Первый фактор
        for i in range(1, len(self.factors), 2):  # Перебираем операторы и факторы
            operator = self.factors[i]
            factor = self.factors[i + 1].execute(context)
            if operator == "*":
                result *= factor
            elif operator == "/":
                result /= factor
            elif operator == "DIV":
                result //= factor
            elif operator == "MOD":
                result %= factor
            elif operator == "AND":
                result = bool(result) and bool(factor)

            # костыль для арифметики
            else:
                # Создать SimpleExpressionNode для передачи "наверх"
                rest_factors = self.factors[i:]
                simple_expr = SimpleExpressionNode(terms=[FactorNode(value=result)] + rest_factors)
                return simple_expr.execute(context)
        return result

    def to_dict(self):
        result = {"node": "TermNode", "factors": []}
        for item in self.factors:
            if hasattr(item, 'to_dict'):
                result["factors"].append(item.to_dict())
            else:
                # Если элемент не имеет метода to_dict (например, оператор-строка)
                result["factors"].append(item)
        # Если multiplicative_operator задан отдельно (не обязательно, т.к. часто операторы уже входят в список factors)
        if self.multiplicative_operator:
            result["multiplicative_operator"] = self.multiplicative_operator
        return result

class FactorNode(AstNode):
    def __init__(self, value=None, identifier=None, sub_expression=None, is_not=False):
        super().__init__()
        self.value = value  # Число или строка
        self.identifier = identifier  # Идентификатор переменной
        self.sub_expression = sub_expression  # Подвыражение (если это скобки)
        self.is_not = is_not  # Флаг для "NOT"

    def execute(self, context):
        if self.value is not None:  # Число
            return self.value
        elif self.identifier is not None:  # Идентификатор (переменная)
            return context[self.identifier]
        elif self.sub_expression is not None:  # Выражение в скобках
            return self.sub_expression.execute(context)
        elif self.is_not:  # Операция NOT
            return not self.sub_expression.execute(context)

    def to_dict(self):
        if self.value is not None:
            return {"node": "FactorNode", "value": self.value}
        elif self.identifier is not None:
            return {"node": "FactorNode", "identifier": self.identifier}
        elif self.sub_expression is not None:
            return {
                "node": "FactorNode",
                "sub_expression": self.sub_expression.to_dict(),
                "is_not": self.is_not
            }
        return {"node": "FactorNode"}


class RelationalOperatorNode(AstNode):
    def __init__(self, operator):
        super().__init__()
        self.operator = operator  # Операторы сравнения (например, "=", "<>")

    def execute(self, context):
        # вспомогательный узел для выполнения оператора в ExpressionNode
        pass


class TypeDeclarationNode(AstNode):
    def __init__(self, name, type_node):
        super().__init__()
        self.name = name
        self.type_node = type_node

    def __repr__(self):
        return f"{self.name} = {self.type_node}"


class RecordTypeNode(AstNode):
    def __init__(self, fields=None):
        super().__init__()
        # fields — это список пар (имя_поля, тип_поля)
        # либо более сложная структура (список FieldDeclarationNode, если хотите)
        self.fields = fields if fields is not None else []

    def __repr__(self):
        fields_str = "; ".join(f"{name}: {type_}" for (name, type_) in self.fields)
        return f"record {fields_str} end"


class RecordInitializerNode(AstNode):
    def __init__(self, fields):
        super().__init__()
        # fields — список (field_name_token, value_node)
        self.fields = fields

    def __repr__(self):
        pairs_str = "; ".join(f"{name}: {val}" for name, val in self.fields)
        return f"<RecordInit {pairs_str}>"


class RecordFieldAccessNode(AstNode):
    def __init__(self, record_obj, field_name):
        super().__init__()
        self.record_obj = record_obj    # Может быть IDENTIFIER, ArrayAccessNode, или вложенный RecordFieldAccessNode
        self.field_name = field_name

    def __repr__(self):
        return f"{self.record_obj}.{self.field_name}"

