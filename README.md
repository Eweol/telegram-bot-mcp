# telegram-bot-mcp

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes the [Telegram Bot API](https://core.telegram.org/bots/api) as tools — letting Claude and other MCP clients send messages, photos, polls and more via a Telegram bot.

Built with [FastMCP](https://github.com/jlowin/fastmcp) (Python). No external auth proxy required — OIDC/JWT authentication is built in.

## Features

- **Phase 1 tools**: `get_me`, `send_message`, `send_photo`, `send_document`, `send_location`, `send_poll`, `edit_message_text`, `delete_message`, `get_chat`, `get_chat_member_count`
- **Three auth modes**: stdio (no auth), static Bearer token, OIDC/JWT (e.g. Authentik)
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

### OIDC/JWT (production)

```bash
export TELEGRAM_BOT_TOKEN=your_token_here
export OIDC_ISSUER=https://auth.example.com/application/o/my-app/
export OIDC_AUDIENCE=telegram-bot-mcp         # optional, default: telegram-bot-mcp
python -m telegram_bot_mcp --transport streamable-http --port 8000
```

The server validates Bearer tokens against the issuer's JWKS endpoint (`{OIDC_ISSUER}jwks/`).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from [@BotFather](https://t.me/botfather) |
| `OIDC_ISSUER` | No | OIDC issuer URL — enables JWT validation |
| `OIDC_JWKS_URI` | No | Override JWKS URI (default: `{OIDC_ISSUER}jwks/`) |
| `OIDC_AUDIENCE` | No | Expected JWT audience (default: `telegram-bot-mcp`) |
| `AUTH_TOKEN` | No | Static Bearer token (simpler alternative to OIDC) |

## Docker

```bash
docker run -e TELEGRAM_BOT_TOKEN=... \
  harbor.unimain.de/unimain/telegram-bot-mcp:1.0.0.0 \
  python -m telegram_bot_mcp --transport streamable-http --port 8000
```

## License

MIT — see [LICENSE](LICENSE).
