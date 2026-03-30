import argparse
from pathlib import Path
import sys

# Allow running this file directly via `python src/cli/main.py`.
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.issue_detector import IssueDetector
from src.llm.client import LocalLLM

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="File to analyze")
    args = parser.parse_args()

    path = Path(args.file)
    if not path.is_file():
        parser.error(f"Expected a file path, got: {path}")

    code = path.read_text()

    issues = IssueDetector().detect(code)
    issues_text = "\n".join([i["description"] for i in issues])

    with open("src/llm/prompts/refactor_prompt.txt") as f:
        template = f.read()

    prompt = template.format(issues=issues_text, code=code)

    llm = LocalLLM()
    output = llm.generate(prompt)

    print(output)

if __name__ == "__main__":
    main()