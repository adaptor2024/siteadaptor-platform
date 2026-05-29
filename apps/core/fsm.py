"""Декларативная машина состояний. Спецификация: docs/references/patterns/state-machine.md.

Любая смена статуса — только через StateMachine.apply(). Прямые присваивания
obj.status = ... запрещены (ловится на code review). Каждый переход опционально
пишет audit-событие — пока через мягкий хук (audit-модуль появится отдельным
SHARED-приложением; см. patterns/audit-log.md).
"""

from dataclasses import dataclass


class IllegalTransition(Exception):
    def __init__(self, model, src, dst):
        super().__init__(f"{model}: {src} → {dst} запрещён")
        self.model = model
        self.src = src
        self.dst = dst


@dataclass(frozen=True)
class Transition:
    src: str
    dst: str
    event: str  # имя для audit, напр. 'promotion.activated'


class StateMachine:
    """Базовый FSM поверх CharField-поля статуса. Наследники задают transitions."""

    field = "status"
    transitions: list[Transition] = []

    def __init__(self):
        self._index = {(t.src, t.dst): t for t in self.transitions}

    def can(self, src: str, dst: str) -> bool:
        return (src, dst) in self._index

    def allowed_targets(self, src: str) -> list[str]:
        return [t.dst for t in self.transitions if t.src == src]

    def apply(self, instance, dst: str, *, actor=None, **ctx):
        src = getattr(instance, self.field)
        if src == dst:
            return instance  # идемпотентно: повтор того же статуса — no-op
        t = self._index.get((src, dst))
        if t is None:
            raise IllegalTransition(type(instance).__name__, src, dst)

        setattr(instance, self.field, dst)
        update_fields = [self.field]
        # updated_at есть у TimestampedModel; обновим, если поле присутствует
        if any(f.name == "updated_at" for f in instance._meta.fields):
            update_fields.append("updated_at")
        instance.save(update_fields=update_fields)

        self.on_transition(instance, t, actor=actor, **ctx)
        self._audit(instance, t, actor=actor, ctx=ctx, src=src, dst=dst)
        return instance

    def on_transition(self, instance, t: Transition, **kw):
        """Side-effects конкретного перехода. Переопределяется наследником."""

    def _audit(self, instance, t: Transition, *, actor, ctx, src, dst):
        """Мягкий audit-хук. Если audit-модуль ещё не подключён — тихо пропускаем."""
        try:
            from apps.core.audit import audit_event
        except ImportError:
            return
        audit_event(
            action=t.event,
            resource_type=type(instance).__name__.lower(),
            resource_id=str(instance.pk),
            actor=actor,
            changes={self.field: [src, dst]},
            context=ctx,
        )
