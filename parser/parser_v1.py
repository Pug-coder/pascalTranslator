from lexer.token_type import TokenType
from lexer.token import Token
from ast_node import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens  # Список токенов
        self.pos = 0          # Позиция текущего токена

    def current_token(self):
        """Получить текущий токен."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None, -1, -1)

    def consume(self, expected_type):
        """Потребляет текущий токен, если тип совпадает, и двигается дальше."""
        token = self.current_token()
        if token.type_ != expected_type:
            raise SyntaxError(f"Expected {expected_type}, but got {token.type_} at line {token.line}, col {token.column}")
        self.pos += 1
        return token.value

    def parse_program(self):
        """Program -> 'program' IDENTIFIER ';' Block '.'"""
        self.consume(TokenType.IDENTIFIER)  # program
        program_name = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        block = self.parse_block()
        return ProgramNode(program_name, block)

    def parse_block(self):
        """Block -> Declarations CompoundStatement"""
        declarations = self.parse_var_declaration()
        compound_statement = self.parse_compound_statement()
        return BlockNode(declarations, compound_statement)

    '''
    def parse_declarations(self):
    """Declarations -> 'var' VariableDeclarations"""
    declarations = []
    while self.current_token().type_ == TokenType.VAR:
        self.consume(TokenType.VAR)
        while self.current_token().type_ == TokenType.IDENTIFIER:
            identifier = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            var_type = self.consume(TokenType.IDENTIFIER)  # Например, 'integer'
            declarations.append(VarDeclarationNode(identifier, var_type))
            self.consume(TokenType.SEMICOLON)
    return declarations
    '''


    def parse_type(self):
        """Type -> IDENTIFIER | ARRAY LBRACKET NUMBER TWODOTS NUMBER RBRACKET OF IDENTIFIER"""
        if self.current_token().type_ == TokenType.ARRAY:
            self.consume(TokenType.ARRAY)  # Съедаем ARRAY
            self.consume(TokenType.LBRACKET)  # Съедаем '['
            lower_bound = self.consume(TokenType.NUMBER)  # Начальная граница массива
            self.consume(TokenType.TWODOTS)  # Съедаем '..'
            upper_bound = self.consume(TokenType.NUMBER)  # Конечная граница массива
            self.consume(TokenType.RBRACKET)  # Съедаем ']'
            self.consume(TokenType.OF)  # Съедаем OF
            element_type = self.consume(TokenType.IDENTIFIER)  # Тип элементов массива
            return ArrayTypeNode(lower_bound=int(lower_bound), upper_bound=int(upper_bound), element_type=element_type)
        else:
            # Просто обычный тип данных
            identifier = self.consume(TokenType.IDENTIFIER)
            return TypeNode(identifier)

    def parse_var_declaration(self):
        """VarDeclaration -> VAR (IDENTIFIER (COMMA IDENTIFIER)* COLON Type SEMICOLON)+"""
        self.consume(TokenType.VAR)
        declarations = []

        while self.current_token().type_ == TokenType.IDENTIFIER:
            identifiers = []  # Список для хранения переменных
            # Собираем список идентификаторов, разделённых запятыми
            identifiers.append(self.consume(TokenType.IDENTIFIER))  # Первый идентификатор
            while self.current_token().type_ == TokenType.COMMA:
                self.consume(TokenType.COMMA)  # Съедаем запятую
                identifiers.append(self.consume(TokenType.IDENTIFIER))  # Следующий идентификатор

            # После списка идентификаторов должен идти двоеточие
            self.consume(TokenType.COLON)
            type_node = self.parse_type()  # Тип данных (с поддержкой массивов)
            self.consume(TokenType.SEMICOLON)  # Заканчиваем объявление

            # Создаём VarDeclarationNode для каждой переменной
            for identifier in identifiers:
                declarations.append(VarDeclarationNode(identifier, type_node))

        return DeclarationNode(declarations)

    def parse_compound_statement(self):
        """CompoundStatement -> 'BEGIN' { Statement ';' } 'END'"""
        statements = []
        self.consume(TokenType.BEGIN)
        while self.current_token().type_ != TokenType.END:
            statements.append(self.parse_statement())
            if self.current_token().type_ == TokenType.SEMICOLON:
                self.consume(TokenType.SEMICOLON)
        self.consume(TokenType.END)
        return CompoundStatementNode(statements)

    def parse_statement(self):
        """Statement -> AssignStatement | IfStatement | WhileStatement"""
        token = self.current_token()
        if token.type_ == TokenType.IDENTIFIER:
            return self.parse_assign_statement()
        elif token.type_ == TokenType.IF:
            return self.parse_if_statement()
        elif token.type_ == TokenType.WHILE:
            return self.parse_while_statement()
        elif token.type_ == TokenType.FOR:
            return self.parse_for()
        else:
            raise SyntaxError(f"Unexpected statement at {token}")

    def parse_assign_statement(self):
        """AssignStatement -> IDENTIFIER ':=' Expression"""
        identifier = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.ASSIGN)
        expression = self.parse_expression()
        return AssignStatementNode(identifier, expression)

    def parse_if_statement(self):
        """IfStatement -> 'IF' Expression 'THEN' Statement [ 'ELSE' Statement ]"""
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.THEN)
        then_statement = self.parse_statement()
        else_statement = None
        if self.current_token().type_ == TokenType.ELSE:
            self.consume(TokenType.ELSE)
            else_statement = self.parse_statement()
        return IfStatementNode(condition, then_statement, else_statement)

    def parse_while_statement(self):
        """WhileStatement -> 'WHILE' Expression 'DO' Statement"""
        self.consume(TokenType.WHILE)
        condition = self.parse_expression()
        self.consume(TokenType.DO)
        body = self.parse_statement()
        return WhileStatementNode(condition, body)

    def parse_for(self):
        """ForStatement -> 'for' IDENTIFIER ':=' Expression ('to' | 'downto') Expression 'do' CompoundStatement"""
        self.consume(TokenType.FOR)  # Пропускаем 'for'

        identifier = self.consume(TokenType.IDENTIFIER)  # Получаем идентификатор (например, 'i')
        self.consume(TokenType.ASSIGN)  # Пропускаем ':='

        start_expr = self.parse_expression()  # Начальное значение (Expression)

        direction = None
        if self.current_token().type_ == TokenType.TO:
            direction = 'to'
            self.consume(TokenType.TO)  # Пропускаем 'to'
        else:
            raise SyntaxError("Expected 'to' or 'downto' after start expression")

        end_expr = self.parse_expression()  # Конечное значение (Expression)

        self.consume(TokenType.DO)  # Пропускаем 'do'

        body = self.parse_compound_statement()  # Тело цикла

        # Создаём и возвращаем узел ForStatementNode
        return ForStatementNode(identifier, start_expr, direction, end_expr, body)

    def parse_expression(self):
        """Expression -> SimpleExpression"""
        return self.parse_simple_expression()

    def parse_simple_expression(self):
        """SimpleExpression -> Term { ('+' | '-') Term }"""
        terms = [self.parse_term()]
        while self.current_token().type_ in {TokenType.PLUS, TokenType.MINUS}:
            operator = self.consume(self.current_token().type_)
            terms.append(operator)
            terms.append(self.parse_term())
        return SimpleExpressionNode(terms)

    def parse_term(self):
        """Term -> Factor { ('*' | '/') Factor }"""
        factors = [self.parse_factor()]
        while self.current_token().type_ in {TokenType.ASTERISK, TokenType.DIV}:
            operator = self.consume(self.current_token().type_)
            factors.append(operator)
            factors.append(self.parse_factor())
        return TermNode(factors)

    def parse_factor(self):
        """Factor -> NUMBER | IDENTIFIER | '(' Expression ')'"""
        token = self.current_token()
        if token.type_ == TokenType.NUMBER:
            value = self.consume(TokenType.NUMBER)
            return FactorNode(value=int(value))
        elif token.type_ == TokenType.STRING:
            value = self.consume(TokenType.STRING)
            return FactorNode(value=value)  # Строковое значение
        elif token.type_ == TokenType.IDENTIFIER:
            identifier = self.consume(TokenType.IDENTIFIER)
            return FactorNode(identifier=identifier)
        elif token.type_ == TokenType.LPAREN:
            self.consume(TokenType.LPAREN)
            expression = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return FactorNode(sub_expression=expression)
        else:
            raise SyntaxError(f"Unexpected token {token}")