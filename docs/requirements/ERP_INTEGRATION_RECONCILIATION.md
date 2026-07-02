# Интеграция кнопки в ERP

## Кнопка на странице спецификации
Добавить кнопку:
- `Сверка с 1С`

## Действие кнопки
Открывать отдельную страницу модуля сверки с передачей `spec_id`:

```text
/reconciliation.html?spec_id=<ID_СПЕЦИФИКАЦИИ>
```

Пример:
```text
/reconciliation.html?spec_id=26931
```

## Поведение на странице сверки
Пользователь нажимает одну кнопку `Сверить с 1С`, после чего вызывается:

```http
POST /api/reconciliation/run
{
  "spec_id": 26931,
  "scope": "specification"
}
```

## Будущее расширение
Для уровня клиента:

```http
POST /api/reconciliation/run
{
  "spec_id": 26931,
  "scope": "client",
  "scope_id": <CLIENT_ID>
}
```
