"""Тесты beat-логики: просрочка броней и планировщик статусов акций.

Тестируем чистые helper'ы в текущей (public) схеме — обход схем арендаторов
в самих задачах тривиален.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.promotions.models import Reservation
from apps.promotions.services import reserve
from apps.promotions.tasks import expire_due_reservations, roll_due_promotions
from apps.promotions.tests.factories import PromotionFactory


@pytest.mark.django_db
def test_expire_due_returns_stock():
    promo = PromotionFactory(available_quantity=5)
    res = reserve(promo, name="A", email="a@test.de", quantity=2)
    promo.refresh_from_db()
    assert promo.available_quantity == 3

    # делаем бронь просроченной
    Reservation.objects.filter(pk=res.pk).update(expires_at=timezone.now() - timedelta(hours=1))

    n = expire_due_reservations()
    assert n == 1
    res.refresh_from_db()
    assert res.status == "expired"
    promo.refresh_from_db()
    assert promo.available_quantity == 5  # остаток вернулся


@pytest.mark.django_db
def test_expire_ignores_future_and_terminal():
    promo = PromotionFactory(available_quantity=5)
    fresh = reserve(promo, name="B", email="b@test.de", quantity=1)  # expires в будущем
    n = expire_due_reservations()
    assert n == 0
    fresh.refresh_from_db()
    assert fresh.status == "pending"


@pytest.mark.django_db
def test_roll_activates_scheduled():
    promo = PromotionFactory(
        status="scheduled", starts_at=timezone.now() - timedelta(minutes=1), ends_at=None
    )
    out = roll_due_promotions()
    assert out["activated"] == 1
    promo.refresh_from_db()
    assert promo.status == "active"


@pytest.mark.django_db
def test_roll_ends_active():
    promo = PromotionFactory(status="active", ends_at=timezone.now() - timedelta(minutes=1))
    out = roll_due_promotions()
    assert out["ended"] == 1
    promo.refresh_from_db()
    assert promo.status == "ended"


@pytest.mark.django_db
def test_roll_skips_not_yet_started():
    promo = PromotionFactory(status="scheduled", starts_at=timezone.now() + timedelta(hours=1))
    out = roll_due_promotions()
    assert out["activated"] == 0
    promo.refresh_from_db()
    assert promo.status == "scheduled"
