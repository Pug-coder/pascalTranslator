# Создаём узлы
from parser.ast_node import FactorNode, TermNode, ExpressionNode


factor1 = FactorNode(value=5)
factor2 = FactorNode(value=3)
add_operator = "+"
term = TermNode(factors=[factor1, add_operator, factor2])
print(term.execute({}))
factor3 = FactorNode(value=2)
multiplicative_operator = "*"
term2 = TermNode(factors=[term, multiplicative_operator, factor3])
print(term2.factors)
rel_op = "="
factor4 = FactorNode(value=16)
expr = ExpressionNode(left=term2, relational_operator=rel_op, right=factor4)

# Выполнение выражения
context = {}  # контекст, например, пустой словарь
result = expr.execute(context)
print(result)  # True или False в зависимости от выполнения