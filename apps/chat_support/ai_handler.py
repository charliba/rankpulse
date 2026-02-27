"""
Módulo de integração com IA para o chat de suporte.
Usa Agno Agent + OpenAI para respostas contextualmente inteligentes.

Padrão direto e enxuto inspirado no askjoel (Agno Agent per-request).
Imports de agno/openai são lazy para não bloquear migrations/startup.
"""
import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings as django_settings

from .ai_prompts import USER_SYSTEM_PROMPT, VISITOR_SYSTEM_PROMPT

if TYPE_CHECKING:
    from agno.agent import Agent

logger = logging.getLogger(__name__)


class AIHandler:
    """Gerenciador de respostas da Aura com Agno Agent — contexto-aware."""

    # Palavras que indicam atenção especial
    ATTENTION_KEYWORDS: list[str] = [
        "não entendeu",
        "não resolveu",
        "bug",
        "erro",
        "não funciona",
        "problema",
        "reclamação",
    ]

    def __init__(
        self,
        system_prompt: str | None = None,
        user_context: dict | None = None,
    ) -> None:
        self.api_key: str = getattr(
            django_settings,
            "OPENAI_API_KEY",
            os.environ.get("OPENAI_API_KEY", ""),
        )
        self.model_id: str = getattr(
            django_settings,
            "OPENAI_MODEL",
            "gpt-4.1-mini",
        )
        self.user_context: dict = user_context or {}
        self.system_prompt: str = self._build_prompt(system_prompt)

    # ── prompt builder ──────────────────────────────────────────────
    def _build_prompt(self, base_prompt: str | None) -> str:
        """Seleciona e preenche o prompt correto com dados do usuário."""
        user_type = self.user_context.get("type", "visitor")

        if base_prompt:
            prompt = base_prompt
        elif user_type == "authenticated":
            prompt = USER_SYSTEM_PROMPT
        else:
            prompt = VISITOR_SYSTEM_PROMPT

        # Injetar contexto real do usuário
        if "{user_context}" in prompt:
            prompt = prompt.replace("{user_context}", self._format_user_context())

        return prompt

    def _format_user_context(self) -> str:
        """Formata dados reais do usuário para injeção no prompt."""
        ctx = self.user_context
        lines: list[str] = []

        if ctx.get("username"):
            lines.append(f"Usuário: {ctx['username']}")
        if ctx.get("sites_count") is not None:
            lines.append(f"Sites cadastrados: {ctx['sites_count']}")
        if ctx.get("sites_names"):
            lines.append(f"Sites: {', '.join(ctx['sites_names'])}")
        if ctx.get("total_events") is not None:
            lines.append(f"Eventos GA4 registrados: {ctx['total_events']}")
        if ctx.get("total_kpis") is not None:
            lines.append(f"Metas KPI definidas: {ctx['total_kpis']}")

        return "\n".join(lines) if lines else "Usuário recém-cadastrado, sem dados ainda."

    # ── resposta principal ──────────────────────────────────────────
    def get_response(
        self,
        message: str,
        conversation_history: list | None = None,
    ) -> dict:
        """Gera resposta usando Agno Agent + OpenAI (agent per-request)."""
        if not self.api_key:
            return self._fallback_response()

        try:
            from agno.agent import Agent
            from agno.models.openai import OpenAIChat

            agent = Agent(
                model=OpenAIChat(
                    id=self.model_id,
                    api_key=self.api_key,
                ),
                instructions=self.system_prompt,
                markdown=True,
            )

            full_message = self._build_conversation_message(
                message, conversation_history
            )
            run_response = agent.run(full_message)
            ai_text = run_response.content if run_response.content else ""

            should_escalate = self._should_escalate(message)

            return {
                "success": True,
                "response": ai_text,
                "should_escalate": should_escalate,
            }

        except Exception as exc:
            logger.exception("Erro no Agno Agent (Aura): %s", exc)
            return self._fallback_response()

    # ── helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _build_conversation_message(
        message: str,
        history: list | None,
    ) -> str:
        """Inclui últimas mensagens como contexto inline para o agente."""
        if not history:
            return message

        ctx_lines: list[str] = []
        for msg in history[-10:]:
            role = "Usuário" if msg.get("role") == "user" else "Aura"
            ctx_lines.append(f"{role}: {msg['content']}")
        ctx_lines.append(f"Usuário: {message}")
        return "\n".join(ctx_lines)

    def _should_escalate(self, user_message: str) -> bool:
        """Detecta frustração — log para análise, Aura continua atendendo."""
        text = user_message.lower()
        return any(kw in text for kw in self.ATTENTION_KEYWORDS)

    @staticmethod
    def _fallback_response() -> dict:
        """Resposta segura quando a API não está disponível."""
        return {
            "success": True,
            "response": (
                "Desculpe, estou com dificuldade técnica no momento. 😔\n\n"
                "Você pode:\n"
                "• Tentar novamente em alguns instantes\n"
                "• Navegar pela plataforma — os tooltips (❓) em cada campo explicam tudo\n\n"
                "Peço desculpas pelo transtorno!"
            ),
            "should_escalate": False,
        }
