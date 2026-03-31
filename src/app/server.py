from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.core.issue_detector import IssueDetector
from src.core.repo_loader import RepoLoader
from src.llm.client import LocalLLM


class AnalyzeFileRequest(BaseModel):
    file_path: str


class AnalyzeRepoRequest(BaseModel):
    repo_path: str
    max_files: int | None = Field(default=200, ge=1)
    exclude: List[str] = Field(default_factory=list)


class RefactorRequest(BaseModel):
    file_path: str
    model: str = "deepseek-coder:6.7b"


app = FastAPI(title="Code Refactor AI API", version="0.1.0")


def _format_issues_text(issues: list[dict]) -> str:
    if not issues:
        return "No issues detected."
    return "\n".join(
        f"- [{item.get('severity', 'info')}] line {item.get('line', '?')}: {item.get('description', '')}"
        for item in issues
    )


def _load_prompt_template() -> str:
    prompt_path = Path(__file__).resolve().parents[1] / "llm" / "prompts" / "refactor_prompt.txt"
    return prompt_path.read_text()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Code Refactor AI</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 2rem; max-width: 900px; }
    h1 { margin-bottom: 0.2rem; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 1rem; margin-bottom: 1rem; }
    textarea, input { width: 100%; padding: 0.6rem; margin: 0.4rem 0; }
    button { padding: 0.6rem 1rem; cursor: pointer; }
    pre { white-space: pre-wrap; background: #f7f7f7; padding: 1rem; border-radius: 8px; }
  </style>
</head>
<body>
  <h1>Code Refactor AI</h1>
  <p>Quick app wrapper on top of your CLI/core logic.</p>

  <div class=\"card\">
    <h2>Analyze File</h2>
    <input id=\"filePath\" placeholder=\"src/core/issue_detector.py\" />
    <button onclick=\"analyzeFile()\">Analyze</button>
  </div>

  <div class=\"card\">
    <h2>Analyze Repo</h2>
    <input id=\"repoPath\" placeholder=\"path/to/your/repo\" />
    <button onclick=\"analyzeRepo()\">Analyze</button>
  </div>
  
  <div class=\"card\">
    <h2>Refactor Preview</h2>
    <input id=\"refactorFilePath\" placeholder=\"src/core/issue_detector.py\" />
    <button onclick=\"refactorFile()\">Generate Patch</button>
  </div>

  <h2>Result</h2>
  <pre id=\"result\">Ready.</pre>

  <script>
    async function analyzeFile() {
      const filePath = document.getElementById('filePath').value;
      const res = await fetch('/api/analyze/file', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ file_path: filePath })
      });
      const data = await res.json();
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
    }
    
    async function analyzeRepo() {
        const repoPath = document.getElementById('repoPath').value;
        const res = await fetch('/api/analyze/repo', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ repo_path: repoPath })
        });
        const data = await res.json();
        document.getElementById('result').textContent = JSON.stringify(data, null, 2);
    }

    async function refactorFile() {
      const filePath = document.getElementById('refactorFilePath').value;
      const res = await fetch('/api/refactor/preview', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ file_path: filePath })
      });
      const data = await res.json();
      document.getElementById('result').textContent = JSON.stringify(data, null, 2);
    }
  </script>
</body>
</html>
    """


@app.post("/api/analyze/file")
def analyze_file(payload: AnalyzeFileRequest):
    path = Path(payload.file_path)
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    code = path.read_text()
    issues = IssueDetector().detect(code, file_path=str(path))
    return {
        "file": str(path.resolve()),
        "issue_count": len(issues),
        "issues": issues,
    }


@app.post("/api/analyze/repo")
def analyze_repo(payload: AnalyzeRepoRequest):
    repo = Path(payload.repo_path)
    if not repo.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {repo}")

    loader = RepoLoader(str(repo), include_extensions=(".py",), exclude_patterns=payload.exclude)
    files = loader.load_files(max_files=payload.max_files)

    detector = IssueDetector()
    report = []
    total_issues = 0

    for file_path in files:
        code = Path(file_path).read_text()
        issues = detector.detect(code, file_path=file_path)
        total_issues += len(issues)
        report.append({"path": file_path, "issue_count": len(issues), "issues": issues})

    return {
        "repo": str(repo.resolve()),
        "file_count": len(files),
        "issue_count": total_issues,
        "files": report,
    }


@app.post("/api/refactor/preview")
def refactor_preview(payload: RefactorRequest):
    path = Path(payload.file_path)
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    code = path.read_text()
    issues = IssueDetector().detect(code, file_path=str(path))
    template = _load_prompt_template()
    prompt = template.format(issues=_format_issues_text(issues), code=code)

    llm = LocalLLM(model=payload.model)
    output = llm.generate(prompt)

    return {
        "file": str(path.resolve()),
        "issue_count": len(issues),
        "llm_output": output,
    }
