import re
from pathlib import Path
from typing import List


class PatchError(ValueError):
    pass


class Patcher:
    PATCH_START = "---BEGIN PATCH---"
    PATCH_END = "---END PATCH---"

    def extract_patch(self, llm_output: str) -> str:
        start = llm_output.find(self.PATCH_START)
        end = llm_output.find(self.PATCH_END)
        if start == -1 or end == -1 or end <= start:
            raise PatchError("Patch markers not found in LLM output.")

        return llm_output[start + len(self.PATCH_START) : end].strip()

    def apply_patch_to_code(self, original_code: str, unified_diff: str) -> str:
        original_lines = original_code.splitlines(keepends=True)
        output_lines: List[str] = []
        src_index = 0

        hunk_header_re = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
        diff_lines = unified_diff.splitlines(keepends=True)
        i = 0

        while i < len(diff_lines):
            line = diff_lines[i]
            if line.startswith("--- ") or line.startswith("+++ "):
                i += 1
                continue

            match = hunk_header_re.match(line.rstrip("\n"))
            if not match:
                i += 1
                continue

            old_start = int(match.group(1))
            old_count = int(match.group(2) or "1")
            hunk_src_start = old_start - 1

            output_lines.extend(original_lines[src_index:hunk_src_start])
            src_index = hunk_src_start

            i += 1
            consumed = 0
            while i < len(diff_lines):
                hunk_line = diff_lines[i]
                if hunk_line.startswith("@@ "):
                    break
                if hunk_line.startswith("\\ No newline at end of file"):
                    i += 1
                    continue

                if not hunk_line:
                    i += 1
                    continue

                prefix = hunk_line[0]
                content = hunk_line[1:]

                if prefix == " ":
                    if src_index >= len(original_lines) or original_lines[src_index] != content:
                        raise PatchError("Context mismatch while applying patch.")
                    output_lines.append(original_lines[src_index])
                    src_index += 1
                    consumed += 1
                elif prefix == "-":
                    if src_index >= len(original_lines) or original_lines[src_index] != content:
                        raise PatchError("Delete mismatch while applying patch.")
                    src_index += 1
                    consumed += 1
                elif prefix == "+":
                    output_lines.append(content)
                else:
                    raise PatchError(f"Unsupported diff line prefix: {prefix}")

                i += 1

            if consumed < old_count:
                raise PatchError("Patch hunk did not consume expected source lines.")

        output_lines.extend(original_lines[src_index:])
        return "".join(output_lines)

    def apply_patch_to_file(self, file_path: str, unified_diff: str, dry_run: bool = False) -> str:
        path = Path(file_path)
        original = path.read_text()
        updated = self.apply_patch_to_code(original, unified_diff)
        if not dry_run:
            path.write_text(updated)
        return updated