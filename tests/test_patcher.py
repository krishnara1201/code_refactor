from src.core.patcher import Patcher


def test_extract_patch_block():
    output = """\
---BEGIN PATCH---
--- a/sample.py
+++ b/sample.py
@@ -1,1 +1,1 @@
-print(\"a\")
+print(\"b\")
---END PATCH---
"""
    patch = Patcher().extract_patch(output)
    assert "@@ -1,1 +1,1 @@" in patch


def test_apply_patch_to_code():
    original = 'print("a")\n'
    diff = """\
--- a/sample.py
+++ b/sample.py
@@ -1,1 +1,1 @@
-print(\"a\")
+print(\"b\")
"""
    updated = Patcher().apply_patch_to_code(original, diff)
    assert updated == 'print("b")\n'
