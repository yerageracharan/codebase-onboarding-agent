"""Configuration for the optional OpenAI-compatible model backend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 120.0

    @classmethod
    def from_env(cls) -> "ModelConfig | None":
        """Return configured model settings, or None when no endpoint is configured."""
        base_url = os.getenv("CODEBASE_AGENT_BASE_URL", "").strip().rstrip("/")
        model = os.getenv("CODEBASE_AGENT_MODEL", "").strip()
        api_key = os.getenv("CODEBASE_AGENT_API_KEY", "").strip() or None
        if not base_url and not model and not api_key:
            return None
        if not base_url or not model:
            raise ValueError(
                "AI mode requires both CODEBASE_AGENT_BASE_URL and "
                "CODEBASE_AGENT_MODEL. Set them or run without --with-ai."
            )
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("CODEBASE_AGENT_BASE_URL must be an absolute HTTP(S) URL.")
        if parsed.username or parsed.password:
            raise ValueError("Do not put credentials inside CODEBASE_AGENT_BASE_URL.")
        return cls(base_url=base_url, model=model, api_key=api_key)

    @property
    def endpoint(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"
