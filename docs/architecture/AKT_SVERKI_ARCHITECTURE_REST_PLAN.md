# Акт сверки ERP <-> 1C: целевая архитектура REST

## 1. Решение по стеку

Требования к решению описаны отдельно в `RECONCILIATION_BABOK_REQUIREMENTS.md`: бизнес-требования, пользовательские требования, функциональные требования, нефункциональные требования, переходные требования, бизнес-правила и критерии приемки.

Целевой стек:

- UI: текущий HTML/React экран `akt_sverki/index.html`;
- backend: Python service `reconciliation_api_server.py`;
- ERP data source: MariaDB ERP;
- ERP auth: переход из ERP в модуль с короткоживущим launch token;
- 1C data source: отдельный read-only REST API 1C `/reconciliation/v1/...`.

Не целевой стек:

- не встраивать сверку внутрь PHP ERP;
- не встраивать сверку внутрь 1C;
- не использовать сырой OData 1C как контракт сверки;
- не делать сервис сверки зависимым от внутренних имен объектов 1C.

## 2. Разделение модулей

### ERP-сальдовка по поставкам

Назначение: показать бухгалтеру сальдо по поставкам.

Считается только по ERP:

- счета покупателю;
- оплаты клиента;
- возмещаемые расходы;
- невозмещаемые расходы;
- переплата/долг.

Источник:

- MariaDB ERP;
- routines `get_paidsum/get_realizsum`;
- исходные таблицы ERP, без `view_specinv`.

Результат:

- экран матрицы;
- XLSX в привычном бухгалтерском формате.

### Сверка ERP vs 1C

Назначение: проверить, что документы ERP и 1C совпадают.

Источники:

- ERP: MariaDB;
- 1C: read-only REST DTO.

Результат:

- статусы по документам;
- список расхождений;
- лог типов расхождений для последующей аналитики.

## 3. REST API 1C

Контракт 1C описан отдельно:

- `docs/api/onec_reconciliation_rest_api_tz.md`

Главный принцип: 1C отдает подготовленные DTO, а не сырые документы/справочники.

Основной live endpoint:

```http
GET /reconciliation/v1/snapshot
```

Collection endpoints для batch/runner:

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

## 4. Python backend REST connector

Добавлен целевой REST connector:

- `onec_rest_client.py`
- `contracts/onec/openapi.json`
- `contracts/onec/openapi.yaml`
- `contracts/onec/openapi_ru.md`

Переменные окружения:

- `RECON_ONEC_REST_BASE_URL` - базовый URL 1C REST API.
- `RECON_ONEC_REST_TOKEN` - bearer token технического пользователя 1C.
- `RECON_ONEC_REST_USER` / `RECON_ONEC_REST_PASSWORD` - альтернативная техническая basic auth, если bearer token не используется в контуре 1C.
- `RECON_ONEC_REST_TIMEOUT` - timeout, по умолчанию `60`.
- `RECON_ONEC_REST_SNAPSHOT_PATH` - путь snapshot endpoint, по умолчанию `/reconciliation/v1/snapshot`.
- `RECON_ONEC_REST_HEALTH_PATH` - путь health endpoint, по умолчанию `/reconciliation/v1/health`.
- `RECON_ONEC_REST_CLIENT_MATRIX_MAX_LIMIT` - лимит live-сверки по клиенту, по умолчанию `10`.

Backend endpoints:

```http
GET /api/reconciliation/1c-rest-status
GET /api/reconciliation/client-matrix?client_id=<id>&dog_id=<id>&limit=<n>
GET /api/reconciliation/client-matrix?client_id=<id>&dog_id=<id>&limit=<n>&compare_1c=1
GET /api/reconciliation/client-matrix.xlsx?client_id=<id>&dog_id=<id>&limit=<n>
```

The only direct online 1C source for the Python backend is the read-only REST contract above.

## 5. Canonical model

1C REST DTO и ERP SQL приводятся к единой модели:

- counterparty;
- contract;
- customer_invoice;
- incoming_payment;
- sale_act;
- purchase_act;
- document_line;
- account_movement.

Сверка документов не должна идти только по сумме.

Основные ключи сопоставления:

- тип документа;
- код/номер 1C;
- дата;
- организация;
- контрагент;
- договор покупателя;
- договор комитента;
- base_contract_number;
- spec_number;
- сумма;
- признак posted/deleted.

## 6. Статусы расхождений

Минимальный набор:

- `MATCH` - документ найден и бизнес-поля совпали;
- `NOT_FOUND_IN_1C` - есть в ERP, нет в 1C;
- `NOT_FOUND_IN_ERP` - есть в 1C, нет в ERP;
- `AMOUNT_MISMATCH` - сумма расходится;
- `DATE_MISMATCH` - дата расходится;
- `NUMBER_MISMATCH` - номер/код расходится;
- `DUPLICATE_IN_1C` - по ключу `код 1C + дата 1C + договор` найдено несколько документов 1C;
- `AMBIGUOUS_MATCH` - резервный ключ дал несколько кандидатов и документ нельзя сопоставить автоматически;
- `VAT_MISMATCH` - ставка/сумма НДС расходится;
- `CONTRACT_CONTEXT_MISSING` - нет договора/заявки в 1C DTO;
- `CONTRACT_MISMATCH` - договор/заявка не совпали;
- `SOURCE_ERROR` - 1C REST недоступен или вернул ошибку.

Статусы должны записываться в лог сверки с типом операции/документа, чтобы считать частоту проблем.

## 7. Лог сверки и аудит расхождений

Лог - обязательная часть архитектуры, а не debug-файл. Он нужен, чтобы:

