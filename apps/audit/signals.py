"""Audit-сигналы Sprint 1: создание/обновление Tenant + allauth auth-события."""

from allauth.account.signals import (
    password_changed,
    user_logged_in,
    user_logged_out,
)
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.tenants.models import Tenant

from .services import audit_event


@receiver(post_save, sender=Tenant)
def audit_tenant_saved(sender, instance, created, **kwargs):
    audit_event(
        action="tenant.created" if created else "tenant.updated",
        resource_type="tenant",
        resource_id=instance.pk,
        tenant_schema=instance.schema_name,
        context={"schema": instance.schema_name, "slug": instance.slug},
    )


@receiver(user_logged_in)
def audit_login(sender, request, user, **kwargs):
    audit_event(action="auth.login", resource_type="user", resource_id=user.pk, actor=user)


@receiver(user_logged_out)
def audit_logout(sender, request, user, **kwargs):
    if user is None:
        return
    audit_event(action="auth.logout", resource_type="user", resource_id=user.pk, actor=user)


@receiver(password_changed)
def audit_password_changed(sender, request, user, **kwargs):
    audit_event(
        action="auth.password_changed",
        resource_type="user",
        resource_id=user.pk,
        actor=user,
    )
