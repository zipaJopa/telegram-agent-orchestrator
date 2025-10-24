# Cloudflare Worker Deployment

## Prerequisites

You need your **Cloudflare Global API Key** from:
https://dash.cloudflare.com/profile/api-tokens

## Step 1: Set Environment Variables

```powershell
# Your Cloudflare credentials
$env:CLOUDFLARE_API_KEY = "your_global_api_key_here"
$env:CLOUDFLARE_EMAIL = "pavlebradic@gmail.com"  # Your CF account email

# Or in Git Bash:
export CLOUDFLARE_API_KEY="your_global_api_key_here"
export CLOUDFLARE_EMAIL="pavlebradic@gmail.com"
```

## Step 2: Deploy Worker

```bash
cd ~/telegram-agent-orchestrator/cloudflare-webhook

# Deploy to Cloudflare
wrangler deploy

# You should see:
# ✨ Uploaded pavle-telegram-webhook (x.xx sec)
# ✨ Deployed pavle-telegram-webhook
#    https://pavle-telegram-webhook.yourbow.workers.dev
```

## Step 3: Set Secret Token

```bash
# Set the secret (matches PCT-110 .env)
echo "369ec80e26f81fd71a8e5af6e400d02c8eb2e8db1e8fc0b7fc14ec6981aef116" | wrangler secret put SECRET_TOKEN

# Verify it's set
wrangler secret list
```

## Step 4: Test Worker

```bash
# Get the worker URL from deployment output
WORKER_URL="https://pavle-telegram-webhook.yourbow.workers.dev/webhook"

# Test with curl (should return 400 - invalid update)
curl -X POST $WORKER_URL \
  -H "Content-Type: application/json" \
  -d '{"test": "invalid"}'

# Should see: "Invalid update"
```

## Step 5: Set Telegram Webhook

**IMPORTANT**: First ensure Nginx reverse proxy is set up (see below)

```bash
TOKEN="8408316661:AAFUByKeL_QLQaV3_zUEB63BMY11tYPtsXE"
WORKER_URL="https://pavle-telegram-webhook.yourbow.workers.dev/webhook"

# Set webhook
curl -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -d "url=${WORKER_URL}"

# Verify
curl "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
```

---

## Nginx Reverse Proxy Setup (REQUIRED)

The worker needs to forward to `https://archon-api.paja.pro/telegram/webhook`

### Where is archon-api.paja.pro hosted?

Check your existing Nginx configs:
```bash
# On PCT-123 (nginx-proxy-manager)?
ssh root@192.168.0.123

# Or wherever paja.pro is hosted
grep -r "archon-api" /etc/nginx/
```

### Add this location block:

```nginx
# In your archon-api.paja.pro server block
location /telegram/ {
    proxy_pass http://192.168.0.110:8282/telegram/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Secret-Token $http_x_secret_token;
}

location /health {
    proxy_pass http://192.168.0.110:8282/health;
}
```

### Test Nginx:
```bash
# Test health endpoint
curl https://archon-api.paja.pro/health

# Should return:
# {"status":"healthy","service":"telegram-orchestrator"}
```

---

## Troubleshooting

**Worker deployment fails?**
```bash
# Check wrangler auth
wrangler whoami

# Re-authenticate with Global API Key
wrangler login --api-key
```

**Can't find archon-api.paja.pro?**
```bash
# Check DNS
dig archon-api.paja.pro

# If not set up yet, create it:
# - Point to your Nginx server IP
# - Add SSL cert (Let's Encrypt)
# - Add proxy rules above
```

**Worker forwards but no response?**
```bash
# Check worker logs
wrangler tail

# Check PCT-110 logs
ssh root@192.168.0.110 "cd /root/telegram-agent-orchestrator && docker compose logs -f"
```

---

## Next: Test End-to-End

Once everything is deployed:

1. Send `/start` to your Telegram bot
2. Watch the flow:
   - `wrangler tail` (Cloudflare logs)
   - `docker compose logs -f` (PCT-110 logs)
3. Bot should respond with welcome message!

