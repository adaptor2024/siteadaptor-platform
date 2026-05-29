"""Тесты audit-журнала: запись события, безопасность к ошибкам, сигнал Tenant."""

import pytest

from apps.audit.models import AuditEvent
from apps.audit.services import audit_event


@pytest.mark.django_db
def test_audit_event_records_row():
    audit_event(
        action="thing.done",
        resource_type="thing",
        resource_id="42",
        context={"k": "v"},
    )
    e = AuditEvent.objects.get(action="thing.done")
    assert e.resource_type == "thing"
    assert e.resource_id == "42"
    assert e.actor_type == "system"
    assert e.context == {"k": "v"}


@pytest.mark.django_db
def test_audit_event_never_raises(monkeypatch):
    # Ломаем создание записи — audit_event должен проглотить ошибку, не упасть.
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(AuditEvent.objects, "create", boom)
    # не должно бросить исключение
    audit_event(action="x.y", resource_type="x", resource_id="1")


@pytest.mark.django_db
def test_tenant_create_emits_audit():
    from apps.tenants.tests.factories import TenantFactory

    tenant = TenantFactory()  # post_save сигнал → audit
    assert AuditEvent.objects.filter(action="tenant.created", resource_id=str(tenant.pk)).exists()
