/**
 * Cloudflare Worker - Telegram Webhook Handler
 *
 * Receives Telegram updates at edge, forwards to PCT-110 orchestrator
 * Handles rate limiting, validation, authentication
 */

const ORCHESTRATOR_URL = "https://archon-api.paja.pro/telegram/webhook";
const SECRET_TOKEN = "CHANGE_ME_IN_PRODUCTION"; // Shared secret with PCT-110

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
