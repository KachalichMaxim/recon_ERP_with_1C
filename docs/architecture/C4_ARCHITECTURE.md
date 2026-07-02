# C4 Architecture: ERP vs 1C Reconciliation

## Назначение

Сервис закрывает два разных пользовательских сценария:

1. **Сальдовка по поставкам внутри ERP**: бухгалтер видит счета покупателю, оплаты, возмещаемые расходы, невозмещаемые расходы, переплату или долг по поставке и выгружает XLSX.
2. **Сверка ERP vs 1C**: бухгалтер или ответственный за интеграцию видит, какие документы есть в обеих системах, какие отсутствуют и где расходятся сумма, дата, номер, договор, НДС или аналитика поставки.

Backend реализуется на Python. ERP PHP остается рабочей системой и источником пользовательского контекста: при переходе в модуль из ERP, ERP передает короткоживущий launch token, backend валидирует его в ERP и создает внутреннюю сессию. Модуль сверки читает ERP напрямую из MariaDB и читает 1C через read-only GET REST API.

Диаграммы ниже оформлены в C4-уровнях, но используют обычный Mermaid `flowchart`, чтобы линии не пересекались и схема была компактнее.

## Level 1. System Context

```mermaid
flowchart LR
  accountant["Бухгалтер<br/>сальдовка, акт сверки, XLSX"]
  owner["Ответственный за интеграцию<br/>разбор расхождений"]

  recon["Python Reconciliation Service<br/>сальдовка ERP + сверка ERP vs 1C"]

  subgraph ERP["ERP контур"]
    erp_ui["ERP PHP UI"]
    erp_db[("ERP MariaDB<br/>поставки, договоры, счета, оплаты, акты, users")]
    recon_log[("Reconciliation log tables<br/>veda_reconciliation_runs/items")]
    erp_api["ERP API<br/>launch token validation"]
  end

  onec["1C Enterprise<br/>read-only GET REST API"]

  accountant -->|"HTTPS"| recon
  owner -->|"HTTPS"| recon

  recon -->|"SQL read"| erp_db
  recon -->|"SQL write: runs/items"| recon_log
  recon -->|"HTTP validate launch token"| erp_api
  recon -->|"GET /reconciliation/v1/snapshot"| onec

  erp_ui -->|"PHP/MariaDB"| erp_db
  erp_ui -->|"open module with launch token"| recon
```

## Level 2. Containers

```mermaid
flowchart TB
  user["Бухгалтер / интегратор"]

  subgraph Browser["Browser"]
    ui["Акт сверки UI<br/>matrix, compare, XLSX, auth"]
  end

  subgraph Python["Python backend"]
    api["API Server<br/>reconciliation_api_server.py"]
    auth["Auth layer<br/>ERP launch token + backend session"]
    erp_reader["ERP reader<br/>SQL to MariaDB"]
    onec_adapter["1C REST adapter<br/>onec_rest_client.py"]
    matcher["Matcher<br/>ERP docs vs 1C DTO"]
    xlsx["XLSX exporter<br/>openpyxl"]
    jobs["Background jobs<br/>long-running matrix/compare"]
  end

  subgraph Data["Data sources"]
    mariadb[("ERP MariaDB")]
    audit[("Reconciliation audit log<br/>veda_reconciliation_runs<br/>veda_reconciliation_items")]
    onec["1C REST API<br/>GET-only DTO"]
    erp_token["ERP launch token validation API"]
  end

  user --> ui
  ui -->|"HTTP API"| api

  api --> auth
  api --> erp_reader
  api --> onec_adapter
  api --> matcher
  api --> xlsx
  api --> jobs

  auth -->|"validate launch token"| erp_token
  auth -->|"read veda_users/user profile"| mariadb

  erp_reader -->|"SQL read"| mariadb
  matcher -->|"write run + item statuses"| audit
  jobs -->|"write batch run status"| audit
  onec_adapter -->|"GET /reconciliation/v1/snapshot"| onec

  matcher -->|"comparison result"| api
  xlsx -->|"xlsx bytes"| api
  jobs -->|"async result"| api
```

## Level 3. Python Backend Components

