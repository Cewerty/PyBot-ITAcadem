# План развития PyBot ITAcadem на июнь 2026

## Формат и горизонт

План рассчитан на четыре рабочие недели с момента начала исполнения и использует MoSCoW:

- **Must** — обязательный результат месяца. Без него период не считается закрытым.
- **Should** — важное продолжение, которое выполняется только после стабилизации Must.
- **Could** — ограниченные улучшения при наличии реального остатка времени.
- **Won't this month** — сознательно исключённые задачи, а не забытый долг.

## Контекст

- Первоначальный MVP фактически сдан; система задач была исключена из его фактического scope.
- Ближайшая практическая цель — довести текущего бота до устойчивой работы в клубном чате.
- Переход с SQLite на PostgreSQL нужно выполнить до накопления живых данных и новых интеграций.
- Публичный endpoint `monitoring.probochka-corp.ru` больше не доступен проекту: конфигурация была удалена владельцем shared host, поэтому работоспособный observability-контур сейчас не имеет внешнего маршрута.
- MCP-сервер относится к следующему этапу развития продукта и требует собственного контракта доступа, auth/authz и аудита.
- Регламент клуба задаёт долгосрочный вектор развития, но не является acceptance criteria текущего месяца.
- Проект развивается одним разработчиком, поэтому параллельное ведение нескольких крупных эпиков запрещено.

## Цель месяца

Закрыть техническую финализацию версии `v1`: перевести production-контур на PostgreSQL, проверить основные сценарии в клубном чате и устранить подтверждённые release-blocking дефекты. После стабилизации `v1` подготовить ограниченный и безопасный фундамент MCP-сервера без превращения июня в разработку образовательной SaaS-платформы.

## Ограничения выполнения

- Одновременно в работе находится не более одной задачи уровня epic.
- Не менее 20% доступного времени остаётся на регрессии, документацию, здоровье и непредвиденные проблемы.
- Новые продуктовые пожелания попадают в inbox и не меняют Must без явного снятия другой задачи.
- После двух последовательных дней без измеримого продвижения задача уменьшается или возвращается на перепроектирование.
- Работа после прохождения критериев завершения не продолжается ради дополнительного polishing.
- Broad review и broad security audit не повторяются без нового threat surface или конкретного сигнала.

## Must

### M1. Перевести runtime с SQLite на PostgreSQL

**Результат:** local, CI и production runtime используют согласованный PostgreSQL-контракт.

- Принять новый ADR, superseding ADR-0004, и зафиксировать причины возвращения к PostgreSQL.
- Проверить ORM-модели, типы PK/FK, ограничения, enum/string storage и dialect-specific поведение.
- Подготовить PostgreSQL-сервис и healthcheck в local/prod Compose.
- Обновить `DATABASE_URL`, settings boundary, `.env.example`, CI/CD и deploy validation.
- Проверить Alembic upgrade на чистой PostgreSQL.
- Подготовить перенос существующих данных SQLite или явно зафиксировать clean-start стратегию.
- Проверить seed/bootstrap на PostgreSQL и исправить dialect-specific ошибки.
- Обновить backup/restore и operator runbook для PostgreSQL.
- Прогнать targeted repository/service tests и полный `just quality-gate`.
- Выполнить локальный parity smoke после переключения.

**Не входит:** переписывание repository layer без подтверждённой необходимости и одновременная поддержка двух production СУБД.

**DoD:**

- чистая PostgreSQL поднимается одной документированной командой;
- `alembic upgrade head` и seed завершаются успешно;
- bot, worker, scheduler и health используют одну PostgreSQL;
- основные flows проходят smoke;
- rollback или recovery path описан;
- SQLite больше не заявлена как production backend.

### M2. Исправить exit semantics seed-процесса

**Результат:** ошибка seed никогда не выглядит успешным one-shot процессом.

- После rollback пробрасывать ошибку или завершать CLI с ненулевым exit code.
- Проверить, какие seed-шаги уже фиксируют отдельные транзакции, и честно определить atomicity contract.
- Добавить тесты на успешный seed, rollback и ненулевой exit при ошибке.
- Проверить поведение local Compose, production one-shot service и Ansible deploy.

**DoD:** CI/CD и оператор однозначно отличают успешный seed от неуспешного.

### M3. Завершить controlled rollout бота в клубном чате

**Результат:** текущая версия работает не только как технический runtime, но и в целевом Telegram-чате.

- Зафиксировать production chat/thread IDs и доступные роли без помещения секретов в репозиторий.
- Проверить `/start`, `/help`, `/profile`, роли, компетенции, баллы, leaderboard и broadcast.
- Проверить permissions бота, reply/mention resolution, HTML rendering и rate-limit UX.
- Проверить admin-only команды и deny paths обычного пользователя.
- Проверить уведомления, TaskIQ worker/scheduler и readiness после реального deploy.
- Исправлять только дефекты, обнаруженные в критических сценариях rollout.
- Зафиксировать smoke checklist и release note для `v1`.

