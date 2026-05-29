# SiteAdaptor — Полное руководство разработчика

> **Единая пошаговая инструкция.** Здесь всё, что нужно, чтобы вести разработку
> от нуля до прод-запуска: команды, порядок спринтов, git-флоу, деплой. Остальные
> документы — это деталировка; ссылки на них по ходу.

Дата актуализации: 2026-05-29. Стек: Python 3.12 · Django 5.1 · django-tenants
(schema-per-tenant) · PostgreSQL 16 · Redis 7 · Celery 5 · HTMX/Alpine/Tailwind ·
allauth · dj-stripe · django-unfold · Caddy 2 · Hetzner Cloud (EU).

---

## 0. Карта документации (что где лежать)

| Файл | Для чего |
|---|---|
| **`docs/DEVELOPMENT-GUIDE.md`** (этот) | Главная инструкция. Начинай отсюда. |
| `docs/full-platform-vision.md` | Продуктовое видение целиком (Phase 1–3). |
| `docs/platform-core-architecture.md` | Архитектура: схемы, модели, потоки. |
| `docs/phase1-implementation-guide.md` | Деталировка спринтов Phase 1. |
| `docs/phase1-plan-additions.md` | **Слой улучшений** поверх плана (читать вместе с гайдом). |
| `docs/monetization-unit-economics.md` | Цены, тарифы, unit-экономика. |
| `docs/hetzner-claude-code-setup.md` | Поднятие серверов Hetzner. |
| `docs/references/patterns/*.md` | Готовые паттерны с кодом (см. §6). |

---

## 1. Архитектура за 2 минуты (что держать в голове)

- **Schema-per-tenant.** Каждый бизнес = отдельная PostgreSQL-схема. `django-tenants`
  определяет арендатора по домену (`Host`-заголовок → модель `Domain` → схема).
- **SHARED vs TENANT приложения** (`config/settings/base.py`):
  - `SHARED_APPS` (public-схема): `tenants`, admin, allauth, celery, djstripe,
    `aggregator`, `global_categories`.
  - `TENANT_APPS` (схема каждого бизнеса): `core`, `catalog`, `promotions`,
    `subscriptions`, `publishing`, `notifications`, `billing`.
  - Приложения раскомментируются в `base.py` **по мере прохождения спринтов**.
- **Два urlconf:**
  - `config/urls_public.py` — public-схема (главный домен `siteadaptor.de`): admin,
    агрегатор, health. **Django admin живёт только здесь.**
  - `config/urls_tenant.py` — субдомены бизнесов (`{slug}.siteadaptor.de`): дашборд,
    лендинг, health.
- **Поддомен → арендатор:** `baeckerei-test.siteadaptor.de` → строка `Domain` →
  схема `baeckerei_test`. Главный домен → public-схема.
- **Порядок миграций важен:** сначала `migrate_schemas --shared`, потом
  `migrate_schemas` (по всем tenant-схемам).
- **i18n-конвенция:** переводимые поля = `JSONField` вида `{"de": "...", "en": "..."}`.
  Язык по умолчанию `de`. Цепочка фолбэка: запрошенный → `default_locale` → `en` →
  первый доступный.
- **Сквозные конвенции** (см. паттерны §6): soft-delete (`deleted_at` + partial
  unique), `metadata = JSONField` на runtime-моделях, `dedupe_key` (unique) для
  идемпотентности, audit с первого дня, cursor-пагинация вместо offset.

---

## 2. Локальная разработка: первый запуск

```bash
# 1. uv (один раз)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. venv + зависимости
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. инфра (postgres + redis в docker)
docker compose up -d db redis

# 4. окружение
cp .env.example .env        # отредактируй SECRET_KEY и пр.

# 5. миграции: сначала shared, потом tenant
python manage.py makemigrations tenants
python manage.py migrate_schemas --shared

# 6. суперпользователь (public-схема)
python manage.py createsuperuser

# 7. тестовый арендатор (public + baeckerei_test в Hilden)
python manage.py create_test_tenant
# другой базовый домен:
python manage.py create_test_tenant --base-domain siteadaptor.de

# 8. dev-сервер
python manage.py runserver 0.0.0.0:8000
```

