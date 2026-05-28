"""pytest-django настройка для tenants-приложения.

django-tenants управляет схемами вручную: миграции каждой схемы запускаются
через `migrate_schemas`, а стандартная pytest-django fixture `db` ставит
только public-схему. Этого достаточно для тестов Tenant/Domain, которые
живут в public.

Тесты, которые реально создают tenant-схемы (`auto_create_schema=True`),
помечены `transaction=True` и сами зачищают за собой через
`DROP SCHEMA ... CASCADE`.
"""
