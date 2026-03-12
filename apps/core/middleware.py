"""Error tracking middleware — captures unhandled exceptions into SystemErrorLog."""
import logging
import re
import traceback

from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

# Fields to strip from request body before logging (security)
_SENSITIVE_PATTERN = re.compile(
    r"(password|secret|token|api_key|refresh_token|access_token|authorization)",
    re.IGNORECASE,
)


def _sanitize_body(body_str: str, max_length: int = 2000) -> str:
    """Remove sensitive fields from request body string."""
    if not body_str:
        return ""
    for match in _SENSITIVE_PATTERN.finditer(body_str):
        # Replace the value after the key
        key = match.group(0)
        body_str = re.sub(
            rf'("{key}"\s*:\s*)"[^"]*"',
            rf'\1"***REDACTED***"',
            body_str,
            flags=re.IGNORECASE,
        )
        body_str = re.sub(
            rf"({key}=)[^&\s]+",
            rf"\1***REDACTED***",
            body_str,
            flags=re.IGNORECASE,
        )
    return body_str[:max_length]


def _classify_error(exc: Exception, view_name: str) -> str:
    """Classify error type based on exception and view name."""
    exc_name = type(exc).__name__.lower()
    if "audit" in view_name.lower() or "audit" in exc_name:
        return "audit_error"
    if any(kw in exc_name for kw in ("connection", "timeout", "http", "request")):
        return "api_error"
    if any(kw in exc_name for kw in ("oauth", "token", "credential")):
        return "integration_error"
    if any(kw in view_name.lower() for kw in ("oauth", "meta", "google", "gsc", "ga4")):
        return "integration_error"
    return "view_error"


def log_error(error_message, error_type="unknown", severity="error", user=None,
              view_name="", url_path="", http_method="", request_body="",
              session_key="", user_agent="", tb=""):
    """Utility to programmatically log errors to SystemErrorLog.

    Can be called from anywhere in the codebase:
        from apps.core.middleware import log_error
        log_error("Something failed", error_type="audit_error", ...)
    """
    try:
        from apps.core.models import SystemErrorLog
        SystemErrorLog.objects.create(
            user=user,
            error_type=error_type,
            severity=severity,
            error_message=str(error_message)[:2000],
            traceback=str(tb)[:5000],
            view_name=str(view_name)[:200],
            url_path=str(url_path)[:500],
            http_method=str(http_method)[:10],
            request_body=_sanitize_body(str(request_body)),
            session_key=str(session_key)[:100],
            user_agent=str(user_agent)[:500],
        )
    except Exception:
        logger.exception("Failed to write SystemErrorLog")


class ErrorTrackingMiddleware(MiddlewareMixin):
    """Captures unhandled exceptions and logs them to SystemErrorLog."""

    def process_exception(self, request, exception):
        """Called when a view raises an unhandled exception."""
        try:
            from apps.core.models import SystemErrorLog

            # Determine view name
            view_name = ""
            if hasattr(request, "resolver_match") and request.resolver_match:
                view_name = request.resolver_match.view_name or ""

            # Get sanitized request body
            body = ""
            try:
                body = request.body.decode("utf-8", errors="replace")[:4000]
            except Exception:
                pass

            user = request.user if hasattr(request, "user") and request.user.is_authenticated else None
            session_key = request.session.session_key or "" if hasattr(request, "session") else ""

            SystemErrorLog.objects.create(
                user=user,
                error_type=_classify_error(exception, view_name),
                severity="error",
                error_message=str(exception)[:2000],
                traceback=traceback.format_exc()[:5000],
                view_name=view_name[:200],
                url_path=request.path[:500],
                http_method=request.method[:10],
                request_body=_sanitize_body(body),
                session_key=session_key[:100],
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            )
        except Exception:
            # Never let error logging break the error handling chain
            logger.exception("ErrorTrackingMiddleware failed to log error")

        # Return None to let Django's default error handling continue
        return None
