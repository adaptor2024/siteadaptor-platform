"""Совместимость: FSM (apps/core/fsm.py) импортирует audit_event отсюда.

Сам журнал живёт в SHARED-приложении apps.audit (AuditEvent должен быть в
SHARED-схеме, а apps.core — TENANT-приложение). Здесь только ре-экспорт.
"""

from apps.audit.services import audit_event

__all__ = ["audit_event"]
