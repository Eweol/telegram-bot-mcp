# telegram-bot-mcp

Docker image wrapping [@node2flow/telegram-bot-mcp](https://github.com/node2flow-th/telegram-bot-mcp-community) for deployment in the Unimain k8s cluster.

## Build

CI pipeline builds multi-arch (amd64 + arm64) images and pushes to `harbor.unimain.de/unimain/telegram-bot-mcp`.

## Deployment

See `k8s-iac/unimain-de/telegram-bot-mcp/` for Terragrunt configuration.
