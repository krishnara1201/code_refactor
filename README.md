# Code Refactor AI

`code_refactor` is an AI-assisted Python refactoring toolchain that can:

- Analyze a single file or an entire repository.
- Detect maintainability and correctness smells using AST rules.
- Ask a local LLM to generate a unified diff patch.
- Validate and optionally apply the generated patch.

## Current Tooling

### 1) Issue detection (`src/core/issue_detector.py`)

The detector currently flags:

- `syntax_error`
- `long_file`
- `long_function`
- `too_many_parameters`
- `high_nesting`
- `bare_except`
- `broad_exception`
- `unused_import`
- `duplicate_logic` (repeated 3-line blocks)

Each issue returns structured metadata (`rule`, `severity`, `line`, `description`, `suggestion`, `file`).

### 2) Repository loader (`src/core/repo_loader.py`)

- Recursive file scanning with extension filters.
- Built-in ignored directories (`.git`, `.venv`, `node_modules`, caches, build outputs).
- User-defined glob exclusions.
- Optional max-file limit for faster runs.

### 3) Patcher (`src/core/patcher.py`)

- Extracts patch sections from LLM output markers.
- Applies unified diff hunks to code with context checks.
- Supports file-level dry-run mode before writing changes.

## CLI Usage

### Analyze one file

```bash
python src/cli/main.py analyze path/to/file.py
```

### Analyze a repository

```bash
python src/cli/main.py analyze /path/to/repo --repo --max-files 100
```

### Analyze and emit JSON

```bash
python src/cli/main.py analyze /path/to/repo --repo --json
```

### Generate refactor patch with local model

```bash
python src/cli/main.py refactor path/to/file.py --model deepseek-coder:6.7b
```

### Generate and apply patch

```bash
python src/cli/main.py refactor path/to/file.py --apply-patch
```

### Backward-compatible shortcut

This still works and defaults to `refactor`:

```bash
python src/cli/main.py path/to/file.py
```

## Tests

Run tests with:

```bash
python -m pytest -q
```

Current suite covers detector rules, patch parsing/application, and repository loading filters.

## App Layer (Web + API)

You can run an app on top of the CLI/core logic using FastAPI.

### Start the app

```bash
python -m uvicorn src.app.server:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` for a simple UI.

### API endpoints

- `POST /api/analyze/file`
- `POST /api/analyze/repo`
- `POST /api/refactor/preview`

### Example API calls

Analyze one file:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze/file \
	-H "Content-Type: application/json" \
	-d '{"file_path":"src/core/issue_detector.py"}'
```

Analyze a repository:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze/repo \
	-H "Content-Type: application/json" \
	-d '{"repo_path":".","max_files":50,"exclude":["tests/*"]}'
```

Generate refactor preview:

```bash
curl -X POST http://127.0.0.1:8000/api/refactor/preview \
	-H "Content-Type: application/json" \
	-d '{"file_path":"src/core/issue_detector.py","model":"deepseek-coder:6.7b"}'
```