```mermaid
flowchart LR
  subgraph Input["Input / HTTP"]
    http["HTTP Handler<br/>routes, params, responses"]
    session["Session/Auth middleware"]
  end

  subgraph ERPRead["ERP side"]
    users["ERP user lookup<br/>veda_users by token user id/login"]
    supplies["Supply context reader<br/>contacts, clients, dogs, specs"]
    docs["ERP document reader<br/>schets, akts, payments, operations"]
    saldo["Supply balance calculator<br/>get_paidsum / get_realizsum logic"]
  end

  subgraph OneCRead["1C side"]
    query["GET query builder<br/>date, org, counterparty, contract, spec, docs"]
    rest["1C REST client<br/>GET-only"]
    normalize["1C DTO normalizer<br/>docs, lines, movements, balances"]
  end

  subgraph Reconcile["Reconciliation"]
    compare["Matcher<br/>primary + secondary business keys"]
    status["Status classifier<br/>OK, missing, amount/date/contract/vat mismatch"]
    log_writer["Reconciliation log writer<br/>runs, item statuses, mismatch fields"]
  end

  subgraph Output["Output"]
    matrix["Matrix model<br/>hierarchy rows"]
    export["XLSX export<br/>accounting layout"]
    api_result["JSON / XLSX response"]
  end

  db[("ERP MariaDB")]
  logdb[("Audit tables<br/>veda_reconciliation_runs<br/>veda_reconciliation_items")]
  onec["1C REST API"]
  erpapi["ERP launch token validation"]

  http --> session
  session --> users
  users --> db
  session --> erpapi

  http --> supplies
  http --> docs
  supplies --> db
  docs --> db
  docs --> saldo

  http --> query
  supplies --> query
  docs --> query
  query --> rest
  rest --> onec
  rest --> normalize

  saldo --> compare
  normalize --> compare
  compare --> status
  status --> log_writer
  log_writer --> logdb

  saldo --> matrix
  status --> matrix
  matrix --> export
  matrix --> api_result
  export --> api_result
```

## Runtime Flow. Login, Matrix, Compare, Export

```mermaid
sequenceDiagram
  autonumber
  actor User as Бухгалтер
  participant UI as Browser UI
  participant API as Python API
  participant DB as ERP MariaDB
  participant ERPAPI as ERP token validation
  participant OneC as 1C REST API

  User->>UI: Переходит из ERP в модуль
  UI->>API: POST /api/auth/erp-launch {launch_token}

  API->>ERPAPI: validate launch token
  ERPAPI-->>API: user id/login/profile
  API->>DB: SELECT veda_users WHERE id/login = ERP user
  API-->>UI: backend session + user profile

  UI->>API: GET /api/reconciliation/client-matrix?client_id&dog_id&limit
  API->>DB: SQL по поставкам, счетам, оплатам, актам, операциям
  API-->>UI: ERP-сальдовка по поставкам

  User->>UI: Запускает сверку с 1C
  UI->>API: GET /api/reconciliation/client-matrix?client_id&dog_id&limit&compare_1c=1
  API->>DB: Контекст ERP: ЮЛ, договор, поставка, документы
  API->>OneC: GET /reconciliation/v1/snapshot?date_from&date_to&counterparty_inn&contract_number&spec_number
  OneC-->>API: normalized 1C DTO
  API->>DB: INSERT veda_reconciliation_runs / items
  API-->>UI: статусы: ОК / нет в 1C / нет в ERP / сумма / дата / договор / НДС

  User->>UI: Нажимает Выгрузить
  UI->>API: GET /api/reconciliation/client-matrix.xlsx
  API-->>UI: XLSX файл
```

## Ключевые архитектурные правила

- **Сальдовка по поставкам** и **сверка ERP vs 1C** - разные сценарии. Сальдовка отвечает “сколько по поставке”, сверка отвечает “что выгружено, чего нет и что разошлось”.
- Live-матрица не должна автоматически считать всю историю клиента. Пользователь выбирает клиента/ЮЛ/договор и ограничение поставок.
- 1C API только read-only и GET-only. Основной endpoint: `GET /reconciliation/v1/snapshot`.
- Python backend передает в 1C только query-фильтры: период, организация, контрагент, договор, поставка, коды/номера документов, `include`, `cursor`, `limit`.
- Пользователь не проходит отдельный внешний вход. Доступ открывается только из ERP по короткоживущему launch token.
- Backend session создается после валидации launch token в ERP. ERP token не хранится в URL и не используется как публичный долгоживущий секрет.
- Для больших объемов используется background runner и collection endpoints с `cursor`/`limit`.
- Все запуски сверки пишутся в `veda_reconciliation_runs`.
- Все документные результаты и расхождения пишутся в `veda_reconciliation_items`.
- Документы сопоставляются по бизнес-ключу `тип документа + код 1C + дата 1C + договор 1C`; матч только по коду 1C запрещен из-за дублей.
- Расхождения логируются типизированно: `MISSING_IN_ERP`, `MISSING_IN_1C`, `AMOUNT_MISMATCH`, `DATE_MISMATCH`, `NUMBER_MISMATCH`, `CONTRACT_MISMATCH`, `VAT_MISMATCH`, `DUPLICATE_IN_1C`, `AMBIGUOUS_MATCH`, `SOURCE_ERROR`.

## Persistent Log Model

```mermaid
flowchart LR
  run["veda_reconciliation_runs<br/>scope, scope_id, spec_id, client_id,<br/>source_mode, counts, status,<br/>summary_json, created_at"]
  item["veda_reconciliation_items<br/>run_id, oper_id, erp_doc_id,<br/>ERP fields, 1C fields,<br/>status, mismatch_fields_json, note"]
  analytics["Аналитика качества обмена<br/>частота ошибок по типам,<br/>проблемные документы, повторяемость"]

  run -->|"1:N"| item
  item --> analytics
```

Лог используется не как технический debug-log, а как бизнес-аудит сверки: когда запускали, по какому объекту, сколько документов сравнили, какие типы расхождений получили и какие поля не совпали.
