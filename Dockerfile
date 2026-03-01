FROM node:20-alpine

RUN apk add --no-cache curl

WORKDIR /app

# Install from npm - pin to specific version for reproducibility
ARG VERSION=1.0.4
RUN npm install @node2flow/telegram-bot-mcp@${VERSION}

# Non-root user
RUN addgroup -g 1000 appuser && \
    adduser -D -s /bin/sh -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV TELEGRAM_BOT_TOKEN="" \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/mcp || exit 1

CMD ["npx", "@node2flow/telegram-bot-mcp", "--http"]
