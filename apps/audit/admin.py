from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "action",
        "resource_type",
        "resource_id",
        "actor_display",
        "tenant_schema",
    )
    list_filter = ("action", "resource_type", "actor_type", "tenant_schema")
    search_fields = ("resource_id", "actor_display", "action")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    # Audit неизменяем: только чтение.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
