from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    label = "audit"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # регистрируем сигналы (tenant create/update, allauth login/logout)
        from . import signals  # noqa: F401
