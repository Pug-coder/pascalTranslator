from lexer.token_type import TokenType
from lexer.token import Token
from .ast_node import *


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens  # Список токенов
        self.pos = 0  # Позиция текущего токена

    def save_position(self):
        return self.pos

    def restore_position(self, saved_pos):
        self.pos = saved_pos

    def lookahead(self, offset):
        """Посмотреть токен на offset позиций вперёд от текущего."""
        index = self.pos + offset
        if index < len(self.tokens):
            return self.tokens[index]
        # Если вышли за границы, возвращаем фиктивный токен EOF
        return Token(TokenType.EOF, None, -1, -1)

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
        self.pos += 1 # возможно придется поменять порядок
        value = token.value

        if expected_type == TokenType.NUMBER:
            if not value.isnumeric():
                raise ValueError(f"Expected numeric value, but got '{value}' at line {token.line}, col {token.column}")
            value = int(value)
            return value
        elif expected_type == TokenType.STRING:
            return value
        else:
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
                self.match(TokenType.FUNCTION) or self.match(TokenType.PROCEDURE) \
                or self.match(TokenType.TYPE):
            if self.match(TokenType.TYPE):
                declarations.extend(self.parse_type_section())
            elif self.match(TokenType.CONST):
                declarations.extend(self.parse_const_declaration())
            elif self.match(TokenType.VAR):
                declarations.extend(self.parse_var_declaration())
            elif self.match(TokenType.FUNCTION) or self.match(TokenType.PROCEDURE):
                declarations.append(self.parse_procedure_or_function_declaration())

        return declarations

    def parse_array_declaration(self, allow_initialization=True):
        self.consume(TokenType.ARRAY)
        self.consume(TokenType.LBRACKET)

        dimensions = []
        while True:
            lower_bound = self.consume(TokenType.NUMBER)
            self.consume(TokenType.TWODOTS)
            upper_bound = self.consume(TokenType.NUMBER)
            dimensions.append((lower_bound, upper_bound))

            if not self.match(TokenType.COMMA):
                break
            self.consume(TokenType.COMMA)

        self.consume(TokenType.RBRACKET)
        self.consume(TokenType.OF)

        if not self.match(TokenType.IDENTIFIER):
            raise SyntaxError("Expected type identifier after 'of'")

        element_type = self.consume(TokenType.IDENTIFIER)

        array_values = None
        if allow_initialization and self.match(TokenType.EQ):
            self.consume(TokenType.EQ)
            self.consume(TokenType.LPAREN)
            array_values = []

            # Используем parse_const_value для обработки вложенных массивов и структур
            while not self.match(TokenType.RPAREN):
                array_values.append(self.parse_const_value())

                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                else:
                    break

            self.consume(TokenType.RPAREN)

        # Возвращаем узел
        return ArrayTypeNode(
            dimensions=dimensions,
            element_type=element_type,
            initial_values=array_values
        )

    def parse_const_declaration(self):
        """
        Пример, позволяющий объявления вида:
          const
            x = 10;
            y, z: integer = 20;
            s, t: string = "Hello";
            arr1, arr2: array [1..3] of integer = (1,2,3);
        """
        const_declarations = []
        self.consume(TokenType.CONST)

        # Пока следующий токен - IDENTIFIER, значит есть ещё объявления
        while self.match(TokenType.IDENTIFIER):
            # Сначала считываем список идентификаторов: (x, y, z)
            identifiers = [self.consume(TokenType.IDENTIFIER)]
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                identifiers.append(self.consume(TokenType.IDENTIFIER))

            declared_type = None
            const_value = None

            if self.match(TokenType.COLON):
                self.consume(TokenType.COLON)

                # Парсим тип (простой или массив)
                if self.match(TokenType.ARRAY):
                    declared_type = self.parse_array_declaration(allow_initialization=True)
                else:
                    # Предположим, что тип может быть либо IDENTIFIER (например, integer),
                    # либо STRING (если ваш лексер токенизирует ключевое слово 'string' как TokenType.STRING).
                    if self.match(TokenType.IDENTIFIER):
                        declared_type = self.consume(TokenType.IDENTIFIER)
                    elif self.match(TokenType.STRING):
                        declared_type = self.consume(TokenType.STRING)
                    else:
                        raise SyntaxError(
                            f"Expected a type (IDENTIFIER or STRING) after ':' "
                            f"at line {self.current_token().line}, col {self.current_token().column}"
                        )

                # Может быть инициализация через '='
                if self.match(TokenType.EQ):
                    self.consume(TokenType.EQ)
                    const_value = self.parse_const_value()
                    # parse_const_value может парсить NUMBER, STRING или массив в скобках (...)
                    # смотрите пример ниже
            elif self.match(TokenType.EQ):
                # Случай: x = 10 (без явного типа)
                self.consume(TokenType.EQ)
                const_value = self.parse_const_value()
            else:
                raise SyntaxError(
                    f"Expected ':' or '=' after identifier(s) {identifiers} "
                    f"at line {self.current_token().line}, col {self.current_token().column}"
                )

            # В конце каждого объявления должно быть ';'
            self.consume(TokenType.SEMICOLON)

            # Теперь создаём ConstDeclarationNode на каждый идентификатор в группе
            for ident in identifiers:
                const_declarations.append(
                    ConstDeclarationNode(identifier=ident, value=(declared_type, const_value))
                )

        return const_declarations

    def parse_record_initializer(self):
        """
        Парсит синтаксис вида:
          (field1: value1; field2: value2; ...)
        Возвращает структуру (например, список кортежей [(field1, value1), (field2, value2), ...])
        или специализированный узел RecordInitializerNode.
        """
        self.consume(TokenType.LPAREN)
        fields = []

        while True:
            # Ожидаем идентификатор поля
            if not self.match(TokenType.IDENTIFIER):
                # Если мы не видим IDENTIFIER, возможно, это пустая/ошибочная инициализация
                # Или мы дошли до RPAREN раньше времени
                break
            field_name_token = self.consume(TokenType.IDENTIFIER)

            # Ожидаем двоеточие
            self.consume(TokenType.COLON)

            # Значение поля может быть любым "константным значением" (число, строка, массив или рекорд)
            value = self.parse_const_value()

            fields.append((field_name_token, value))

            # После каждого поля может идти либо `;`, либо `)` если это последнее поле.
            if self.match(TokenType.SEMICOLON):
                self.consume(TokenType.SEMICOLON)
                # и продолжаем цикл, если не встретили `)`
                continue
            elif self.match(TokenType.COMMA):
                # Если вдруг вы хотите поддержать запятые вместо `;`
                self.consume(TokenType.COMMA)
                continue
            else:
                # Значит, либо закрывающая скобка, либо что-то нелегальное
                break

        # Завершаем скобки
        self.consume(TokenType.RPAREN)
        return RecordInitializerNode(fields)

    def parse_const_value(self):
        """
        Парсит то, что может стоять справа от '=' в секции const.
        Может быть:
          - NUMBER
          - STRING
          - '(' ... ')' (это может быть массив ИЛИ record)
        """
        if self.match(TokenType.NUMBER):
            return self.consume(TokenType.NUMBER)

        elif self.match(TokenType.STRING):
            return self.consume(TokenType.STRING)

        elif self.match(TokenType.LPAREN):
            # Посмотрим, что за конструкция внутри скобок:
            #   - Если после '(' сразу IDENTIFIER + ':' -> record
            #   - Иначе (например, число, строка, '(') -> "массивная" инициализация
            #     (или просто список значений).

            # Смотрим "вперёд" на следующий токен и токен после него
            # сохраним позицию парсера, чтобы проверить lookahead
            saved_position = self.save_position()
            self.consume(TokenType.LPAREN)

            is_record_init = False

            if self.match(TokenType.IDENTIFIER):
                # берём этот IDENTIFIER
                temp_id_token = self.current_token()
                # смотрим дальше — двоеточие?
                if self.lookahead(1).type_ == TokenType.COLON:
                    # Похоже на record
                    is_record_init = True

            # восстанавливаемся к началу скобок, т.к. мы только глянули lookahead
            self.restore_position(saved_position)

            if is_record_init:
                # Парсим record
                return self.parse_record_initializer()
            else:
                # Парсим список значений
                self.consume(TokenType.LPAREN)
                values = []
                while self.match(TokenType.NUMBER) or self.match(TokenType.STRING) or self.match(TokenType.LPAREN):
                    # Позволим вложенные скобки (на случай, если внутри массива лежит record)
                    values.append(self.parse_const_value())

                    if self.match(TokenType.COMMA):
                        self.consume(TokenType.COMMA)
                    else:
                        break
                self.consume(TokenType.RPAREN)
                return values

        else:
            raise SyntaxError(
                f"Expected NUMBER, STRING, or '(...)' after '=' in const declaration "
                f"at line {self.current_token().line}, col {self.current_token().column}"
            )

    def parse_var_declaration(self):
        """
        Пример, позволяющий объявления вида:
          var
            x, y: integer;
            s: string;
            arr1, arr2: array [1..3] of integer = (1,2,3);
        """
        var_declarations = []
        self.consume(TokenType.VAR)

        # Пока следующий токен - IDENTIFIER, значит есть ещё объявления
        while self.match(TokenType.IDENTIFIER):
            # Считываем список идентификаторов: (x, y, ...)
            identifiers = [self.consume(TokenType.IDENTIFIER)]
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                identifiers.append(self.consume(TokenType.IDENTIFIER))

            self.consume(TokenType.COLON)

            # Парсим тип: либо массив, либо простой
            declared_type = None
            if self.match(TokenType.ARRAY):
                declared_type = self.parse_array_declaration(allow_initialization=True)
            else:
                if self.match(TokenType.IDENTIFIER):
                    declared_type = self.consume(TokenType.IDENTIFIER)
                elif self.match(TokenType.STRING):
                    declared_type = self.consume(TokenType.STRING)
                else:
                    raise SyntaxError(
                        f"Expected a type (IDENTIFIER or STRING) after ':' "
                        f"at line {self.current_token().line}, col {self.current_token().column}"
                    )

            # Опциональная инициализация: = ...
            init_value = None
            if self.match(TokenType.EQ):
                self.consume(TokenType.EQ)
                init_value = self.parse_var_init_value()

            self.consume(TokenType.SEMICOLON)

            # Для каждого идентификатора создаём отдельный VarDeclarationNode
            for ident in identifiers:
                var_declarations.append(
                    VarDeclarationNode(identifier=ident, var_type=declared_type, init_value=init_value)
                )

        return var_declarations

    def parse_var_init_value(self):
        """
        Парсит инициализацию после '=' в секции var.
        Может быть:
          - Число / строка (для простых типов)  -> x, y: integer = 10;
          - Список значений в скобках (для массива) -> arr: array [1..3] of integer = (1,2,3);
        """
        # Если это массив, чаще всего предполагается (value1, value2, ...).
        # Но некоторые диалекты могут разрешать инициализацию простого типа прямо через =.
        # Например, x: integer = 5;
        if self.match(TokenType.LPAREN):
            # Парсим (value1, value2, ...)
            self.consume(TokenType.LPAREN)
            values = []
            while self.match(TokenType.NUMBER) or self.match(TokenType.STRING):
                if self.match(TokenType.NUMBER):
                    values.append(self.consume(TokenType.NUMBER))
                else:
                    values.append(self.consume(TokenType.STRING))

                if self.match(TokenType.COMMA):
                    self.consume(TokenType.COMMA)
                else:
                    break
            self.consume(TokenType.RPAREN)
            return values
        elif self.match(TokenType.NUMBER):
            return self.consume(TokenType.NUMBER)
        elif self.match(TokenType.STRING):
            return self.consume(TokenType.STRING)
        else:
            raise SyntaxError(
                f"Expected '(' or NUMBER or STRING after '=' in var declaration "
                f"at line {self.current_token().line}, col {self.current_token().column}"
            )

    def parse_type_section(self):
        """
            TypeSection = "TYPE" { TypeDeclaration ";" }

            Пример:
              type
                TPerson = record
                  name: string;
                  age: integer;
                end;

                TIntArray = array [1..10] of integer;
            """
        type_declarations = []
        self.consume(TokenType.TYPE)

        while self.match(TokenType.IDENTIFIER):
            type_declarations.append(self.parse_type_declaration())

        return type_declarations

    def parse_type_declaration(self):
        """
        TypeDeclaration = IDENTIFIER "=" Type ";"

        Пример:
          TPerson = record ... end
          TIntArray = array [1..10] of integer
        """
        name = self.consume(TokenType.IDENTIFIER)  # например, 'TPerson'
        self.consume(TokenType.EQ)

        the_type = self.parse_type()

        if self.match(TokenType.SEMICOLON):
            self.consume(TokenType.SEMICOLON)

        return TypeDeclarationNode(name, the_type)

    def parse_type(self):
        """
        parse_type обрабатывает:
           - простой тип (например, integer, string, и т.п. — через IDENTIFIER)
           - массив (array [lower..upper] of <type>)

        Если хотите поддержать вложенные массивы, рекурсия в parse_type тоже сработает.
        """
        if self.match(TokenType.ARRAY):
            return self.parse_array_declaration()
        elif self.match(TokenType.RECORD):
            return self.parse_record_type()
        elif self.match(TokenType.IDENTIFIER):
            # Предположим, что это простой тип, т.е. IDENTIFIER (integer, string, real, и т.д.)
            type_name = self.consume(TokenType.IDENTIFIER)
            return TypeNode(identifier_type=type_name)
        elif self.match(TokenType.STRING):
            type_name = self.consume(TokenType.STRING)
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
        if self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.WHILE):
            return self.parse_while_statement()
        elif self.match(TokenType.FOR):
            return self.parse_for_statement()
        elif self.match(TokenType.BEGIN):
            return self.parse_compound_statement()

        elif self.match(TokenType.IDENTIFIER):
            lookahead = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None

            # Проверяем, если следующий токен ":=" или "[",
            # значит это, скорее всего, присваивание (arr[i] := ...)
            if lookahead and (lookahead.type_ == TokenType.ASSIGN or lookahead.type_ == TokenType.LBRACKET or
            lookahead.type_ == TokenType.DOT):
                return self.parse_assign_statement()
            else:
                return self.parse_procedure_call()

        else:
            raise SyntaxError(
                f"Unexpected token {self.current_token().type_} at line "
                f"{self.current_token().line}, col {self.current_token().column}"
            )

    def parse_assign_statement(self):
        """
        AssignStatement = LValue ":=" Expression
        где LValue может быть:
          - IDENTIFIER
          - IDENTIFIER '[' Expression ']'
          - (и даже повторные '[]' для многомерных массивов, если нужно)
        """
        lval = self.parse_lvalue()
        self.consume(TokenType.ASSIGN)
        expr = self.parse_expression()
        return AssignStatementNode(identifier=lval, expression=expr)

    def parse_lvalue(self):
        """
        Считывает либо один идентификатор,
        либо идентификатор со скобками для массива: arr[i], arr[i+1], ...
        Если хотите поддержать многомерные массивы (arr[i,j]),
        придётся распарсить список выражений внутри скобок.
        """
        base_ident = self.consume(TokenType.IDENTIFIER)

        # Пока за идентификатором идёт [ ... ] .field
        while True:
            if self.match(TokenType.LBRACKET):
                # доступ к элементу массива
                self.consume(TokenType.LBRACKET)
                index_expr = self.parse_expression()
                self.consume(TokenType.RBRACKET)
                base_ident = ArrayAccessNode(array_name=base_ident, index_expr=index_expr)
            elif self.match(TokenType.DOT):
                # доступ к полю записи
                self.consume(TokenType.DOT)
                field = self.consume(TokenType.IDENTIFIER)  # имя поля
                base_ident = RecordFieldAccessNode(record_obj=base_ident, field_name=field)
            else:
                # ничего из вышеуказанного
                break

        return base_ident

    def parse_record_type(self):
        """
        Синтаксис (упрощённо):
          RECORD
             IdentifierList : Type ;
             IdentifierList : Type ;
             ...
          END
        """
        self.consume(TokenType.RECORD)

        fields = []
        # Пока не встретили 'END', читаем поля
        while not self.match(TokenType.END):
            # Парсим одну группу полей
            #  например: name, surname: string;
            #  или: x, y: integer;

            # Сначала считываем список идентификаторов
            identifiers = [self.consume(TokenType.IDENTIFIER)]
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                identifiers.append(self.consume(TokenType.IDENTIFIER))

            self.consume(TokenType.COLON)
            field_type = self.parse_type()

            for ident in identifiers:
                fields.append((ident, field_type))

            if self.match(TokenType.SEMICOLON):
                self.consume(TokenType.SEMICOLON)
            else:
                if self.match(TokenType.END):
                    break
                else:
                    raise SyntaxError(
                        f"Expected ';' or 'END' after record field declaration, got {self.current_token().type_} "
                        f"at line {self.current_token().line}, col {self.current_token().column}"
                    )

        self.consume(TokenType.END)

        # Создаём и возвращаем RecordTypeNode
        return RecordTypeNode(fields=fields)

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

    def parse_function_call(self, func_name):
        """
        Парсит вызов функции внутри выражения:
          func_name ( expr1, expr2, ... )
        Возвращает, например, FunctionCallNode(func_name, [expr1, expr2, ...])
        """
        self.consume(TokenType.LPAREN)
        arguments = []

        # Может быть пустой список аргументов:
        if not self.match(TokenType.RPAREN):
            # Парсим хотя бы одно выражение
            arguments.append(self.parse_expression())

            # Если несколько, они идут через запятую
            while self.match(TokenType.COMMA):
                self.consume(TokenType.COMMA)
                arguments.append(self.parse_expression())

        self.consume(TokenType.RPAREN)
        return FunctionCallNode(func_name, arguments)

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
        # (1) число
        if self.match(TokenType.NUMBER):
            val = self.consume(TokenType.NUMBER)
            return FactorNode(value=val)

        # (2) строка
        elif self.match(TokenType.STRING):
            val = self.consume(TokenType.STRING)
            return FactorNode(value=val)

        # (3) идентификатор => переменная, массив, или вызов функции
        elif self.match(TokenType.IDENTIFIER):
            ident = self.consume(TokenType.IDENTIFIER)

            # Могут быть индексы массива (arr[i]) — цикл while, если разрешаете многомерные
            while self.match(TokenType.LBRACKET):
                self.consume(TokenType.LBRACKET)
                index_expr = self.parse_expression()
                self.consume(TokenType.RBRACKET)
                ident = ArrayAccessNode(array_name=ident, index_expr=index_expr)

            while self.match(TokenType.DOT):
                self.consume(TokenType.DOT)
                field_ident = self.consume(TokenType.IDENTIFIER)
                node = RecordFieldAccessNode(record_obj=ident, field_name=field_ident)

                return node

            # Теперь проверяем, не идёт ли вызов (   fun2( ... )
            if self.match(TokenType.LPAREN):
                # Это значит, что мы имеем вызов функции, а не просто идентификатор
                func_call_node = self.parse_function_call(ident)
                return func_call_node

            # Иначе это просто FactorNode с identifier=ident
            if isinstance(ident, str):  # Если так и осталось строкой
                return FactorNode(identifier=ident)
            else:
                # Если ident превратился в ArrayAccessNode
                return ident

        # (4) скобки ( ... )
        elif self.match(TokenType.LPAREN):
            self.consume(TokenType.LPAREN)
            inner_expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return FactorNode(sub_expression=inner_expr)

        # (5) NOT factor
        elif self.match(TokenType.NOT):
            self.consume(TokenType.NOT)
            factor = self.parse_factor()
            return FactorNode(sub_expression=factor, is_not=True)

        else:
            raise SyntaxError(
                f"Unexpected token {self.current_token().type_} "
                f"at line {self.current_token().line}, col {self.current_token().column}"
            )
