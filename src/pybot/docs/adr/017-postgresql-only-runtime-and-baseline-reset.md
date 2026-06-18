# ADR 0017: PostgreSQL-only runtime и сброс Alembic baseline

## Дата: 10-06-2026

## Статус: Accepted

## Контекст

ADR 0004 перевёл проект с PostgreSQL на SQLite ради более простого MVP и
локального запуска. По мере развития проекта это решение перестало
соответствовать фактическим требованиям:

- bot, TaskIQ worker и scheduler образуют конкурентный runtime с несколькими
  процессами, работающими с одной БД;
- production deploy уже использует Docker Compose и может управлять отдельным
  database service без возвращения к ручной установке PostgreSQL;
- SQLite требует dialect-specific обходов для foreign keys, autoincrement,
  migrations и enum storage;
- схема использует связи, partial unique index и общие enum-контракты, которые
  естественнее и точнее выражаются средствами PostgreSQL;
- integration-тесты должны проверять поведение той же СУБД, которая работает в
  production;
- существующей production SQLite БД или legacy volume, данные из которых
  требуется переносить, нет.

Поддержка двух runtime backend увеличила бы объём схемных компромиссов,
тестирования и deploy-вариантов без продуктовой необходимости.

## Решение

Принято решение использовать **PostgreSQL 18 как единственную поддерживаемую
Dev/Test/Prod базу данных** и supersede ADR 0004.

### Схема и Alembic

1. Внутренние primary и foreign keys используют `BigInteger`. `Integer`
   сохраняется для неидентификационных бизнес-значений.
2. Схемные enum-поля используют именованные PostgreSQL native `ENUM`.
3. `DATABASE_URL` приложения и Alembic должен использовать
   `postgresql+asyncpg`.
4. Старая SQLite Alembic history удалена. Активная история начинается с одной
   PostgreSQL initial baseline с `down_revision = None`.
5. Baseline предназначена для новой PostgreSQL БД. Старые SQLite revision ID и
   данные не переносятся, upgrade path с SQLite не предоставляется.

### Runtime и deploy

1. Local и production Compose используют `postgres:18-alpine`.
2. Application services ждут healthy PostgreSQL и Redis.
3. PostgreSQL data хранится в отдельном persistent volume.
4. Custom-format dumps хранятся в отдельном backup volume.
5. Production deploy создаёт backup перед migration.
6. Restore является ручной destructive operation с явным подтверждением.
7. Migrations и seed остаются явными one-shot process types и не выполняются при обычном старте приложения.

### Тестирование

1. Integration-тесты выполняются на PostgreSQL 18.
2. Локально используется один Testcontainers container на тестовую сессию.
3. CI передаёт существующий PostgreSQL service через
   `PYBOT_TEST_DATABASE_URL`, чтобы не запускать второй container.
4. Тестовая схема создаётся через `alembic upgrade head`, а данные очищаются
   между тестами без пересоздания schema.
5. Unit-тесты остаются независимыми от Docker.

## Альтернативы

- **Сохранить SQLite для разработки, PostgreSQL только для production:**
  - *Плюсы:* локальный запуск базы не требует container.
  - *Минусы:* schema и integration-тесты продолжают работать на другом
    dialect; сохраняются SQLite-specific ограничения и риск production-only
    ошибок.

- **Поддерживать SQLite и PostgreSQL одновременно:**
  - *Плюсы:* больше вариантов локального запуска.
  - *Минусы:* двойная матрица тестирования, ограничения на native enums и
    migrations, более сложный runtime contract.

- **Перенести существующие SQLite данные и старую migration history:**
  - *Плюсы:* сохраняется upgrade path для legacy installations.
  - *Минусы:* существенно усложняет переход без фактического источника данных,
    который необходимо сохранить.

- **Использовать PostgreSQL 17:**
  - *Плюсы:* более длительный период эксплуатации на момент решения.
  - *Минусы:* новый кластер всё равно создаётся с нуля, поэтому выбор предыдущей
    major version сразу создаёт будущую задачу обновления без compatibility
    преимущества для проекта.

## Последствия

### Положительные

- [+] Dev, test и production используют один database dialect.
- [+] Удалены SQLite-specific runtime helpers и migration workarounds.
- [+] PK/FK, native enums, constraints и indexes проверяются на реальном PostgreSQL.
- [+] Конкурентные runtime-процессы работают с server-based СУБД.
- [+] Backup/restore и migration order становятся явной частью deploy flow.

### Отрицательные

- [-] Для integration-тестов и рекомендуемого локального runtime требуется
  Docker или отдельно доступный PostgreSQL.
- [-] Старые SQLite базы нельзя обновить текущей Alembic chain.
- [-] Удаление local PostgreSQL volume приводит к потере локальных данных, а backup volume требует ручной retention policy.
- [-] Major upgrade PostgreSQL в будущем потребует отдельного operator runbook и проверки backup/restore.

## Ссылки

- [ADR 0004: Миграция с PostgreSQL на SQLite](004-migration-from-PostgreSQL-to-SQLite.md)
- [ARCHITECTURE.md](../../../../ARCHITECTURE.md)
- [README.md](../../../../README.md)
- [DEPLOYMENT.md](../../../../DEPLOYMENT.md)
- [docker-compose.yml](../../../../docker-compose.yml)
- [docker-compose.prod.yml](../../../../docker-compose.prod.yml)
- [Alembic initial PostgreSQL baseline](../../../../alembic/versions/1de8107fe120_initial_postgresql_schema.py)
