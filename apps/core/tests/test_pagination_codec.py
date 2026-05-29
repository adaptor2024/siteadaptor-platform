"""Тесты курсор-кодека — чистый Python, без БД."""

from apps.core.pagination import _decode, _encode


def test_encode_decode_roundtrip():
    payload = {"v": "2026-05-29T10:00:00", "pk": "abc-123"}
    cursor = _encode(payload)
    assert _decode(cursor) == payload


def test_cursor_is_url_safe_base64():
    cursor = _encode({"v": 42, "pk": 7})
    # urlsafe base64 не содержит '+' и '/'
    assert "+" not in cursor and "/" not in cursor
    assert _decode(cursor) == {"v": 42, "pk": 7}
