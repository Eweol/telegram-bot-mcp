# syntax=docker/dockerfile:1
FROM python:3.13-alpine

RUN apk upgrade --no-cache

WORKDIR /app

# Copy source and metadata together — hatchling needs src/ at build time
COPY pyproject.toml README.md ./
COPY src/ src/
# pip/setuptools are build-only: pip bundles stale vendored libs (urllib3, msgpack) that trigger scanner findings
RUN pip install --no-cache-dir . \
 && pip uninstall -y pip setuptools wheel

# Non-root user for security (home dir needed by OIDCProxy for session storage)
RUN adduser -D -u 1000 -G users mcp

# Persistent data directory for chat store
RUN mkdir -p /data && chown mcp:users /data

USER mcp

ENV TELEGRAM_BOT_TOKEN="" \
    PORT=8000 \
    CHAT_STORE_PATH=/data/chats.json

VOLUME /data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('localhost', 8000)); s.close()"

CMD ["python", "-m", "telegram_bot_mcp", "--transport", "streamable-http", "--port", "8000"]
