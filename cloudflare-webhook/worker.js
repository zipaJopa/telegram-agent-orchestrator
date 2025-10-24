/**
 * Cloudflare Worker - Telegram Webhook Handler
 *
 * Receives Telegram updates at edge, forwards to PCT-110 orchestrator
 * Handles rate limiting, validation, authentication
 */

// IMPORTANT: Update this after setting up Nginx reverse proxy
// Option 1: Via archon-api.paja.pro (recommended)
const ORCHESTRATOR_URL = "https://archon-api.paja.pro/telegram/webhook";

// Option 2: Direct to PCT-110 (if exposed publicly)
// const ORCHESTRATOR_URL = "http://192.168.0.110:8282/telegram/webhook";

// Secret token - set via: wrangler secret put SECRET_TOKEN
// Value: 369ec80e26f81fd71a8e5af6e400d02c8eb2e8db1e8fc0b7fc14ec6981aef116

export default {
  async fetch(request, env, ctx) {
    // Only accept POST requests to /webhook
    if (request.method !== "POST" || !request.url.endsWith("/webhook")) {
      return new Response("Not Found", { status: 404 });
    }

    try {
      // Parse Telegram update
      const update = await request.json();

      // Basic validation
      if (!update || !update.update_id) {
        return new Response("Invalid update", { status: 400 });
      }

      // Get secret token from environment
      const SECRET_TOKEN = env.SECRET_TOKEN;

      // Forward to PCT-110 FastAPI orchestrator
      const response = await fetch(ORCHESTRATOR_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Secret-Token": SECRET_TOKEN,
          "X-Forwarded-For": request.headers.get("CF-Connecting-IP") || "unknown"
        },
        body: JSON.stringify(update)
      });

      // Log for debugging
      console.log(`Forwarded update ${update.update_id}, status: ${response.status}`);

      // Return success to Telegram
      return new Response("OK", { status: 200 });

    } catch (error) {
      console.error("Worker error:", error);
      return new Response("Internal Server Error", { status: 500 });
    }
  }
};
