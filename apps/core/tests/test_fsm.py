"""Тесты FSM — чистый Python, без БД (фейковый объект вместо модели)."""

import pytest

from apps.core.fsm import IllegalTransition, StateMachine, Transition


class _TrafficSM(StateMachine):
    transitions = [
        Transition("red", "green", "light.go"),
        Transition("green", "yellow", "light.slow"),
        Transition("yellow", "red", "light.stop"),
    ]


class _Light:
    """Минимальный stand-in для модели: status + перехват save()."""

    def __init__(self, status):
        self.status = status
        self.pk = 1
        self.saved = []
        self._meta = type("M", (), {"fields": []})()  # нет updated_at

    def save(self, update_fields=None):
        self.saved.append(tuple(update_fields or []))


def test_allowed_transition_changes_status_and_saves():
    sm = _TrafficSM()
    light = _Light("red")
    sm.apply(light, "green")
    assert light.status == "green"
    assert light.saved == [("status",)]


def test_illegal_transition_raises():
    sm = _TrafficSM()
    light = _Light("red")
    with pytest.raises(IllegalTransition):
        sm.apply(light, "yellow")  # red→yellow не разрешён
    assert light.status == "red"
    assert light.saved == []  # не сохраняли


def test_same_status_is_noop():
    sm = _TrafficSM()
    light = _Light("green")
    sm.apply(light, "green")
    assert light.saved == []  # идемпотентность: ничего не делаем


def test_can_and_allowed_targets():
    sm = _TrafficSM()
    assert sm.can("red", "green") is True
    assert sm.can("red", "yellow") is False
    assert sm.allowed_targets("green") == ["yellow"]


def test_on_transition_hook_fires():
    calls = []

    class _HookedSM(_TrafficSM):
        def on_transition(self, instance, t, **kw):
            calls.append(t.event)

    sm = _HookedSM()
    sm.apply(_Light("red"), "green")
    assert calls == ["light.go"]
