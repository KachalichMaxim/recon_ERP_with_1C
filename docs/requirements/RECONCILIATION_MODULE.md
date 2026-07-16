# Reconciliation Module

## Назначение

Модуль закрывает два production-сценария:

1. **Сальдовка ERP по поставкам** - бухгалтер видит по клиенту, ЮЛ, договору и поставкам счета покупателю, оплаты, возмещаемые расходы, невозмещаемые расходы, долг или переплату.
2. **Сверка ERP vs 1C** - ответственный пользователь видит, какие документы совпали между ERP и 1C, какие отсутствуют и какие поля расходятся.

В Phase 1 это реализовано как контроль документов ERP → 1C в доступной поставочной области. Зеленый результат означает отсутствие найденных проблем только в этой области, а не доказательство полноты всех документов двух систем. См. `MVP_SCOPE.md`.

## Основные документы

- `RECONCILIATION_BABOK_REQUIREMENTS.md` - бизнес-требования, пользовательские требования, функциональные и нефункциональные требования по BABOK.
- `AKT_SVERKI_ARCHITECTURE_REST_PLAN.md` - целевая REST-архитектура Python backend + ERP MariaDB + 1C read-only REST.
- `C4_ARCHITECTURE.md` - C4-архитектура production-контура.
- `sql/1c_reconciliation_schema.sql` - таблицы логирования запусков и расхождений.
- `contracts/onec/openapi.json` / `.yaml` - OpenAPI contract для 1C read-only REST API.
- `contracts/onec/openapi_ru.md` - русская документация по контракту 1C REST API.
- `docs/api/onec_reconciliation_rest_api_tz.md` - ТЗ для 1C-разработчика по REST-контракту.

## Production stack

- UI: `akt_sverki/index.html`.
- Backend: Python service `reconciliation_api_server.py`.
- ERP источник: MariaDB ERP.
- ERP авторизация: переход из ERP в модуль с короткоживущим launch token.
- 1C источник: отдельный read-only GET REST API `/reconciliation/v1/...`.
- Логирование: ERP MariaDB tables `veda_reconciliation_runs` и `veda_reconciliation_items`.

## Production API backend

```http
GET /api/reconciliation/1c-rest-status
GET /api/reconciliation/client-matrix?client_id=<id>&dog_id=<id>&limit=<n>
GET /api/reconciliation/client-matrix?client_id=<id>&dog_id=<id>&limit=<n>&compare_1c=1
GET /api/reconciliation/client-matrix.xlsx?client_id=<id>&dog_id=<id>&limit=<n>
```

Назначение:

- `client-matrix` без `compare_1c=1` возвращает ERP-сальдовку по поставкам.
- `client-matrix` с `compare_1c=1` строит ERP-сальдовку и дополнительно выполняет сверку документов с 1C через REST API.
- `client-matrix.xlsx` возвращает бухгалтерскую XLSX-выгрузку сальдовки.

В документной сверке ERP-документы должны содержать прямые ссылки на исходные карточки ERP: счет покупателю (`pgid=17`), закрывающий документ (`pgid=83`) и, при наличии `operation_id`, операцию (`pgid=35&invtb=145`). Если ERP хранит дочерние акты под агрегирующим актом, код/дата документа 1C берутся из `veda_akts.f_mainakt`, а сумма и ссылка на карточку — из дочернего акта.

Различие договора не является расхождением, если ERP-документ однозначно найден в 1C по типу, коду/номеру, дате и сумме либо сопоставлен со строкой/распределением. Один договор поставки может содержать связанные документы, проведенные в 1C по другим договорам. Договор участвует в выборе кандидата при дублях и всегда показывается справочно, но сам по себе не меняет статус `match`.
- `1c-rest-status` показывает готовность production REST-источника 1C.

## ERP source model

Иерархия:

```text
veda_contacts -> veda_clients -> veda_dogs -> veda_specs
```

Правила:

