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

1. Пользователь открывает экран из ERP. ERP передает launch token, backend валидирует его и создает короткую сессию сервиса. Прямой логин/пароль разрешен только в dev/demo-режиме.
2. Пользователь задает фильтры: `client_id`, `dog_id`, период и лимит строк. Сервис показывает список поставок из ERP.
3. Пользователь выбирает поставку и запускает сверку. UI показывает шаги: ERP context -> ERP documents -> 1C snapshot -> matching -> log.
4. После завершения пользователь видит статусы документов и может фильтровать строки по типу расхождения.
5. Пользователь скачивает XLSX по той же поставке и периоду.

## Что уже заложено по производительности

- список поставок ограничивается `limit/offset`, верхний предел `limit` на стороне API - 500;
- API матрицы возвращает `metrics.erp_sql_ms` для измерения фактической скорости ERP SQL;
- целевой SLA live-матрицы: до 10 секунд для страницы до 50 поставок;
- целевой SLA полного набора одного договора: до 15 секунд для объема до 150 поставок;
- целевой SLA XLSX-выгрузки одного договора: до 20 секунд для объема до 150 поставок;
- чтение 1C начинается с одного snapshot-запроса по поставке/периоду/кодам договоров; пока 1C не поддерживает batch по `document_code`, известные ERP-документы добираются параллельными GET-запросами;
- ERP SQL локализован в `infrastructure/erp_mariadb/queries.py`;
- операции поставки выбираются по исходным таблицам ERP и учитывают `f_parenttype IN (2, 4)`;
- платежи и акты перед сравнением агрегируются по типу документа и номеру/коду 1C, чтобы не получать ложные расхождения из-за распределения одной оплаты на несколько строк;
- результаты запуска пишутся в `veda_reconciliation_runs` и `veda_reconciliation_items` для последующего анализа частоты ошибок.

Production-baseline от 2026-07-08 на договоре `client_id=221`, `dog_id=88`, период `2025-01-01..2026-07-08`:

| Сценарий | Объем | Время |
| --- | ---: | ---: |
| Матрица, `limit=50` | 50 поставок | 7.2 сек |
| Матрица, полный договор | 126 поставок | 12.7 сек |
| XLSX-выгрузка | 126 поставок / 1227 строк | 12.9 сек |

Повторный production smoke 13.07.2026 после пакетного расчета через ERP-процедуры:

| Сценарий | Объем | Время |
| --- | ---: | ---: |
| Матрица взаиморасчетов | 5 из 126 поставок | 3.92 сек |
| XLSX текущей выборки | 5 поставок / 23 строки | 3.84 сек |

Полная документная сверка 14.07.2026 на воспроизводимой выборке из 10 закрытых поставок 2024 года: p50 `12.65` сек, p95 `17.81` сек; ERP p50 `4.83` сек, REST 1C p50 `6.35` сек. Технических ошибок `0`. Подробности: `docs/testing/E2E_RANDOM_CLOSED_DELIVERIES_2026-07-14.md`.

Итоги матрицы берутся из `get_paidsum/get_realizsum`, вычисленных одним пакетным проходом по операциям выбранных поставок. Документы используются для расшифровки, но не подменяют расчетные суммы верхнего уровня.

Если фактическое время стабильно превышает SLA, расчет должен уходить в пагинацию, batch/background runner или кэширование snapshot-результата.

## Проверки

```bash
python3 -m py_compile $(find src -name '*.py')
PYTHONPATH=src python3 -m pytest tests -q
python3 tools/smoke_onec_rest_adapter.py
```

Полный E2E по одной поставке запускается без UI. По умолчанию результат не пишется в production-журнал; для записи нужен явный `--persist-log`:

```bash
python3 tools/e2e_reconcile_delivery.py \
  --spec-id 20334 \
  --date-from 2025-07-01 \
  --date-to 2025-08-31 \
  --json outputs/e2e-spec-20334.json \
  --xlsx outputs/e2e-spec-20334.xlsx
```

Случайная, но воспроизводимая выборка закрытых поставок:

```bash
python3 tools/e2e_random_sample.py \
  --sample-size 10 --seed 20260714 --closed-only \
  --delivery-date-from 2024-01-01 --delivery-date-to 2024-12-31 \
  --document-date-from 2024-01-01 --document-date-to 2025-12-31 \
  --json outputs/e2e-random.json --markdown outputs/e2e-random.md
```

Exit code `0` означает полное совпадение, `2` — корректно завершенную сверку с найденными расхождениями, `1` — техническую ошибку.

Для локальной проверки 1C через split-tunnel VPN можно указать адрес VPN-интерфейса:

```bash
RECON_ERP_DB_HOST=erp.vedagent \
RECON_ERP_DB_NAME=veda25 \
RECON_ERP_DB_USER=... \
RECON_ERP_DB_PASSWORD=... \
RECON_ERP_DB_BIND_ADDRESS=10.54.10.53 \
RECON_ONEC_REST_BASE_URL=http://10.54.1.25/vedagent_dev/hs \
RECON_ONEC_REST_USER=... \
RECON_ONEC_REST_PASSWORD=... \
RECON_ONEC_REST_BIND_ADDRESS=10.54.10.53 \
python3 tools/smoke_onec_rest_adapter.py
```

В production `RECON_ERP_DB_BIND_ADDRESS` и `RECON_ONEC_REST_BIND_ADDRESS` должны быть пустыми: серверу нужен нормальный сетевой маршрут до ERP MariaDB и 1C.

## Prototype-only

`reference/prototype/prototype_server.py` - перенос текущего серверного прототипа для справки и поэтапной миграции.

Новый production-код не должен импортировать файлы из `reference/prototype`.