- видеть, когда и по какому объекту запускали сверку;
- считать частоту типов расхождений;
- находить проблемные операции, документы, договоры и источники;
- отличать ошибку источника 1C от реального расхождения данных.

Таблицы ERP MariaDB:

```text
veda_reconciliation_runs
veda_reconciliation_items
```

DDL зафиксирован в:

```text
sql/1c_reconciliation_schema.sql
```

`veda_reconciliation_runs` хранит один запуск сверки:

- `scope`: `specification`, `contract`, `client`, `batch`;
- `scope_id`;
- `spec_id`;
- `client_id`;
- `source_mode`: `rest-live`, `rest-batch`, `server-run`;
- количество документов ERP/1C;
- общий статус запуска;
- `summary_json`;
- `created_at`.

`veda_reconciliation_items` хранит результат по каждой документной паре или отсутствующему документу:

- ссылка на `run_id`;
- ERP-документ: id, код 1C, номер, дата, сумма, тип;
- 1C-документ: код, номер, дата, сумма, тип;
- `status`;
- `mismatch_fields_json`;
- `note`;
- `created_at`.

Запись выполняется после расчета matcher-а:

```text
ERP snapshot + 1C snapshot -> matcher -> statuses -> INSERT run -> INSERT items
```

Если таблицы не установлены, backend не должен падать: результат возвращается в UI, но `run_id = null`. Для production таблицы должны быть установлены обязательно.

## 8. Производительность

Live:

- не грузить всю историю клиента;
- ограничивать количество поставок `limit`;
- для live-сверки с 1C применять `RECON_ONEC_REST_CLIENT_MATRIX_MAX_LIMIT`;
- REST-запрос в 1C строить только по контексту ERP: период, организация, контрагент, договоры, номера/коды документов;
- UI сначала показывает ERP-сальдовку, а сверку 1C запускает отдельным действием.

Batch:

- использовать collection endpoints с `changed_since`;
- хранить raw snapshot и normalized snapshot;
- запускать по расписанию/очереди;
- не выполнять полный исторический проход синхронно из UI.

## 9. Авторизация

### 9.1 Целевой flow

1. Пользователь авторизован в ERP.
2. Пользователь нажимает пункт меню/кнопку перехода в модуль сверки.
3. ERP генерирует короткоживущий `launch_token`, привязанный к пользователю, времени выдачи и разрешенному действию `reconciliation.open`.
4. ERP открывает модуль сверки и передает token:

```http
https://<reconciliation-host>/akt_sverki/index.html?launch_token=<token>
```

или через POST/iframe/message, если ERP не хочет класть token в query string.

5. UI сразу отправляет token в backend:

```http
POST /api/auth/erp-launch
Content-Type: application/json

{"launch_token":"..."}
```

6. Backend валидирует token через ERP и получает профиль пользователя.
7. Backend создает свою короткую session и возвращает в UI только session token и публичный профиль пользователя.
8. UI удаляет `launch_token` из адресной строки через `history.replaceState`.

Пользовательские поля, переданные из браузера вместе с переходом (`email`, `fio`, `user_id`), не являются основанием для доступа. Они могут использоваться только как подсказка для UX до проверки token. Авторитетный профиль пользователя должен прийти из ERP token validation response.

### 9.2 Backend

- принимает только ERP launch token, полученный при переходе из ERP;
- валидирует token через ERP endpoint;
- получает `user_id`, `login/email`, ФИО и роли/права;
- дополнительно может сверить пользователя с `veda_users`;
- создает внутреннюю session сервиса сверки;
- не возвращает ERP launch token в браузер после успешного обмена;
- не читает пароль пользователя из `veda_users` и не делает вход по login/password;
- не принимает внешние identity token вне ERP.

Минимальный endpoint, который нужен со стороны ERP:

```http
POST /veda/api/erp/validatetoken/
Content-Type: application/json

{"token":"...","audience":"reconciliation"}
```

Минимальный ответ ERP:

```json
{
  "ok": true,
  "user": {
    "id": 123,
    "login": "user@vedagent.ru",
    "email": "user@vedagent.ru",
    "display_name": "Иванов Иван",
    "roles": ["accountant"]
  },
  "expires_at": "2026-07-01T12:30:00+07:00"
}
```

Если в ERP уже есть действующий token API другого формата, нужно согласовать endpoint валидации, который по token возвращает тот же профиль пользователя.

1C REST:

- отдельный технический read-only token/basic auth;
- не связан с пользовательской session ERP;
- права только на чтение согласованных объектов.

## 10. Что нужно от 1C-разработчика

1. Подтвердить, какие документы/регистры/справочники являются источниками полей DTO.
2. Реализовать `/reconciliation/v1/health`.
3. Реализовать `/reconciliation/v1/snapshot`.
4. Реализовать collection endpoints для batch.
5. Поддержать фильтры: период, организация, контрагент, договор, тип документа, `changed_since`.
6. Поддержать пагинацию.
7. Вернуть `source_id`, `updated_at`, `posted`, `deleted`, `hash`.
8. Отдать скрытую аналитику строк `Услуги`, где хранится договор-заявка/комитент, если она есть в 1C.
9. Для недоступной аналитики явно вернуть warning, а не скрывать проблему.

## 11. Что уже сделано в Python skeleton

- `onec_rest_client.py` - read-only REST client.
- `reconciliation_api_server.py` использует 1C REST adapter как целевой источник данных 1C.
- `GET /api/reconciliation/1c-rest-status` показывает конфигурацию REST-источника.
- REST-ответ нормализуется в текущую модель matcher-а.
- C4 архитектура обновлена под REST.
- ТЗ 1C REST API добавлено в `docs/api/onec_reconciliation_rest_api_tz.md`.