- `veda_contacts` - клиент верхнего уровня.
- `veda_clients` - ЮЛ клиента.
- `veda_dogs.f_contrid -> veda_clients.f_id` - договор оформлен на ЮЛ.
- `veda_clients.f_contactid -> veda_contacts.f_id` - ЮЛ связано с клиентом.
- `veda_specs.f_dogid -> veda_dogs.f_id` - поставка/заявка/спецификация связана с договором.
- `veda_dogs.f_clientid` не использовать как надежный источник клиента.
- Тип поставки показывать через `veda_spr.f_type=33` и `veda_spr.f_type=130`.

Сальдовка:

- счета покупателю - `veda_schets` по бизнес-типу `Счет покупателю`;
- оплаты клиента - `get_paidsum(veda_spec_invoices.f_id)`; для построчного отображения по счетам используется связь `veda_schets.f_operid = veda_spec_invoices.f_id`;
- возмещаемые расходы - `get_realizsum` по операциям `veda_spec_invoices.f_isvozm=1`;
- невозмещаемые расходы - `get_realizsum` по операциям `veda_spec_invoices.f_isvozm=2`;
- итог `(+/-)` - `Сумма оплаты - Возмещаемые расходы - Невозмещаемые расходы`;
- отрицательный итог показывать как `Долг`, положительный итог - как `Переплата`, нулевой итог - как `ОК`.

Операции поставки:

- `f_parenttype=2`: связь с поставкой через `veda_spec_invoices.f_specid`;
- `f_parenttype=4`: связь с поставкой через `veda_categs`:

```sql
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
```

## 1C source model

1C отдает нормализованные DTO по read-only REST API. Сервис сверки не читает сырые таблицы/объекты 1C и не зависит от внутренних имен документов 1C.

Основной live endpoint:

```http
GET /reconciliation/v1/snapshot
```

Collection endpoints для фоновых проверок:

```http
GET /reconciliation/v1/counterparties
GET /reconciliation/v1/contracts
GET /reconciliation/v1/invoices
GET /reconciliation/v1/payments
GET /reconciliation/v1/sales
GET /reconciliation/v1/purchases
GET /reconciliation/v1/document-lines
GET /reconciliation/v1/account-movements
GET /reconciliation/v1/balances
```

1C DTO должны содержать:

- `source_id`;
- `document_type`;
- `number`;
- `date`;
- `organization_id`;
- `counterparty_id`;
- `contract_id` / `contract_number`;
- `spec_id` / `spec_number`, если аналитика доступна;
- `amount_total`;
- `vat_rate` / `vat_amount`;
- `currency`;
- `posted`;
- `deleted`;
- `updated_at`;
- `hash`.

## Статусы сверки ERP vs 1C

- `MATCH` - документ найден и поля совпали.
- `MISSING_ERP_INVOICE` - по операции ERP не выставлен либо не привязан счет; документную сверку начинать рано.
- `MISSING_ERP_CLOSING_DOCUMENT` - по операции ERP отсутствует связь с закрывающим документом.
- `NOT_FOUND_IN_1C` - полноценный ERP-документ с кодом и датой 1C отсутствует в ответе 1C.
- `NOT_LINKED_TO_DELIVERY_IN_ERP` - документ 1C существует в ERP, но связан с другой поставкой.
- `NOT_FOUND_IN_ERP` - документ 1C не найден глобальным поиском в исходных таблицах ERP.
- `AMOUNT_MISMATCH` - расходится сумма.
- `DATE_MISMATCH` - расходится дата.
- `NUMBER_MISMATCH` - расходится номер.
- `CONTRACT_MISMATCH` - договор используется для разрешения неоднозначного совпадения; у однозначно найденного связанного документа другой договор показывается как контекст, а не как ошибка.
- `VAT_MISMATCH` - расходится ставка или сумма НДС.
- `CONTRACT_CONTEXT_MISSING` - в 1C DTO нет аналитики договора/поставки.
- `SOURCE_ERROR` - ERP или 1C источник недоступен.

## XLSX сальдовки

XLSX выгрузка должна повторять бухгалтерский формат:

```text
№ спецификации | | Счет | Сумма по счету | Сумма оплаты | | Возмещаемые расходы | Невозмещаемые расходы | | № счф | (+/-)
```

Правила:

