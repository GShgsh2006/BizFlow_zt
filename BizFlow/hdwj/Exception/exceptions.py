#统一异常类
class hdwjException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")

    def __str__(self):
        return f"[{self.code}] {self.message}"