**DoD:** существует воспроизводимый smoke-протокол, критические сценарии пройдены в клубном чате, найденные blocker/high дефекты закрыты.

### M4. Восстановить публичный доступ к monitoring и health

**Результат:** у production observability-контура снова есть стабильный HTTPS endpoint, не конфликтующий с конфигурацией владельца shared host.

- Согласовать и создать отдельную DNS-запись для проекта; предпочтительный кандидат — `bot.monitoring.probochka-corp.ru`, итоговое имя определяется доступным DNS-контрактом.
- Подготовить отдельный host Nginx site, который не перезаписывает и не захватывает конфигурацию основного `monitoring.probochka-corp.ru`.
- Выпустить отдельный TLS-сертификат через существующий Certbot webroot и проверить автоматическое продление.
- Обновить `PUBLIC_DOMAIN`, production environment, deploy validation и operator runbook под согласованный поддомен.
- Проверить внешний маршрут до `/health/`, `/health/ready` и `/grafana/`, включая HTTP -> HTTPS redirect и корректный SAN сертификата.
- Зафиксировать владельца DNS/Nginx-конфигурации и recovery-порядок на случай повторного удаления конфигурации shared host.
- Не помещать DNS credentials, сертификаты, приватные ключи или содержимое production `.env` в репозиторий.

**DoD:** новый поддомен разрешается через публичный DNS, обслуживается по HTTPS, открывает Grafana и health endpoints снаружи, проходит внешний smoke-check и не зависит от владения старым endpoint `monitoring.probochka-corp.ru`.

### M5. Зафиксировать границы `v1` и контракт следующего этапа

**Результат:** у проекта появляется административная конечность.

- Создать краткую traceability-матрицу: первоначальное ТЗ -> реализовано / изменено / исключено / post-MVP.
- Зафиксировать interface drift ролей и исключение task subsystem из `v1`.
- Разделить backlog на bot v1 hardening, MCP и долгосрочную платформу.
- Для MCP подготовить PRD-lite:
  - конкретные actors и use cases;
  - список read/write operations;
  - tool use против MCP transport;
  - auth/authz boundary;
  - audit requirements;
  - запрещённые операции;
  - failure и rollback semantics.
- Не принимать формулировку "добавить больше функциональности" без сценария и acceptance criteria.

**DoD:** `v1` имеет явный состав и дату закрытия, а MCP не может незаметно расшириться до всей системы.

### M6. Обязательная проверка результата месяца

- Targeted tests выполняются после каждого завершённого slice.
- `just quality-gate` проходит после PostgreSQL migration и перед release.
- `just docs-build` проходит после обновления документации.
- Выполнены migration, seed, parity и club-chat smoke.
- Выполнен внешний HTTPS smoke нового monitoring-поддомена.
- Проверено отсутствие новых mojibake и утечек секретов.
- Невыполненные проверки явно записаны в итог месяца.

## Should

Should выполняется строго по порядку. Следующая задача не начинается, пока предыдущая не завершена или явно снята.

### S1. Реализовать минимальный MCP-сервер

**Результат:** один небольшой вертикальный срез поверх существующих services/DTO, а не второй application layer.

- Использовать уже подготовленный план MCP и PRD-lite из M4.
- Начать с минимального transport и локального/закрытого deployment mode.
- Первая версия по умолчанию read-only.
- Экспортировать только 2-4 конкретных resources/tools с доказанной пользой.
- Не обращаться к БД напрямую из MCP presentation/adapter.
- Добавить typed contracts, error mapping, tests и audit-ready metadata.
- Write tools не включать без завершённых auth/authz и Audit Log contracts.

**Предпочтительный первый slice:** health/runtime status и безопасные агрегированные данные без массовой выдачи PII.

### S2. Добавить canary-проверку TaskIQ worker

- Canary должна подтверждать прохождение задачи через broker и реальное исполнение worker, а не наличие контейнера.
- Определить timeout, failure signal и место отображения статуса.
- Интегрировать проверку в post-deploy smoke или readiness без превращения её в тяжёлую постоянную нагрузку.
- Добавить targeted tests и operator guidance.

### S3. Унифицировать logging contract и сократить PII

- Разделить обязательные operational fields и пользовательский content.
- Не логировать message content по умолчанию; sensitive flows должны использовать strict policy.
- Не логировать DTO пользователя целиком.
- Редактировать credentials в URL и exception context.
- Согласовать bot, TaskIQ, health и notification event naming.
- Обновить тесты logging policy.

### S4. Подготовить минимальный Audit Log foundation

- Определить audit event: actor, action, target, outcome, timestamp, correlation ID.
- Отличить security/business audit от обычных application logs.
- Покрыть сначала административные изменения ролей и баллов.
- Не строить универсальную event platform до появления MCP write tools.

