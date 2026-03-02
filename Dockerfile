# syntax=docker/dockerfile:1
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/

# Non-root user for security
RUN useradd -r -u 1000 -g users mcp
USER mcp

ENV TELEGRAM_BOT_TOKEN="" \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('localhost', 8000)); s.close()"

CMD ["python", "-m", "telegram_bot_mcp", "--transport", "streamable-http", "--port", "8000"]
