# Deployment Status

## ✅ Phase 1: COMPLETE

### PCT-110 FastAPI Orchestrator - DEPLOYED
- **URL**: http://192.168.0.110:8282
- **Container**: `pavle-telegram-orchestrator`
- **Status**: Running and healthy
- **Features**:
  - Smart model router (52 free models discovered)
  - Session management (per-user state)
  - OpenRouter client (400+ models)
  - Commands: /start, /models, /model, /cwd, /reset

### Test Results
```bash
# Health check
$ curl http://192.168.0.110:8282/health
{"status":"healthy","service":"telegram-orchestrator"}

# Free models sync
$ docker compose exec telegram-orchestrator python3 scripts/sync_free_models.py
✅ Found 52 free models
```

### Database Initialized
- Location: `/root/telegram-agent-orchestrator/data/models.db`
- Tables: `models`, `free_models`
- Default models: DeepSeek R1, Gemini 2.0 Flash, Hermes 3 405B

---

## 🔄 Phase 2: NEXT STEPS

### 1. Deploy Cloudflare Worker (5 minutes)

```bash
cd ~/telegram-agent-orchestrator/cloudflare-webhook

# Install Wrangler (if not installed)
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Set secret token (must match PCT-110)
wrangler secret put SECRET_TOKEN
# Enter: your_secret_here (generate one!)

# Deploy worker
wrangler deploy

# Note the URL (example):
# https://pavle-telegram-webhook.yourbow.workers.dev
```

### 2. Update Worker with PCT-110 Endpoint

Edit `cloudflare-webhook/worker.js`:
```javascript
const ORCHESTRATOR_URL = "http://192.168.0.110:8282/telegram/webhook";
```

**IMPORTANT**: PCT-110:8282 must be accessible from Cloudflare!

Options:
- **A**: Expose via Nginx reverse proxy at `https://archon-api.paja.pro/telegram/webhook`
- **B**: Use Tailscale Funnel to expose PCT-110 publicly
- **C**: Use Cloudflare Tunnel

**Recommended**: Option A (Nginx on existing domain)

### 3. Set Up Nginx Reverse Proxy (if using Option A)

On your existing Nginx server (wherever `archon-api.paja.pro` is hosted):

```nginx
location /telegram/ {
    proxy_pass http://192.168.0.110:8282/telegram/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

Test:
```bash
curl https://archon-api.paja.pro/health
```

### 4. Update Cloudflare Worker (if using Nginx)

```javascript
const ORCHESTRATOR_URL = "https://archon-api.paja.pro/telegram/webhook";
```

Redeploy:
```bash
wrangler deploy
```

### 5. Set Telegram Webhook

```bash
TOKEN="your_telegram_bot_token"  # From .env or @BotFather
WEBHOOK_URL="https://pavle-telegram-webhook.yourbow.workers.dev/webhook"

curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=${WEBHOOK_URL}"
```

Verify:
```bash
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

Should show:
- `url`: Your Cloudflare Worker URL
- `has_custom_certificate`: false
- `pending_update_count`: 0

### 6. Test End-to-End

Send message to your Telegram bot:
```
/start
```

Expected flow:
1. Telegram → Cloudflare Worker (edge)
2. CF Worker → `https://archon-api.paja.pro/telegram/webhook`
3. Nginx → PCT-110:8282
4. FastAPI processes → OpenRouter API
5. Response → Telegram

Check logs:
```bash
# Cloudflare Worker logs
wrangler tail

# PCT-110 orchestrator logs
ssh root@192.168.0.110 "cd /root/telegram-agent-orchestrator && docker compose logs -f"
```

---

## 🚀 Phase 3: AUTOMATION (Future)

### Daily Cron Job (PCT-110)

```bash
ssh root@192.168.0.110
crontab -e

# Add line:
0 6 * * * cd /root/telegram-agent-orchestrator && docker compose exec -T telegram-orchestrator python3 scripts/sync_free_models.py >> /var/log/telegram-sync.log 2>&1
```

### Archon MCP Integration

```python
# app/commands/archon.py
from archon_mcp_client import ArchonClient

archon = ArchonClient("http://192.168.0.110:8051/mcp")

async def cmd_gam(user_id, chat_id, query):
    results = await archon.rag_search_knowledge_base(query, source_id="gam_docs")
    # Send to Telegram
```

### Skyvern Integration

```python
# app/commands/browse.py
from skyvern_client import SkyvernClient

skyvern = SkyvernClient("http://192.168.0.107:8000")

async def cmd_browse(user_id, chat_id, url, task):
    session = await skyvern.navigate(url, task)
    # Return session replay URL
```

---

## 📊 Current Status

| Component | Status | URL |
|-----------|--------|-----|
| PCT-110 Orchestrator | ✅ Running | http://192.168.0.110:8282 |
| Cloudflare Worker | ⏳ Pending | - |
| Telegram Webhook | ⏳ Pending | - |
| Nginx Proxy | ⏳ Pending | https://archon-api.paja.pro |
| Archon MCP | ⏳ Future | http://192.168.0.110:8051 |
| Skyvern MCP | ⏳ Future | http://192.168.0.107:8000 |

---

## 🔍 Troubleshooting

**Bot not responding?**
1. Check webhook: `curl https://api.telegram.org/bot$TOKEN/getWebhookInfo`
2. Check CF Worker logs: `wrangler tail`
3. Check PCT-110 logs: `docker compose logs -f`

**Models not working?**
1. Verify free models: `docker compose exec telegram-orchestrator python3 scripts/sync_free_models.py`
2. Check database: `sqlite3 data/models.db "SELECT * FROM free_models LIMIT 10;"`

**Session issues?**
1. Sessions stored in `data/sessions/{user_id}.json`
2. Reset: `rm data/sessions/*.json`
3. Or use `/reset` command in Telegram

---

## 📦 Repository

**GitHub**: https://github.com/zipaJopa/telegram-agent-orchestrator

**Quick update**:
```bash
ssh root@192.168.0.110
cd /root/telegram-agent-orchestrator
git pull
docker compose up --build -d
```
