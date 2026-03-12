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
from .models import ChatMessage, ChatSession, ChatSettings, FeedbackLog

logger = logging.getLogger(__name__)


def _send_feedback_confirmation(fb: "FeedbackLog"):
    """Send email confirmation with ticket number to feedback author."""
    try:
        from django.conf import settings as _s
        if not _s.EMAIL_HOST_USER:
            return
        user_email = getattr(fb.user, "email", None) if fb.user else None
        if not user_email and fb.email:
            user_email = fb.email
        if not user_email:
            return
        from django.core.mail import send_mail
        name = (fb.user.get_full_name() or fb.user.username) if fb.user else "Usuário"
        send_mail(
            subject=f"[{_s.APP_NAME}] Ticket #{fb.id} — Feedback recebido: {fb.title}",
            message=(
                f"Olá {name},\n\n"
                f"Seu feedback foi registrado com sucesso!\n\n"
                f"🎫 Ticket: #{fb.id}\n"
                f"📌 Título: {fb.title}\n"
                f"🏷 Categoria: {fb.get_category_display()}\n"
                f"⚡ Prioridade: {fb.get_priority_display()}\n"
                f"📊 Status: Novo\n\n"
                f"Vamos analisar e retornar em breve.\n\n"
                f"— Equipe {_s.APP_NAME}"
            ),
            from_email=_s.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.warning("Failed to send feedback confirmation email: %s", exc)


def _send_feedback_status_email(fb: "FeedbackLog"):
    """Notify user when feedback status changes; include resolution details if resolved."""
    try:
        from django.conf import settings as _s
        if not _s.EMAIL_HOST_USER:
            return
        user_email = getattr(fb.user, "email", None) if fb.user else None
        if not user_email and fb.email:
            user_email = fb.email
        if not user_email:
            return
        from django.core.mail import send_mail
        name = (fb.user.get_full_name() or fb.user.username) if fb.user else "Usuário"
        body = (
            f"Olá {name},\n\n"
            f"Seu feedback foi atualizado.\n\n"
            f"🎫 Ticket: #{fb.id}\n"
            f"📌 Título: {fb.title}\n"
            f"📊 Novo status: {fb.get_status_display()}\n"
        )
        if fb.status == "resolved" and fb.resolution_notes:
            body += f"\n✅ Solução aplicada:\n{fb.resolution_notes}\n"
        body += f"\n— Equipe {_s.APP_NAME}"
        send_mail(
            subject=f"[{_s.APP_NAME}] Ticket #{fb.id} — {fb.get_status_display()}: {fb.title}",
            message=body,
            from_email=_s.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=True,
        )
    except Exception as exc:
        logger.warning("Failed to send feedback status email: %s", exc)


def _notify_ceo_bot(fb: "FeedbackLog", event: str = "new"):
    """Fire-and-forget Telegram notification about feedback events."""
    from django.conf import settings as _s
    token = getattr(_s, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(_s, 'TELEGRAM_OWNER_CHAT_ID', '')
    if not token or not chat_id:
        return

    app_name = getattr(_s, 'APP_NAME', 'RankPulse')
    emoji_map = {
        'new': '\U0001f195', 'approved': '\U0001f44d', 'in_progress': '\U0001f527',
        'resolved': '\u2705', 'rejected': '\u274c', 'closed': '\U0001f4e6',
    }
    emoji = emoji_map.get(event, '\U0001f4dd')
    cat = fb.get_category_display()
    priority = fb.get_priority_display()
    user_str = fb.user.email if fb.user else 'Visitante'
    text = (
        f"{emoji} [{app_name} \U0001f4c8] Feedback {event.upper()}\n\n"
        f"\U0001f4cc {fb.title}\n"
        f"\U0001f3f7 {cat} | \u26a1 {priority}\n"
        f"\U0001f464 {user_str}\n"
    )
    if fb.page_url:
        text += f"\U0001f517 {fb.page_url}\n"
    if fb.description:
        text += f"\n{fb.description[:300]}"

    def _send():
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10,
            )
        except Exception as exc:
            logger.warning("Telegram notify failed: %s", exc)

    import threading
    threading.Thread(target=_send, daemon=True).start()


# ── helpers de contexto ─────────────────────────────────────────────
def _build_user_context(request) -> dict:
    """Detecta tipo e dados do usuário para injetar no prompt da Aura."""
    user = request.user
    if not user.is_authenticated:
        return {"type": "visitor"}

    from apps.core.models import (
        AuditReport,
        GA4EventDefinition,
        KPIGoal,
        Project,
        ProjectScore,
        Site,
        WeeklySnapshot,
    )

    sites = Site.objects.filter(project__owner=user)
    project = Project.objects.filter(owner=user, is_active=True).first()
    ctx = {
        "type": "authenticated",
        "username": user.get_full_name() or user.username,
        "sites_count": sites.count(),
        "sites_names": list(sites.values_list("name", flat=True)[:10]),
        "total_events": GA4EventDefinition.objects.filter(site__project__owner=user).count(),
        "total_kpis": KPIGoal.objects.filter(site__project__owner=user).count(),
    }
    if project:
        ctx["project"] = project
        ctx["project_name"] = project.name

        # Latest audit score and summary
        latest_audit = (
            AuditReport.objects.filter(project=project, status="done")
            .order_by("-created_at")
            .values("overall_score", "overall_analysis", "created_at")
            .first()
        )
        if latest_audit:
            ctx["audit_score"] = latest_audit["overall_score"]
            ctx["audit_summary"] = (latest_audit["overall_analysis"] or "")[:600]
            ctx["audit_date"] = str(latest_audit["created_at"].date())

        # Project score
        score = ProjectScore.objects.filter(project=project).first()
        if score:
            ctx["project_score"] = score.overall_score

        # Latest weekly snapshot
        snapshot = (
            WeeklySnapshot.objects.filter(site__project=project)
            .order_by("-week_start")
            .first()
        )
        if snapshot:
            ctx["last_week"] = {
                "sessions": snapshot.sessions,
                "organic": snapshot.organic_sessions,
                "clicks": snapshot.search_clicks,
                "impressions": snapshot.search_impressions,
                "avg_position": float(snapshot.avg_position) if snapshot.avg_position else None,
            }

        # KPI progress
        kpis = KPIGoal.objects.filter(site__project=project).select_related("site")[:5]
        if kpis:
            ctx["kpis"] = [
                {"name": k.name, "target": float(k.target_value), "current": float(k.current_value) if k.current_value else 0}
                for k in kpis
            ]

    return ctx


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

        # Gerar resposta via AIRouter (multi-provider)
        user_context = _build_user_context(request)
        project = user_context.pop("project", None)
        ai_handler = AIHandler(user_context=user_context, project=project)
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
        # Log to admin error panel
        try:
            import traceback as tb_mod
            from apps.core.middleware import log_error
            log_error(
                error_message=str(exc),
                error_type="api_error",
                severity="error",
                user=request.user if request.user.is_authenticated else None,
                view_name="chat_support:send_message",
                url_path=request.path,
                http_method=request.method,
                tb=tb_mod.format_exc(),
            )
        except Exception:
            pass
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


# ── Feedback endpoints ──────────────────────────────────────────────

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render


@csrf_exempt
@require_http_methods(["POST"])
def submit_feedback(request) -> JsonResponse:
    """Submit feedback/bug report from Aura widget."""
    try:
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "bug")
        page_url = request.POST.get("page_url", "")

        if not title or not description:
            return JsonResponse({"error": "Título e descrição são obrigatórios"}, status=400)

        valid_categories = [c[0] for c in FeedbackLog.CATEGORY_CHOICES]
        if category not in valid_categories:
            category = "other"

        fb = FeedbackLog(
            user=request.user if request.user.is_authenticated else None,
            title=title[:300],
            description=description,
            category=category,
            email=request.POST.get("email", "").strip()[:254],
            page_url=page_url[:500],
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )

        # Link to chat session if provided
        session_id = request.POST.get("session_id", "").strip()
        if session_id:
            from .models import ChatSession
            try:
                fb.chat_session = ChatSession.objects.get(pk=session_id)
                # Capture last 20 messages as transcript
                msgs = fb.chat_session.messages.order_by("-created_at")[:20]
                fb.chat_transcript = "\n".join(
                    f"[{m.sender}] {m.content}" for m in reversed(msgs)
                )
            except ChatSession.DoesNotExist:
                pass

        # Capture error context
        error_ctx = request.POST.get("error_context", "").strip()
        if error_ctx:
            import json as _json
            try:
                fb.error_context = _json.loads(error_ctx)
            except (ValueError, TypeError):
                fb.error_context = {"raw": error_ctx[:2000]}

        if request.FILES.get("screenshot"):
            fb.screenshot = request.FILES["screenshot"]
        fb.save()

        # Handle multiple image uploads
        from .models import FeedbackImage
        for f in request.FILES.getlist("images"):
            FeedbackImage.objects.create(feedback=fb, image=f)

        # Send confirmation email to the user (if they have an email)
        _send_feedback_confirmation(fb)
        _notify_ceo_bot(fb, event="new")

        return JsonResponse({"success": True, "id": fb.pk})
    except Exception as exc:
        logger.exception("Erro em submit_feedback: %s", exc)
        return JsonResponse({"error": str(exc)}, status=500)


