# Pavle's Telegram Agent Orchestrator

**Architecture**: Cloudflare Worker (edge) → FastAPI (PCT-110) → OpenRouter/Archon/Skyvern

## Quick Start

### 1. Deploy Cloudflare Worker

```bash
cd cloudflare-webhook
npm install -g wrangler
wrangler login
wrangler secret put SECRET_TOKEN  # Enter shared secret
wrangler deploy

# Get URL: https://pavle-telegram-webhook.yourbow.workers.dev/webhook
```

### 2. Set Telegram Webhook

```bash
TOKEN="8408316661:AAFUByKeL_QLQaV3_zUEB63BMY11tYPtsXE"
WEBHOOK_URL="https://pavle-telegram-webhook.yourbow.workers.dev/webhook"

curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" -d "url=${WEBHOOK_URL}"
```

### 3. Deploy PCT-110 Orchestrator

```bash
# On PCT-110
cd /root
git clone <this-repo> telegram-agent-orchestrator
cd telegram-agent-orchestrator

# Set secret token (same as Cloudflare)
echo "SECRET_TOKEN=your_secret_here" > .env

# Deploy
docker compose up --build -d

# Check logs
docker compose logs -f
```

### 4. Expose via Nginx (archon-api.paja.pro)

```nginx
location /telegram/ {
    proxy_pass http://192.168.0.110:8282/telegram/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Architecture

```
┌─────────────────┐
│  Telegram API   │
└────────┬────────┘
         │ Webhook
         ▼
┌─────────────────────────┐
│  Cloudflare Worker      │  ← Global Edge
│  (Edge, 100k req/day)   │
└────────┬────────────────┘
         │ HTTP POST
         ▼
┌─────────────────────────┐
│  PCT-110 FastAPI        │  ← Proxmox LXC
│  Port 8282              │
│  - Model Router         │
│  - Session Manager      │
│  - Command Handlers     │
└────────┬────────────────┘
         │ MCP / HTTP
         ▼
┌─────────────────────────┐
│  Services               │
│  - OpenRouter (400+ LLM)│
│  - Archon MCP (8051)    │
│  - Skyvern (PCT-107)    │
└─────────────────────────┘
```

## Features

### ✅ Phase 1 (Current)
- Cloudflare webhook receiver (edge)
- FastAPI orchestrator on PCT-110
- Smart model router with free models
- Session management (per-user state)
- Basic commands: /start, /models, /model, /cwd, /reset

### 🔄 Phase 2 (Next)
- Daily free model scanner
- LLM leaderboard sync
- Archon MCP integration (/gam, /task, /project)
- Skyvern integration (/browse, /scrape)

### 🚀 Phase 3 (Future)
- Proactive monitoring
- Email intelligence
- Schedule awareness
- Multi-agent coordination

## Commands

```
/start       - Welcome & status
/models      - List available models
/model <id>  - Switch model
/cwd <path>  - Set working directory
/reset       - Clear conversation

# Coming soon:
/gam <query> - Search GAM/YourBow docs
/task [id]   - Get current/specific task
/browse <url> - Skyvern automation
```

## Daily Automation

```bash
# Add to crontab on PCT-110
0 6 * * * cd /root/telegram-agent-orchestrator && python3 scripts/sync_free_models.py
```

## Monitoring

```bash
# Health check
curl http://192.168.0.110:8282/health

# Logs
docker compose logs -f telegram-orchestrator

# Webhook status
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

## Development

```bash
# Local testing (without Cloudflare)
export TELEGRAM_TOKEN="..."
export SECRET_TOKEN="test123"
uvicorn app.webhook:app --reload

# Test endpoint directly
curl -X POST http://localhost:8000/telegram/webhook \
  -H "X-Secret-Token: test123" \
  -H "Content-Type: application/json" \
  -d '{"message": {"from": {"id": 123}, "chat": {"id": 123}, "text": "/start"}}'
```

## Troubleshooting

**Bot not responding?**
1. Check Cloudflare Worker logs: `wrangler tail`
2. Check PCT-110 logs: `docker compose logs -f`
3. Verify webhook: `curl https://api.telegram.org/bot$TOKEN/getWebhookInfo`

**Model errors?**
1. Check free models: `curl http://localhost:8282/health`
2. Run sync: `docker compose exec telegram-orchestrator python3 scripts/sync_free_models.py`

**Session issues?**
1. Sessions stored in `./data/sessions/{user_id}.json`
2. Reset: Delete session file and /reset in Telegram
