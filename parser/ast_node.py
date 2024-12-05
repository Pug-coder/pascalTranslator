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


class ConstDeclarationNode(AstNode):
    def __init__(self, identifier, value):
        super().__init__()
        self.identifier = identifier
        self.value = value


class VarDeclarationNode(AstNode):
    def __init__(self, identifier, var_type):
        super().__init__()
        self.identifier = identifier
        self.var_type = var_type


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
    def __init__(self, identifier, type_node):
        super().__init__()
        self.identifier = identifier  # Имя параметра
        self.type_node = type_node    # Тип параметра (это TypeNode)

    def __repr__(self):
        return f"{self.identifier}: {self.type_node}"


class ArrayTypeNode(AstNode):
    def __init__(self, lower_bound, upper_bound, element_type):
        super().__init__()
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.element_type = element_type

    def __repr__(self):
        return f"Array[{self.lower_bound}..{self.upper_bound}] of {self.element_type}"


class ProcedureOrFunctionDeclarationNode(AstNode):
    def __init__(self, kind, identifier, parameters=None, block=None):
        super().__init__()
        self.kind = kind
        self.identifier = identifier
        self.parameters = parameters
        self.block = block

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


class ProcedureCallNode(StatementNode):
    def __init__(self, identifier, arguments=None):
        super().__init__()
        self.identifier = identifier  # Имя процедуры или функции
        self.arguments = arguments if arguments else []  # Список аргументов (список узлов ExpressionNode)

    def __repr__(self):
        args = ', '.join(map(str, self.arguments)) if self.arguments else ''
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


class RelationalOperatorNode(AstNode):
    def __init__(self, operator):
        super().__init__()
        self.operator = operator  # Операторы сравнения (например, "=", "<>")

    def execute(self, context):
        # вспомогательный узел для выполнения оператора в ExpressionNode
        pass