@login_required
def feedback_panel(request):
    """Staff-only feedback management panel."""
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("Acesso restrito")

    status_filter = request.GET.get("status", "")
    qs = FeedbackLog.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)

    from apps.core.models import Project
    return render(request, "chat_support/feedback_panel.html", {
        "feedbacks": qs[:100],
        "status_filter": status_filter,
        "status_choices": FeedbackLog.STATUS_CHOICES,
        "priority_choices": FeedbackLog.PRIORITY_CHOICES,
        "category_choices": FeedbackLog.CATEGORY_CHOICES,
        "page_title": "Feedback & Bugs",
        "page_id": "feedback_panel",
        "projects": Project.objects.filter(owner=request.user, is_active=True),
    })


@login_required
@require_http_methods(["POST"])
def feedback_update_status(request, pk: int) -> JsonResponse:
    """Staff: update feedback status, priority, notes."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Acesso restrito"}, status=403)

    fb = get_object_or_404(FeedbackLog, pk=pk)

    status = request.POST.get("status", "")
    priority = request.POST.get("priority", "")
    notes = request.POST.get("developer_notes", "")

    valid_statuses = [s[0] for s in FeedbackLog.STATUS_CHOICES]
    valid_priorities = [p[0] for p in FeedbackLog.PRIORITY_CHOICES]

    fields = []
    if status and status in valid_statuses:
        fb.status = status
        fields.append("status")
    if priority and priority in valid_priorities:
        fb.priority = priority
        fields.append("priority")
    if notes is not None:
        fb.developer_notes = notes
        fields.append("developer_notes")

    if fields:
        fields.append("updated_at")
        fb.save(update_fields=fields)
        if "status" in fields:
            _send_feedback_status_email(fb)
            _notify_ceo_bot(fb, event=fb.status)

    return JsonResponse({"success": True})


@login_required
@require_http_methods(["POST"])
def feedback_approve(request, pk: int) -> JsonResponse:
    """Staff: quick approve or reject a feedback item."""
    if not request.user.is_staff:
        return JsonResponse({"error": "Acesso restrito"}, status=403)

    fb = get_object_or_404(FeedbackLog, pk=pk)
    action = request.POST.get("action", "approve")

    from django.utils import timezone as _tz
    now_str = _tz.now().strftime("%d/%m/%Y %H:%M")

    if action == "approve":
        fb.status = "approved"
        note = f"Aprovado por {request.user.username} em {now_str}"
    elif action == "reject":
        fb.status = "rejected"
        note = f"Rejeitado por {request.user.username} em {now_str}"
    else:
        return JsonResponse({"error": "Ação inválida"}, status=400)

    fb.developer_notes = (fb.developer_notes + "\n" + note) if fb.developer_notes else note
    fb.save(update_fields=["status", "developer_notes", "updated_at"])
    _send_feedback_status_email(fb)
    _notify_ceo_bot(fb, event="approved" if action == "approve" else "rejected")
    return JsonResponse({"success": True, "new_status": fb.status})
