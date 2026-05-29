"""Базовые абстрактные модели и миксины для всех TENANT-приложений.

Спецификации:
- TimestampedModel / I18nMixin — phase1-implementation-guide.md, Часть 2
- SoftDeleteMixin            — docs/references/patterns/soft-delete.md

Все модели абстрактные → миграций в этом приложении нет.
"""

import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import get_language


class TimestampedModel(models.Model):
    """UUID-PK + created_at/updated_at. База для большинства tenant-моделей."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class I18nMixin:
    """Утилиты для переводимых JSONField вида {"de": "...", "en": "..."}.

    Фолбэк: запрошенный → default_locale (de) → en → первое доступное → ''.
    """

    def get_i18n(self, field_name: str, locale: str | None = None) -> str:
        locale = locale or get_language() or "de"
        value = getattr(self, field_name) or {}
        if not isinstance(value, dict):
            return ""
        if value.get(locale):
            return value[locale]
        if value.get("de"):
            return value["de"]
        if value.get("en"):
            return value["en"]
        # первое непустое значение из словаря
        for v in value.values():
            if v:
                return v
        return ""


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):  # bulk soft-delete
        return self.update(deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()


class AliveManager(models.Manager):
    """Менеджер по умолчанию: отдаёт только не удалённые записи."""

    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteMixin(TimestampedModel):
    """Мягкое удаление через deleted_at.

    objects     — только живые (default-менеджер, используется в related-доступе).
    all_objects — все записи, включая удалённые (для admin/корзины/восстановления).

    ВНИМАНИЕ про unique: удалённая строка продолжает занимать уникальное значение.
    Для уникальных полей используй partial constraint, см. soft-delete.md:
        UniqueConstraint(fields=[...], condition=Q(deleted_at__isnull=True), name=...)
    """

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = AliveManager()
    all_objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
