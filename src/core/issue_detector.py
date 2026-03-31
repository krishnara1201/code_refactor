import ast
from typing import Dict, List, Optional, Set


class _IssueVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.function_issues: List[Dict] = []
        self.broad_except_issues: List[Dict] = []
        self.current_nesting = 0
        self.max_nesting = 0

        self.imported_names: Dict[str, int] = {}
        self.used_names: Set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.AST) -> None:
        name = getattr(node, "name", "<anonymous>")
        lineno = getattr(node, "lineno", 1)
        end_lineno = getattr(node, "end_lineno", lineno)

        length = max(1, end_lineno - lineno + 1)
        if length > 40:
            self.function_issues.append(
                {
                    "rule": "long_function",
                    "severity": "medium",
                    "line": lineno,
                    "description": f"Function '{name}' is {length} lines long.",
                    "suggestion": "Break it into smaller helper functions.",
                }
            )

        args = getattr(node, "args", None)
        if args is not None:
            arg_count = len(args.args) + len(args.kwonlyargs)
            if arg_count > 5:
                self.function_issues.append(
                    {
                        "rule": "too_many_parameters",
                        "severity": "medium",
                        "line": lineno,
                        "description": f"Function '{name}' has {arg_count} parameters.",
                        "suggestion": "Use a dataclass/config object or split responsibilities.",
                    }
                )

    def _track_nesting(self, node: ast.AST) -> None:
        self.current_nesting += 1
        self.max_nesting = max(self.max_nesting, self.current_nesting)
        self.generic_visit(node)
        self.current_nesting -= 1

    def visit_If(self, node: ast.If) -> None:
        self._track_nesting(node)

    def visit_For(self, node: ast.For) -> None:
        self._track_nesting(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._track_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        self._track_nesting(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._track_nesting(node)
        for handler in node.handlers:
            if handler.type is None:
                self.broad_except_issues.append(
                    {
                        "rule": "bare_except",
                        "severity": "high",
                        "line": getattr(handler, "lineno", getattr(node, "lineno", 1)),
                        "description": "Bare 'except:' catches all exceptions.",
                        "suggestion": "Catch specific exception types.",
                    }
                )
            elif isinstance(handler.type, ast.Name) and handler.type.id == "Exception":
                self.broad_except_issues.append(
                    {
                        "rule": "broad_exception",
                        "severity": "medium",
                        "line": getattr(handler, "lineno", getattr(node, "lineno", 1)),
                        "description": "Catching generic 'Exception' can hide real errors.",
                        "suggestion": "Catch narrower exceptions where possible.",
                    }
                )

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imported_names[name] = getattr(node, "lineno", 1)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            self.imported_names[name] = getattr(node, "lineno", 1)

    def visit_Name(self, node: ast.Name) -> None:
        self.used_names.add(node.id)


class IssueDetector:
    def detect(self, code: str, file_path: Optional[str] = None) -> List[Dict]:
        issues: List[Dict] = []

        lines = code.splitlines()
        line_count = len(lines)

        if line_count > 200:
            issues.append(
                {
                    "rule": "long_file",
                    "severity": "low",
                    "line": 1,
                    "description": f"File has {line_count} lines.",
                    "suggestion": "Split the file into smaller modules.",
                    "file": file_path,
                }
            )

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            issues.append(
                {
                    "rule": "syntax_error",
                    "severity": "high",
                    "line": exc.lineno or 1,
                    "description": exc.msg,
                    "suggestion": "Fix syntax errors before refactoring.",
                    "file": file_path,
                }
            )
            return issues

        visitor = _IssueVisitor()
        visitor.visit(tree)

        for issue in visitor.function_issues + visitor.broad_except_issues:
            issue["file"] = file_path
            issues.append(issue)

        if visitor.max_nesting > 4:
            issues.append(
                {
                    "rule": "high_nesting",
                    "severity": "medium",
                    "line": 1,
                    "description": f"Maximum control-flow nesting depth is {visitor.max_nesting}.",
                    "suggestion": "Use guard clauses and smaller helper functions.",
                    "file": file_path,
                }
            )

        unused_imports = sorted(name for name in visitor.imported_names if name not in visitor.used_names)
        for name in unused_imports:
            issues.append(
                {
                    "rule": "unused_import",
                    "severity": "low",
                    "line": visitor.imported_names[name],
                    "description": f"Imported name '{name}' is never used.",
                    "suggestion": "Remove the unused import.",
                    "file": file_path,
                }
            )

        duplicate_blocks = self._find_duplicate_blocks(lines, file_path=file_path)
        issues.extend(duplicate_blocks)

        return sorted(issues, key=lambda i: (i.get("line", 1), i.get("rule", "")))

    def _find_duplicate_blocks(self, lines: List[str], file_path: Optional[str]) -> List[Dict]:
        # Detect repeated 3-line normalized blocks as a cheap duplication signal.
        issues: List[Dict] = []
        window_size = 3
        if len(lines) < window_size * 2:
            return issues

        seen: Dict[str, int] = {}
        for idx in range(0, len(lines) - window_size + 1):
            block = [line.strip() for line in lines[idx : idx + window_size]]
            if not all(block):
                continue
            key = "\n".join(block)
            if len(key) < 45:
                continue
            if key in seen:
                issues.append(
                    {
                        "rule": "duplicate_logic",
                        "severity": "low",
                        "line": idx + 1,
                        "description": f"Code block duplicates an earlier block near line {seen[key]}.",
                        "suggestion": "Extract shared logic into a helper function.",
                        "file": file_path,
                    }
                )
            else:
                seen[key] = idx + 1
        return issues