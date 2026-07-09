# C4 Architecture: ERP vs 1C Reconciliation

## Назначение

Сервис закрывает два разных пользовательских сценария:

1. **Сальдовка по поставкам внутри ERP**: бухгалтер видит счета покупателю, оплаты, возмещаемые расходы, невозмещаемые расходы, переплату или долг по поставке и выгружает XLSX.
2. **Сверка ERP vs 1C**: бухгалтер или ответственный за интеграцию видит, какие документы есть в обеих системах, какие отсутствуют и где расходятся сумма, дата, номер, договор, НДС или аналитика поставки.

Backend реализуется на Python. ERP PHP остается рабочей системой и источником пользовательского контекста: при переходе в модуль из ERP, ERP передает короткоживущий launch token, backend валидирует его в ERP и создает внутреннюю сессию. Модуль сверки читает ERP напрямую из MariaDB и читает 1C через read-only GET REST API.

Диаграммы ниже представлены в двух формах:

- **Canonical C4 Mermaid notation** - формальная C4-нотация `C4Context`, `C4Container`, `C4Component`;
- **Compact flowchart views** - те же уровни C4, но в обычном Mermaid `flowchart`, чтобы линии не пересекались и схема была компактнее.

## Canonical C4 Mermaid Notation

### C4 Level 1. System Context

```mermaid
C4Context
  title ERP / 1C Reconciliation - System Context

  Person(accountant, "Бухгалтер", "Смотрит сальдовку по поставкам, выгружает XLSX, запускает сверку")
  Person(integration_owner, "Ответственный за интеграцию", "Разбирает ошибки обмена ERP и 1C")

  System(recon, "Python Reconciliation Service", "Сальдовка ERP по поставкам и документная сверка ERP vs 1C")

  System_Ext(erp, "ERP PHP", "Рабочий интерфейс ERP и источник launch token")
  SystemDb_Ext(erp_db, "ERP MariaDB", "Поставки, договоры, счета, операции, оплаты, акты, пользователи")
  System_Ext(onec, "1C Enterprise", "Read-only GET REST API для нормализованных документов сверки")

  Rel(accountant, erp, "Переходит в модуль сверки из ERP")
  Rel(accountant, recon, "Работает с матрицей, сверкой и XLSX", "HTTPS")
  Rel(integration_owner, recon, "Анализирует расхождения и журнал", "HTTPS")

  Rel(erp, erp_db, "Читает и пишет бизнес-данные", "PHP / SQL")
  Rel(erp, recon, "Передает short-lived launch token", "HTTPS")
  Rel(recon, erp, "Валидирует launch token", "HTTPS")
  Rel(recon, erp_db, "Читает ERP-данные и пишет журнал сверки", "SQL")
  Rel(recon, onec, "Получает 1C snapshot", "GET /reconciliation/v1/snapshot")
```

### C4 Level 2. Containers

```mermaid
C4Container
  title ERP / 1C Reconciliation - Containers

  Person(user, "Бухгалтер / интегратор", "Пользователь модуля сверки")

  System_Boundary(recon_system, "Python Reconciliation Service") {
    Container(web_ui, "Web UI", "HTML / CSS / JavaScript", "Матрица сальдовки, экран сверки ERP vs 1C, XLSX export, фильтры")
    Container(api, "HTTP API", "Python stdlib HTTP server", "Auth, matrix API, reconciliation API, export API")
    Container(auth, "Auth / Session", "Python", "Валидация ERP launch token и backend session")
    Container(erp_reader, "ERP Reader", "Python + PyMySQL", "Читает поставки, счета, операции, get_paidsum/get_realizsum")
    Container(onec_adapter, "1C REST Adapter", "Python HTTP client", "Читает normalized 1C DTO через GET-only API")
    Container(matcher, "Matcher", "Python domain logic", "Сопоставляет документы по типу, коду 1C, дате, договору, сумме, НДС")
    Container(xlsx_exporter, "XLSX Exporter", "Python + openpyxl", "Формирует бухгалтерскую выгрузку")
  }

  System_Ext(erp_php, "ERP PHP", "Рабочая ERP и launch-token provider")
  SystemDb_Ext(erp_db, "ERP MariaDB", "Исходные ERP-таблицы и таблицы журнала сверки")
  System_Ext(onec_api, "1C REST API", "Read-only GET contract")

  Rel(user, web_ui, "Открывает модуль и работает с данными", "Browser")
  Rel(web_ui, api, "JSON / XLSX requests", "HTTPS")

  Rel(api, auth, "Проверяет доступ")
  Rel(auth, erp_php, "Validate launch token", "HTTPS")
  Rel(auth, erp_db, "Читает профиль пользователя", "SQL")

  Rel(api, erp_reader, "Запрашивает ERP matrix / ERP documents")
  Rel(erp_reader, erp_db, "SELECT исходных таблиц ERP", "SQL")

  Rel(api, onec_adapter, "Запрашивает 1C snapshot")
  Rel(onec_adapter, onec_api, "GET snapshot / docs / dictionaries", "HTTPS")

  Rel(api, matcher, "Передает ERP и 1C документы")
  Rel(matcher, erp_db, "Пишет veda_reconciliation_runs/items", "SQL")

  Rel(api, xlsx_exporter, "Передает matrix/run payload")
  Rel(xlsx_exporter, web_ui, "Возвращает XLSX bytes", "Download")
```

