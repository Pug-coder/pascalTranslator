# Грамматика
## программа
    Program = "program", IDENTIFIER, ';', Block, "end", '.'

## Объявления
    Block = [ Declaration ], CompoundStatement ;
    
    Declarations = { 
        ConstDeclaration 
        | VarDeclaration 
        | ProcedureOrFunctionDeclaration } ;
    
    ConstDeclaration = "CONST", {
        IDENTIFIER "=", (NUMBER | STRING), ";" 
    } ;
    
    VarDeclaration = "VAR", { 
        IDENTIFIER ":" Type, ";"
    } ;
    
    Type = "integer"
        | "string" 
        | "array" "[" NUMBER ".." NUMBER "]" "of" Type ;
    
    ProcedureOrFunctionDeclaration = ( "PROCEDURE" | "FUNCTION" ), 
        IDENTIFIER, [ "(" ParameterList ")" ], ";" Block ";" ;
    
    ParameterList = IDENTIFIER ":" Type, { ";" IDENTIFIER ":" Type } ;

## Операторы 
    CompoundStatement = "BEGIN", { Statement ";" }, "END" ;

    Statement = AssignStatement
              | IfStatement
              | WhileStatement
              | ForStatement
              | ProcedureCall
              | CompoundStatement ;
    AssignStatement = IDENTIFIER ":=" Expression ;

    IfStatement = "IF", Expression, "THEN", Statement, 
    [ "ELSE", Statement ] ;

    WhileStatement = "WHILE", Expression, "DO", Statement ;

    ForStatement = "FOR", IDENTIFIER ":=", Expression, 
        ("TO" | "DOWNTO"), Expression, "DO", Statement ;

    ProcedureCall = IDENTIFIER, [ "(" { Expression, "," }, ")" ] ;

## Выражения
    Expression = SimpleExpression, 
        [ RelationalOperator, SimpleExpression ] ;

    SimpleExpression = Term, { AdditiveOperator, Term } ;

    Term = Factor, { MultiplicativeOperator, Factor } ;

    Factor = NUMBER
           | IDENTIFIER
           | "(" Expression ")"
           | "NOT" Factor ;
    
    RelationalOperator = "=" | "<>" | "<" | ">" | "<=" | ">=" ;

    AdditiveOperator = "+" | "-" | "OR" ;

    MultiplicativeOperator = "*" | "/" | "DIV" | "MOD" | "AND" ;

### Заметки
    Решено использовать только статические массивы опираясь на лекции по НУИЯП
    В  языке глобальная переменная (например, массив) компилируется в метку, 
    а память может быть инициализирована либо нулями, либо значениями, указанными в коде.

    Это совпадает с поведением статических массивов в Паскале, где:

    Если массив объявлен глобально, его элементы инициализируются нулями по умолчанию.

### Const declaration
    ConstSection = "CONST" { ConstItem ";" }

    ConstItem =
        IdentifierList ":" (SimpleType | ArrayType) [ "=" ConstValue ]
        |
        Identifier "=" ConstValue
    
    IdentifierList = IDENTIFIER { "," IDENTIFIER }
    
    ConstValue =
        NUMBER
      | STRING
      | "(" [ ValueItem { "," ValueItem } ] ")" 

### Var
    VarSection = "VAR" { VarItem ";" } ;

    VarItem = IdentifierList ":" Type [ "=" VarInit ] ;
    
    IdentifierList = IDENTIFIER { "," IDENTIFIER } ;
    Type          = (простой тип) | (array [..] of ...)
    VarInit       = (число/строка) | "(" список значений ")"