В отдельных терминалах (когда появятся задачи):

```bash
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Доступ:**
- Admin: http://localhost:8000/admin/
- Тестовый арендатор: http://baeckerei-test.siteadaptor.de:8000
- Health: http://localhost:8000/health/ · Readiness: http://localhost:8000/health/ready/

> **Локальные субдомены.** Либо настрой wildcard-DNS на dev-сервере
> (`*.siteadaptor.de` → IP), либо добавь в `/etc/hosts`:
> `127.0.0.1 baeckerei-test.siteadaptor.de`.

---

## 3. Ежедневный цикл разработки

```bash
# 0. свежий main
git checkout main && git pull origin main

# 1. ветка под задачу
git checkout -b claude/sprintN-taskX-краткое-описание

# 2. код + тесты ...

# 3. качество
ruff check .
ruff format .
pytest

# 4. миграции, если менял модели (ВСЕГДА проверяй обе команды)
python manage.py makemigrations <app>
python manage.py migrate_schemas --shared    # если менял SHARED-модель
python manage.py migrate_schemas             # tenant-схемы

# 5. коммит и пуш
git add -A
git commit -m "Sprint N / Task X: что сделано"
git push -u origin <branch>
```

Дальше — Pull Request в `main`, ревью, merge. Деплой на сервер — отдельный шаг (§5).

**Правило миграций:** меняешь `SHARED_APPS`-модель (`Tenant` и пр.) →
`migrate_schemas --shared`. Меняешь `TENANT_APPS`-модель (`Product` и пр.) →
`migrate_schemas`. Сомневаешься — гоняй обе.

---

## 4. Дорожная карта Phase 1 (6 спринтов, ~13 недель)

Для каждого спринта: задачи + Definition of Done. Деталировка — в
`phase1-implementation-guide.md`, улучшения — в `phase1-plan-additions.md`.

### Sprint 1 — Foundation & Multi-tenancy ✅ (1.1–1.2 готовы)
- **1.1** Bootstrap: Django, settings (base/dev/prod), `pyproject.toml`, `.env`. ✅
- **1.2** Модели `Tenant`/`Domain`, admin (unfold), `create_test_tenant`. ✅
- **1.3** `apps/core/`: `TimestampedModel`, `SoftDeleteMixin`, audit-модуль, `pagination.py`, FSM-база.
- **1.4** Auth: allauth (login/signup, email-verification).
- **1.5** CI: GitHub Actions (`ruff` + `pytest`), pre-commit.
- **1.6** Scaffold `apps/integrations/webhooks/` (только модели).

**DoD:** `migrate_schemas --shared` чисто · тестовый арендатор резолвится на
субдомене · **изоляция арендаторов проверена тестом** (есть:
`apps/tenants/tests/test_isolation.py`) · `pytest` зелёный, `ruff` чистый · audit
пишется на создание Tenant и login/logout.

> Паттерны для 1.3/1.6: `soft-delete.md`, `audit-log.md`, `cursor-pagination.md`,
> `webhook-hmac-signing.md`.

### Sprint 2 — Catalog & Dashboard
- **2.1** Модели `Product`/`Category` (JSONField i18n, иерархия).
- **2.2** CRUD-дашборд продуктов (HTMX + Alpine + Tailwind).
- **2.3** Загрузка картинок (FileRef-envelope, S3/Hetzner Object Storage).
- **2.4** 4-шаговый CSV-импорт (`uploaded→mapped→previewed→running→completed`).
- **2.5** Управление категориями.

**DoD:** владелец создаёт/редактирует/удаляет товары · CSV-импорт с маппингом
колонок и превью · картинки в object storage · поля de/en редактируются.

> Паттерны: `csv-import-wizard.md`, `soft-delete.md`.

### Sprint 3 — Promotions & Reservations
- **3.1** `Promotion` + FSM (`draft→scheduled→active→ended`).
- **3.2** `Reservation` + анти-oversell (conditional UPDATE + `F()`).
- **3.3** FSM-фреймворк (явные переходы).
- **3.4** Дашборд акций + планирование.
- **3.5** Поток резервирования + кнопка для покупателя.

**DoD:** переходы статуса акции форсятся · 100 параллельных резерваций →
ровно N успешных (ноль перепродаж) · beat-задача авто-активирует/завершает акции
· `metadata` на `Reservation`.

> Паттерны: `anti-oversell.md`, `state-machine.md`.

### Sprint 4 — Publishing & Landing Pages
- **4.1** `Channel`/`Publication` (**`dedupe_key`, идемпотентность — в ядре, не опция**).
- **4.2** `BasePublisher` + audit-callback; Telegram-публикатор.
- **4.3** Celery-задачи публикации (идемпотентные, с ретраями).
- **4.4** Лендинг арендатора (субдомен, активные акции).
- **4.5** SEO-база (meta, OpenGraph, sitemap).

**DoD:** активация акции публикует в каналы · повторная публикация идемпотентна
(нет дублей) · лендинг рендерится на субдомене · упавшая публикация ретраится с
backoff.

> Паттерны: `notification-dedupe.md` (Publication idempotency), `state-machine.md`.

### Sprint 5 — Aggregator & Customer Experience
- **5.1** `AggregatorListing` (денормализованный) + sync-задача (без обхода схем!).
- **5.2** Фид (cursor-пагинация, anti-spam reorder), `search_vector` (полнотекст).
- **5.3** Magic-link авторизация покупателя.
- **5.4** Facets-эндпоинт (counts по категории/городу/цене, кэш 60с).
- **5.5** Подписки покупателя (таргет по категории/городу).
- **5.6** `AggregatorPortal` — шов под вертикальные/мультидоменные агрегаторы
  (Phase 1 — один портал; мультидомен — Phase 2).

**DoD:** фид показывает акции всех бизнесов города · cursor-пагинация работает ·
покупатель входит по magic-link · не более 2 акций одного бизнеса подряд.

> Паттерны: `cursor-pagination.md`, `magic-link-auth.md`.

### Sprint 6 — Notifications, Billing & Launch
- **6.1** `Notification` (`dedupe_key`, мультиканальность).
- **6.2** Email (Resend) + Web Push (pywebpush/VAPID).
- **6.3** `idempotent_task` обёртка для всех рисковых задач.
- **6.4** Stripe (dj-stripe), тарифы, жизненный цикл триала.
- **6.5** Напоминания о триале + FSM подписки (`trial→active→past_due→suspended`).
- **6.6** Прод-деплой, мониторинг (Sentry), launch-чеклист.

**DoD:** подписчик получает уведомление о подходящей акции · Stripe checkout +
webhook обновляет `subscription_status` · авто-истечение триала (3d/1d напоминания
→ suspend) · прод развёрнут, SSL, мониторинг.

> Паттерны: `notification-dedupe.md`, `state-machine.md` (subscription lifecycle).
> Цены/тарифы — `monetization-unit-economics.md` (свериться перед биллингом).

---

## 5. Деплой на сервер

### 5.1 Топология (см. `hetzner-claude-code-setup.md`)
- **App-сервер** CPX21 (~€7/мес): Django (gunicorn) + Celery worker/beat + Redis +
  Caddy. Здесь живёт репозиторий и запускается деплой.
- **DB-сервер** CCX13 (~€17/мес): PostgreSQL 16. Связан с app по приватной сети,
  задаётся через `DB_HOST` в `.env.prod`.
- Claude Code на прод-серверы **не ставится**.

### 5.2 Разовая подготовка сервера
```bash
# на app-сервере, под пользователем deploy
sudo mkdir -p /opt && cd /opt
git clone <repo-url> siteadaptor-platform
cd siteadaptor-platform
cp .env.prod.example .env.prod      # заполни все CHANGE-ME (БД, Stripe, Resend, S3,
                                    # SECRET_KEY, HETZNER_DNS_API_TOKEN)

