import argparse
import json
from pathlib import Path
import sys

# Allow running this file directly via `python src/cli/main.py`.
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.issue_detector import IssueDetector
from src.core.patcher import PatchError, Patcher
from src.core.repo_loader import RepoLoader
from src.llm.client import LocalLLM

def _format_issues_text(issues):
    if not issues:
        return "No issues detected."
    return "\n".join(
        [
            f"- [{issue.get('severity', 'info')}] line {issue.get('line', '?')}: {issue['description']}"
            for issue in issues
        ]
    )


def _load_prompt_template():
    prompt_path = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "refactor_prompt.txt"
    return prompt_path.read_text()


def run_analyze(args):
    detector = IssueDetector()

    if args.repo:
        loader = RepoLoader(args.target, include_extensions=(".py",), exclude_patterns=args.exclude)
        files = loader.load_files(max_files=args.max_files)
        report = {"repo": str(Path(args.target).resolve()), "files": []}

        total_issues = 0
        for file_path in files:
            path = Path(file_path)
            code = path.read_text()
            issues = detector.detect(code, file_path=str(path))
            total_issues += len(issues)
            report["files"].append(
                {
                    "path": str(path),
                    "issue_count": len(issues),
                    "issues": issues,
                }
            )

        if args.json:
            print(json.dumps(report, indent=2))
            return

        print(f"Scanned {len(files)} Python files and found {total_issues} issues.")
        for file_report in report["files"]:
            if file_report["issue_count"] == 0:
                continue
            print(f"\n{file_report['path']} ({file_report['issue_count']} issues)")
            for issue in file_report["issues"]:
                print(f"  - [{issue['severity']}] line {issue['line']}: {issue['description']}")
        return

    target = Path(args.target)
    if not target.is_file():
        raise ValueError(f"Expected a file path, got: {target}")

    issues = detector.detect(target.read_text(), file_path=str(target))
    if args.json:
        print(json.dumps({"file": str(target.resolve()), "issues": issues}, indent=2))
        return

    print(f"Detected {len(issues)} issues in {target}.")
    print(_format_issues_text(issues))


def run_refactor(args):
    path = Path(args.file)
    if not path.is_file():
        raise ValueError(f"Expected a file path, got: {path}")

    code = path.read_text()
    issues = IssueDetector().detect(code, file_path=str(path))
    issues_text = _format_issues_text(issues)

    template = _load_prompt_template()
    prompt = template.format(issues=issues_text, code=code)

    llm = LocalLLM(model=args.model)
    output = llm.generate(prompt)

    if args.apply_patch:
        patcher = Patcher()
        diff = patcher.extract_patch(output)
        try:
            patcher.apply_patch_to_file(str(path), diff, dry_run=args.dry_run)
        except PatchError as exc:
            raise ValueError(f"Failed to apply patch: {exc}") from exc

    print(output)


def build_parser():
    parser = argparse.ArgumentParser(description="AI-assisted refactoring tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze one file or an entire repo")
    analyze_parser.add_argument("target", help="Target file path or repository path")
    analyze_parser.add_argument("--repo", action="store_true", help="Analyze all Python files in a repo")
    analyze_parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output")
    analyze_parser.add_argument("--max-files", type=int, default=None, help="Limit files analyzed in repo mode")
    analyze_parser.add_argument(
        "--exclude",
        nargs="*",
        default=(),
        help="Glob patterns to exclude in repo mode, e.g. tests/*",
    )
    analyze_parser.set_defaults(handler=run_analyze)

    refactor_parser = subparsers.add_parser("refactor", help="Generate refactor patch with LLM")
    refactor_parser.add_argument("file", help="File path to refactor")
    refactor_parser.add_argument("--model", default="deepseek-coder:6.7b", help="LLM model name")
    refactor_parser.add_argument("--apply-patch", action="store_true", help="Apply patch from model output")
    refactor_parser.add_argument("--dry-run", action="store_true", help="Validate patch application without writing")
    refactor_parser.set_defaults(handler=run_refactor)

    return parser


def main():
    parser = build_parser()
    argv = sys.argv[1:]
    if argv and argv[0] not in {"analyze", "refactor", "-h", "--help"}:
        argv = ["refactor", *argv]
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except ValueError as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()