### C4 Level 3. Backend Components

```mermaid
C4Component
  title ERP / 1C Reconciliation - Python Backend Components

  Container_Boundary(api_boundary, "Python HTTP API") {
    Component(router, "HTTP Router", "BaseHTTPRequestHandler", "Маршруты auth, matrix, reconciliation, comments, xlsx")
    Component(session, "Session Guard", "Python", "Проверяет backend session и user profile")
    Component(matrix_uc, "Matrix Use Case", "Application service", "Строит иерархию клиент -> ЮЛ -> договор -> поставка")
    Component(reconcile_uc, "Reconcile Use Case", "Application service", "Запускает сверку поставки или batch")
    Component(comment_api, "Comment API", "Python", "Сохраняет пользовательские причины и комментарии разбора")
  }

  Container_Boundary(domain_boundary, "Domain / Application") {
    Component(balance_calc, "Balance Calculator", "Domain service", "Считает сальдо: get_paidsum - get_realizsum по возмещаемым и невозмещаемым")
    Component(key_builder, "Match Key Builder", "Domain service", "Ключ: kind + code1c + date1c + contract_code1c")
    Component(classifier, "Mismatch Classifier", "Domain service", "OK, нет в 1C, нет в ERP, сумма, дата, договор, НДС, дубли")
    Component(status_model, "Status Model", "Domain entities", "Типизированные статусы и поля расхождений")
  }

  Container_Boundary(infra_boundary, "Infrastructure") {
    Component(erp_repo, "MariaDB ERP Repository", "PyMySQL", "Исходные таблицы ERP, get_paidsum/get_realizsum, veda_users")
    Component(onec_repo, "1C REST Repository", "HTTP client", "Нормализованный read-only DTO из 1C")
    Component(log_repo, "Reconciliation Log Repository", "PyMySQL", "veda_reconciliation_runs/items/comments")
    Component(xlsx, "XLSX Builder", "openpyxl", "Бухгалтерская матрица XLSX")
  }

  SystemDb_Ext(erp_db_c4, "ERP MariaDB", "ERP data + reconciliation logs")
  System_Ext(onec_c4, "1C REST API", "GET-only normalized snapshot")
  System_Ext(erp_auth_c4, "ERP Token Validation", "Validates launch token")

  Rel(router, session, "Проверяет session")
  Rel(session, erp_auth_c4, "Validate launch token", "HTTPS")
  Rel(session, erp_repo, "Load user profile")

  Rel(router, matrix_uc, "GET matrix")
  Rel(matrix_uc, erp_repo, "Load supplies, invoices, payments, sales")
  Rel(matrix_uc, balance_calc, "Calculate saldo")
  Rel(matrix_uc, xlsx, "Export visible/all rows")

  Rel(router, reconcile_uc, "GET/POST reconciliation")
  Rel(reconcile_uc, erp_repo, "Load ERP documents")
  Rel(reconcile_uc, onec_repo, "Load 1C snapshot")
  Rel(reconcile_uc, key_builder, "Build matching keys")
  Rel(key_builder, classifier, "Classify matches and mismatches")
  Rel(classifier, log_repo, "Persist run and item statuses")
  Rel(comment_api, log_repo, "Persist user decision / reason")

  Rel(erp_repo, erp_db_c4, "SQL")
  Rel(log_repo, erp_db_c4, "SQL")
  Rel(onec_repo, onec_c4, "HTTPS GET")
```

## Compact Flowchart Views

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
