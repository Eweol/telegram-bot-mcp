"""Auth provider selection based on environment variables.

Supported modes (checked in order):
  1. OIDC Proxy — OIDC_DISCOVERY_URL + OIDC_CLIENT_ID + OIDC_CLIENT_SECRET + BASE_URL
                  Full OAuth2/OIDC flow; works with Authentik, Keycloak, Auth0, etc.
  2. Bearer     — AUTH_TOKEN (static token, for simple deployments or testing)
  3. None       — no auth (local dev / stdio transport)

Notes:
  - JWT_SIGNING_KEY (optional): stable key for OIDCProxy; if unset a random key is
    generated per startup (clients must re-authenticate after server restart).
  - SESSION_LIFETIME_HOURS (optional): session duration in hours (default: 8).
    After a single OAuth login the session stays valid for this long without
    re-authenticating, regardless of the upstream provider's token expiry.
"""

from __future__ import annotations

import logging
import os
import time

logger = logging.getLogger(__name__)

# Default session lifetime: 8 hours (like mcp-auth-proxy)
_DEFAULT_SESSION_HOURS = 8


def _make_session_oidc_proxy(
    discovery_url: str,
    client_id: str,
    client_secret: str,
    base_url: str,
    jwt_signing_key: str | bytes | None,
    session_lifetime: int,
) -> object:
    """Return a SessionOIDCProxy — long-lived sessions, no per-request JWKS re-validation."""
    from fastmcp.server.auth import OIDCProxy  # type: ignore[import]
    from fastmcp.server.auth.oauth_proxy.proxy import ClientCode  # type: ignore[import]
    from mcp.server.auth.provider import AccessToken  # type: ignore[import]

    class SessionOIDCProxy(OIDCProxy):  # type: ignore[misc]
        """OIDCProxy variant that behaves like mcp-auth-proxy sessions.

        Key differences from plain OIDCProxy:
        - Session lifetime is SESSION_LIFETIME seconds (default 8 h), independent
          of the upstream provider's access token expiry (e.g. Authentik's 5 min).
        - Per-request token validation only checks the local session store (FastMCP
          JWT + JTI mapping). The upstream token is NOT re-validated via JWKS on
          every request, avoiding frequent re-auth interruptions.
        """

        _session_lifetime: int = session_lifetime

        async def exchange_authorization_code(self, client: object, authorization_code: object) -> object:  # type: ignore[override]
            """Patch upstream expires_in → session_lifetime before super() processes it."""
            code_model: ClientCode | None = await self._code_store.get(key=authorization_code.code)  # type: ignore[attr-defined]
            if code_model is not None:
                patched_tokens = {**code_model.idp_tokens, "expires_in": self._session_lifetime}
                patched_code = code_model.model_copy(update={"idp_tokens": patched_tokens})
                remaining = max(1, int(code_model.expires_at - time.time()))
                await self._code_store.put(key=authorization_code.code, value=patched_code, ttl=remaining)  # type: ignore[attr-defined]
            return await super().exchange_authorization_code(client, authorization_code)

        async def load_access_token(self, token: str) -> AccessToken | None:  # type: ignore[override]
            """Validate session via local store only — no upstream JWKS re-validation."""
            try:
                payload = self.jwt_issuer.verify_token(token)  # type: ignore[attr-defined]
                jti: str = payload["jti"]

                jti_mapping = await self._jti_mapping_store.get(key=jti)  # type: ignore[attr-defined]
                if not jti_mapping:
                    logger.debug("Session expired or not found (jti=%s...)", jti[:16])
                    return None

                upstream = await self._upstream_token_store.get(key=jti_mapping.upstream_token_id)  # type: ignore[attr-defined]
                if not upstream:
                    logger.debug("Upstream session data not found")
                    return None

                scopes = upstream.scope.split() if upstream.scope else []
                return AccessToken(
                    token=upstream.access_token,
                    client_id=upstream.client_id,
                    scopes=scopes,
                    expires_at=int(upstream.expires_at),
                )
            except Exception as e:
                logger.debug("Session validation failed: %s", e)
                return None

    logger.info(
        "Auth: SessionOIDCProxy — discovery=%s  base_url=%s  session=%dh",
        discovery_url,
        base_url,
        session_lifetime // 3600,
    )
    return SessionOIDCProxy(
        config_url=discovery_url,
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        jwt_signing_key=jwt_signing_key,
        allowed_client_redirect_uris=None,
    )


def create_auth() -> object | None:
    """Return a FastMCP-compatible auth provider or None for open access."""

    # --- Mode 1: OIDC Proxy ---
    discovery_url = os.getenv("OIDC_DISCOVERY_URL", "")
    client_id = os.getenv("OIDC_CLIENT_ID", "")
    client_secret = os.getenv("OIDC_CLIENT_SECRET", "")
    base_url = os.getenv("BASE_URL", "")

    if discovery_url and client_id and client_secret and base_url:
        jwt_signing_key: str | bytes | None = os.getenv("JWT_SIGNING_KEY") or None
        session_hours = int(os.getenv("SESSION_LIFETIME_HOURS", str(_DEFAULT_SESSION_HOURS)))
        session_lifetime = session_hours * 3600

        return _make_session_oidc_proxy(
            discovery_url=discovery_url,
            client_id=client_id,
            client_secret=client_secret,
            base_url=base_url,
            jwt_signing_key=jwt_signing_key,
            session_lifetime=session_lifetime,
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
