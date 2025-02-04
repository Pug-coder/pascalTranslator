from parser.ast_node import *

class CodeGenerator:
    def __init__(self):
        self.result = []

    def generate(self, node):
        """Основная функция генерации кода"""
        if isinstance(node, CompoundStatementNode):
            return self.generate_compound_statement(node)
        elif isinstance(node, AssignStatementNode):
            return self.generate_assign_statement(node)
        elif isinstance(node, ExpressionNode):
            return self.generate_expression(node)
        elif isinstance(node, SimpleExpressionNode):
            return self.generate_simple_expression(node)
        elif isinstance(node, FactorNode):
            return self.generate_factor(node)
        return None

    def generate_compound_statement(self, node: CompoundStatementNode):
        """Обрабатывает блок операторов"""
        return {
            "type": "Block",
            "statements": [self.generate(stmt) for stmt in node.statements]
        }

    def generate_assign_statement(self, node: AssignStatementNode):
        """Генерирует присваивание a := b + c"""
        return {
            "type": "Assignment",
            "target": node.identifier,
            "value": self.generate(node.expression)
        }

    def generate_expression(self, node: ExpressionNode):
        """Генерирует выражение (арифметическое или логическое)"""
        return self.generate(node.left)  # Основное выражение в левой части

    def generate_simple_expression(self, node: SimpleExpressionNode):
        """Генерирует сложное выражение a + b + c"""
        if len(node.terms) == 1:
            return self.generate(node.terms[0])

        # Преобразуем цепочку операций в дерево
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
        """Генерирует отдельные значения (переменные, числа)"""
        if node.sub_expression:
            return self.generate(node.sub_expression)

        if node.identifier:
            return {"type": "Variable", "name": node.identifier}

        if isinstance(node.value, int):
            return {"type": "Integer", "value": node.value}

        if isinstance(node.value, str):
            return {"type": "String", "value": node.value}

        raise Exception(f"Неизвестный фактор: {node.to_dict()}")
