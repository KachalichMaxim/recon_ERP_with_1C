# ТЗ: read-only GET REST API 1C для сервиса сверки ERP и 1C

OpenAPI/Swagger-контракт:

- JSON: `contracts/onec/openapi.json`
- YAML: `contracts/onec/openapi.yaml`

Русская документация и маппинг 1C -> DTO:

- `contracts/onec/openapi_ru.md`

## 1. Цель

1C должна предоставить read-only REST API для Python-сервиса сверки ERP и 1C.

API должен быть **GET-only**:

- без тела запроса;
- без записи в 1C;
- без публикации сырых OData-объектов;
- с нормализованными DTO, понятными сервису сверки.

## 2. Обязательные endpoints

Минимум для первой интеграции:

```http
GET /reconciliation/v1/health
GET /reconciliation/v1/snapshot
```

Для фоновой сверки:

```http
GET /reconciliation/v1/counterparties
GET /reconciliation/v1/contracts
GET /reconciliation/v1/invoices
GET /reconciliation/v1/payments
GET /reconciliation/v1/sales
GET /reconciliation/v1/purchases
GET /reconciliation/v1/account-movements
GET /reconciliation/v1/balances
```

## 3. Главный GET-запрос

Endpoint:

```http
GET /reconciliation/v1/snapshot
```

Пример по договору:

```http
GET /reconciliation/v1/snapshot?date_from=2025-01-01&date_to=2025-12-31&counterparty_inn=7811451960&contract_number=660%2F1
```

Пример по поставке:

```http
GET /reconciliation/v1/snapshot?date_from=2025-07-01&date_to=2025-08-31&counterparty_inn=7811451960&contract_number=660%2F1&spec_number=921
```

Пример по известным кодам документов:

```http
GET /reconciliation/v1/snapshot?date_from=2025-07-01&date_to=2025-08-31&organization_code=000000001&counterparty_code=БП-000123&document_code=ВА-007703&document_code=00БП-010299&document_type=customer_invoice&document_type=payment
```

## 4. Параметры `/snapshot`

| Параметр | Обяз. | Повторяемый | Назначение |
|---|---:|---:|---|
| `date_from` | да | нет | начало периода документов 1C |
| `date_to` | да | нет | конец периода документов 1C |
| `request_id` | нет | нет | id запроса для трассировки |
| `mode` | нет | нет | режим области поиска: `delivery_reconciliation`, `contract_reconciliation`, `client_reconciliation` |
| `organization_code` | нет | нет | код организации 1C |
| `organization_inn` | нет | нет | ИНН организации |
| `counterparty_code` | нет | нет | код контрагента 1C |
| `counterparty_inn` | нет | нет | ИНН ЮЛ клиента |
| `contract_code` | нет | да | код договора 1C |
| `contract_number` | нет | да | номер договора, например `660/1` |
| `contract_role` | нет | да | `buyer`, `committent`, `supplier`, `agent`, `related` |
| `base_contract` | нет | нет | базовый договор |
| `spec_id` | нет | нет | ERP id поставки, только для трассировки |
| `spec_number` | нет | нет | номер поставки/заявки/спецификации |
| `document_code` | нет | да | код/номер документа 1C |
| `document_number` | нет | да | номер документа для fallback-поиска |
| `document_type` | нет | да | `customer_invoice`, `payment`, `sale`, `purchase`, `closing_document`, `account_movement` |
| `include` | нет | да | какие блоки вернуть |
| `cursor` | нет | нет | курсор страницы |
| `limit` | нет | нет | размер страницы, default 500, max 2000 |

Минимальное правило фильтра:

```text
date_from + date_to обязательны,
и дополнительно нужен хотя бы один бизнес-фильтр:
contract_code / contract_number / counterparty_code / counterparty_inn / document_code.
```

### 4.1 Режим `delivery_reconciliation`

Целевой запрос Python для сверки одной поставки:

```http
mode=delivery_reconciliation
buyer_contract_code=<код договора с покупателем>
committent_contract_code=<код договора с комитентом>
```

До публикации поддержки этих параметров в 1С Python сохраняет совместимый запрос без `mode`, `spec_number` и `base_contract`. После приемочного теста расширенный запрос включается настройкой `RECON_ONEC_DELIVERY_SCOPE_ENABLED=1`.

Новый параметр `scope=delivery` не требуется: его смысл уже выражен параметром `mode`.

В этом режиме документ попадает в ответ, если хотя бы один из переданных кодов договора найден:

1. в договоре шапки документа;
2. в договоре строки табличной части документа;
3. в расшифровке/распределении платежа;
4. в иной аналитике документа, которая однозначно связывает его с договором-заявкой.

По найденному документу нужно вернуть одну шапку и все строки его табличной части в `document_lines`, а не только совпавшую строку. Каждая строка должна содержать собственный `contract_code`, сумму и идентификатор строки. Это позволяет Python проверить сумму шапки и корректно распределить документ между поставками.

`spec_number` и `base_contract` передаются как контрольный контекст. Они не заменяют точный поиск по `buyer_contract_code` / `committent_contract_code`.

В режиме `contract_reconciliation` допускается обычный отбор по договору шапки без расширения области через табличные части. Python-сервис поставочной сверки этот режим не использует.

