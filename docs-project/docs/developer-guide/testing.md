# Тестирование

Качество кода проверяется через `just quality-gate`.

Если локальный `uv` или host Python path не может дать стабильный `Python 3.14`, используйте Docker-based tooling path:

```bash
just test-unit-docker
just test-integration-docker
just test-coverage-docker
just quality-gate-docker
```

Host path и Docker path существуют параллельно:

- host quality/test path:
  - `just test-unit`
  - `just test-integration`
  - `just test-coverage`
  - `just quality-gate`
- docker quality/test path:
  - `just test-unit-docker`
  - `just test-integration-docker`
  - `just test-coverage-docker`
  - `just quality-gate-docker`

Используйте host path как быстрый вариант на машинах со стабильным `Python 3.14`, а Docker path - как reproducible fallback для Linux/host Python drift.

## Основные команды

```bash
just format-check
just lint
just type-check
uv run pytest -q
just docs-build
```

## Что проверять при изменениях

- для сервисов, DTO и репозиториев: targeted unit/integration tests;
- для пользовательских bot-flow: поведение handler/dialog flow;
- для документации: строгую сборку MkDocs;
- для крупных изменений: дополнительный smoke-check критичного сценария.

## Полезное правило

Если модуль переименован или API изменился, сразу обновляйте страницу в `docs-project/docs/api-reference/`, иначе `mkdocstrings` начнет падать на отсутствующих импортах.
