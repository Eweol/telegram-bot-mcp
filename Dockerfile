# syntax=docker/dockerfile:1
FROM node:20-alpine

RUN apk add --no-cache curl

WORKDIR /app

# Install from npm - pin to specific version for reproducibility
ARG VERSION=1.0.4
RUN npm install @node2flow/telegram-bot-mcp@${VERSION}

# Patch: replace GET /mcp SSE handler with 405 response.
# mcp-auth-proxy v2.5.3 panics when reverse-proxying SSE streams, which
# triggers transport.onclose and deletes the in-memory session. Returning
# 405 prevents Claude from opening an SSE channel at all, keeping sessions alive.
# See: https://git.unimain.de/Unimain/telegram-bot-mcp/issues/1
RUN <<JS node
const fs = require('fs');
const file = '/app/node_modules/@node2flow/telegram-bot-mcp/dist/index.js';
let c = fs.readFileSync(file, 'utf8');
c = c.replace(
  /app\.get\('\/mcp',[\s\S]*?\}\);/,
  "app.get('/mcp',(_r,s)=>{s.status(405).end();});"
);
fs.writeFileSync(file, c);
console.log('Patched: GET /mcp SSE handler replaced with 405');
JS

# node:20-alpine already has a 'node' user (uid/gid 1000)
RUN chown -R node:node /app

USER node

ENV TELEGRAM_BOT_TOKEN="" \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["npx", "@node2flow/telegram-bot-mcp", "--http"]