## Could

Выбирается не более одной продуктовой и одной внутренней задачи.

### Продуктовые кандидаты

- Добавить команду просмотра собственных баллов и баллов указанного пользователя.
- Добавить команду просмотра пользователей с pagination и role protection.
- Добавить редактирование профиля через staged-flow.
- Перевести одну наиболее сложную административную команду на staged-flow.
- Добавить blacklist для role requests.
- Добавить поддержку Telegram tags, если определён точный пользовательский сценарий.

### Внутренние кандидаты

- Начать разбиение `presentation/texts/texts.py` на:
  - Telegram-specific renderers;
  - общие безопасные шаблоны;
  - feature-oriented text modules.
- Перевести broadcast dispatch на существующий TaskIQ-контур.
- Добавить Webhook mode как опциональный runtime profile, не заменяя polling без production-причины.
- Подготовить ADR для Messaging Patterns, если появился конкретный delivery/retry problem.
- Провести узкий security review нового PostgreSQL/MCP surface.
- Провести узкий code review изменённых migration/runtime/MCP модулей.

## Won't This Month

Следующие задачи сознательно не входят в июнь:

- полноценная система задач;
- доменные события через FastStreams;
- общий event-driven слой и полный набор Messaging Patterns;
- интеграция API колледжа и Circuit Breaker;
- PoS SQLAdmin;
- полноценная JWT auth-platform для SQLAdmin и MCP одновременно;
- MCP write access без auth/authz и Audit Log;
- SaaS/multi-tenant архитектура;
- multi-instance bot/worker support;
- массовый рефакторинг всех handlers и команд;
- повторный полный security audit и полный code review всего репозитория;
- одновременная реализация Webhook и переработка Telegram runtime;
- большие новые функции без PRD и acceptance criteria.

Эти задачи возвращаются в план только после закрытия `v1`, стабилизации PostgreSQL и оценки фактической нагрузки.

## План по неделям

### Неделя 1. Контракт PostgreSQL и подготовка миграции

- ADR и решение по переносу данных.
- Аудит моделей и миграций под PostgreSQL.
- Compose, settings, CI и deploy wiring.
- Тестовый `alembic upgrade head`.
- Начало исправления seed semantics.

**Checkpoint:** чистая PostgreSQL принимает схему, а объём оставшихся несовместимостей известен.

### Неделя 2. Завершение миграции и regression pass

- Seed/bootstrap и repository/service tests на PostgreSQL.
- Data transfer rehearsal или clean-start verification.
- Backup/restore и deploy runbook.
- Полный parity runtime.
- `just quality-gate`.

**Checkpoint:** PostgreSQL migration соответствует DoD M1, rollback/recovery описан.

### Неделя 3. Controlled production rollout

- Production deploy.
- Настройка отдельного DNS, host Nginx и TLS для нового monitoring-поддомена.
- Внешний smoke Grafana и health endpoints.
- Club-chat smoke.
- Исправление только blocker/high дефектов.
- TaskIQ canary, если M1-M3 стабильны.
- Release note и traceability `v1`.

**Checkpoint:** версия `v1` считается закрытой и пригодной для внутренней эксплуатации, а monitoring и health снова доступны через отдельный публичный HTTPS endpoint.

### Неделя 4. MCP foundation и резерв

- PRD-lite и threat/access boundary MCP.
- Минимальный read-only MCP slice.
- Logging/Audit Log foundation при необходимости для выбранного slice.
- Буфер на дефекты PostgreSQL и реального rollout.

**Checkpoint:** либо есть небольшой проверенный MCP slice, либо документировано, почему резерв был потрачен на стабилизацию `v1`. Второй исход не считается провалом месяца.

## Stop Rules

Работа месяца прекращается после выполнения M1-M6. Дополнительные задачи не добавляются для искусственного заполнения оставшегося времени.

MCP write operations автоматически переносятся, если отсутствует хотя бы одно:

- определённый actor;
- auth/authz;
- Audit Log;
- перечень разрешённых полей;
- rollback/failure semantics;
- тесты запрета недоступных операций.

Система задач не возвращается в разработку без отдельного PRD, владельца требований и пересмотра доступной команды.

## Критерий успеха месяца

Июнь успешен, если:

- production runtime переведён на PostgreSQL;
- seed корректно сигнализирует ошибки;
- бот прошёл smoke в клубном чате;
- monitoring и health доступны через отдельный управляемый поддомен;
- `v1` имеет зафиксированную конечную границу;
- quality gate и релевантные smoke-проверки пройдены;
- MCP либо получил маленький безопасный read-only slice, либо остался за границей стабилизации без чувства незакрытого долга.

Главный результат месяца — не максимальное количество реализованных пунктов, а закрытая и эксплуатируемая `v1` без бесконтрольного расширения scope.
