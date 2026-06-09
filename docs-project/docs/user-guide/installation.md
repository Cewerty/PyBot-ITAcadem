# Установка

Канонические инструкции по локальному запуску находятся в корневом `README.md`. Ниже краткая версия, синхронизированная с текущим проектом.

## Требования

- Python 3.14+
- `uv`
- Docker + Compose plugin для рекомендуемого локального runtime-path
- доступ к Telegram Bot API

## Шаги

```bash
git clone https://github.com/NikkiShuRA/PyBot-ITAcadem.git
cd PyBot_ITAcadem
uv sync
```

Создайте `.env` на основе `.env.example` и задайте как минимум:

- `BOT_TOKEN`
- `BOT_TOKEN_TEST` if you plan to run with `BOT_MODE=test`
- `ROLE_REQUEST_ADMIN_TG_ID`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`

`.env.example` уже содержит опциональную переменную `TELEGRAM_PROXY_URL`. В обычной среде ее можно оставить пустой и заполнять только там, где Telegram Bot API доступен через proxy.

После этого можно применить миграции и поднять официальный локальный dev/prod-like path:

```bash
docker compose up -d --wait postgres redis
docker compose --profile migration run --rm migrate
just run-parity
curl -i http://127.0.0.1:8001/
curl -i http://127.0.0.1:8001/ready
```

Локальный и production runtime используют PostgreSQL 18. Внутри Compose приложение подключается по hostname `postgres`, а локальный PostgreSQL port публикуется только на `127.0.0.1:${POSTGRES_PORT:-5432}`. Обычный `docker compose up` не применяет Alembic migrations автоматически.

Этот путь считается официальным parity path, потому что он использует тот же Compose-based runtime, те же core process types, что и production, и дополнительно поднимает отдельный `health` process type для readiness-проверки.

`just run-parity` использует `LOG_FORMAT=json`, то есть тот же machine-readable logging contract, что и production/prod-like запуск.

Если нужен только базовый local runtime без отдельного `health` process type, используйте:

```bash
just run
```

`just run` использует `docker compose up --build` и поднимает `bot`, `taskiq-worker`, `taskiq-scheduler`, `postgres` и `redis`.

Прямой `uv run run.py` остаётся доступным как bot-only advanced path, но он не поднимает `worker`, `scheduler`, `postgres` и `redis`. Для него PostgreSQL и Redis должны быть доступны отдельно. Если `LOG_FORMAT` не задан явно, такой запуск может остаться на `text` — это осознанный debug/DX trade-off для ручного interactive path.

Если нужен именно официальный parity path для smoke-check и readiness, используйте:

```bash
just run-parity
```

Эта команда включает `HEALTH_API_ENABLED=true` и поднимает отдельный `health` process type тем же profile-based способом, что и production. `just run-health` остаётся совместимым alias.

Короткая локальная проверка после старта:

```bash
curl -i http://127.0.0.1:8001/
curl -i http://127.0.0.1:8001/ready
```

Успешный результат:

- `GET /` возвращает `200` и подтверждает, что health-процесс жив;
- `GET /ready` возвращает `200`, когда приложение реально готово.

Если нужен расширенный локальный observability stack без ручной сборки окружения, используйте:

```bash
just run-observability
```

Эта команда поднимает основной runtime вместе с `loki`, `alloy`, `grafana` и `nginx`, reuse-ит существующие production observability assets и по умолчанию открывает Grafana на `http://127.0.0.1:8088/grafana/`.

Локальный observability path считается успешным, когда:

- Grafana открывается по локальному URL;
- datasource Loki уже provisioned;
- в Loki/Grafana видны логи `bot`, `taskiq-worker` и `taskiq-scheduler`.

## Для документации

Чтобы локально собирать сайт на MkDocs Material:

```bash
just docs-install
just docs-build
```
