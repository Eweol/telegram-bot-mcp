"""Auth provider selection based on environment variables.

Supported modes (checked in order):
  1. OIDC Proxy — OIDC_DISCOVERY_URL + OIDC_CLIENT_ID + OIDC_CLIENT_SECRET + BASE_URL
                  Full OAuth2/OIDC flow; works with Authentik, Keycloak, Auth0, etc.
  2. Bearer     — AUTH_TOKEN (static token, for simple deployments or testing)
  3. None       — no auth (local dev / stdio transport)

Notes:
  - JWT_SIGNING_KEY (optional): stable key for OIDCProxy; if unset a random key is
    generated per startup (clients must re-authenticate after server restart).
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def create_auth() -> object | None:
    """Return a FastMCP-compatible auth provider or None for open access."""

    # --- Mode 1: OIDC Proxy ---
    discovery_url = os.getenv("OIDC_DISCOVERY_URL", "")
    client_id = os.getenv("OIDC_CLIENT_ID", "")
    client_secret = os.getenv("OIDC_CLIENT_SECRET", "")
    base_url = os.getenv("BASE_URL", "")

    if discovery_url and client_id and client_secret and base_url:
        from fastmcp.server.auth import OIDCProxy  # type: ignore[import]

        jwt_signing_key: str | bytes | None = os.getenv("JWT_SIGNING_KEY") or None

        logger.info(
            "Auth: OIDCProxy — discovery=%s  base_url=%s",
            discovery_url,
            base_url,
        )
        return OIDCProxy(
            config_url=discovery_url,
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            jwt_signing_key=jwt_signing_key,
            allowed_client_redirect_uris=None,  # allow all (Claude Code loopback)
        )

    # --- Mode 2: Static Bearer Token ---
    auth_token = os.getenv("AUTH_TOKEN", "")
    if auth_token:
        try:
            from fastmcp.server.auth import StaticTokenVerifier  # type: ignore[import]

            logger.info("Auth: static bearer token")
            return StaticTokenVerifier(token=auth_token)
        except ImportError:
            logger.info("Auth: static bearer token (ASGI middleware fallback)")
            return _make_bearer_middleware(auth_token)

    logger.warning(
        "Auth: DISABLED — set OIDC_DISCOVERY_URL + OIDC_CLIENT_ID + "
        "OIDC_CLIENT_SECRET + BASE_URL (or AUTH_TOKEN) for production use"
    )
    return None


def _make_bearer_middleware(expected_token: str):
    """Minimal ASGI middleware for static bearer-token auth (fallback)."""

    class _BearerMiddleware:
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            if scope["type"] in ("http", "websocket"):
                headers = dict(scope.get("headers", []))
                auth = headers.get(b"authorization", b"").decode()
                if auth != f"Bearer {expected_token}":
                    from starlette.responses import JSONResponse

                    resp = JSONResponse(
                        {"error": "Unauthorized"},
                        status_code=401,
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                    await resp(scope, receive, send)
                    return
            await self.app(scope, receive, send)

    return _BearerMiddleware
