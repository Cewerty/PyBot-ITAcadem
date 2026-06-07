# ADR 0016: Режимный контракт BOT_MODE и LOG_FORMAT

## Дата: 28-05-2026

## Статус: Accepted

## Контекст

В проекте постепенно сформировались две разные оси runtime-конфигурации, которые легко смешать:

- `BOT_MODE` выбирает рабочий режим бота и соответствующий токен (`BOT_TOKEN_TEST` или `BOT_TOKEN`);
- `LOG_FORMAT` определяет, в каком формате runtime пишет логи в stdout.

При этом фактический контракт уже стал неоднородным и без явной фиксации выглядит двусмысленно:

- в `AppSettings` default `LOG_FORMAT` выводится из `BOT_MODE`: `text` для `BOT_MODE=test` и `json` для `BOT_MODE=prod`;
- `.env.example` уже задаёт `LOG_FORMAT=json`;
- `docker-compose.prod.yml` жёстко фиксирует `LOG_FORMAT=json`;
- canonical local runtime теперь запускается через `just run` / `docker compose up --build`, то есть через Compose-based path;
- ручной bot-only запуск через `uv run run.py` остаётся отдельным developer path и может вести себя иначе, если `LOG_FORMAT` не задан явно.

Без отдельного решения становится неясно, какое из различий является intentional, а какое — случайным drift между локальной разработкой, prod-like запуском и production runtime.

## Решение

Принято решение считать `BOT_MODE` и `LOG_FORMAT` **разными осями runtime-контракта** и зафиксировать их независимую семантику.

### Детали реализации

1. `BOT_MODE` отвечает только за runtime mode и выбор активного bot token.
2. `LOG_FORMAT` отвечает только за формат логового вывода (`text` или `json`).
3. Canonical local runtime через `just run` / Docker Compose использует `json` как prod-like logging contract.
4. Production runtime использует `json` как основной machine-readable формат для observability и log shipping.
5. Ручной bot-only запуск через `uv run run.py` допускает `text`, если `LOG_FORMAT` не задан явно. Это считается осознанным DX trade-off в пользу читаемости interactive/debug path, а не отклонением от production contract.
6. `.env.example` и Compose-конфигурация задают canonical local/prod-like logging path и не должны трактоваться как случайный override над неявным runtime default.
7. Документация должна явно различать:
   - Compose/prod-like runtime path;
   - manual bot-only/debug path;
   - роль `BOT_MODE` и роль `LOG_FORMAT`.

Иными словами, `BOT_MODE=test` не означает автоматически “нужны text-логи в любом локальном сценарии”. Для canonical Compose-based local runtime формат логов задаётся отдельно и сознательно.

## Альтернативы

- **Использовать `json` везде, включая manual bot-only path:**
  - *Плюсы:* максимальная консистентность между всеми runtime-сценариями.
  - *Минусы:* ручной локальный debug-path становится менее удобным для чтения человеком без log collector tooling.

- **Использовать `text` для любого локального запуска, а `json` только в production:**
  - *Плюсы:* проще локальная отладка и визуальное чтение логов.
  - *Минусы:* canonical local runtime отдаляется от production observability contract и хуже моделирует prod-like запуск.

- **Не фиксировать решение отдельным ADR и оставить только пояснение в docs:**
  - *Плюсы:* меньше архитектурной документации.
  - *Минусы:* contract остаётся слабее, его проще случайно размыть следующими config/runtime изменениями.

## Последствия

### Положительные

- [+] Уменьшается неявность между dev, prod-like и production logging behavior.
- [+] Проще объяснять, почему Compose-based local runtime использует `json`, даже если `BOT_MODE=test`.
- [+] Logging contract становится устойчивее к будущим изменениям в `.env.example`, Compose и runtime bootstrap.
- [+] Проще поддерживать observability-oriented сценарии без смешения их с token/runtime mode semantics.

### Отрицательные

- [-] Сохраняется split между Compose path и manual bot-only path, и его нужно помнить при локальной отладке.
- [-] Разработчику нужно понимать, что `BOT_MODE` и `LOG_FORMAT` независимы и не должны читаться как одна настройка “режима запуска”.

## Ссылки

- [ADR 0009: Минимальный контракт событийного логирования](009-minimal-logging-event-contract.md)
- [ADR 0013: Границы конфигурации, fail-fast и явная инъекция настроек](013-configuration-runtime-boundaries-and-explicit-injection.md)
- [src/pybot/core/config.py](../../core/config.py)
- [src/pybot/core/logger.py](../../core/logger.py)
- [docker-compose.prod.yml](../../../../docker-compose.prod.yml)
- [README.md](../../../../README.md)
- [docs-project/docs/user-guide/configuration.md](../../../../docs-project/docs/user-guide/configuration.md)
