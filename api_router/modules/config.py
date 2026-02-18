"""Config module — loads and resolves proxy configuration."""

__all__ = [
    "ProxyConfig",
    "TargetConfig",
    "ClientPolicy",
    "load_config",
]

# ─── API (public contract) ───────────────────────────

from dataclasses import dataclass, field


@dataclass
class TargetConfig:
    """An upstream service the proxy can forward to."""

    base_url: str
    default_headers: dict[str, str] = field(default_factory=dict)


@dataclass
class ClientPolicy:
    """Access policy for a single clientKey."""

    target: str
    allowed_methods: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)
    timeout_ms: int = 30000
    auth_header_ref: str | None = None
    rapid_api_key_ref: str | None = None


@dataclass
class ProxyConfig:
    """Complete resolved configuration."""

    targets: dict[str, TargetConfig] = field(default_factory=dict)
    clients: dict[str, ClientPolicy] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=dict)


def load_config(path: str = "config.yaml") -> ProxyConfig:
    """Load and resolve configuration from a YAML file.

    Environment variables in secrets are expanded (${VAR_NAME} syntax).
    Missing env vars resolve to empty string.
    """
    raw = _load_yaml(path)

    targets = {}
    for name, t in (raw.get("targets") or {}).items():
        targets[name] = TargetConfig(
            base_url=str(t.get("baseUrl", "")),
            default_headers=dict(t.get("defaultHeaders") or {}),
        )

    secrets = {}
    for name, template in (raw.get("secrets") or {}).items():
        secrets[name] = _expand_env(str(template))

    clients = {}
    for key, c in (raw.get("clients") or {}).items():
        clients[key] = ClientPolicy(
            target=str(c.get("target", "")),
            allowed_methods=[m.upper() for m in (c.get("allowedMethods") or [])],
            allowed_paths=list(c.get("allowedPaths") or []),
            timeout_ms=int(c.get("timeoutMs", 30000)),
            auth_header_ref=c.get("authHeaderRef"),
            rapid_api_key_ref=c.get("rapidApiKeyRef"),
        )

    return ProxyConfig(targets=targets, clients=clients, secrets=secrets)


# ─── INTERNAL (private — do not import from outside) ──

import os
import re

import yaml

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value: str) -> str:
    """Replace ${VAR_NAME} with env var value. Missing vars become empty string."""

    def _repl(match: re.Match) -> str:
        return os.environ.get(match.group(1), "")

    return _ENV_PATTERN.sub(_repl, value)


def _load_yaml(path: str) -> dict:
    """Load a YAML file and return its contents as a dict."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        raise SystemExit(f"Config file not found: {path}\nCopy config.example.yaml to config.yaml")
