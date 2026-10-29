from __future__ import annotations

import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from codebase_onboarding_agent.repository import RepositoryError, _safe_extract_zip, open_repository, parse_github_url


def make_zip(files: dict[str, str]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return stream.getvalue()


def test_parse_github_url_accepts_only_public_repo_shape() -> None:
    assert parse_github_url("https://github.com/owner/repo") == ("owner", "repo")
    assert parse_github_url("https://github.com/owner/repo.git") == ("owner", "repo")
    assert parse_github_url("https://github.com/owner/repo/") == ("owner", "repo")
    assert parse_github_url("http://github.com/owner/repo") is None
    assert parse_github_url("https://github.com/owner/repo/tree/main") is None
    assert parse_github_url("https://user:pass@github.com/owner/repo") is None
    assert parse_github_url("https://github.com/owner/repo?token=secret") is None
    assert parse_github_url("https://example.com/owner/repo") is None


def test_zip_extraction_and_public_repo_loader_mock(tmp_path: Path) -> None:
    data = make_zip({"owner-repo-abc/README.md": "# Hello", "owner-repo-abc/src/main.py": "print('hi')"})
    root = _safe_extract_zip(data, tmp_path)
    assert (root / "README.md").read_text() == "# Hello"
    assert (root / "src" / "main.py").exists()

    class FakeResponse(io.BytesIO):
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            self.close()

    with patch("codebase_onboarding_agent.repository.urllib.request.urlopen", return_value=FakeResponse(data)):
        with open_repository("https://github.com/owner/repo") as (repo_root, description):
            assert (repo_root / "README.md").exists()
            assert "https://github.com/owner/repo" in description


def test_zip_traversal_is_rejected(tmp_path: Path) -> None:
    data = make_zip({"repo/../escape.txt": "bad"})
    with pytest.raises(RepositoryError, match="unsafe path"):
        _safe_extract_zip(data, tmp_path)


def test_open_repository_rejects_non_directory(tmp_path: Path) -> None:
    file = tmp_path / "file.txt"
    file.write_text("hi")
    with pytest.raises(RepositoryError, match="not a directory"):
        with open_repository(str(file)):
            pass
