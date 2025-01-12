class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def declare(self, name, info):
        if name in self.symbols:
            raise Exception(f"Duplicate identifier '{name}' in the same scope.")
        self.symbols[name] = info

    def lookup(self, name):
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent is not None:
            return self.parent.lookup(name)
        else:
            return None
