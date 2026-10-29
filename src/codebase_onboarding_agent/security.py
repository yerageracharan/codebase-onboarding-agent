"""Repository file filtering and conservative secret redaction."""

from __future__ import annotations

import re
from pathlib import Path

EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "dist", "build", "target", "vendor", "coverage", "htmlcov", ".next",
    ".turbo", "site-packages", "bower_components",
}

_SECRET_FILENAMES = {
    "credentials", "credentials.json", "secrets.json", "service-account.json",
    "id_rsa", "id_ed25519", "known_hosts", "authorized_keys",
    "dockerconfig.json", ".npmrc", ".pypirc", ".netrc",
}
_SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".keystore", ".jks", ".crt"}

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?im)(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----).*?(-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)", re.DOTALL),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"(?i)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|secret[_-]?key)\b\s*[:=]\s*)(['\"]?)([^\s'\"\,;]{8,})(\2)"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def is_sensitive_path(path: Path, relative_path: str | None = None) -> bool:
    """Return True for files that should never be read into report/model context."""
    name = path.name.lower()
    rel = (relative_path or str(path)).replace("\\", "/").lower()
    if name in _SECRET_FILENAMES or path.suffix.lower() in _SENSITIVE_SUFFIXES:
        return True
    if name == ".env" or name.startswith(".env.") or name.startswith(".env-"):
        return True
    if any(part in {".ssh", ".aws", ".azure", ".gnupg"} for part in rel.split("/")):
        return True
    if name.endswith((".tfstate", ".tfstate.backup")):
        return True
    return False


def is_excluded_directory(name: str) -> bool:
    return name.lower() in EXCLUDED_DIRS


def redact_secrets(text: str) -> str:
    """Redact common high-confidence secret patterns from text before analysis."""
    output = _SECRET_PATTERNS[0].sub("[REDACTED PRIVATE KEY BLOCK]", text)
    for pattern in _SECRET_PATTERNS[1:4]:
        output = pattern.sub("[REDACTED SECRET]", output)
    output = _SECRET_PATTERNS[4].sub(lambda m: f"{m.group(1)}[REDACTED]", output)
    output = _SECRET_PATTERNS[5].sub("[REDACTED JWT]", output)
    return output
