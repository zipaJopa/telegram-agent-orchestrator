#!/usr/bin/env python3
"""
Daily cron job - Scan OpenRouter for free models
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.openrouter import OpenRouterClient
from app.model_router import ModelRouter

async def sync_free_models():
    """Fetch and update free models list"""
    print("Syncing free models from OpenRouter...")

    client = OpenRouterClient()
    router = ModelRouter()

    try:
        # Get free models from OpenRouter
        free_models = await client.get_free_models()
        print(f"Found {len(free_models)} free models")

        # Extract model IDs
        model_ids = [m["id"] for m in free_models]

        # Update database
        router.update_free_models(model_ids)

        print("✅ Free models synced successfully")
        for model in free_models[:10]:  # Show first 10
            print(f"  • {model['id']}")

    except Exception as e:
        print(f"❌ Error syncing models: {e}")

    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(sync_free_models())
