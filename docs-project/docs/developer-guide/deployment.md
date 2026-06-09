# Деплой

Полное описание деплоя находится в корневом `DEPLOYMENT.md`. Эта страница дает быстрый обзор для навигации в сайте документации.

## Базовый контур

1. CI на `main` должен пройти успешно.
2. Workflow `CD - Build and Deploy` собирает Docker image и публикует его в GHCR.
3. Ansible разворачивает `docker-compose.prod.yml` на сервере.
4. PostgreSQL 18 запускается и проходит healthcheck.
5. Отдельный backup-контейнер создаёт custom-format dump.
6. Отдельный migration-контейнер применяет миграции.
7. При явном `RUN_SEED_ON_DEPLOY=true` выполняется seed.
8. Запускается runtime и выполняется post-deploy smoke-check PostgreSQL, Redis и readiness API.

## Ключевые файлы

- `docker-compose.prod.yml`
- `.github/workflows/deploy.yml`
- `ansible/playbooks/bootstrap.yml`
- `ansible/playbooks/deploy.yml`

## Что не забывать

- синхронизировать `.env.example` и runtime config;
- использовать только `postgresql+asyncpg` URL, согласованный с `POSTGRES_*`;
- проверять PostgreSQL native enums, `BigInteger` PK/FK и Alembic drift;
- помнить, что текущая PostgreSQL baseline не обновляет старые SQLite базы и revision ID;
- проверять restore на тестовом стенде, а не только факт создания backup;
- документировать rollback и operator steps, если изменение не backward-compatible.
