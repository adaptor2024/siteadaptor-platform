"""Тесты CRUD-вьюх каталога (через Django test client, с залогиненным юзером).

Урлы каталога живут в urls_tenant; тестовый клиент с ROOT_URLCONF по умолчанию
резолвит их, т.к. в тестах схема — public. Логин-гейт проверяем тоже.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from apps.catalog.models import Product
from apps.catalog.tests.factories import CategoryFactory, ProductFactory


@pytest.fixture
def auth_client(db):
    User = get_user_model()
    User.objects.create_user(username="owner", email="owner@test.de", password="pw12345678")
    c = Client()
    c.login(username="owner", password="pw12345678")
    return c


@override_settings(ROOT_URLCONF="config.urls_tenant")
@pytest.mark.django_db
def test_list_requires_login():
    c = Client()
    resp = c.get(reverse("catalog:product-list"))
    assert resp.status_code in (302, 301)  # redirect to login


@override_settings(ROOT_URLCONF="config.urls_tenant")
@pytest.mark.django_db
def test_list_shows_products(auth_client):
    ProductFactory(name={"de": "Brot", "en": "Bread"})
    resp = auth_client.get(reverse("catalog:product-list"))
    assert resp.status_code == 200
    assert b"Brot" in resp.content


@override_settings(ROOT_URLCONF="config.urls_tenant")
@pytest.mark.django_db
def test_create_product(auth_client):
    cat = CategoryFactory()
    resp = auth_client.post(
        reverse("catalog:product-create"),
        {
            "name_de": "Apfelstrudel",
            "name_en": "Apple strudel",
            "description_de": "",
            "description_en": "",
            "category": str(cat.pk),
            "base_price": "4.50",
            "currency": "EUR",
            "sku": "APF-1",
            "is_active": "on",
        },
    )
    assert resp.status_code == 302
    p = Product.objects.get(sku="APF-1")
    assert p.name["de"] == "Apfelstrudel"
    assert p.category_id == cat.pk


@override_settings(ROOT_URLCONF="config.urls_tenant")
@pytest.mark.django_db
def test_edit_product(auth_client):
    p = ProductFactory(name={"de": "Alt", "en": ""}, base_price="1.00")
    resp = auth_client.post(
        reverse("catalog:product-edit", args=[p.pk]),
        {
            "name_de": "Neu",
            "name_en": "",
            "description_de": "",
            "description_en": "",
            "base_price": "2.00",
            "currency": "EUR",
            "sku": "",
            "is_active": "on",
        },
    )
    assert resp.status_code == 302
    p.refresh_from_db()
    assert p.name["de"] == "Neu"
    assert str(p.base_price) == "2.00"


@override_settings(ROOT_URLCONF="config.urls_tenant")
@pytest.mark.django_db
def test_delete_product_is_soft(auth_client):
    p = ProductFactory()
    pk = p.pk
    resp = auth_client.post(reverse("catalog:product-delete", args=[pk]))
    assert resp.status_code == 302
    assert not Product.objects.filter(pk=pk).exists()
    assert Product.all_objects.filter(pk=pk).exists()


@override_settings(ROOT_URLCONF="config.urls_tenant")
@pytest.mark.django_db
def test_search_filters_by_sku(auth_client):
    ProductFactory(name={"de": "Brot"}, sku="AAA")
    ProductFactory(name={"de": "Kuchen"}, sku="BBB")
    resp = auth_client.get(reverse("catalog:product-list"), {"q": "AAA"}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    assert b"AAA" in resp.content
    assert b"BBB" not in resp.content
