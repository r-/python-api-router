# Architecture

This project follows the **Pragmatic Modular Monolith** architecture.

Full architecture document: [github.com/r-/pragmatic-modular-monolith](https://github.com/r-/pragmatic-modular-monolith)

## Project-specific layout

```
api_router/
  main.py                    # Edge layer (FastAPI routes, CORS, HTTP parsing)
  composition/
    startup.py               # Wires modules — no business logic
  modules/
    config.py                # Level 1: config loading (YAML, env expansion)
    proxy.py                 # Level 1: proxy logic (auth, policy, upstream)
```

All modules follow **Level 1** (single file, `__all__` + `_` prefix separation).

## Module dependency direction

```
main.py (edge)
    ↓
composition/startup.py (wiring)
    ↓
modules/proxy.py  →  modules/config.py (types only)
```

- `main.py` depends on `composition` + public API of `proxy`
- `composition` depends on public API of `config` + `proxy`
- `proxy` depends on public API of `config` (types: `ProxyConfig`, `ClientPolicy`, `TargetConfig`)
- `config` has no internal dependencies
