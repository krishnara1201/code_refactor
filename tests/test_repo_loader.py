from pathlib import Path

from src.core.repo_loader import RepoLoader


def test_repo_loader_filters_python_files(tmp_path: Path):
    (tmp_path / "a.py").write_text("print('a')")
    (tmp_path / "b.txt").write_text("hello")
    ignored_dir = tmp_path / ".venv"
    ignored_dir.mkdir()
    (ignored_dir / "ignore.py").write_text("print('skip')")

    loader = RepoLoader(str(tmp_path), include_extensions=(".py",))
    files = loader.load_files()

    assert str(tmp_path / "a.py") in files
    assert str(tmp_path / "b.txt") not in files
    assert str(ignored_dir / "ignore.py") not in files
