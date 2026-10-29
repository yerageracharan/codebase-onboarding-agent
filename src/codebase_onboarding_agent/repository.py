"""Resolve local directories or securely download public GitHub ZIP archives."""

from __future__ import annotations

import contextlib
import io
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterator

MAX_ARCHIVE_BYTES = 30 * 1024 * 1024
MAX_UNPACKED_BYTES = 60 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 4000
_GITHUB_REPO_RE = re.compile(r"^/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


class RepositoryError(ValueError):
    """Raised when a repository source cannot safely be opened."""


def parse_github_url(source: str) -> tuple[str, str] | None:
    """Parse a narrowly supported public GitHub repository URL."""
    parsed = urllib.parse.urlparse(source.strip())
    if parsed.scheme != "https" or parsed.hostname != "github.com":
        return None
    if parsed.port not in (None, 443) or parsed.username or parsed.password:
        return None
    if parsed.query or parsed.fragment:
        return None
    match = _GITHUB_REPO_RE.fullmatch(parsed.path)
    if not match:
        return None
    owner, repo = match.groups()
    if owner in {".", ".."} or repo in {".", ".."}:
        return None
    return owner, repo.removesuffix(".git")


def _read_limited(response, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(1024 * 1024, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise RepositoryError(f"GitHub archive exceeds the {limit // (1024 * 1024)} MB download limit.")
    return b"".join(chunks)


def _safe_extract_zip(data: bytes, destination: Path) -> Path:
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise RepositoryError("GitHub returned an invalid ZIP archive.") from exc

    members = archive.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise RepositoryError(f"Archive contains too many entries (limit: {MAX_ARCHIVE_MEMBERS}).")
    expanded_total = sum(max(0, item.file_size) for item in members)
    if expanded_total > MAX_UNPACKED_BYTES:
        raise RepositoryError("Archive expands beyond the 60 MB safety limit.")

    root_names: set[str] = set()
    for item in members:
        posix_path = PurePosixPath(item.filename)
        if posix_path.is_absolute() or ".." in posix_path.parts or not posix_path.parts:
            raise RepositoryError("Archive contains an unsafe path; extraction was stopped.")
        unix_mode = (item.external_attr >> 16) & 0xFFFF
        if (unix_mode & 0o170000) == 0o120000:
            continue
        root_names.add(posix_path.parts[0])
        target = destination.joinpath(*posix_path.parts)
        resolved_destination = destination.resolve()
        if resolved_destination not in target.resolve().parents and target.resolve() != resolved_destination:
            raise RepositoryError("Archive path escapes the temporary extraction directory.")
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(item, "r") as src, target.open("wb") as out:
            remaining = item.file_size
            while remaining:
                chunk = src.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise RepositoryError("Archive ended before a file was fully extracted.")
                out.write(chunk)
                remaining -= len(chunk)
    if len(root_names) != 1:
        raise RepositoryError("Expected a GitHub ZIP with exactly one top-level repository directory.")
    root = destination / next(iter(root_names))
    if not root.is_dir():
        raise RepositoryError("The archive does not contain a repository directory.")
    return root


@contextlib.contextmanager
def open_repository(source: str) -> Iterator[tuple[Path, str]]:
    """Yield repository root and source description; never execute repository content."""
    trimmed = source.strip()
    if not trimmed:
        raise RepositoryError("Provide a local directory or public GitHub repository URL.")
    if trimmed.startswith(("http://", "https://")):
        parsed = parse_github_url(trimmed)
        if parsed is None:
            raise RepositoryError(
                "Only public repository URLs in the form https://github.com/OWNER/REPOSITORY are supported. "
                "Do not pass a file URL, private URL, token, or query string."
            )
        owner, repo = parsed
        request = urllib.request.Request(
            f"https://api.github.com/repos/{owner}/{repo}/zipball",
            headers={"User-Agent": "codebase-onboarding-agent/0.2.0", "Accept": "application/vnd.github+json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                archive_bytes = _read_limited(response, MAX_ARCHIVE_BYTES)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise RepositoryError("GitHub returned 404. Check that the repository is public and the URL is correct.") from exc
            raise RepositoryError(f"GitHub archive download failed with HTTP {exc.code}.") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RepositoryError(f"Could not download the public GitHub repository: {exc.__class__.__name__}.") from exc
        with tempfile.TemporaryDirectory(prefix="codebase-onboard-") as tmp:
            root = _safe_extract_zip(archive_bytes, Path(tmp))
            yield root, f"https://github.com/{owner}/{repo} (downloaded ZIP; branch/revision not pinned)"
        return
    path = Path(trimmed).expanduser().resolve()
    if not path.exists():
        raise RepositoryError(f"Path does not exist: {path}")
    if not path.is_dir():
        raise RepositoryError(f"Source path is not a directory (it is a file): {path}")
    yield path, str(path)
