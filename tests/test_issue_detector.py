from src.core.issue_detector import IssueDetector


def test_detects_unused_import_and_broad_except():
    code = """\
import os

def run(value):
    try:
        return value + 1
    except Exception:
        return 0
"""
    issues = IssueDetector().detect(code, file_path="sample.py")

    rules = {issue["rule"] for issue in issues}
    assert "unused_import" in rules
    assert "broad_exception" in rules


def test_detects_long_function():
    body = "\n".join(["    x += 1" for _ in range(45)])
    code = f"""\
def foo(x):
{body}
    return x
"""
    issues = IssueDetector().detect(code, file_path="sample.py")
    assert any(issue["rule"] == "long_function" for issue in issues)
