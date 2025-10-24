"""
FastAPI Webhook Handler - Main orchestrator
"""
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import httpx
import os
from typing import Optional

from .session_manager import SessionManager
from .model_router import ModelRouter
from .models.openrouter import OpenRouterClient

# Initialize
app = FastAPI(title="Pavle's Telegram Agent Orchestrator")
session_manager = SessionManager()
model_router = ModelRouter()
openrouter = OpenRouterClient()

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable must be set")
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "CHANGE_ME_IN_PRODUCTION")


async def send_telegram_message(chat_id: int, text: str, parse_mode: str = "Markdown"):
    """Send message to Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        })


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_secret_token: Optional[str] = Header(None)
):
    """
    Main webhook endpoint - receives updates from Cloudflare Worker
    """
    # Verify secret token
    if x_secret_token != SECRET_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid secret token")

    # Parse update
    update = await request.json()

    # Extract message
    message = update.get("message")
    if not message or "text" not in message:
        return JSONResponse({"status": "ignored"})

    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]
    text = message["text"]

    # Handle commands
    if text.startswith("/"):
        await handle_command(user_id, chat_id, text)
    else:
        await handle_message(user_id, chat_id, text)

    return JSONResponse({"status": "ok"})


async def handle_command(user_id: int, chat_id: int, text: str):
    """Handle bot commands"""
    parts = text.split(maxsplit=1)
    command = parts[0][1:]  # Remove /
    args = parts[1] if len(parts) > 1 else ""

    if command == "start":
        session = session_manager.load_session(user_id)
        await send_telegram_message(chat_id, f"""
🤖 **Pavle's Telegram Coding Agent**

**Current setup:**
• Model: `{session.current_model}`
• Working dir: `{session.cwd}`

**Commands:**
/models - List available models
/model <name> - Switch model
/cwd <path> - Set working directory
/reset - Clear conversation

Just send me a message to start coding!
""")

    elif command == "models":
        models = model_router.list_available_models(free_only=True)
        text = "**Available FREE models:**\n\n"
        for m in models[:10]:
            text += f"• `{m['model_id']}`\n  {m['name']} ({m['context']} context, score: {m['score']})\n\n"
        await send_telegram_message(chat_id, text)

    elif command == "model":
        if not args:
            await send_telegram_message(chat_id, "Usage: /model <model_id>")
            return

        session = session_manager.update_model(user_id, args)
        await send_telegram_message(chat_id, f"✅ Switched to `{args}`\n\nConversation reset.")

    elif command == "cwd":
        if not args:
            session = session_manager.load_session(user_id)
            await send_telegram_message(chat_id, f"Current directory: `{session.cwd}`")
            return

        session = session_manager.update_cwd(user_id, args)
        await send_telegram_message(chat_id, f"✅ Working directory set to: `{args}`")

    elif command == "reset":
        session_manager.reset_conversation(user_id)
        await send_telegram_message(chat_id, "✅ Conversation cleared")

    else:
        await send_telegram_message(chat_id, f"Unknown command: /{command}")


async def handle_message(user_id: int, chat_id: int, text: str):
    """Handle regular messages - call LLM"""
    # Load session
    session = session_manager.load_session(user_id)

    # Add user message to history
    session_manager.add_message(user_id, "user", text)

    # Get conversation history
    messages = session.conversation_history

    # System prompt
    system_message = {
        "role": "system",
        "content": f"""You are Pavle's remote coding agent, accessed via Telegram.

Working directory: {session.cwd}

Keep responses concise and practical. Use code blocks with language tags.
When suggesting file changes, show exact diffs or complete updated files.
"""
    }

    # Prepend system message
    full_messages = [system_message] + messages

    # Call LLM (streaming)
    model = session.current_model

    try:
        # Send "typing" action
        response_text = ""
        message_id = None

        async for chunk in openrouter.chat_completion(model, full_messages, stream=True):
            response_text += chunk

            # Update message every 50 chars
            if len(response_text) % 50 == 0:
                if message_id:
                    # Edit existing message
                    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
                    async with httpx.AsyncClient() as client:
                        await client.post(url, json={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "text": response_text[:4096],  # Telegram limit
                            "parse_mode": "Markdown"
                        })
                else:
                    # Send initial message
                    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    async with httpx.AsyncClient() as client:
                        result = await client.post(url, json={
                            "chat_id": chat_id,
                            "text": response_text[:4096],
                            "parse_mode": "Markdown"
                        })
                        data = result.json()
                        message_id = data.get("result", {}).get("message_id")

        # Final update
        if message_id:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
            async with httpx.AsyncClient() as client:
                await client.post(url, json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "text": response_text[:4096],
                    "parse_mode": "Markdown"
                })

        # Save assistant message
        session_manager.add_message(user_id, "assistant", response_text)

    except Exception as e:
        await send_telegram_message(chat_id, f"❌ Error: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "telegram-orchestrator"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Pavle's Telegram Agent Orchestrator",
        "endpoints": [
            "POST /telegram/webhook",
            "GET /health"
        ]
    }
