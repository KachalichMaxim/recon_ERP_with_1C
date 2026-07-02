# Project Tree

```text
erp_1c_reconciliation/
  contracts/
    onec/
      openapi.json
      openapi.yaml
      openapi_ru.md
  deploy/
    systemd/
      reconciliation-api.service
  docs/
    api/
    architecture/
    reference/
    requirements/
    screenshots/
  reference/
    live_samples/
    prototype/
  sql/
    1c_reconciliation_schema.sql
  src/
    recon_erp_1c/
      application/
        ports/
        serializers.py
        use_cases/
      bootstrap/
      domain/
      infrastructure/
        erp_mariadb/
        logging/
        onec_rest/
        persistence/
      interfaces/
        http/
          api.py
          auth.py
        web/
  tests/
  tools/
```

## Реализованные production entrypoints

```text
src/recon_erp_1c/interfaces/http/api.py
```

Endpoints:

```text
GET /health
GET /api/config/status
GET /api/reconciliation/specifications
GET /api/reconciliation/run
```

## Реализованные adapters

```text
infrastructure/erp_mariadb/repository.py
infrastructure/onec_rest/repository.py
infrastructure/persistence/mariadb_log_repository.py
```

`reference/prototype` не является production-кодом и не импортируется из `src`.
