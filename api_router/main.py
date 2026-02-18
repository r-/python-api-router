"""API Router — FastAPI entry point.

This is the edge/UI layer. It handles HTTP concerns (request parsing,
response formatting, CORS) and delegates all logic to the proxy service.
"""

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from api_router.composition.startup import create_proxy_service
from api_router.modules.proxy import ProxyError, ProxyRequest

# --- App setup ---

app = FastAPI(
    title="API Router",
    description="Lightweight API proxy with multi-tenant auth",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Wire up via composition ---

_config, _proxy_service = create_proxy_service()


# --- Error handler ---


@app.exception_handler(ProxyError)
async def proxy_error_handler(request: Request, exc: ProxyError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


# --- Routes ---


def _extract_client_key(request: Request) -> str:
    """Extract clientKey from Authorization: Bearer <key> header."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return ""
    return auth.removeprefix("Bearer ").strip()


@app.post("/proxy")
async def proxy(request: Request) -> Response:
    """General-purpose proxy endpoint.

    Expects JSON body:
    {
      "method": "GET|POST|PUT|DELETE|PATCH",
      "path": "/some/path",
      "query": { "key": "value" },    // optional
      "headers": { ... },             // optional (non-secret only)
      "body": { ... }                 // optional
    }
    """
    client_key = _extract_client_key(request)

    payload = await request.json()
    if not isinstance(payload, dict):
        return JSONResponse(status_code=400, content={"error": "invalid_json"})

    proxy_request = ProxyRequest(
        client_key=client_key,
        method=str(payload.get("method", "GET")).upper(),
        path=str(payload.get("path", "")).strip(),
        query=payload.get("query") or {},
        headers=payload.get("headers") or {},
        body=payload.get("body"),
    )

    result = await _proxy_service.handle(proxy_request)

    return Response(
        content=result.content,
        status_code=result.status_code,
        media_type=result.content_type,
    )


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"ok": True}
