# telegram-bot-mcp

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes the [Telegram Bot API](https://core.telegram.org/bots/api) as tools — letting Claude and other MCP clients send messages, photos, polls and more via a Telegram bot.

Built with [FastMCP](https://github.com/jlowin/fastmcp) (Python). No external auth proxy required — OIDC/JWT authentication is built in.

## Features

- **Tools**: `get_me`, `list_chats`, `send_message`, `send_photo`, `send_document`, `send_location`, `send_poll`, `edit_message_text`, `delete_message`, `get_chat`, `get_chat_member_count`
- **Three auth modes**: stdio (no auth), static Bearer token, full OIDC OAuth2 proxy (e.g. Authentik, Keycloak)
- **Transports**: stdio (Claude Desktop) + Streamable HTTP (remote/K8s)
- **Multi-arch Docker image**: linux/amd64 + linux/arm64

## Quick Start

### stdio (Claude Desktop / local)

```bash
pip install .
export TELEGRAM_BOT_TOKEN=your_token_here
python -m telegram_bot_mcp
```

Add to Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "telegram": {
      "command": "python",
      "args": ["-m", "telegram_bot_mcp"],
      "env": {
        "TELEGRAM_BOT_TOKEN": "your_token_here"
      }
    }
  }
}
```

### Streamable HTTP (remote)

```bash
export TELEGRAM_BOT_TOKEN=your_token_here
export AUTH_TOKEN=your_secret_bearer_token   # optional: require auth
python -m telegram_bot_mcp --transport streamable-http --port 8000
```

Connect from Claude Code:

```bash
claude mcp add telegram --transport http https://your-host:8000/mcp \
  --header "Authorization: Bearer your_secret_bearer_token"
```

### OIDC OAuth2 (production)

Full OAuth2 flow — the server acts as an OIDC proxy. Users authenticate via your identity provider (Authentik, Keycloak, Auth0, etc.) and receive a session that lasts `SESSION_LIFETIME_HOURS` (default: 8h).

```bash
export TELEGRAM_BOT_TOKEN=your_token_here
export OIDC_DISCOVERY_URL=https://auth.example.com/application/o/my-app/.well-known/openid-configuration
export OIDC_CLIENT_ID=your_client_id
export OIDC_CLIENT_SECRET=your_client_secret
export BASE_URL=https://telegram-bot-mcp.example.com
python -m telegram_bot_mcp --transport streamable-http --port 8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from [@BotFather](https://t.me/botfather) |
| `OIDC_DISCOVERY_URL` | No* | OIDC discovery URL — enables full OAuth2 proxy mode |
| `OIDC_CLIENT_ID` | No* | OAuth2 client ID |
| `OIDC_CLIENT_SECRET` | No* | OAuth2 client secret |
| `BASE_URL` | No* | Public base URL of this server (required for OAuth2 redirects) |
| `JWT_SIGNING_KEY` | No | Stable key for signing session JWTs; random per startup if unset |
| `SESSION_LIFETIME_HOURS` | No | Session duration in hours (default: `8`) |
| `AUTH_TOKEN` | No | Static Bearer token (simpler alternative to OIDC) |
| `KNOWN_CHATS` | No | Pre-configured chats: `Name=chat_id,Name2=chat_id2` |
| `CHAT_STORE_PATH` | No | Path for discovered-chat cache (default: `~/.local/share/fastmcp/chats.json`) |

\* All four OIDC variables must be set together to enable OAuth2 mode.

## Docker

```bash
docker run -p 8000:8000 \
  -e TELEGRAM_BOT_TOKEN=your_token_here \
  -v telegram-data:/data \
  ghcr.io/your-org/telegram-bot-mcp:latest
```

The named volume (`telegram-data:/data`) persists discovered chat IDs across container restarts.

Or use Docker Compose:

```bash
cp .env.example .env  # fill in your token
docker compose up -d
```

## License

MIT — see [LICENSE](LICENSE).
