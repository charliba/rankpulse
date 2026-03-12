"""AI Router — Multi-provider text & image generation dispatcher.

Routes generation requests to the configured AI provider (OpenAI, Gemini,
Anthropic, Grok) based on project-level AIProvider settings.

Usage:
    from apps.core.ai_router import AIRouter

    router = AIRouter(project)
    text = router.generate_text("Write a tagline for a beauty clinic")
    image_bytes = router.generate_image("Professional beauty clinic photo")
"""
from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from apps.core.models import AIProvider, Project

logger = logging.getLogger("ai_router")


# ── Provider Adapters ────────────────────────────────────────────

class _OpenAIAdapter:
    """OpenAI adapter (GPT-4, GPT-4o, etc.)."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, system: str = "",
                      temperature: float = 0.7, max_tokens: int = 4096) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes | None:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        resp = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1,
            response_format="b64_json",
        )
        import base64
        b64 = resp.data[0].b64_json
        if b64:
            return base64.b64decode(b64)
        return None


class _GeminiAdapter:
    """Google Gemini adapter (text + image generation)."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, system: str = "",
                      temperature: float = 0.7, max_tokens: int = 4096) -> str:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        if system:
            config.system_instruction = system
        resp = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return resp.text or ""

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes | None:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=self.api_key)
        resp = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
        if resp.candidates:
            for part in resp.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    return part.inline_data.data
        return None


class _AnthropicAdapter:
    """Anthropic Claude adapter — text only (Futuro: image)."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, system: str = "",
                      temperature: float = 0.7, max_tokens: int = 4096) -> str:
        import httpx
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=body, timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("content", [{}])[0].get("text", "")

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes | None:
        logger.warning("Anthropic image generation not supported yet")
        return None


class _GrokAdapter:
    """xAI Grok adapter — OpenAI-compatible endpoint."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate_text(self, prompt: str, system: str = "",
                      temperature: float = 0.7, max_tokens: int = 4096) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key, base_url="https://api.x.ai/v1")
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    def generate_image(self, prompt: str, size: str = "1024x1024") -> bytes | None:
        logger.warning("Grok image generation not supported yet")
        return None


# ── Adapter Factory ──────────────────────────────────────────────

_ADAPTERS = {
    "openai": _OpenAIAdapter,
    "google": _GeminiAdapter,
    "anthropic": _AnthropicAdapter,
    "xai": _GrokAdapter,
}


def _get_adapter(provider_name: str, api_key: str, model: str):
    """Build the appropriate adapter for a provider/model combination."""
    cls = _ADAPTERS.get(provider_name)
    if not cls:
        raise ValueError(f"Unknown provider: {provider_name}")
    return cls(api_key=api_key, model=model)


# ── Main Router ──────────────────────────────────────────────────

class AIRouter:
    """Multi-provider AI generation router for a project."""

    def __init__(self, project: "Project"):
        self.project = project

    def _get_text_provider(self, provider_id: int | None = None) -> "AIProvider":
        """Get the text generation provider (explicit or project default)."""
        from apps.core.models import AIProvider
        if provider_id:
            return AIProvider.objects.get(pk=provider_id, project=self.project, is_active=True)
        # Project default
        prov = AIProvider.objects.filter(
            project=self.project, is_default_text=True, is_active=True,
        ).exclude(text_model="").first()
        if prov:
            return prov
        # Fallback: any active provider with text_model set
        prov = AIProvider.objects.filter(
            project=self.project, is_active=True,
        ).exclude(text_model="").first()
        if prov:
            return prov
        # Last resort: use global OpenAI key from settings
        if settings.OPENAI_API_KEY:
            dummy = AIProvider(
                provider="openai",
                text_model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
            )
            return dummy
        raise ValueError(f"No AI provider configured for project '{self.project.name}'")

    def _get_image_provider(self, provider_id: int | None = None) -> "AIProvider":
        """Get the image generation provider (explicit or project default)."""
        from apps.core.models import AIProvider
        if provider_id:
            return AIProvider.objects.get(pk=provider_id, project=self.project, is_active=True)
        prov = AIProvider.objects.filter(
            project=self.project, is_default_image=True, is_active=True,
        ).exclude(image_model="").first()
        if prov:
            return prov
        # Fallback: any provider with image_model set
        prov = AIProvider.objects.filter(
            project=self.project, is_active=True,
        ).exclude(image_model="").first()
        if prov:
            return prov
        # Fallback: Gemini from settings
        if settings.GEMINI_API_KEY:
            dummy = AIProvider(
                provider="google",
                image_model="gemini-2.5-flash-image",
                api_key=settings.GEMINI_API_KEY,
            )
            return dummy
        # Fallback: OpenAI DALL-E
        if settings.OPENAI_API_KEY:
            dummy = AIProvider(
                provider="openai",
                image_model="dall-e-3",
                api_key=settings.OPENAI_API_KEY,
            )
            return dummy
        raise ValueError(f"No image AI provider configured for project '{self.project.name}'")

    # ── Public API ───────────────────────────────────────────

    def generate_text(self, prompt: str, system: str = "",
                      temperature: float = 0.7, max_tokens: int = 4096,
                      provider_id: int | None = None) -> str:
        """Generate text using the project's configured AI provider."""
        prov = self._get_text_provider(provider_id)
        adapter = _get_adapter(prov.provider, prov.api_key, prov.text_model)
        logger.info("Generating text via %s/%s for project %s",
                     prov.provider, prov.text_model, self.project.name)
        return adapter.generate_text(prompt, system, temperature, max_tokens)

    def generate_image(self, prompt: str, size: str = "1024x1024",
                       provider_id: int | None = None) -> bytes | None:
        """Generate image using the project's configured AI provider."""
        prov = self._get_image_provider(provider_id)
        adapter = _get_adapter(prov.provider, prov.api_key, prov.image_model)
        logger.info("Generating image via %s/%s for project %s",
                     prov.provider, prov.image_model, self.project.name)
        return adapter.generate_image(prompt, size)

    def generate_text_json(self, prompt: str, system: str = "",
                           temperature: float = 0.7,
                           provider_id: int | None = None) -> dict | list:
        """Generate text and parse as JSON (with fallback extraction)."""
        raw = self.generate_text(prompt, system, temperature, provider_id=provider_id)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks or raw text
            match = re.search(r'[\[{].*[}\]]', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
        logger.warning("Failed to parse AI response as JSON")
        return {}

    @staticmethod
    def test_connection(provider: str, api_key: str, model: str) -> dict:
        """Test an AI provider connection. Returns {"ok": bool, "error": str}."""
        adapter = _get_adapter(provider, api_key, model)
        try:
            result = adapter.generate_text("Say 'OK' in one word.", max_tokens=10)
            return {"ok": bool(result.strip()), "response": result.strip()[:50]}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}
