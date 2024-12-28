from lexer.token_type import TokenType
from lexer.token import Token
from ast_node import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens  # Список токенов
        self.pos = 0  # Позиция текущего токена

    def current_token(self):
        """Получить текущий токен."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None, -1, -1)

    def consume(self, expected_type):
        """Потребляет текущий токен, если тип совпадает, и двигается дальше."""
        token = self.current_token()
        if token.type_ != expected_type:
            raise SyntaxError(
                f"Expected {expected_type}, but got {token.type_} at line {token.line}, col {token.column}")
        self.pos += 1
        return token.value

    def match(self, token_type):
        """Проверяет тип текущего токена, не потребляя его."""
        return self.current_token().type_ == token_type

    def parse_program(self):
        """Program -> 'program' IDENTIFIER ';' Block '.'"""
        # По классической грамматике Паскаля сначала должно идти ключевое слово PROGRAM
        # Но в вашем коде не было этого. Предположим, что вы хотите это поддержать:
        # self.consume(TokenType.PROGRAM)  # если хотите строго по грамматике
        program_name = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        block = self.parse_block()
        self.consume(TokenType.DOT)
        return ProgramNode(program_name=program_name, block=block)

    def parse_block(self):
        """Block -> [Declarations] CompoundStatement"""
        declarations = self.parse_declarations()
        compound_statement = self.parse_compound_statement()
        return BlockNode(declarations=declarations, compound_statement=compound_statement)

    def parse_declarations(self):
        """Declarations -> { ConstDeclaration | VarDeclaration | ProcedureOrFunctionDeclaration }"""
        declarations = []

        # Проверяем типы токенов, которые могут указывать на начало деклараций
        while self.match(TokenType.CONST) or self.match(TokenType.VAR) or \
                self.match(TokenType.FUNCTION) or self.match(TokenType.PROCEDURE):

            if self.match(TokenType.CONST):
                declarations.extend(self.parse_const_declaration())
            elif self.match(TokenType.VAR):
                declarations.extend(self.parse_var_declaration())
            elif self.match(TokenType.FUNCTION) or self.match(TokenType.PROCEDURE):
                declarations.append(self.parse_procedure_or_function_declaration())

        return declarations

    def parse_const_declaration(self):
        """ConstDeclaration = "CONST" { IDENTIFIER "=" (NUMBER | STRING) ";" }"""
        const_declarations = []
        self.consume(TokenType.CONST)

        while self.match(TokenType.IDENTIFIER):
            const_name = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.EQ)

            # Ожидаем NUMBER или STRING
            if self.match(TokenType.NUMBER):
                const_value = self.consume(TokenType.NUMBER)
            elif self.match(TokenType.STRING):
                const_value = self.consume(TokenType.STRING)
            else:
                raise SyntaxError(
                    f"Expected NUMBER or STRING for constant {const_name} at line {self.current_token().line}")

            self.consume(TokenType.SEMICOLON)
            const_declarations.append(ConstDeclarationNode(identifier=const_name, value=const_value))

        return const_declarations

    def parse_var_declaration(self):
        """VarDeclaration = "VAR" { IDENTIFIER ":" Type ";" }"""
        var_declarations = []
        self.consume(TokenType.VAR)

        while self.match(TokenType.IDENTIFIER):
            ident = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            var_type = self.parse_type()
            self.consume(TokenType.SEMICOLON)

            var_declarations.append(VarDeclarationNode(identifier=ident, var_type=var_type))

        return var_declarations

    def parse_type(self):
        """Type = "integer" | "string" | "array" "[" NUMBER ".." NUMBER "]" "of" Type"""
        if self.match(TokenType.IDENTIFIER):
            # Предполагаем, что это либо integer, либо string, или что-то подобное
            ident_type = self.consume(TokenType.IDENTIFIER)
            return TypeNode(identifier_type=ident_type)

        elif self.match(TokenType.ARRAY):
            self.consume(TokenType.ARRAY)
            self.consume(TokenType.LBRACKET)
            lower_bound = self.consume(TokenType.NUMBER)
            self.consume(TokenType.TWODOTS)
            upper_bound = self.consume(TokenType.NUMBER)
            self.consume(TokenType.RBRACKET)
            self.consume(TokenType.OF)
            element_type = self.parse_type()
            return ArrayTypeNode(lower_bound=lower_bound, upper_bound=upper_bound, element_type=element_type)

        else:
            raise SyntaxError(f"Expected type at line {self.current_token().line}, col {self.current_token().column}")

    def parse_procedure_or_function_declaration(self):
        """ProcedureOrFunctionDeclaration = ( "PROCEDURE" | "FUNCTION" ) IDENTIFIER [ "(" ParameterList ")" ] ";" Block ";" """
        kind_token = self.current_token()
        if kind_token.type_ not in [TokenType.PROCEDURE, TokenType.FUNCTION]:
            raise SyntaxError(f"Expected PROCEDURE or FUNCTION at line {kind_token.line}, col {kind_token.column}")

        kind = self.consume(kind_token.type_)
        ident = self.consume(TokenType.IDENTIFIER)

        parameters = []
        if self.match(TokenType.LPAREN):
            parameters = self.parse_parameter_list()

        self.consume(TokenType.SEMICOLON)
        block = self.parse_block()
        self.consume(TokenType.SEMICOLON)

        return ProcedureOrFunctionDeclarationNode(kind=kind, identifier=ident, parameters=parameters, block=block)

    def parse_parameter_list(self):
        """ParameterList = "(" IDENTIFIER ":" Type { ";" IDENTIFIER ":" Type } ")" """
        params = []
        self.consume(TokenType.LPAREN)
        # хотя в грамматике вы писали так, мы делаем классическую реализацию
        ident = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.COLON)
        param_type = self.parse_type()
        params.append(ParameterNode(identifier=ident, type_node=param_type))

        while self.match(TokenType.SEMICOLON):
            self.consume(TokenType.SEMICOLON)
            ident = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            param_type = self.parse_type()
            params.append(ParameterNode(identifier=ident, type_node=param_type))

        self.consume(TokenType.RPAREN)
        return params

    def parse_compound_statement(self):
        """CompoundStatement = "BEGIN" { Statement ";" } "END" """
        self.consume(TokenType.BEGIN)
        statements = []

        while not self.match(TokenType.END) and self.current_token().type_ != TokenType.EOF:
            stmt = self.parse_statement()
            statements.append(stmt)
            if self.match(TokenType.SEMICOLON):
                self.consume(TokenType.SEMICOLON)
            else:
                # Если нет ';', выходим, возможно END сразу
                break

        self.consume(TokenType.END)
        return CompoundStatementNode(statements=statements)

    def parse_statement(self):
        """Statement = AssignStatement | IfStatement | WhileStatement | ForStatement | ProcedureCall | CompoundStatement"""
        token = self.current_token()

        if self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_statement()
        elif self.match(TokenType.FOR):
            return self.parse_for_statement()
        elif self.match(TokenType.BEGIN):
            return self.parse_compound_statement()
        elif self.match(TokenType.IDENTIFIER):
            # Может быть присваивание или вызов процедуры
            # Посмотрим дальше
            lookahead = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if lookahead and lookahead.type_ == TokenType.ASSIGN:
                return self.parse_assign_statement()
            else:
                return self.parse_procedure_call()
        else:
            # Пустой оператор или что-то неожиданное
            # В Паскале нет пустых операторов кроме ';' между ними, но мы можем вернуть None или поднять ошибку
            raise SyntaxError(f"Unexpected token {token.type_} at line {token.line}, col {token.column}")

    def parse_assign_statement(self):
        """AssignStatement = IDENTIFIER ":=" Expression"""
        ident = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.ASSIGN)
        expr = self.parse_expression()
        return AssignStatementNode(identifier=ident, expression=expr)

    def parse_if_statement(self):
        """IfStatement = "IF" Expression "THEN" Statement [ "ELSE" Statement ]"""
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.THEN)
        then_stmt = self.parse_statement()
        else_stmt = None
        if self.match(TokenType.ELSE):
            self.consume(TokenType.ELSE)
            else_stmt = self.parse_statement()
        return IfStatementNode(condition=condition, then_statement=then_stmt, else_statement=else_stmt)

    def parse_while_statement(self):
        """WhileStatement = "WHILE" Expression "DO" Statement"""
        self.consume(TokenType.WHILE)
        condition = self.parse_expression()
        self.consume(TokenType.DO)
        body = self.parse_statement()
        return WhileStatementNode(condition=condition, body=body)

    def parse_for_statement(self):
        """ForStatement = "FOR" IDENTIFIER ":=" Expression ("TO" | "DOWNTO") Expression "DO" Statement"""
        self.consume(TokenType.FOR)
        ident = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.ASSIGN)
        start_expr = self.parse_expression()
        if self.match(TokenType.TO):
            direction = self.consume(TokenType.TO)
        elif self.match(TokenType.IDENTIFIER) and self.current_token().value.upper() == 'DOWNTO':
            # Допустим вы не добавили DOWNTO как токен, тогда нужна проверка по value
            # или добавьте DOWNTO в TokenType
            # Если DOWNTO есть в TokenType, можно использовать:
            # direction = self.consume(TokenType.DOWNTO)
            direction = self.consume(TokenType.IDENTIFIER)
            if direction.upper() != 'DOWNTO':
                raise SyntaxError("Expected TO or DOWNTO in for statement.")
        else:
            raise SyntaxError("Expected TO or DOWNTO in for statement.")

        end_expr = self.parse_expression()
        self.consume(TokenType.DO)
        body = self.parse_statement()
        return ForStatementNode(identifier=ident, start_expr=start_expr, direction=direction, end_expr=end_expr,
                                body=body)

    def parse_procedure_call(self):
        """ProcedureCall = IDENTIFIER [ "(" { Expression "," } Expression ")" ]"""
        ident = self.consume(TokenType.IDENTIFIER)
        args = []
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            # парсим список выражений через запятую
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                args.append(self.parse_expression())
            self.consume(TokenType.RPAREN)
        return ProcedureCallNode(identifier=ident, arguments=args)

    def parse_expression(self):
        """Expression = SimpleExpression [ RelationalOperator SimpleExpression ]"""
        # Для простоты предположим, что parse_simple_expression уже есть
        # или мы пишем его сейчас
        left = self.parse_simple_expression()
        if self.match(TokenType.EQ) or self.match(TokenType.NEQ) or self.match(TokenType.LT) or \
                self.match(TokenType.GT) or self.match(TokenType.LTE) or self.match(TokenType.GTE):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_simple_expression()
            return ExpressionNode(left=left, relational_operator=op, right=right)
        return ExpressionNode(left=left)

    def parse_simple_expression(self):
        """SimpleExpression = Term { AdditiveOperator Term }"""
        left = self.parse_term()
        # Смотрим есть ли +, -, OR
        while self.match(TokenType.PLUS) or self.match(TokenType.MINUS) or self.match(TokenType.OR):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_term()
            # В отличие от ранее показанного кода, SimpleExpressionNode мы
            # можем построить как цепочку или сделать сразу список термов и операторов.
            # Для упрощения сейчас просто вернём новый SimpleExpressionNode
            # Но лучше собирать в список.
            left = SimpleExpressionNode(terms=[left, op, right])
        return left

    def parse_term(self):
        """Term = Factor { MultiplicativeOperator Factor }"""
        left = self.parse_factor()
        while self.match(TokenType.ASTERISK) or self.match(TokenType.SLASH) or \
                self.match(TokenType.DIV) or self.match(TokenType.MOD) or self.match(TokenType.AND):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_factor()
            left = TermNode(factors=[left, op, right])
        return left

    def parse_factor(self):
        """Factor = NUMBER | IDENTIFIER | "(" Expression ")" | "NOT" Factor"""
        if self.match(TokenType.NUMBER):
            value = self.consume(TokenType.NUMBER)
            return FactorNode(value=int(value))
        elif self.match(TokenType.STRING):
            value = self.consume(TokenType.STRING)
            return FactorNode(value=value)
        elif self.match(TokenType.IDENTIFIER):
            ident = self.consume(TokenType.IDENTIFIER)
            return FactorNode(identifier=ident)
        elif self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return FactorNode(sub_expression=expr)
        elif self.match(TokenType.NOT):
            self.consume(TokenType.NOT)
            # парсим фактор для NOT
            factor = self.parse_factor()
            return FactorNode(sub_expression=factor, is_not=True)
        else:
            raise SyntaxError(f"Unexpected token {self.current_token().type_} at line {self.current_token().line}")


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens  # Список токенов
        self.pos = 0  # Позиция текущего токена

    def current_token(self):
        """Получить текущий токен."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None, -1, -1)

    def consume(self, expected_type):
        """Потребляет текущий токен, если тип совпадает, и двигается дальше."""
        token = self.current_token()
        if token.type_ != expected_type:
            raise SyntaxError(
                f"Expected {expected_type}, but got {token.type_} at line {token.line}, col {token.column}")
        self.pos += 1
        return token.value

    def match(self, token_type):
        """Проверяет тип текущего токена, не потребляя его."""
        return self.current_token().type_ == token_type

    def parse_program(self):
        """Program -> 'program' IDENTIFIER ';' Block '.'"""
        # По классической грамматике Паскаля сначала должно идти ключевое слово PROGRAM
        # Но в вашем коде не было этого. Предположим, что вы хотите это поддержать:
        # self.consume(TokenType.PROGRAM)  # если хотите строго по грамматике
        self.consume(TokenType.IDENTIFIER) # program type?
        program_name = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.SEMICOLON)
        block = self.parse_block()
        self.consume(TokenType.DOT)
        return ProgramNode(program_name=program_name, block=block)

    def parse_block(self):
        """Block -> [Declarations] CompoundStatement"""
        declarations = self.parse_declarations()
        compound_statement = self.parse_compound_statement()
        return BlockNode(declarations=declarations, compound_statement=compound_statement)

    def parse_declarations(self):
        """Declarations -> { ConstDeclaration | VarDeclaration | ProcedureOrFunctionDeclaration }"""
        declarations = []

        # Проверяем типы токенов, которые могут указывать на начало деклараций
        while self.match(TokenType.CONST) or self.match(TokenType.VAR) or \
                self.match(TokenType.FUNCTION) or self.match(TokenType.PROCEDURE):

            if self.match(TokenType.CONST):
                declarations.extend(self.parse_const_declaration())
            elif self.match(TokenType.VAR):
                declarations.extend(self.parse_var_declaration())
            elif self.match(TokenType.FUNCTION) or self.match(TokenType.PROCEDURE):
                declarations.append(self.parse_procedure_or_function_declaration())

        return declarations

    def parse_const_declaration(self):
        """
        ConstDeclaration = "CONST" {
           IDENTIFIER
             (
                "=" (NUMBER | STRING)
                |
                ":" "array" "[" NUMBER ".." NUMBER "]" "of" (IDENTIFIER) [ "=" "(" (NUMBER|STRING) { "," (NUMBER|STRING) } ")" ]
             )
           ";"
        }
        """

        const_declarations = []
        self.consume(TokenType.CONST)

        while self.match(TokenType.IDENTIFIER):
            const_name = self.consume(TokenType.IDENTIFIER)

            # Три варианта продолжения: '=' (обычная константа), ':' (объявление массива),
            # либо SyntaxError, если что-то другое.
            if self.match(TokenType.EQ):
                # Обычная константа: IDENTIFIER = (NUMBER|STRING)
                self.consume(TokenType.EQ)
                if self.match(TokenType.NUMBER):
                    const_value = self.consume(TokenType.NUMBER)
                elif self.match(TokenType.STRING):
                    const_value = self.consume(TokenType.STRING)
                else:
                    raise SyntaxError(
                        f"Expected NUMBER or STRING for constant {const_name} "
                        f"at line {self.current_token().line}, col {self.current_token().column}"
                    )

                # Создаем узел и ждём ';'
                const_declarations.append(ConstDeclarationNode(identifier=const_name, value=const_value))
                self.consume(TokenType.SEMICOLON)

            elif self.match(TokenType.COLON):
                # Объявление массива: IDENTIFIER : array [1..N] of TYPE ...
                self.consume(TokenType.COLON)
                if not self.match(TokenType.ARRAY):
                    raise SyntaxError(
                        f"Expected 'array' after ':' in constant declaration {const_name} "
                        f"at line {self.current_token().line}, col {self.current_token().column}"
                    )
                self.consume(TokenType.ARRAY)

                self.consume(TokenType.LBRACKET)
                lower_bound = self.consume(TokenType.NUMBER)
                self.consume(TokenType.TWODOTS)
                upper_bound = self.consume(TokenType.NUMBER)
                self.consume(TokenType.RBRACKET)

                self.consume(TokenType.OF)
                # Предположим, что тип массива — это просто идентификатор (например, "integer")
                if not self.match(TokenType.IDENTIFIER):
                    raise SyntaxError(
                        f"Expected type identifier (e.g. 'integer') after 'of' "
                        f"at line {self.current_token().line}, col {self.current_token().column}"
                    )
                element_type = self.consume(TokenType.IDENTIFIER)

                # Проверяем, есть ли инициализация массива: `= ( ... )`
                array_values = None
                if self.match(TokenType.EQ):
                    self.consume(TokenType.EQ)
                    self.consume(TokenType.LPAREN)
                    array_values = []

                    # Собираем элементы в круглых скобках (числа или строки)
                    while self.match(TokenType.NUMBER) or self.match(TokenType.STRING):
                        if self.match(TokenType.NUMBER):
                            array_values.append(self.consume(TokenType.NUMBER))
                        else:
                            array_values.append(self.consume(TokenType.STRING))

                        if self.match(TokenType.COMMA):
                            self.consume(TokenType.COMMA)
                        else:
                            break

                    self.consume(TokenType.RPAREN)

                # Ждем `;`
                self.consume(TokenType.SEMICOLON)

                # Создаем узел для константы-массива
                # Можно использовать тот же `ConstDeclarationNode`, просто сохраняя структуру в .value
                # Или создать отдельный узел ConstArrayDeclarationNode, но упрощённо так:
                array_info = {
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "element_type": element_type,
                    "values": array_values,
                }
                const_declarations.append(
                    ConstDeclarationNode(identifier=const_name, value=array_info)
                )
            else:
                raise SyntaxError(
                    f"Expected '=' or ':' after constant name {const_name} "
                    f"at line {self.current_token().line}, col {self.current_token().column}"
                )

        return const_declarations

    def parse_var_declaration(self):
        """
        VarDeclaration = "VAR"
          {
             IDENTIFIER ":"
               (
                 SimpleType
                 | "array" "[" NUMBER ".." NUMBER "]" "of" SimpleType [ "=" "(" (NUMBER|STRING) { "," (NUMBER|STRING) } ")" ]
               )
             ";"
          }
        """

        var_declarations = []
        self.consume(TokenType.VAR)

        # В классическом Паскале допускается несколько объявлений подряд до встречи чего-то другого
        # Например:
        #    VAR
        #        x: integer;
        #        arr: array [1..5] of integer = (1,2,3,4,5);
        while self.match(TokenType.IDENTIFIER):
            var_name = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)

            # Проверяем, это массив или обычный тип
            if self.match(TokenType.ARRAY):
                # Парсим массив
                self.consume(TokenType.ARRAY)
                self.consume(TokenType.LBRACKET)
                lower_bound = self.consume(TokenType.NUMBER)
                self.consume(TokenType.TWODOTS)
                upper_bound = self.consume(TokenType.NUMBER)
                self.consume(TokenType.RBRACKET)
                self.consume(TokenType.OF)

                # Предположим, что тип массива это идентификатор (например, integer)
                if not self.match(TokenType.IDENTIFIER):
                    raise SyntaxError(
                        f"Expected type identifier after 'of' at line {self.current_token().line}, col {self.current_token().column}"
                    )
                element_type = self.consume(TokenType.IDENTIFIER)

                # Проверяем наличие инициализации:  = ( ... )
                array_values = None
                if self.match(TokenType.EQ):
                    self.consume(TokenType.EQ)
                    self.consume(TokenType.LPAREN)
                    array_values = []

                    # Собираем элементы в круглых скобках (числа или строки)
                    while self.match(TokenType.NUMBER) or self.match(TokenType.STRING):
                        if self.match(TokenType.NUMBER):
                            array_values.append(self.consume(TokenType.NUMBER))
                        else:
                            array_values.append(self.consume(TokenType.STRING))

                        if self.match(TokenType.COMMA):
                            self.consume(TokenType.COMMA)
                        else:
                            break

                    self.consume(TokenType.RPAREN)

                self.consume(TokenType.SEMICOLON)

                # Создаём соответствующий узел для переменной-массива
                array_info = {
                    "lower_bound": lower_bound,
                    "upper_bound": upper_bound,
                    "element_type": element_type,
                    "values": array_values
                }
                var_declarations.append(
                    VarDeclarationNode(identifier=var_name, var_type=array_info)
                )

            else:
                # Иначе это обычный тип (integer, string, etc.)
                type_name = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.SEMICOLON)

                # Создаём узел VarDeclarationNode.
                # В простейшем случае можем сохранить тип как строку,
                # или же создать TypeNode и поместить туда type_name.
                var_declarations.append(
                    VarDeclarationNode(identifier=var_name, var_type=type_name)
                )

        return var_declarations

    def parse_type(self):
        """Type = "integer" | "string" | "array" "[" NUMBER ".." NUMBER "]" "of" Type"""
        if self.match(TokenType.IDENTIFIER):
            # Предполагаем, что это либо integer, либо string, или что-то подобное
            ident_type = self.consume(TokenType.IDENTIFIER)
            return TypeNode(identifier_type=ident_type)

        elif self.match(TokenType.ARRAY):
            self.consume(TokenType.ARRAY)
            self.consume(TokenType.LBRACKET)
            lower_bound = self.consume(TokenType.NUMBER)
            self.consume(TokenType.TWODOTS)
            upper_bound = self.consume(TokenType.NUMBER)
            self.consume(TokenType.RBRACKET)
            self.consume(TokenType.OF)
            element_type = self.parse_type()
            return ArrayTypeNode(lower_bound=lower_bound, upper_bound=upper_bound, element_type=element_type)

        else:
            raise SyntaxError(f"Expected type at line {self.current_token().line}, col {self.current_token().column}")

    def parse_procedure_or_function_declaration(self):
        """
        ProcedureOrFunctionDeclaration =
            "PROCEDURE" IDENTIFIER [ "(" ParameterList ")" ] ";" Block ";"
          | "FUNCTION"  IDENTIFIER [ "(" ParameterList ")" ] ":" Type ";" Block ";"
        """
        kind_token = self.current_token()
        if kind_token.type_ not in [TokenType.PROCEDURE, TokenType.FUNCTION]:
            raise SyntaxError(
                f"Expected PROCEDURE or FUNCTION at line {kind_token.line}, col {kind_token.column}"
            )

        # Считываем "PROCEDURE" или "FUNCTION"
        kind = self.consume(kind_token.type_)  # либо 'PROCEDURE', либо 'FUNCTION'
        ident = self.consume(TokenType.IDENTIFIER)

        parameters = []
        # Если есть скобки — парсим список параметров
        if self.match(TokenType.LPAREN):
            parameters = self.parse_parameter_list()

        return_type = None
        # Если это FUNCTION, то ожидаем двоеточие и тип
        if kind_token.type_ == TokenType.FUNCTION:
            # Проверяем наличие ':'
            if self.match(TokenType.COLON):
                self.consume(TokenType.COLON)
                return_type = self.parse_type()
            else:
                raise SyntaxError(
                    f"Expected ':' and return type after FUNCTION {ident} "
                    f"at line {self.current_token().line}, col {self.current_token().column}"
                )

        self.consume(TokenType.SEMICOLON)

        # Парсим тело (Block)
        block = self.parse_block()

        # В конце объявления процедуры/функции тоже стоит ';'
        self.consume(TokenType.SEMICOLON)

        return ProcedureOrFunctionDeclarationNode(
            kind=kind,
            identifier=ident,
            parameters=parameters,
            block=block,
            return_type=return_type
        )

    def parse_parameter_list(self):
        """ParameterList = "(" IDENTIFIER ":" Type { ";" IDENTIFIER ":" Type } ")" """
        params = []
        self.consume(TokenType.LPAREN)
        # хотя в грамматике вы писали так, мы делаем классическую реализацию
        ident = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.COLON)
        param_type = self.parse_type()
        params.append(ParameterNode(identifier=ident, type_node=param_type))

        while self.match(TokenType.SEMICOLON):
            self.consume(TokenType.SEMICOLON)
            ident = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)
            param_type = self.parse_type()
            params.append(ParameterNode(identifier=ident, type_node=param_type))

        self.consume(TokenType.RPAREN)
        return params

    def parse_compound_statement(self):
        """CompoundStatement = "BEGIN" { Statement ";" } "END" """
        self.consume(TokenType.BEGIN)
        statements = []

        while not self.match(TokenType.END) and self.current_token().type_ != TokenType.EOF:
            stmt = self.parse_statement()
            statements.append(stmt)
            if self.match(TokenType.SEMICOLON):
                self.consume(TokenType.SEMICOLON)
            else:
                # Если нет ';', выходим, возможно END сразу
                break

        self.consume(TokenType.END)
        return CompoundStatementNode(statements=statements)

    def parse_statement(self):
        """Statement = AssignStatement | IfStatement | WhileStatement | ForStatement | ProcedureCall | CompoundStatement"""
        token = self.current_token()

        if self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_statement()
        elif self.match(TokenType.FOR):
            return self.parse_for_statement()
        elif self.match(TokenType.BEGIN):
            return self.parse_compound_statement()
        elif self.match(TokenType.IDENTIFIER):
            # Может быть присваивание или вызов процедуры
            # Посмотрим дальше
            lookahead = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if lookahead and lookahead.type_ == TokenType.ASSIGN:
                return self.parse_assign_statement()
            else:
                return self.parse_procedure_call()
        else:
            # Пустой оператор или что-то неожиданное
            # В Паскале нет пустых операторов кроме ';' между ними, но мы можем вернуть None или поднять ошибку
            raise SyntaxError(f"Unexpected token {token.type_} at line {token.line}, col {token.column}")

    def parse_assign_statement(self):
        """AssignStatement = IDENTIFIER ":=" Expression"""
        ident = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.ASSIGN)
        expr = self.parse_expression()
        return AssignStatementNode(identifier=ident, expression=expr)

    def parse_if_statement(self):
        """IfStatement = "IF" Expression "THEN" Statement [ "ELSE" Statement ]"""
        self.consume(TokenType.IF)
        condition = self.parse_expression()
        self.consume(TokenType.THEN)
        then_stmt = self.parse_statement()
        else_stmt = None
        if self.match(TokenType.ELSE):
            self.consume(TokenType.ELSE)
            else_stmt = self.parse_statement()
        return IfStatementNode(condition=condition, then_statement=then_stmt, else_statement=else_stmt)

    def parse_while_statement(self):
        """WhileStatement = "WHILE" Expression "DO" Statement"""
        self.consume(TokenType.WHILE)
        condition = self.parse_expression()
        self.consume(TokenType.DO)
        body = self.parse_statement()
        return WhileStatementNode(condition=condition, body=body)

    def parse_for_statement(self):
        """ForStatement = "FOR" IDENTIFIER ":=" Expression ("TO" | "DOWNTO") Expression "DO" Statement"""
        self.consume(TokenType.FOR)
        ident = self.consume(TokenType.IDENTIFIER)
        self.consume(TokenType.ASSIGN)
        start_expr = self.parse_expression()
        if self.match(TokenType.TO):
            direction = self.consume(TokenType.TO)
        elif self.match(TokenType.IDENTIFIER) and self.current_token().value.upper() == 'DOWNTO':
            # Допустим вы не добавили DOWNTO как токен, тогда нужна проверка по value
            # или добавьте DOWNTO в TokenType
            # Если DOWNTO есть в TokenType, можно использовать:
            # direction = self.consume(TokenType.DOWNTO)
            direction = self.consume(TokenType.IDENTIFIER)
            if direction.upper() != 'DOWNTO':
                raise SyntaxError("Expected TO or DOWNTO in for statement.")
        else:
            raise SyntaxError("Expected TO or DOWNTO in for statement.")

        end_expr = self.parse_expression()
        self.consume(TokenType.DO)
        body = self.parse_statement()
        return ForStatementNode(identifier=ident, start_expr=start_expr, direction=direction, end_expr=end_expr,
                                body=body)

    def parse_procedure_call(self):
        """ProcedureCall = IDENTIFIER [ "(" { Expression "," } Expression ")" ]"""
        ident = self.consume(TokenType.IDENTIFIER)
        args = []
        if self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            # парсим список выражений через запятую
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                args.append(self.parse_expression())
            self.consume(TokenType.RPAREN)
        return ProcedureCallNode(identifier=ident, arguments=args)

    def parse_expression(self):
        """Expression = SimpleExpression [ RelationalOperator SimpleExpression ]"""
        # Для простоты предположим, что parse_simple_expression уже есть
        # или мы пишем его сейчас
        left = self.parse_simple_expression()
        if self.match(TokenType.EQ) or self.match(TokenType.NEQ) or self.match(TokenType.LT) or \
                self.match(TokenType.GT) or self.match(TokenType.LTE) or self.match(TokenType.GTE):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_simple_expression()
            return ExpressionNode(left=left, relational_operator=op, right=right)
        return ExpressionNode(left=left)

    def parse_simple_expression(self):
        """SimpleExpression = Term { AdditiveOperator Term }"""
        left = self.parse_term()
        # Смотрим есть ли +, -, OR
        while self.match(TokenType.PLUS) or self.match(TokenType.MINUS) or self.match(TokenType.OR):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_term()
            # В отличие от ранее показанного кода, SimpleExpressionNode мы
            # можем построить как цепочку или сделать сразу список термов и операторов.
            # Для упрощения сейчас просто вернём новый SimpleExpressionNode
            # Но лучше собирать в список.
            left = SimpleExpressionNode(terms=[left, op, right])
        return left

    def parse_term(self):
        """Term = Factor { MultiplicativeOperator Factor }"""
        left = self.parse_factor()
        while self.match(TokenType.ASTERISK) or self.match(TokenType.SLASH) or \
                self.match(TokenType.DIV) or self.match(TokenType.MOD) or self.match(TokenType.AND):
            op = self.current_token().value
            self.pos += 1
            right = self.parse_factor()
            left = TermNode(factors=[left, op, right])
        return left

    def parse_factor(self):
        """Factor = NUMBER | IDENTIFIER | "(" Expression ")" | "NOT" Factor"""
        if self.match(TokenType.NUMBER):
            value = self.consume(TokenType.NUMBER)
            return FactorNode(value=int(value))
        elif self.match(TokenType.STRING):
            value = self.consume(TokenType.STRING)
            return FactorNode(value=value)
        elif self.match(TokenType.IDENTIFIER):
            ident = self.consume(TokenType.IDENTIFIER)
            return FactorNode(identifier=ident)
        elif self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return FactorNode(sub_expression=expr)
        elif self.match(TokenType.NOT):
            self.consume(TokenType.NOT)
            # парсим фактор для NOT
            factor = self.parse_factor()
            return FactorNode(sub_expression=factor, is_not=True)
        else:
            raise SyntaxError(f"Unexpected token {self.current_token().type_} at line {self.current_token().line}")
