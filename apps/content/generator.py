"""Content generator service — Uses OpenAI to generate SEO blog posts."""
from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generate SEO-optimized blog posts using OpenAI."""

    def __init__(self, model: str = "") -> None:
        self.model = model or settings.OPENAI_MODEL or "gpt-4.1-mini"
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-load OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def generate_post(
        self,
        topic_title: str,
        target_keyword: str,
        site_name: str = "",
        site_domain: str = "",
        content_type: str = "blog_post",
        word_target: int = 1500,
        language: str = "pt-BR",
    ) -> dict[str, Any]:
        """Generate a full blog post with HTML content.

        Returns:
            Dict with keys: title, slug, meta_description, content_html,
            content_markdown, word_count, model_used, prompt_used, tokens_used
        """
        prompt = self._build_prompt(
            topic_title=topic_title,
            target_keyword=target_keyword,
            site_name=site_name,
            site_domain=site_domain,
            content_type=content_type,
            word_target=word_target,
            language=language,
        )

        logger.info("Generating content: %s (model=%s)", topic_title, self.model)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._system_prompt(language)},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=4096,
            )

            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0

            # Parse the response
            result = self._parse_response(content, topic_title, target_keyword)
            result["model_used"] = self.model
            result["prompt_used"] = prompt
            result["tokens_used"] = tokens_used

            logger.info(
                "Generated post: %s (%d words, %d tokens)",
                result["title"], result["word_count"], tokens_used,
            )
            return result

        except Exception as e:
            logger.exception("Content generation failed: %s", e)
            return {
                "title": topic_title,
                "slug": slugify(topic_title),
                "meta_description": "",
                "content_html": f"<p>Erro ao gerar conteúdo: {e}</p>",
                "content_markdown": "",
                "word_count": 0,
                "model_used": self.model,
                "prompt_used": prompt,
                "tokens_used": 0,
                "error": str(e),
            }

    def _system_prompt(self, language: str) -> str:
        """Build system prompt for the AI."""
        return (
            f"Você é um especialista em SEO e marketing de conteúdo. "
            f"Escreva conteúdo de alta qualidade em {language}, "
            f"otimizado para mecanismos de busca. "
            f"Use headers HTML (h2, h3), parágrafos, listas e bold para palavras-chave. "
            f"O conteúdo deve ser informativo, original e engajante. "
            f"Sempre inclua uma introdução, corpo estruturado e conclusão com CTA."
        )

    @staticmethod
    def _build_prompt(
        topic_title: str,
        target_keyword: str,
        site_name: str,
        site_domain: str,
        content_type: str,
        word_target: int,
        language: str,
    ) -> str:
        """Build the generation prompt."""
        site_ref = f" para o site {site_name} ({site_domain})" if site_name else ""
        return (
            f"Escreva um {content_type}{site_ref}.\n\n"
            f"**Título:** {topic_title}\n"
            f"**Keyword principal:** {target_keyword}\n"
            f"**Tamanho alvo:** {word_target} palavras\n"
            f"**Idioma:** {language}\n\n"
            f"Formato de resposta:\n"
            f"---TITLE---\n[título otimizado para SEO]\n"
            f"---META---\n[meta description 150-160 chars]\n"
            f"---CONTENT---\n[conteúdo em HTML com h2, h3, p, ul, strong]\n"
        )

    @staticmethod
    def _parse_response(content: str, fallback_title: str, keyword: str) -> dict[str, Any]:
        """Parse the AI response into structured fields."""
        title = fallback_title
        meta_description = ""
        content_html = content

        if "---TITLE---" in content:
            parts = content.split("---TITLE---")
            if len(parts) > 1:
                rest = parts[1]
                if "---META---" in rest:
                    title_part, rest = rest.split("---META---", 1)
                    title = title_part.strip()
                    if "---CONTENT---" in rest:
                        meta_part, content_part = rest.split("---CONTENT---", 1)
                        meta_description = meta_part.strip()[:200]
                        content_html = content_part.strip()
                    else:
                        meta_description = rest.strip()[:200]

        # Clean up
        word_count = len(content_html.split())

        return {
            "title": title,
            "slug": slugify(title),
            "meta_description": meta_description,
            "content_html": content_html,
            "content_markdown": "",
            "word_count": word_count,
        }