## 5. Ответ `/snapshot`

```json
{
  "ok": true,
  "request_id": "spec-20334-20260629123000",
  "snapshot": {
    "metadata": {
      "source_system": "1c",
      "generated_at": "2026-06-29T12:31:02",
      "timezone": "Asia/Novosibirsk",
      "date_from": "2025-07-01",
      "date_to": "2025-08-31",
      "total_before_filter": 128,
      "returned_count": 24,
      "elapsed_ms": 940,
      "next_cursor": null
    },
    "counterparties": [],
    "contracts": [],
    "customer_invoices": [],
    "payments": [],
    "sales": [],
    "purchases": [],
    "document_lines": [],
    "account_movements": [],
    "balances": [],
    "warnings": []
  }
}
```

## 6. Что возвращать в блоках

| Блок | Источник 1C |
|---|---|
| `counterparties` | `Справочник.Контрагенты` |
| `contracts` | `Справочник.ДоговорыКонтрагентов` |
| `customer_invoices` | `Документ.СчетНаОплатуПокупателю` |
| `payments` | `Документ.ПоступлениеНаРасчетныйСчет`, при необходимости `СписаниеСРасчетногоСчета`, табличная часть `РасшифровкаПлатежа` |
| `sales` | `Документ.РеализацияТоваровУслуг`, связанные счет-фактуры/УПД |
| `purchases` | `Документ.ПоступлениеТоваровУслуг` |
| `document_lines` | табличные части `Товары`, `Услуги`, `АгентскиеУслуги` |
| `account_movements` | `РегистрБухгалтерии.Хозрасчетный` |
| `balances` | `РегистрБухгалтерии.Хозрасчетный.Остатки` или `ОборотыИОстатки` |

Подробный маппинг каждого поля описан в `contracts/onec/openapi_ru.md`.

`document_lines` не является отдельным поисковым endpoint в MVP. Это блок строк тех документов, которые уже попали в `snapshot` по текущим фильтрам и `include`. Если документ не попал в `customer_invoices` / `sales` / `purchases`, его строки в `document_lines` возвращать не нужно.

Обязательные уточнения по документам:

1. В DTO документа нужно разделять:
   - `number` - внутренний номер документа 1C;
   - `incoming_number` - входящий номер / номер платежного поручения / номер документа поставщика;
   - `incoming_date` - дата входящего документа, если есть.

2. При запросе по `buyer_contract_code` / `committent_contract_code` 1C должна вернуть не только документы с прямым `ДоговорКонтрагента.Код` равным этим кодам, но и документы, которые сама 1C показывает во вкладке "Документы" этой заявки/договора, даже если прямой договор документа является договором поставщика.

3. Для таких связанных документов 1C должна заполнить:
   - `contract_code` - прямой договор документа;
   - `linked_contract_codes` - коды договоров заявки/спецификации, через которые документ попал в snapshot.

4. Если один физический документ относится к нескольким поставкам/заявкам, 1C должна вернуть `allocations[]`:
   - `allocations[].amount` - сумма, относящаяся к конкретной заявке/строке;
   - `allocations[].contract_code` - прямой договор строки;
   - `allocations[].linked_contract_code` - договор заявки/спецификации, через который строка попала в snapshot;
   - `allocations[].document_line_id` - id строки документа, если доступен.

   Без `allocations[]` Python видит только полную сумму документа 1C и будет фиксировать `amount_mismatch`, если ERP сверяет долю документа в рамках одной поставки.

5. Если связанные документы по заявке невозможно получить из аналитики 1C, API должно вернуть предупреждение в `warnings[]`, а не молча отдавать неполный набор.

## 7. Пагинация

Для `/snapshot` пагинация нужна, если ответ слишком большой.

Для collection endpoints пагинация обязательна.

Правила:

- `limit` по умолчанию 500;
- максимум 2000;
- если есть следующая страница, вернуть `next_cursor`;
- следующий запрос должен принимать тот же набор фильтров + `cursor`.

## 8. Ошибки

```json
{
  "ok": false,
  "error": "validation_error",
  "message": "Не указан date_from",
  "request_id": "spec-20334-20260629123000",
  "details": {}
}
```

Типовые коды:

- `bad_request`;
- `unauthorized`;
- `validation_error`;
- `source_timeout`;
- `internal_error`.

## 9. Производительность

Интерактивный `/snapshot` не должен выгружать всю историю.

1C должна фильтровать по:

- периоду;
- организации;
- контрагенту;
- договору;
- номеру поставки/заявки/спецификации;
- переданным кодам документов.

Для больших периодов использовать collection endpoints и фоновый runner.

## 10. Критерии приемки

1. `GET /reconciliation/v1/health` возвращает `ok=true`.
2. `GET /reconciliation/v1/snapshot` работает без request body.
3. Запрос по договору возвращает только документы указанного контрагента/договора/периода.
4. Запрос по поставке дополнительно ограничивает данные номером заявки/спецификации, если такая аналитика есть в 1C.
5. Запрос по `document_code` возвращает конкретные документы и связанные строки/движения.
6. Все DTO содержат `source_id`, `posted`, `deleted`, `updated_at`, `hash`.
7. Collection endpoints поддерживают `cursor` и `limit`.
8. API не содержит write-операций.
