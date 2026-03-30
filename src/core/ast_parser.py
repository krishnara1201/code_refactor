from tree_sitter import Parser
from tree_sitter_languages import get_language

class ASTParser:
    def __init__(self, language="python"):
        self.language = get_language(language)
        self.parser = Parser()
        self.parser.set_language(self.language)

    def parse_file(self, path):
        with open(path, "rb") as f:
            code = f.read()
        return self.parser.parse(code)