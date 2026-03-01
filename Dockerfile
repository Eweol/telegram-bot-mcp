FROM node:20-alpine

RUN apk add --no-cache curl

WORKDIR /app

# Install from npm - pin to specific version for reproducibility
ARG VERSION=1.0.4
RUN npm install @node2flow/telegram-bot-mcp@${VERSION}

# node:20-alpine already has a 'node' user (uid/gid 1000)
RUN chown -R node:node /app

USER node

ENV TELEGRAM_BOT_TOKEN="" \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/mcp || exit 1

CMD ["npx", "@node2flow/telegram-bot-mcp", "--http"]
