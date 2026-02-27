"""
Views do chat de suporte Aura — RankPulse.

Endpoints JSON para o widget de chat no frontend:
  POST /chat/send/       → Enviar mensagem e receber resposta da IA
  GET  /chat/messages/   → Carregar histórico de mensagens
  POST /chat/close/      → Fechar sessão
"""
import json
import logging
import uuid
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .ai_handler import AIHandler
from .models import ChatMessage, ChatSession, ChatSettings

logger = logging.getLogger(__name__)


# ── helpers de contexto ─────────────────────────────────────────────
def _build_user_context(request) -> dict:
    """Detecta tipo e dados do usuário para injetar no prompt da Aura."""
    user = request.user
    if not user.is_authenticated:
        return {"type": "visitor"}

    from apps.core.models import GA4EventDefinition, KPIGoal, Site

    sites = Site.objects.filter(owner=user)
    return {
        "type": "authenticated",
        "username": user.get_full_name() or user.username,
        "sites_count": sites.count(),
        "sites_names": list(sites.values_list("name", flat=True)[:10]),
        "total_events": GA4EventDefinition.objects.filter(site__owner=user).count(),
        "total_kpis": KPIGoal.objects.filter(site__owner=user).count(),
    }


def _get_or_create_session(request) -> ChatSession:
    """Obtém ou cria sessão persistente.

    - Autenticados: sessão reutilizável por até 1 ano.
    - Visitantes: via session cookie.
    """
    user = request.user if request.user.is_authenticated else None
    one_year_ago = timezone.now() - timedelta(days=365)

    if user:
        session = (
            ChatSession.objects.filter(
                user=user,
                status="active",
                started_at__gte=one_year_ago,
            )
            .order_by("-started_at")
            .first()
        )
        if session:
            return session

        session = ChatSession.objects.create(
            user=user,
            visitor_id=str(uuid.uuid4()),
        )
        settings = ChatSettings.get_settings()
        ChatMessage.objects.create(
            session=session,
            sender="ai",
            content=settings.welcome_message,
        )
        return session

    # Visitante — session cookie
    session_id = request.session.get("chat_session_id")
    session = None
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, status="active")
        except ChatSession.DoesNotExist:
            session = None

    if not session:
        visitor_id = request.session.get("visitor_id")
        if not visitor_id:
            visitor_id = str(uuid.uuid4())
            request.session["visitor_id"] = visitor_id

        session = ChatSession.objects.create(user=None, visitor_id=visitor_id)
        request.session["chat_session_id"] = str(session.id)

        settings = ChatSettings.get_settings()
        ChatMessage.objects.create(
            session=session,
            sender="ai",
            content=settings.welcome_message,
        )

    return session


# ── endpoints ───────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def send_message(request) -> JsonResponse:
    """Envia mensagem do usuário e recebe resposta da Aura."""
    try:
        data = json.loads(request.body)
        message = data.get("message", "").strip()

        if not message:
            return JsonResponse({"error": "Mensagem vazia"}, status=400)

        session = _get_or_create_session(request)

        # Salvar mensagem do usuário
        ChatMessage.objects.create(
            session=session,
            sender="user",
            content=message,
        )

        # Montar histórico (últimas 20 mensagens)
        history: list[dict] = []
        for msg in session.messages.exclude(sender="system").order_by("created_at")[:20]:
            role = "assistant" if msg.sender == "ai" else "user"
            history.append({"role": role, "content": msg.content})

        # Gerar resposta via Agno Agent
        user_context = _build_user_context(request)
        ai_handler = AIHandler(user_context=user_context)
        result = ai_handler.get_response(message, history[:-1])

        # Salvar resposta
        ChatMessage.objects.create(
            session=session,
            sender="ai",
            content=result["response"],
        )

        if result.get("should_escalate"):
            logger.warning(
                "Aura detectou frustração na sessão %s: %s",
                session.id,
                message[:100],
            )

        return JsonResponse(
            {
                "success": True,
                "response": result["response"],
            }
        )

    except Exception as exc:
        logger.exception("Erro em send_message: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)


@require_http_methods(["GET"])
def get_messages(request) -> JsonResponse:
    """Retorna mensagens do chat atual."""
    try:
        session = _get_or_create_session(request)
        messages = session.messages.all().order_by("created_at")

        return JsonResponse(
            {
                "success": True,
                "session_id": str(session.id),
                "messages": [
                    {
                        "id": str(msg.id),
                        "sender": msg.sender,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                    }
                    for msg in messages
                ],
            }
        )
    except Exception as exc:
        logger.exception("Erro em get_messages: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def close_chat(request) -> JsonResponse:
    """Fecha a sessão de chat."""
    try:
        session_id = request.session.get("chat_session_id")
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id)
                session.status = "closed"
                session.ended_at = timezone.now()
                session.save()
                del request.session["chat_session_id"]
            except ChatSession.DoesNotExist:
                pass

        return JsonResponse({"success": True})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)
