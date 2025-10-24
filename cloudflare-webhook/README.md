# Cloudflare Worker - Telegram Webhook

## Deployment

```bash
cd cloudflare-webhook

# Install Wrangler CLI
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Set secret token (same as PCT-110)
wrangler secret put SECRET_TOKEN

# Deploy
wrangler deploy

# Get webhook URL (example: https://pavle-telegram-webhook.yourbow.workers.dev/webhook)
```

## Set Telegram Webhook

```bash
TOKEN="8408316661:AAFUByKeL_QLQaV3_zUEB63BMY11tYPtsXE"
WEBHOOK_URL="https://pavle-telegram-webhook.yourbow.workers.dev/webhook"

curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}"
```

## Verify Webhook

```bash
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

## Architecture

```
Telegram API → Cloudflare Worker (Global Edge)
                      ↓
              archon-api.paja.pro/telegram/webhook
                      ↓
           PCT-110 FastAPI Orchestrator
                      ↓
         OpenRouter / Archon MCP / Skyvern
```

## Benefits

- **Global edge**: Low latency from anywhere
- **No cold starts**: Always-on webhook receiver
- **Free tier**: 100k requests/day
- **Stateless**: Just forwards to PCT-110
- **Simple**: ~50 lines of code
