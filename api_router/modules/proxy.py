"""Proxy module — authenticates clients, enforces policy, forwards to upstream."""

__all__ = [
    "ProxyRequest",
    "ProxyResponse",
    "ProxyService",
]

# ─── API (public contract) ───────────────────────────

from dataclasses import dataclass, field
from typing import Any

from api_router.modules.config import ProxyConfig


@dataclass
class ProxyRequest:
    """Inbound request from a client."""

    client_key: str
    method: str = "GET"
    path: str = "/"
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None


@dataclass
class ProxyResponse:
    """Response returned to the client."""

    status_code: int
    content: bytes
    content_type: str = "application/json"


class ProxyError(Exception):
    """Error with a status code for HTTP responses."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


class ProxyService:
    """Core proxy logic. Stateless — receives config at init.

    Usage:
        service = ProxyService(config)
        response = await service.handle(request)
    """

    def __init__(self, config: ProxyConfig):
        self._config = config

    async def handle(self, request: ProxyRequest) -> ProxyResponse:
        """Process a proxy request: authenticate, check policy, forward upstream."""
        policy = self.validate_client(request.client_key)
        _check_allowed(policy, request.method, request.path)
        target = _get_target(self._config, policy.target)
        headers = _build_upstream_headers(
            target_headers=target.default_headers,
            policy=policy,
            secrets=self._config.secrets,
            client_headers=request.headers,
        )
        return await _forward_upstream(
            base_url=target.base_url,
            path=request.path,
            method=request.method,
            query=request.query,
            headers=headers,
            body=request.body,
            timeout_ms=policy.timeout_ms,
        )

    def validate_client(self, client_key: str) -> Any:
        """Public method to validate a clientKey without exposing internals."""
        return _get_policy(self._config, client_key)


# ─── INTERNAL (private — do not import from outside) ──

import httpx

from api_router.modules.config import ClientPolicy, ProxyConfig, TargetConfig

# Headers that clients must never override (security).
_BLOCKED_HEADERS = {"authorization", "x-api-key", "x-rapidapi-key"}


def _get_policy(config: ProxyConfig, client_key: str) -> ClientPolicy:
    """Look up and validate a client key."""
    if not client_key:
        raise ProxyError(401, "missing_client_key")
    policy = config.clients.get(client_key)
    if not policy:
        raise ProxyError(401, "invalid_client_key")
    return policy


def _check_allowed(policy: ClientPolicy, method: str, path: str) -> None:
    """Enforce method and path allowlists."""
    if not path.startswith("/"):
        raise ProxyError(400, "path_must_start_with_slash")

    if policy.allowed_methods and method.upper() not in policy.allowed_methods:
        raise ProxyError(403, f"method_not_allowed: {method}")

    if policy.allowed_paths and path not in policy.allowed_paths:
        raise ProxyError(403, f"path_not_allowed: {path}")


def _get_target(config: ProxyConfig, target_name: str) -> TargetConfig:
    """Resolve the upstream target."""
    target = config.targets.get(target_name)
    if not target:
        raise ProxyError(500, f"unknown_target: {target_name}")
    if not target.base_url:
        raise ProxyError(500, "target_missing_base_url")
    return target


def _resolve_secret(secrets: dict[str, str], ref: str | None) -> str:
    """Resolve a secret reference. Returns empty string if ref is None."""
    if not ref:
        return ""
    value = secrets.get(ref, "")
    if not value:
        raise ProxyError(500, f"missing_secret: {ref}")
    return value


def _build_upstream_headers(
    *,
    target_headers: dict[str, str],
    policy: ClientPolicy,
    secrets: dict[str, str],
    client_headers: dict[str, str],
) -> dict[str, str]:
    """Build the final headers for the upstream request."""
    headers = dict(target_headers)

    # Add secret auth header (OpenRouter/OpenAI style).
    if policy.auth_header_ref:
        headers["Authorization"] = _resolve_secret(secrets, policy.auth_header_ref)

    # Add RapidAPI key header.
    if policy.rapid_api_key_ref:
        headers["X-RapidAPI-Key"] = _resolve_secret(secrets, policy.rapid_api_key_ref)

    # Forward non-blocked headers from client.
    for key, value in client_headers.items():
        if key.lower() not in _BLOCKED_HEADERS:
            headers[key] = value

    return headers


async def _forward_upstream(
    *,
    base_url: str,
    path: str,
    method: str,
    query: dict[str, str],
    headers: dict[str, str],
    body: Any,
    timeout_ms: int,
) -> ProxyResponse:
    """Send the request to the upstream service and return the response."""
    url = base_url.rstrip("/") + path
    timeout = timeout_ms / 1000

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            r = await client.request(
                method=method.upper(),
                url=url,
                params=query or None,
                headers=headers,
                json=body,
            )
        except httpx.RequestError as e:
            raise ProxyError(502, f"upstream_connection_error: {type(e).__name__}")

    content_type = r.headers.get("content-type", "application/json")
    return ProxyResponse(
        status_code=r.status_code,
        content=r.content,
        content_type=content_type,
    )
