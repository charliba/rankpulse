from django.apps import AppConfig


class ChatSupportConfig(AppConfig):
    """Configuração do app Aura — assistente IA do RankPulse."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat_support"
    verbose_name = "Aura — Chat de Suporte"
