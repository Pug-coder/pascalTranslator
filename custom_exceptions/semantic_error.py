class SemanticError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(f"[Семантическая ошибка]: {message}")

    def __str__(self):
        return f"[Семантическая ошибка]: {self.message}"

    def display(self):
        print(self.__str__())