"""Auth provider selection based on environment variables.

Supported modes (checked in order):
  1. OIDC/JWT  — set OIDC_ISSUER (and optionally OIDC_AUDIENCE)
  2. Bearer    — set AUTH_TOKEN
  3. None      — no auth (local dev / stdio)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def create_auth() -> object | None:
    """Return a FastMCP-compatible auth provider or None for open access."""

    oidc_issuer = os.getenv("OIDC_ISSUER", "").rstrip("/")
    if oidc_issuer:
        try:
            from fastmcp.server.auth import JWTVerifier  # type: ignore[import]
        except ImportError:
            logger.error(
                "OIDC_ISSUER is set but fastmcp.server.auth.JWTVerifier is not "
                "available in the installed fastmcp version. Falling back to no auth."
            )
            return None

        # Allow explicit JWKS URI override; default: {issuer}/jwks/
        jwks_uri = os.getenv("OIDC_JWKS_URI") or f"{oidc_issuer}/jwks/"
        audience = os.getenv("OIDC_AUDIENCE", "telegram-bot-mcp")

        logger.info(
            "Auth: JWT/OIDC — issuer=%s  jwks=%s  audience=%s",
            oidc_issuer,
            jwks_uri,
            audience,
        )
        return JWTVerifier(jwks_uri=jwks_uri, issuer=oidc_issuer, audience=audience)

    auth_token = os.getenv("AUTH_TOKEN", "")
    if auth_token:
        try:
            from fastmcp.server.auth import BearerAuthProvider  # type: ignore[import]

            logger.info("Auth: static bearer token")
            return BearerAuthProvider(token=auth_token)
        except ImportError:
            pass

        # Fallback: implement a minimal ASGI middleware-compatible shim.
        # FastMCP will receive the requests; a separate Starlette middleware
        # (added in __main__) validates the token before requests reach FastMCP.
        logger.info("Auth: static bearer token (middleware mode)")
        return _make_bearer_middleware(auth_token)

    logger.warning("Auth: DISABLED — set OIDC_ISSUER or AUTH_TOKEN for production")
    return None


def _make_bearer_middleware(expected_token: str):
    """Return a callable that wraps an ASGI app with static token validation."""

    class _BearerMiddleware:
        """Very small ASGI middleware for static bearer-token auth."""

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

    # Return the class itself; __main__ wraps the ASGI app with it.
    return _BearerMiddleware
