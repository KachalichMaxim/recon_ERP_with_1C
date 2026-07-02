# ERP ↔ 1C Reconciliation

Самостоятельный Python-проект для сверки ERP и 1C.

Проект отделен от каталога печатных шаблонов и разложен по Clean Architecture + DDD:

```text
erp_1c_reconciliation/
  src/recon_erp_1c/
    domain/                 # бизнес-модель: поставка, договор, документ, статус сверки
    application/            # use cases и порты, без SQL/HTTP/REST деталей
    infrastructure/         # MariaDB, REST 1C, логирование, persistence adapters
    interfaces/             # HTTP API, web UI adapters
    bootstrap/              # конфигурация и сборка зависимостей
  contracts/onec/           # OpenAPI контракт read-only REST API 1C
  docs/                     # требования, архитектура, скриншоты, API docs
  sql/                      # схемы логирования и служебные SQL
  tools/                    # smoke-тесты и сервисные утилиты
  deploy/                   # systemd/nginx/deploy-конфиги
  reference/                # контрольные samples и prototype-only код
```

## Архитектурное правило

Зависимости направлены внутрь:

```text
interfaces -> application -> domain
infrastructure -> application -> domain
domain -> ничего
```

Домен не импортирует:

- MariaDB;
- REST-клиент 1C;
- HTTP;
- Excel;
- UI;
- файловую систему.

## Основной bounded context

`Reconciliation`:

- `Delivery` - поставка/заявка ERP;
- `Contract` - договор 1C с ролью `buyer` или `committent`;
- `AccountingDocument` - счет, оплата, акт, реализация, движение;
- `ReconciliationRun` - запуск сверки;
- `ReconciliationIssue` - результат сравнения одного объекта.

## Ключи связи ERP и 1C

Основной ключ поставки в 1C:

```text
veda_specs.f_kod1cb -> buyer_contract_code
veda_specs.f_kod1cp -> committent_contract_code
```

`spec_id`, `dog_id`, `oper_id`, `client_id` не передаются в 1C. Они остаются внутренними ERP/Python identifiers.

## Где что дорабатывать

| Задача | Папка |
|---|---|
| Новая бизнес-логика сверки | `src/recon_erp_1c/domain` |
| Новый сценарий пользователя | `src/recon_erp_1c/application/use_cases` |
| Чтение ERP MariaDB | `src/recon_erp_1c/infrastructure/erp_mariadb` |
| Чтение 1C REST | `src/recon_erp_1c/infrastructure/onec_rest` |
| HTTP endpoints | `src/recon_erp_1c/interfaces/http` |
| UI | `src/recon_erp_1c/interfaces/web` |
| Контракт 1C | `contracts/onec` |
| Логи и таблицы | `sql` |

## Контракт read-only REST API 1C

Канонические файлы контракта лежат в `contracts/onec`:

- `contracts/onec/openapi.json` - OpenAPI/Swagger JSON;
- `contracts/onec/openapi.yaml` - OpenAPI/Swagger YAML;
- `contracts/onec/openapi_ru.md` - русская документация и маппинг 1C -> DTO.

Старые копии контракта удалены, чтобы не было двух источников правды. В ТЗ и разработке использовать только `contracts/onec`.

## Реализованный каркас до готовности endpoint 1C

HTTP API уже можно запускать без доступов к 1C. В этом режиме доступны health/config endpoints, а рабочие endpoints честно вернут ошибку конфигурации, если не заданы MariaDB или 1C REST credentials.

```text
GET /health
GET /api/config/status
POST /api/auth/login
GET /api/auth/me
GET /api/reconciliation/specifications?client_id=221&dog_id=88&date_from=2025-01-01&date_to=2025-12-31&limit=50
GET /api/reconciliation/run?spec_id=20334&date_from=2025-01-01&date_to=2025-12-31&persist_log=1
GET /api/reconciliation/run.xlsx?spec_id=20334&date_from=2025-01-01&date_to=2025-12-31
```

Авторизация не использует Google. При переходе из ERP сервис принимает ERP-токен:

```text
Authorization: Bearer <erp-token>
или
X-ERP-Token: <erp-token>
```

Если `RECON_REQUIRE_ERP_TOKEN=1`, рабочие endpoints без токена возвращают `401`.

## Пользовательские пути

1. Пользователь открывает экран сверки и входит по логину/паролю ERP. Backend проверяет `veda_users.f_login`, `veda_users.f_password`, `veda_users.f_isactived`.
2. Пользователь задает фильтры: `client_id`, `dog_id`, период и лимит строк. Сервис показывает список поставок из ERP.
3. Пользователь выбирает поставку и запускает сверку. UI показывает шаги: ERP context -> ERP documents -> 1C snapshot -> matching -> log.
4. После завершения пользователь видит статусы документов и может фильтровать строки по типу расхождения.
5. Пользователь скачивает XLSX по той же поставке и периоду.

## Что уже заложено по производительности

- список поставок ограничивается `limit/offset`, верхний предел `limit` на стороне API - 500;
- чтение 1C идет через один snapshot-запрос по поставке/периоду/кодам договоров;
- ERP SQL локализован в `infrastructure/erp_mariadb/queries.py`;
- операции поставки выбираются по исходным таблицам ERP и учитывают `f_parenttype IN (2, 4)`;
- платежи и акты перед сравнением агрегируются по типу документа и номеру/коду 1C, чтобы не получать ложные расхождения из-за распределения одной оплаты на несколько строк;
- результаты запуска пишутся в `veda_reconciliation_runs` и `veda_reconciliation_items` для последующего анализа частоты ошибок.

## Проверки

```bash
python3 -m py_compile $(find src -name '*.py')
PYTHONPATH=src python3 -m pytest tests -q
python3 tools/smoke_onec_rest_adapter.py
```

## Prototype-only

`reference/prototype/prototype_server.py` - перенос текущего серверного прототипа для справки и поэтапной миграции.

Новый production-код не должен импортировать файлы из `reference/prototype`.
