# Конфигурация

Настройки приложения определены в [`pybot.core.config.BotSettings`](../api-reference/core.md). Источником значений служит `.env`.

Отдельно от `BotSettings` есть orchestration-переменные уровня Compose/runtime. Сейчас это `TASKIQ_WORKERS`: она управляет числом worker-процессов TaskIQ в `docker-compose.yml` и `docker-compose.prod.yml`, а не бизнес-конфигом Python-приложения.

## Обязательные переменные

| Переменная | Назначение |
| --- | --- |
| `BOT_TOKEN` | production-токен бота |
| `BOT_TOKEN_TEST` | тестовый токен |
| `BOT_MODE` | режим `test` или `prod` |
| `ROLE_REQUEST_ADMIN_TG_ID` | Telegram ID администратора для role request |
| `DATABASE_URL` | строка подключения к SQLite; канонический runtime path — `sqlite+aiosqlite:///./data/pybot_itacadem.db` |

## Часто используемые параметры

| Переменная | Что регулирует |
| --- | --- |
| `LOG_LEVEL` | уровень логирования |
| `LOG_FORMAT` | формат stdout-логов: `text` или `json` |
| `DEBUG` | debug-режим |
| `FSM_STORAGE_BACKEND` | backend хранения FSM |
| `REDIS_URL` | Redis для FSM и TaskIQ |
| `NOTIFICATION_BACKEND` | `telegram` или `logging` |
| `TELEGRAM_PROXY_URL` | optional proxy для Telegram Bot API |
| `RUNTIME_ALERTS_ENABLED` | включает runtime alerts для bot startup/shutdown |
| `RUNTIME_ALERTS_CHAT_ID` | chat id для runtime alerts |
| `HEALTH_API_ENABLED` | отдельный health API |
| `TASKIQ_WORKERS` | concurrency `taskiq-worker` в Compose; сейчас поддерживается только `1` |

## Logging contract

`BOT_MODE` и `LOG_FORMAT` решают разные задачи:

- `BOT_MODE` выбирает runtime mode и активный bot token;
- `LOG_FORMAT` выбирает формат stdout-логов.

Рекомендуемый контракт такой:

- `just run-parity` / `HEALTH_API_ENABLED=true docker compose --profile health up --build` — официальный local dev/prod-like parity path, поэтому здесь используется `LOG_FORMAT=json`;
- `just run` / `docker compose up --build` — базовый local runtime без отдельного `health` process type, но с тем же machine-readable logging contract;
- production runtime тоже использует `LOG_FORMAT=json`;
- `uv run run.py` остаётся manual bot-only/debug path и может использовать `text`, если `LOG_FORMAT` не задан явно.

То есть `BOT_MODE=test` не означает автоматически, что любой локальный запуск обязан использовать `text`. Для Compose-based local runtime формат логов задаётся отдельно и сознательно.

## Local observability profile

Локальный Compose также поддерживает opt-in profile `observability`.

- `just run` оставляет локальный runtime лёгким и поднимает только app-сервисы и Redis;
- `just run-observability` включает `loki`, `alloy`, `grafana` и `nginx` поверх того же runtime;
- local observability path reuse-ит конфиги из `observability/`, но не требует production host nginx или public HTTPS;
- локальный ingress считается HTTP-only и по умолчанию использует `http://127.0.0.1:8088/grafana/`.

Для этого сценария локальный Compose уже содержит безопасные defaults для Grafana/nginx, поэтому отдельный `.env` только ради observability-контура не нужен.

## Local health profile

Локальный Compose также поддерживает opt-in profile `health`.

- `just run` не поднимает отдельный health-process type;
- `just run-parity` включает `HEALTH_API_ENABLED=true` и запускает тот же отдельный `health` process type, который используется в production;
- `just run-parity` считается одним официальным local parity path для smoke-check и readiness, а `just run` остаётся более лёгким runtime-сценарием;
- `just run-health` остаётся совместимым alias для плавного перехода;
- локальный smoke-check идёт напрямую в health API порт, а не через production ingress path.

Каноническая локальная проверка:

- `GET http://127.0.0.1:8001/` — liveness, ожидается `200`;
- `GET http://127.0.0.1:8001/ready` — readiness, ожидается `200`, когда приложение готово.

## Orchestration-переменные

`TASKIQ_WORKERS` управляет worker concurrency на уровне Compose:

- по умолчанию используется `${TASKIQ_WORKERS:-1}`;
- текущее поддерживаемое значение только `1`;
- синтаксис для будущего масштабирования уже заложен, но значения больше `1` пока намеренно отклоняются fail-fast guard-ом.

Примеры:

```bash
TASKIQ_WORKERS=1 docker compose up --build
TASKIQ_WORKERS=1 docker compose -f docker-compose.prod.yml up -d
```

Синтаксис вида `TASKIQ_WORKERS=2 ...` зарезервирован на будущее, но в текущей системе не поддерживается.

## Broadcast-настройки

В `BotSettings` также есть группа параметров для рассылок:

- `BROADCAST_BULK_SIZE`
- `BROADCAST_MAX_CONCURRENCY`
- `BROADCAST_BATCH_PAUSE_MS`
- `BROADCAST_JITTER_MIN_MS`
- `BROADCAST_JITTER_MAX_MS`
- `BROADCAST_RETRY_ATTEMPTS`
- `BROADCAST_RETRY_MAX_WAIT_S`

!!! tip "Практика"
    Для локальной разработки по умолчанию удобнее держать `BOT_MODE=test`, `FSM_STORAGE_BACKEND=redis` и SQLite в каталоге проекта, а официальный parity path поднимать через `just run-parity`. Если нужен только более быстрый базовый runtime без readiness-процесса, используйте `just run` / `docker compose up --build`.

`FSM_STORAGE_BACKEND=memory` остаётся поддерживаемым, но только как явный opt-in fallback для bot-only debug path. Если вы запускаете только `uv run run.py`, Redis должен быть уже доступен отдельно, если backend не переключён вручную на `memory`.

`TELEGRAM_PROXY_URL` можно оставить пустым. Переменная нужна только для окружений, где доступ к Telegram Bot API возможен через proxy.

`RUNTIME_ALERTS_ENABLED` и `RUNTIME_ALERTS_CHAT_ID` тоже являются опциональными. В v1 они покрывают только lifecycle основного `bot` runtime: startup-уведомление идет через TaskIQ, а shutdown-уведомление отправляется напрямую как best effort.
