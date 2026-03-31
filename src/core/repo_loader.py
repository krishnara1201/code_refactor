import fnmatch
import os
from pathlib import Path
from typing import Iterable, List, Optional, Sequence


class RepoLoader:
    DEFAULT_IGNORED_DIRS = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        "dist",
        "build",
    }

    def __init__(
        self,
        repo_path: str,
        include_extensions: Optional[Sequence[str]] = None,
        exclude_patterns: Optional[Sequence[str]] = None,
    ) -> None:
        self.repo_path = Path(repo_path).resolve()
        self.include_extensions = tuple(include_extensions or (".py",))
        self.exclude_patterns = tuple(exclude_patterns or ())

    def load_files(self, max_files: Optional[int] = None) -> List[str]:
        files: List[str] = []
        for path in self._iter_files():
            files.append(str(path))
            if max_files is not None and len(files) >= max_files:
                break
        return files

    def _iter_files(self) -> Iterable[Path]:
        for root, dirs, filenames in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in self.DEFAULT_IGNORED_DIRS]
            root_path = Path(root)
            for filename in filenames:
                path = root_path / filename
                if not self._is_candidate(path):
                    continue
                yield path

    def _is_candidate(self, path: Path) -> bool:
        rel_path = path.relative_to(self.repo_path).as_posix()

        if path.suffix not in self.include_extensions:
            return False

        for pattern in self.exclude_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return False

        return True
