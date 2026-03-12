"""Social Content Generator — BestContent-style AI post generation for RankPulse.

Uses AIRouter (multi-provider) + BrandProfile to generate social media posts
with copy, hashtags, CTA, and optionally AI-generated images.

Usage:
    from apps.content.social_generator import SocialContentGenerator
    gen = SocialContentGenerator(project)
    themes = gen.generate_themes(count=5, platforms=["instagram_feed"])
    post = gen.generate_post(theme="Dica de skincare", platform="instagram_feed")
    batch = gen.generate_batch(themes=[...], platform="instagram_feed")
"""
from __future__ import annotations

import json
import logging

from apps.core.ai_router import AIRouter
from apps.core.models import BrandProfile, Project

from .models import SocialPost

logger = logging.getLogger("social_generator")


class SocialContentGenerator:
    """Generate social media posts using AI + brand context."""

    def __init__(self, project: Project):
        self.project = project
        self.router = AIRouter(project)
        self._brand = None

    @property
    def brand(self) -> BrandProfile | None:
        if self._brand is None:
            try:
                self._brand = self.project.brand_profile
            except BrandProfile.DoesNotExist:
                self._brand = None
        return self._brand

    def _brand_context(self) -> str:
        """Build brand context string for prompts."""
        b = self.brand
        if not b:
            return f"Projeto: {self.project.name}. Sem perfil de marca configurado."
        parts = [f"Marca: {self.project.name}"]
        if b.brand_summary:
            parts.append(f"DNA da marca: {b.brand_summary[:500]}")
        if b.target_audience:
            parts.append(f"Público-alvo: {b.target_audience[:200]}")
        if b.tone_of_voice:
            parts.append(f"Tom de voz: {b.tone_of_voice}")
        if b.key_services:
            parts.append(f"Serviços: {', '.join(b.key_services[:10])}")
        if b.differentiators:
            parts.append(f"Diferenciais: {b.differentiators[:200]}")
        return "\n".join(parts)

    # ── THEME GENERATION ────────────────────────────────────

    def generate_themes(self, count: int = 5,
                        platforms: list[str] | None = None) -> list[dict]:
        """Generate theme suggestions based on brand profile."""
        brand_ctx = self._brand_context()
        platform_str = ", ".join(platforms) if platforms else "Instagram Feed"

        prompt = f"""Você é um especialista em social media marketing.
Com base no perfil da marca abaixo, sugira {count} temas para posts em {platform_str}.

{brand_ctx}

Retorne um JSON array com objetos contendo:
- "theme": título curto do tema (max 80 chars)
- "platform": plataforma sugerida
- "angle": ângulo/abordagem (1 frase)
- "content_type": tipo (educativo, inspiracional, promocional, bastidores, depoimento)

Retorne APENAS o JSON array, sem texto adicional."""

        result = self.router.generate_text_json(prompt)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("data", "themes", "suggestions"):
                if key in result and isinstance(result[key], list):
                    return result[key]
        logger.error("Theme generation returned unexpected format: %s", type(result).__name__)
        return []

    # ── POST GENERATION ─────────────────────────────────────

    def generate_post(self, theme: str, platform: str = "instagram_feed",
                      style: str = "") -> SocialPost | None:
        """Generate a single social post with copy, hashtags, CTA."""
        brand_ctx = self._brand_context()

        platform_tips = {
            "instagram_feed": "Legenda de 150-300 palavras, emojis moderados, 20-30 hashtags relevantes, CTA claro.",
            "instagram_stories": "Texto curto e impactante (2-3 frases), CTA direto (swipe up, ver mais).",
            "instagram_reels": "Hook nos primeiros 3 seg, texto em bullet points p/ legendas, hashtags trending.",
            "facebook": "Texto mais longo permitido (300-500 palavras), tom conversacional, 3-5 hashtags.",
            "linkedin": "Tom profissional mas acessível, storytelling, 3-5 hashtags de nicho.",
            "tiktok": "Hook viral, linguagem jovem, hashtags trending, texto super curto.",
        }
        tips = platform_tips.get(platform, platform_tips["instagram_feed"])

        style_instruction = f"\nEstilo adicional: {style}" if style else ""

        prompt = f"""Você é um social media manager expert.
Crie um post para {platform} sobre o tema: "{theme}".

Contexto da marca:
{brand_ctx}

Diretrizes da plataforma: {tips}{style_instruction}

Retorne um JSON com:
- "caption": legenda completa (com emojis)
- "hashtags": string de hashtags (separadas por espaço)
- "cta": call-to-action
- "image_prompt": prompt em inglês para gerar imagem complementar (DALL-E style, max 200 chars)

Retorne APENAS o JSON, sem texto adicional."""

        result = self.router.generate_text_json(prompt)
        data = result if isinstance(result, dict) else {}
        # AI may wrap response under a nested key
        if "caption" not in data:
            for key in ("data", "post"):
                if key in data and isinstance(data[key], dict):
                    data = data[key]
                    break
        if not isinstance(data, dict) or "caption" not in data:
            logger.error("Post generation failed — invalid response: %s", result)
            return None

        post = SocialPost.objects.create(
            project=self.project,
            platform=platform,
            theme=theme[:300],
            caption=data.get("caption", ""),
            hashtags=data.get("hashtags", ""),
            cta=data.get("cta", ""),
            image_prompt=data.get("image_prompt", ""),
            model_used=data.get("model", ""),
            generation_params={"theme": theme, "style": style, "platform": platform},
        )
        return post

    # ── IMAGE GENERATION ────────────────────────────────────

    def generate_image(self, post: SocialPost) -> str | None:
        """Generate an image for a post using the image prompt."""
        if not post.image_prompt:
            return None
        image_bytes = self.router.generate_image(post.image_prompt)
        if not image_bytes:
            logger.error("Image generation returned no data for post %s", post.pk)
            return None

        from django.core.files.base import ContentFile
        filename = f"social_{post.pk}.png"
        post.image_file.save(filename, ContentFile(image_bytes), save=False)
        post.save(update_fields=["image_file", "updated_at"])
        return post.image_file.url

    # ── BATCH GENERATION ────────────────────────────────────

    def generate_batch(self, themes: list[str],
                       platform: str = "instagram_feed",
                       style: str = "") -> list[SocialPost]:
        """Generate multiple posts from a list of themes."""
        posts = []
        for theme in themes:
            post = self.generate_post(theme=theme, platform=platform, style=style)
            if post:
                posts.append(post)
        return posts

    # ── STATS ───────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Get social post stats for the project."""
        qs = SocialPost.objects.filter(project=self.project)
        return {
            "total": qs.count(),
            "draft": qs.filter(status="draft").count(),
            "review": qs.filter(status="review").count(),
            "approved": qs.filter(status="approved").count(),
            "published": qs.filter(status="published").count(),
        }
