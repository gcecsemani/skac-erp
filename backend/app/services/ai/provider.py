"""Provider-agnostic LLM client. Works with free tiers; degrades gracefully.

Supported providers (selected via AI_PROVIDER env):
  - "gemini": Google Generative Language API (free tier: gemini-flash-latest)
  - "groq":   Groq OpenAI-compatible API (free tier: llama-3.1-8b-instant)
  - "none":   no external calls; the assistant falls back to a heuristic router.

The provider only ever returns text. It never touches the database and never
produces SQL that is executed — see app.services.ai.assistant for how output
is constrained to the vetted tool registry.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


class LLMProvider:
    def available(self) -> bool:  # pragma: no cover - trivial
        return False

    def generate(self, prompt: str, *, temperature: float = 0.1) -> str | None:
        raise NotImplementedError


class NoneProvider(LLMProvider):
    def available(self) -> bool:
        return False

    def generate(self, prompt: str, *, temperature: float = 0.1) -> str | None:
        return None


def _gemini_text(data: dict) -> str | None:
    candidates = data.get("candidates") or []
    if not candidates:
        return None
    parts = (candidates[0].get("content") or {}).get("parts") or []
    for part in parts:
        text = part.get("text")
        if text:
            return text
    return None


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model or "gemini-flash-latest"

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, *, temperature: float = 0.1) -> str | None:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        try:
            resp = httpx.post(
                url, params={"key": self.api_key}, json=payload, timeout=30
            )
            if not resp.is_success:
                log.warning("Gemini %s returned %s: %s", self.model, resp.status_code, resp.text[:300])
                return None
            return _gemini_text(resp.json())
        except Exception:
            log.exception("Gemini request failed")
            return None


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model or "llama-3.1-8b-instant"

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, *, temperature: float = 0.1) -> str | None:
        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            return None


def get_provider() -> LLMProvider:
    provider = (settings.ai_provider or "none").lower()
    if provider == "gemini":
        return GeminiProvider(settings.ai_api_key, settings.ai_model)
    if provider == "groq":
        return GroqProvider(settings.ai_api_key, settings.ai_model)
    return NoneProvider()
