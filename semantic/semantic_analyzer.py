from semantic.symbol_table import SymbolTable
from parser.ast_node import *


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()

    def visit_program(self, node: ProgramNode):
        self.visit_block(node.children[0])

    def visit_block(self, node: BlockNode):
        print(node)
        if node.declarations:
            self.visit_declarations(node.declarations)
        self.visit_compound_statement(node.compound_statement)

    def visit_declarations(self, node: DeclarationNode):
        for declaration in node:
            if isinstance(declaration, ConstDeclarationNode):
                self.visit_const_declaration(declaration)
            elif isinstance(declaration, TypeDeclarationNode):
                self.visit_type_declaration(declaration)
            elif isinstance(declaration, VarDeclarationNode):
                self.visit_var_declaration()
            elif isinstance(declaration, ProcedureOrFunctionDeclarationNode):
                self.visit_proc_or_func_declaration()

    def visit_compound_statement(self, node: CompoundStatementNode):
        ...
    def visit_var_declaration(self):
        ...
    def visit_proc_or_func_declaration(self):
        ...

    def create_array_info(self, node: ArrayTypeNode, declaration_place):

        type_checks = {
            "integer": int,
            "string": str,
        }


        size = node.upper_bound - node.lower_bound + 1

        if declaration_place == 'const':
            # Обязаны указать значение
            if node.initial_values is None:
                raise ValueError(f'{declaration_place} declaration array can not be empty, enter values')

            # Проверка на то, что длина верная
            elif len(node.initial_values) != size:
                raise ValueError(f'array size is not correct expected {size} got {len(node.initial_values)}')

            # Если длина верная, то проверяем соответствие типов
            else:
                if node.element_type in type_checks:
                    expected_type = type_checks[node.element_type]
                    if all(isinstance(element, expected_type) for element in node.initial_values):
                        arr_info = {
                            "element_type": node.element_type,
                            "size": size,
                            "lower_bound": node.lower_bound,
                            "upper_bound": node.upper_bound,
                            "initial_values": node.initial_values
                        }
                        return arr_info
                    else:
                        raise ValueError(f'Wrong type of array element expected {expected_type}')

    def visit_type_declaration(self, node: TypeDeclarationNode):
        name = node.name
        type_node = node.type_node

        fields = []
        for field_name, field in type_node.fields:
            print(field)
            if isinstance(field, TypeNode):
                if field.identifier_type in ("integer", "string") or\
                self.symbol_table.lookup(field.identifier_type):
                    field_info = {
                        "field_name": field_name,
                        "field_type": field.identifier_type
                    }
                    fields.append(field_info)
                else:
                    # если не в symbol_table, значит не запись
                    raise Exception(f'Wrong type {field.identifier_type} in field {field_name}')

            elif isinstance(field, ArrayTypeNode):
                arr_info = self.create_array_info(field, "record")
                field_info = {
                    "field_name": field_name,
                    "field_type": 'array',
                    "arr_info": arr_info
                }
                fields.append(field_info)

        print(fields)
        info = {
            "name": name,
            "type": 'record',
            "fields_info": fields
        }
        self.symbol_table.declare(name, info)

    def visit_const_declaration(self, node: ConstDeclarationNode):
        name = node.identifier
        const_value = node.value

        info = self.look_const_type(const_value)

        const_info = {"name": name, "info": info}
        self.symbol_table.declare(name, info)

    def look_const_type(self, value):
        const_type = None
        const_value = None

        type_checks = {
            "integer": int,
            "string": str,
        }

        const_type = value[0]
        const_value = value[1]

        if const_type in type_checks:
            expected_type = type_checks[const_type]
            if isinstance(const_value, expected_type):
                info = {
                    "type": const_type,
                    "value": const_value,
                }
                return info
            else:
                raise Exception(f"Value is not {const_type.capitalize()}")

        elif isinstance(value[0], ArrayTypeNode):
            info = self.create_array_info(const_type, declaration_place="const")
            return info

        elif self.symbol_table.lookup(value[0]):
            pass
