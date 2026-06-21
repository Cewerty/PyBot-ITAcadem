# Architecture Decision Records

Перед изменениями, которые затрагивают архитектуру, слои, DTO, DI, runtime/deploy, БД, middleware или security-контракты, проверьте релевантные ADR в `src/pybot/docs/adr/`.

ADR в этом проекте фиксируют не только то, как система устроена сейчас, но и почему было выбрано именно такое решение. Это часть engineering contract: там уже закреплены решения вроде PostgreSQL-only runtime, anonymous user id, import-time side effects и logging contract.

Если изменение противоречит существующему ADR, сначала нужно явно обновить или заменить архитектурное решение, а не молча обходить его в коде.

- Каталог ADR: [src/pybot/docs/adr/](https://github.com/Cewerty/PyBot-ITAcadem/tree/main/src/pybot/docs/adr)
