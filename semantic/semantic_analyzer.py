from semantic.symbol_table import SymbolTable
from parser.ast_node import *


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table = SymbolTable()

    def visit_program(self, node: ProgramNode):
        self.visit_block(node.block)

    def visit_block(self, node: BlockNode):
        if node.declarations:
            self.visit_declarations(node.declarations)
        self.visit_compound_statement(node.compound_statement)

    def visit_declarations(self, node: DeclarationNode):
        for declaration in node.declarations:
            if isinstance(declaration, ConstDeclarationNode):
                self.visit_const_declaration(declaration)
            elif isinstance(declaration, TypeDeclarationNode):
                self.visit_type_declaration(declaration)
            elif isinstance(declaration, VarDeclarationNode):
                self.visit_var_declaration(declaration)
            elif isinstance(declaration, ProcedureOrFunctionDeclarationNode):
                self.visit_proc_or_func_declaration(declaration)

    def visit_const_declaration(self, node: ConstDeclarationNode):
        name = node.identifier
        const_value = node.value

        info = self.look_const_type(const_value)

        const_info = {"name": name, "info": info}
        self.symbol_table.declare(name, info)

    def look_const_type(self, value):
        const_type = None
        const_value = None

        if value[0] in ("integer", "string"):
            const_type = value[0]
            const_val = int(value[1]) if isinstance(value[0], int) else value[1]

            info = {
                "type": const_type,
                "value": const_value,
            }

            return info

        elif isinstance(value[0], ArrayTypeNode):
            const_type = "array"
            ar_len = int(value[0].upper_bound) - int(value[0].lower_bound) + 1
            ar_lower_bound = int(value[0].lower_bound)
            ar_upper_bound = int(value[0].upper_bound)

            # потом посмотрим как с массивами
            ar_type = value[0].element_type
            ar_value = value[1]

            arr_info = {
                "ar_len": ar_len,
                "ar_lower_bound": ar_lower_bound,
                "ar_upper_bound": ar_upper_bound,
                "ar_type": ar_type,
                "ar_value": ar_value
            }

            info = {
                "type": const_type,
                "arr_info": arr_info,
            }

            return info

        else:
            type_name = value[0]
            type_info = self.symbol_table.lookup(type_name)

            if type_info is None:
                raise Exception(f"Неизвестный тип '{type_name}'.")

            # Проверяем, record ли это
            if type_info.get('type') == 'record':
                # Значит, это record. Формируем нужное вам описание:
                info = {
                    "type": "record",
                    "fields": type_info["fields"],
                    #"value": value[1] на попозже
                }
                return info
            else:
                # Иначе этот тип не record, и это, возможно, ошибка или другая ветка
                raise Exception(f"Тип '{type_name}' не является record.")


