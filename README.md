# Python Api Router

A lightweight API proxy with multi-tenant auth and upstream routing.

Built with [FastAPI](https://fastapi.tiangolo.com/) · Follows [Pragmatic Modular Monolith](https://github.com/r-/pragmatic-modular-monolith) architecture

## What it does

Your app talks to **your server**, your server forwards to the **real API** — with secret keys on the server side.

```
Client (browser/app)
    │ Authorization: Bearer <clientKey>
    ▼
┌──────────────────────┐
│  python-api-router   │  ← validates clientKey, enforces policy
│  POST /proxy         │  ← adds secret upstream headers
└──────────┬───────────┘
           │
           ▼
   Upstream API (OpenRouter, RapidAPI, etc.)
```

**Use it for:**
- AI providers (OpenRouter / OpenAI / Anthropic / …)
- API hubs (RapidAPI, etc.)
- Any REST API where you want to protect keys and control access

## Quick start

**Requires:** Python ≥ 3.11, [uv](https://github.com/astral-sh/uv)

```bash
git clone https://github.com/<your-user>/python-api-router.git
cd python-api-router
uv sync

# Set up config
cp config.example.yaml config.yaml
cp .env.example .env
# Edit .env with your real API keys
# Edit config.yaml with your targets/clients

# Run
uv run fastapi dev api_router/main.py --host 0.0.0.0 --port 8787
```

Check it works:
- Health: http://127.0.0.1:8787/health
- Docs: http://127.0.0.1:8787/docs

## How it works

### Two kinds of keys

| Key | Who has it | Where it lives |
|-----|-----------|----------------|
| **clientKey** | Your app / browser | `config.yaml` → `clients` section |
| **upstream key** | Only the server | `.env` file (never committed) |

### Config structure (`config.yaml`)

```yaml
# 1) Where can the proxy forward to?
targets:
  openrouter:
    baseUrl: https://openrouter.ai/api/v1
    defaultHeaders:
      Content-Type: "application/json; charset=utf-8"

# 2) Secret keys (resolved from env vars)
secrets:
  or_rk1: "Bearer ${OPENROUTER_KEY_RK1}"

# 3) Who can use the proxy, and what can they do?
clients:
  rk-robot-1:
    target: openrouter
    authHeaderRef: or_rk1
    allowedMethods: [POST]
    allowedPaths:
      - /chat/completions
    timeoutMs: 60000
```

### Request format

```bash
curl -X POST http://127.0.0.1:8787/proxy \
  -H "Authorization: Bearer rk-robot-1" \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{
    "method": "POST",
    "path": "/chat/completions",
    "body": {
      "model": "anthropic/claude-opus-4-5",
      "messages": [{"role": "user", "content": "Hello!"}]
    }
  }'
```

### PowerShell

```powershell
$body = @{
  method = "POST"
  path   = "/chat/completions"
  body   = @{
    model    = "google/gemini-3-pro-preview"
    messages = @(@{ role="user"; content="Hello!" })
    stream   = $false
  }
} | ConvertTo-Json -Depth 10

$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)

Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8787/proxy" `
  -Headers @{ Authorization = "Bearer rk-robot-1" } `
  -ContentType "application/json; charset=utf-8" `
  -Body $bodyBytes
```

## Project structure

```
api_router/
  main.py                    # FastAPI routes (edge layer)
  composition/
    startup.py               # Wires modules together (no logic)
  modules/
    config.py                # Config loading (YAML, env expansion)
    proxy.py                 # Proxy logic (auth, policy, upstream)
```

Architecture: [Pragmatic Modular Monolith](https://github.com/r-/pragmatic-modular-monolith)

## License

MIT

