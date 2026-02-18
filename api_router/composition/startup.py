"""Composition root — wires modules together.

This is the ONLY place that imports from module internals for instantiation.
Contains NO business logic.
"""

from api_router.modules.config import ProxyConfig, load_config
from api_router.modules.proxy import ProxyService


def create_proxy_service(config_path: str = "config.yaml") -> tuple[ProxyConfig, ProxyService]:
    """Create and wire the proxy service.

    Returns:
        Tuple of (config, proxy_service) ready to use.
    """
    config = load_config(config_path)
    proxy = ProxyService(config)
    return config, proxy