- ячейки `№ спецификации`, `Возмещаемые расходы`, `Невозмещаемые расходы`, `№ счф`, `(+/-)` объединяются на количество строк счетов поставки;
- `Сумма оплаты` не объединяется: по каждому счету показывается `get_paidsum(veda_schets.f_operid)`, а не общий агрегат поставки;
- номера и даты закрывающих документов внутри `№ счф` выводятся через перенос строки в формате `номер от ДД.ММ.ГГГГ`;
- если операция входит в агрегированный закрывающий документ (`veda_akts.f_mainakt`), выводится только агрегат; дочерние документы скрываются;
- сумма `get_paidsum` одной операции назначается строкам счетов один раз; отрицательные строки `Оплата без счета` запрещены, положительный несвязанный остаток называется `Оплата, не связанная со счетом`;
- лист `Правила` содержит источник и правило расчета каждого столбца;
- копирование в TSV разворачивает объединенные ячейки в плоские строки.

## Авторизация

- пользователь открывает модуль из ERP;
- ERP передает короткоживущий `launch_token`;
- UI отправляет token в backend через `POST /api/auth/erp-launch`;
- backend валидирует token в ERP;
- backend получает профиль пользователя: `id`, `login/email`, ФИО, роли;
- backend создает внутреннюю session сервиса сверки;
- UI удаляет `launch_token` из адресной строки после обмена;
- в UI отображается ФИО/email пользователя;
- отдельный внешний вход вне ERP не используется.

Если ERP передает вместе с переходом `email`, ФИО или `user_id`, эти значения не считаются доверенными до проверки token. Сервис не читает пароль пользователя из `veda_users` и не выполняет вход в ERP по login/password пользователя.

## Логирование

Обязательные таблицы:

```text
veda_reconciliation_runs
veda_reconciliation_items
```

Логирование фиксирует:

- кто и когда запустил сверку;
- scope запуска: клиент, договор, поставка, batch;
- количество документов ERP и 1C;
- общий статус запуска;
- каждое расхождение и его тип;
- поля, которые не совпали.

## Performance rules

- live-экран всегда использует `limit`;
- целевое время загрузки live-матрицы: до 10 секунд для страницы до 50 поставок при фильтре по ЮЛ/договору/периоду;
- целевое время загрузки полного набора одного договора: до 15 секунд для объема до 150 поставок; больший объем переводится в пагинацию или background runner;
- целевое время XLSX-выгрузки одного договора: до 20 секунд для объема до 150 поставок;
- API матрицы возвращает `metrics.erp_sql_ms`; этот показатель нужно показывать/логировать для диагностики производительности;
- полная историческая сверка запускается только через background runner;
- 1C REST endpoints обязаны поддерживать `limit`, `cursor`, `changed_since`;
- повторная сверка должна использовать `updated_at` и `hash`;
- ERP SQL должен использовать индексы по `veda_specs.f_dogid`, `veda_dogs.f_contrid`, `veda_clients.f_contactid`, `veda_spec_invoices.f_specid`, `veda_spec_invoices.f_parenttype`, `veda_acchist_docs.f_docid`, `veda_categs(f_objectid, f_ctgtype, f_objecttype)`.

Текущий production-baseline от 2026-07-08 для договора `client_id=221`, `dog_id=88`, период `2025-01-01..2026-07-08`: 50 поставок загружаются за 7.2 сек, полный набор 126 поставок - за 12.7 сек, XLSX на 126 поставок - за 12.9 сек.

## Environment variables

- `PRINT_DB_HOST`
- `PRINT_DB_PORT`
- `PRINT_DB_NAME`
- `PRINT_DB_USER`
- `PRINT_DB_PASSWORD`
- `RECON_API_HOST`
- `RECON_API_PORT`
- `RECON_STATIC_ROOT`
- `RECON_ERP_TOKEN_VALIDATE_URL`
- `RECON_ERP_TOKEN_AUDIENCE`
- `RECON_ONEC_REST_BASE_URL`
- `RECON_ONEC_REST_TOKEN`
- `RECON_ONEC_REST_USER`
- `RECON_ONEC_REST_PASSWORD`
- `RECON_ONEC_REST_TIMEOUT`
- `RECON_ONEC_REST_SNAPSHOT_PATH`
- `RECON_ONEC_REST_HEALTH_PATH`
- `RECON_ONEC_REST_CLIENT_MATRIX_MAX_LIMIT`
