# Clean Architecture / DDD Layout

## Слои

### Domain

Папка: `src/recon_erp_1c/domain`

Содержит только бизнес-понятия:

- `Delivery`;
- `Contract`;
- `AccountingDocument`;
- `ReconciliationRun`;
- `ReconciliationIssue`;
- `Money`;
- `DateRange`;
- статусы и роли договоров.

Domain не знает, откуда пришли данные: из ERP, 1C REST, файла или теста.

### Application

Папка: `src/recon_erp_1c/application`

Содержит сценарии:

- сверить поставку;
- сверить договор;
- сформировать сальдовку;
- записать лог запуска;
- подготовить XLSX/export model.

Application зависит от domain и от портов. Порты описывают, что нужно получить, но не знают как.

### Infrastructure

Папка: `src/recon_erp_1c/infrastructure`

Содержит адаптеры:

- ERP MariaDB reader;
- 1C REST reader;
- логирование run/items;
- persistence.

Infrastructure реализует application ports.

### Interfaces

Папка: `src/recon_erp_1c/interfaces`

Содержит входы:

- HTTP API;
- web UI;
- CLI/runner в будущем.

Interfaces вызывают application use cases.

## DDD-модули

| Модуль | Ответственность |
|---|---|
| `delivery` | контекст поставки ERP |
| `contracts` | договоры 1C и роли CB/CP |
| `documents` | счета, оплаты, акты, движения |
| `matching` | сравнение ERP и 1C |
| `logging` | история запусков и частотность расхождений |
| `exports` | XLSX/TSV/UI projection |

## Правило по договорам 1C

Для поставки не ищем договор в 1C по `spec_id`.

Основной фильтр:

```text
buyer_contract_code      = veda_specs.f_kod1cb
committent_contract_code = veda_specs.f_kod1cp
```

1C должна искать по:

```text
Справочник.ДоговорыКонтрагентов.Код
```

`contract_number`, `base_contract`, `spec_number` остаются контрольными полями.

## Prototype migration

Текущий монолитный сервер сохранен в:

```text
reference/prototype/prototype_server.py
```

Он нужен только для сравнения поведения и постепенного переноса. Новая разработка не должна добавлять бизнес-логику в prototype.

## Уже проложенные сценарии

1. `ListDeliveriesUseCase` получает список поставок ERP с ограничением `limit/offset`.
2. `ReconcileDeliveryUseCase` получает поставку, договоры, документы ERP, запрашивает snapshot 1C и сравнивает документы.
3. Перед сравнением документы агрегируются по типу и коду/номеру 1C, чтобы один платеж с несколькими распределениями не превращался в ложное расхождение.
4. `MariaDbReconciliationLogRepository` пишет результат запуска и каждое расхождение в таблицы логирования.

## Граница с 1C

Сервис не зависит от внутренних объектов 1C. Единственная зависимость - нормализованный read-only REST контракт:

```text
GET /reconciliation/v1/snapshot
```

Python-сервис передает в 1C только бизнес-ключи сверки:

```text
buyer_contract_code      <- ERP veda_specs.f_kod1cb
committent_contract_code <- ERP veda_specs.f_kod1cp
contract_code[]          <- коды договоров 1C
document_code[]          <- номера/коды документов 1C из ERP
date_from/date_to        <- период сверки
```

`spec_id`, `dog_id`, `oper_id`, `client_id` остаются внутренними идентификаторами ERP/Python и в 1C не отправляются.