# DNS: A-записи *.siteadaptor.de и siteadaptor.de → публичный IP app-сервера.
# Caddy выпускает wildcard-сертификат через DNS-01 (нужен HETZNER_DNS_API_TOKEN).

# Первый запуск + первичные данные
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml run --rm web python manage.py migrate_schemas --shared
docker compose -f docker-compose.prod.yml run --rm web python manage.py createsuperuser
docker compose -f docker-compose.prod.yml run --rm web python manage.py create_test_tenant --base-domain siteadaptor.de
docker compose -f docker-compose.prod.yml up -d
```

### 5.3 Команда деплоя (каждый релиз)

**С локальной машины — одной командой:**
```bash
ssh hetzner-app 'cd /opt/siteadaptor-platform && ./scripts/deploy.sh'
```

**Или на самом сервере:**
```bash
cd /opt/siteadaptor-platform && ./scripts/deploy.sh
```

`scripts/deploy.sh` делает: `git pull` (main) → `build` → `migrate_schemas --shared`
→ `migrate_schemas` → `collectstatic` → `up -d` → `check --deploy` → проверка
`/health/ready/`. Идемпотентно, безопасно гонять повторно.

> **Что такое «миграция» здесь:** Django-миграции БД (напр. `0002_tenant_indexes`)
> применяются шагами `migrate_schemas` внутри деплоя — на сервере, не из git
> напрямую. PR/merge сам по себе ничего на сервере не меняет; выкат запускает
> `deploy.sh`.

### 5.4 Полезное при эксплуатации
```bash
COMPOSE="docker compose -f docker-compose.prod.yml"
$COMPOSE logs -f web              # логи приложения
$COMPOSE logs -f worker           # логи celery
$COMPOSE ps                       # статус сервисов
$COMPOSE exec web python manage.py shell
# Откат: git checkout <prev-tag> && ./scripts/deploy.sh
```

> **DNS-провайдер.** `caddy/Dockerfile` собран с плагином Hetzner DNS. Если домен
> на другом провайдере (Cloudflare и т.п.) — поменяй модуль `--with
> github.com/caddy-dns/<provider>` и соответствующий токен в `.env.prod`.

---

## 6. Каталог паттернов (`docs/references/patterns/`)

Готовые решения с кодом под наш стек. Используй при реализации соответствующих задач.

| Паттерн | Когда | Спринт |
|---|---|---|
| `soft-delete.md` | мягкое удаление, partial unique | 1 |
| `audit-log.md` | журнал действий, нельзя backfill | 1 |
| `cursor-pagination.md` | keyset-пагинация лент | 1 / 5 |
| `webhook-hmac-signing.md` | исходящие вебхуки с HMAC | 1 / 2 |
| `csv-import-wizard.md` | 4-шаговый импорт | 2 |
| `anti-oversell.md` | резервации без перепродажи | 3 |
| `state-machine.md` | FSM статусов (Promotion/Reservation/Subscription) | 3 / 6 |
| `notification-dedupe.md` | идемпотентность уведомлений/публикаций | 4 / 6 |
| `magic-link-auth.md` | беспарольный вход покупателя | 5 |

---

## 7. Быстрый справочник команд

```bash
# Миграции
python manage.py makemigrations <app>
python manage.py migrate_schemas --shared           # public
python manage.py migrate_schemas                     # все tenant-схемы
python manage.py migrate_schemas --schema=baeckerei_test   # одна схема

# Арендаторы
python manage.py create_test_tenant [--base-domain siteadaptor.de]

# Запуск
python manage.py runserver 0.0.0.0:8000
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Качество
ruff check . && ruff format . && pytest

# Деплой
ssh hetzner-app 'cd /opt/siteadaptor-platform && ./scripts/deploy.sh'
```

**Внешние ссылки:** uv — https://astral.sh/uv · Hetzner Console —
https://console.hetzner.com/projects · DNS-плагины Caddy —
https://github.com/caddy-dns
