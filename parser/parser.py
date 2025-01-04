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

    def parse_array_declaration(self, allow_initialization=True):
        """
        Парсит объявление массива вида:
          array [lower_bound..upper_bound] of <element_type> [= (value1, value2, ...)]

        Параметр allow_initialization управляет тем,
        разрешаем ли мы конструкцию '= ( ... )' (например, в секции const или var).
        Для параметров функций (если вы хотите поддержать передачу массивов по значению)
        обычно инициализация не нужна.
        """
        # Уже знаем, что текущий токен - ARRAY
        self.consume(TokenType.ARRAY)

        self.consume(TokenType.LBRACKET)
        lower_bound = self.consume(TokenType.NUMBER)  # предположим, это строка с числом
        self.consume(TokenType.TWODOTS)
        upper_bound = self.consume(TokenType.NUMBER)
        self.consume(TokenType.RBRACKET)

        self.consume(TokenType.OF)
        # Предположим, что тип массива это идентификатор (например, integer)
        if not self.match(TokenType.IDENTIFIER):
            raise SyntaxError(
                f"Expected type identifier after 'of' at line {self.current_token().line}, "
                f"col {self.current_token().column}"
            )
        element_type = self.consume(TokenType.IDENTIFIER)

        # Проверяем наличие инициализации:  = ( ... )
        array_values = None
        if allow_initialization and self.match(TokenType.EQ):
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

        # Собираем всё в одну структуру (или можете возвращать отдельный узел)
        array_info = {
            "lower_bound": lower_bound,
            "upper_bound": upper_bound,
            "element_type": element_type,
            "values": array_values,
        }
        return ArrayTypeNode(
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            element_type=element_type,
            initial_values=array_values
        )

    def parse_const_declaration(self):
        """
        ConstDeclaration = "CONST" {
           IDENTIFIER
             (
                "=" (NUMBER | STRING)
                |
                ":" "array" "[" NUMBER ".." NUMBER "]" "of" IDENTIFIER [ "=" "(" (NUMBER|STRING) { "," (NUMBER|STRING) } ")" ]
             )
           ";"
        }
        """
        const_declarations = []
        self.consume(TokenType.CONST)

        while self.match(TokenType.IDENTIFIER):
            const_name = self.consume(TokenType.IDENTIFIER)

            # Три варианта: '=' (обычная константа), ':' (объявление массива), иначе ошибка.
            if self.match(TokenType.EQ):
                # Обычная константа
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

                const_declarations.append(
                    ConstDeclarationNode(identifier=const_name, value=const_value)
                )
                self.consume(TokenType.SEMICOLON)

            elif self.match(TokenType.COLON):
                # Объявление массива
                self.consume(TokenType.COLON)
                if not self.match(TokenType.ARRAY):
                    raise SyntaxError(
                        f"Expected 'array' after ':' in constant declaration {const_name} "
                        f"at line {self.current_token().line}, col {self.current_token().column}"
                    )
                array_info = self.parse_array_declaration(allow_initialization=True)
                self.consume(TokenType.SEMICOLON)

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

        while self.match(TokenType.IDENTIFIER):
            var_name = self.consume(TokenType.IDENTIFIER)
            self.consume(TokenType.COLON)

            # Проверяем, это массив или обычный тип
            if self.match(TokenType.ARRAY):
                array_info = self.parse_array_declaration(allow_initialization=True)
                self.consume(TokenType.SEMICOLON)

                var_declarations.append(
                    VarDeclarationNode(identifier=var_name, var_type=array_info)
                )
            else:
                # Иначе это обычный тип (integer, string, etc.)
                type_name = self.consume(TokenType.IDENTIFIER)
                self.consume(TokenType.SEMICOLON)

                var_declarations.append(
                    VarDeclarationNode(identifier=var_name, var_type=type_name)
                )

        return var_declarations

    def parse_type(self):
        """
        parse_type обрабатывает:
           - простой тип (например, integer, string, и т.п. — через IDENTIFIER)
           - массив (array [lower..upper] of <type>)

        Если хотите поддержать вложенные массивы, рекурсия в parse_type тоже сработает.
        """
        if self.match(TokenType.ARRAY):
            return self.parse_array_declaration()
        else:
            # Предположим, что это простой тип, т.е. IDENTIFIER (integer, string, real, и т.д.)
            type_name = self.consume(TokenType.IDENTIFIER)
            return TypeNode(identifier_type=type_name)

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
        """
        Синтаксис (упрощённо):
          ParameterList = "(" [ ParameterDeclaration { ";" ParameterDeclaration } ] ")"

        Примеры:
          ()
          (a, b: integer)
          (a: integer; s: string)
          (arr: array [1..10] of integer)
          (var x: integer; const y: string) // с ключевыми словами var/const
        """
        params = []
        self.consume(TokenType.LPAREN)

        # Случай пустого списка параметров
        if self.match(TokenType.RPAREN):
            self.consume(TokenType.RPAREN)
            return params

        # Парсим первую группу
        params.extend(self.parse_parameter_declaration())

        # Может быть несколько групп через точку с запятой
        while self.match(TokenType.SEMICOLON):
            self.consume(TokenType.SEMICOLON)
            params.extend(self.parse_parameter_declaration())

        self.consume(TokenType.RPAREN)
        return params

    def parse_parameter_declaration(self):
        """
        ParameterDeclaration = [ 'var' | 'const' ] IdentifierList ":" Type

        Пример:
          var a, b: integer
          const s: string
          arr: array [1..3] of integer
        """
        param_nodes = []

        # Проверяем, есть ли ключевое слово 'var' или 'const'
        pass_mode = None
        if self.match(TokenType.VAR):
            pass_mode = "var"
            self.consume(TokenType.VAR)
        elif self.match(TokenType.CONST):
            pass_mode = "const"
            self.consume(TokenType.CONST)

        # Считываем один или несколько идентификаторов (через запятую)
        identifiers = [self.consume(TokenType.IDENTIFIER)]
        while self.match(TokenType.COMMA):
            self.consume(TokenType.COMMA)
            identifiers.append(self.consume(TokenType.IDENTIFIER))

        # Ожидаем двоеточие и тип
        self.consume(TokenType.COLON)
        param_type = self.parse_type()  # parse_type может обрабатывать и массивы, и простые типы

        # Создаем ParameterNode для каждого идентификатора
        for ident in identifiers:
            param_nodes.append(ParameterNode(identifier=ident, type_node=param_type, pass_mode=pass_mode))

        return param_nodes

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
