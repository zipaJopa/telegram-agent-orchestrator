"""
OpenRouter Client - Unified access to 400+ models
"""
import httpx
from typing import List, Dict, Optional, AsyncIterator
import json

class OpenRouterClient:
    """Client for OpenRouter API with free model support"""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key (optional for free models)"""
        self.api_key = api_key or "sk-or-v1-free"  # Free tier
        self.client = httpx.AsyncClient(timeout=120.0)

    async def get_models(self) -> List[Dict]:
        """Fetch all available models"""
        response = await self.client.get(
            f"{self.BASE_URL}/models",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        response.raise_for_status()
        return response.json()["data"]

    async def get_free_models(self) -> List[Dict]:
        """Get only free models (pricing.prompt == "0")"""
        models = await self.get_models()
        free_models = [
            m for m in models
            if (m.get("pricing", {}).get("prompt") == "0" or
                ":free" in m.get("id", ""))
        ]
        return free_models

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = True
    ) -> AsyncIterator[str]:
        """
        Send chat completion request

        Args:
            model: Model ID (e.g., "deepseek/deepseek-r1:free")
            messages: List of {"role": "user/assistant", "content": "..."}
            stream: Stream response chunks
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://archon.paja.pro",  # Required by OpenRouter
            "X-Title": "Pavle's Telegram Agent"
        }

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }

        if stream:
            async with self.client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        else:
            response = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            yield result["choices"][0]["message"]["content"]

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
