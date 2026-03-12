"""
Módulo de integração com IA para o chat de suporte.
Usa AIRouter multi-provedor para respostas contextualmente inteligentes.

Roteia chamadas pelo AIRouter (OpenAI, Gemini, Anthropic, Grok) com
fallback automático para a chave global OPENAI_API_KEY.
"""
import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings as django_settings

from .ai_prompts import USER_SYSTEM_PROMPT, VISITOR_SYSTEM_PROMPT

if TYPE_CHECKING:
    from apps.core.models import Project

logger = logging.getLogger(__name__)


class AIHandler:
    """Gerenciador de respostas da Aura — contexto-aware, multi-provider."""

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
        project: "Project | None" = None,
    ) -> None:
        self.user_context: dict = user_context or {}
        self.project = project
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
        if ctx.get("project_name"):
            lines.append(f"Projeto ativo: {ctx['project_name']}")

        # Project-specific data
        if ctx.get("audit_score") is not None:
            lines.append(f"\n═══ ÚLTIMA AUDITORIA ({ctx.get('audit_date', '?')}) ═══")
            lines.append(f"Score geral: {ctx['audit_score']}/100")
            if ctx.get("audit_summary"):
                lines.append(f"Resumo: {ctx['audit_summary']}")

        if ctx.get("project_score") is not None:
            lines.append(f"Score do projeto: {ctx['project_score']}/100")

        if ctx.get("last_week"):
            lw = ctx["last_week"]
            lines.append("\n═══ MÉTRICAS DA ÚLTIMA SEMANA ═══")
            if lw.get("sessions"):
                lines.append(f"Sessões: {lw['sessions']}")
            if lw.get("organic"):
                lines.append(f"Sessões orgânicas: {lw['organic']}")
            if lw.get("clicks"):
                lines.append(f"Cliques (Search Console): {lw['clicks']}")
            if lw.get("impressions"):
                lines.append(f"Impressões: {lw['impressions']}")
            if lw.get("avg_position"):
                lines.append(f"Posição média: {lw['avg_position']:.1f}")

        if ctx.get("kpis"):
            lines.append("\n═══ METAS KPI ═══")
            for kpi in ctx["kpis"]:
                pct = (kpi["current"] / kpi["target"] * 100) if kpi["target"] else 0
                lines.append(f"• {kpi['name']}: {kpi['current']}/{kpi['target']} ({pct:.0f}%)")

        return "\n".join(lines) if lines else "Usuário recém-cadastrado, sem dados ainda."

    # ── resposta principal ──────────────────────────────────────────
    def get_response(
        self,
        message: str,
        conversation_history: list | None = None,
    ) -> dict:
        """Gera resposta usando AIRouter (multi-provider) com fallback global."""
        full_message = self._build_conversation_message(message, conversation_history)
        chat_messages = self._build_chat_messages(message, conversation_history)

        # Try AIRouter when project is available
        if self.project is not None:
            try:
                from apps.core.ai_router import AIRouter
                router = AIRouter(self.project)
                ai_text = router.generate_text(
                    prompt=full_message,
                    system=self.system_prompt,
                    temperature=0.7,
                    max_tokens=4096,
                )
                return {
                    "success": True,
                    "response": ai_text,
                    "should_escalate": self._should_escalate(message),
                }
            except ValueError:
                logger.debug("No AI provider for project %s, falling back to env key", self.project)
            except Exception as exc:
                logger.warning("AIRouter error for Aura: %s, falling back", exc)

        # Fallback: direct OpenAI with env key + proper message roles
        api_key = getattr(django_settings, "OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        if not api_key:
            return self._fallback_response()

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            model = getattr(django_settings, "OPENAI_MODEL", "gpt-4.1-mini")
            resp = client.chat.completions.create(
                model=model,
                messages=chat_messages,
                temperature=0.7,
                max_tokens=4096,
            )
            ai_text = resp.choices[0].message.content or ""
            return {
                "success": True,
                "response": ai_text,
                "should_escalate": self._should_escalate(message),
            }
        except Exception as exc:
            logger.exception("Erro na API de IA (Aura): %s", exc)
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

    def _build_chat_messages(
        self,
        message: str,
        history: list | None,
    ) -> list[dict]:
        """Build proper role-based messages array for OpenAI-compatible APIs."""
        msgs = [{"role": "system", "content": self.system_prompt}]
        if history:
            for msg in history[-10:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                msgs.append({"role": role, "content": msg["content"]})
        msgs.append({"role": "user", "content": message})
        return msgs

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
