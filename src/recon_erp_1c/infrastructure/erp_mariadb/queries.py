"""SQL fragments for ERP MariaDB.

The application layer must not import this module directly. These queries
belong to the MariaDB adapter and are documented here so the data mapping is
kept close to the implementation.
"""

DELIVERY_BY_SPEC_ID = """
SELECT
    s.f_id,
    s.f_num,
    s.f_dt,
    s.f_kod1cb,
    s.f_kod1cp,
    d.f_id AS dog_id,
    d.f_dogname,
    d.f_kod1c AS base_dog_code1c,
    org.f_id AS org_id,
    org.f_kod1c AS org_code1c,
    org.f_inn AS org_inn,
    org.f_cname AS org_name,
    client.f_id AS client_id,
    client.f_kod1c AS client_code1c,
    client.f_inn AS client_inn,
    client.f_cname AS client_name
FROM veda_specs s
JOIN veda_dogs d ON d.f_id = s.f_dogid
LEFT JOIN veda_clients org ON org.f_id = d.f_orgid
LEFT JOIN veda_clients client ON client.f_id = d.f_contrid
WHERE s.f_id = %(spec_id)s
LIMIT 1;
"""

LIST_DELIVERIES = """
SELECT
    s.f_id AS spec_id,
    COALESCE(s.f_num, '') AS spec_number,
    COALESCE(NULLIF(spec_type.f_name, ''), NULLIF(spec_type.f_dopprstr, ''), NULLIF(spec_type.f_uslstr, ''), '') AS spec_type_name,
    s.f_dt AS spec_date,
    s.f_dtclose AS closure_date,
    COALESCE(s.f_status, 0) AS spec_status,
    COALESCE(s.f_kod1cb, '') AS buyer_contract_code,
    COALESCE(s.f_kod1cp, '') AS committent_contract_code,
    d.f_id AS dog_id,
    COALESCE(d.f_dogname, '') AS base_contract_number,
    COALESCE(org.f_abbr, '') AS organization_abbr,
    CONCAT(
        COALESCE(d.f_dogname, ''), '/',
        COALESCE(s.f_num, ''), '/',
        COALESCE(org.f_abbr, ''), '/',
        COALESCE(client.f_cname, '')
    ) AS delivery_full_name,
    COALESCE(main_client.f_id, 0) AS main_client_id,
    COALESCE(main_client.f_name, '') AS main_client_name,
    COALESCE(client.f_id, 0) AS client_id,
    COALESCE(client.f_cname, '') AS client_name,
    COALESCE(client.f_inn, '') AS client_inn
FROM veda_specs s
JOIN veda_dogs d ON d.f_id = s.f_dogid
LEFT JOIN veda_clients client ON client.f_id = d.f_contrid
LEFT JOIN veda_clients org ON org.f_id = d.f_orgid
LEFT JOIN veda_contacts main_client ON main_client.f_id = client.f_contactid
LEFT JOIN veda_spr spec_type ON spec_type.f_type = 33 AND spec_type.f_num = s.f_typez
WHERE (%(spec_id)s IS NULL OR s.f_id = %(spec_id)s)
  AND (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
  AND (%(dog_id)s IS NULL OR d.f_id = %(dog_id)s)
  AND (%(date_from)s IS NULL OR s.f_dt >= %(date_from)s)
  AND (%(date_to)s IS NULL OR s.f_dt <= %(date_to)s)
ORDER BY s.f_dt DESC, s.f_id DESC
LIMIT %(limit)s OFFSET %(offset)s;
"""

COUNT_DELIVERIES = """
SELECT COUNT(*) AS total_count
FROM veda_specs s
JOIN veda_dogs d ON d.f_id = s.f_dogid
WHERE (%(spec_id)s IS NULL OR s.f_id = %(spec_id)s)
  AND (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
  AND (%(dog_id)s IS NULL OR d.f_id = %(dog_id)s)
  AND (%(date_from)s IS NULL OR s.f_dt >= %(date_from)s)
  AND (%(date_to)s IS NULL OR s.f_dt <= %(date_to)s);
"""

MATRIX_TOTAL_SUMMARY = """
SELECT
    COUNT(*) AS deliveries,
    COALESCE(SUM(COALESCE(inv.invoice_sum, 0)), 0) AS invoice_sum,
    COALESCE(SUM(COALESCE(pay.payment_sum, 0)), 0) AS payment_sum,
    COALESCE(SUM(COALESCE(sales.reimbursable_sum, 0)), 0) AS reimbursable_sum,
    COALESCE(SUM(COALESCE(sales.non_reimbursable_sum, 0)), 0) AS non_reimbursable_sum,
    COALESCE(SUM(COALESCE(pay.payment_sum, 0) - COALESCE(sales.reimbursable_sum, 0) - COALESCE(sales.non_reimbursable_sum, 0)), 0) AS balance,
    SUM(CASE WHEN COALESCE(pay.payment_sum, 0) - COALESCE(sales.reimbursable_sum, 0) - COALESCE(sales.non_reimbursable_sum, 0) < 0 THEN 1 ELSE 0 END) AS debts,
    SUM(CASE WHEN COALESCE(pay.payment_sum, 0) - COALESCE(sales.reimbursable_sum, 0) - COALESCE(sales.non_reimbursable_sum, 0) > 0 THEN 1 ELSE 0 END) AS overpayments
FROM (
    SELECT
        s.f_id AS spec_id,
        COALESCE(s.f_kod1cb, '') AS buyer_contract_code
    FROM veda_specs s
    JOIN veda_dogs d ON d.f_id = s.f_dogid
    WHERE (%(spec_id)s IS NULL OR s.f_id = %(spec_id)s)
      AND (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
      AND (%(dog_id)s IS NULL OR d.f_id = %(dog_id)s)
      AND (%(date_from)s IS NULL OR s.f_dt >= %(date_from)s)
      AND (%(date_to)s IS NULL OR s.f_dt <= %(date_to)s)
) filtered_specs
LEFT JOIN (
    SELECT
        schet.f_dogid AS spec_id,
        SUM(COALESCE(schet.f_sum, 0)) AS invoice_sum
    FROM veda_schets schet
    WHERE schet.f_dogtype = 2
      AND COALESCE(schet.f_type, 0) = 1
      AND COALESCE(schet.f_maininv, 0) = 0
    GROUP BY schet.f_dogid
) inv ON inv.spec_id = filtered_specs.spec_id
LEFT JOIN (
    SELECT
        spec.f_id AS spec_id,
        SUM(COALESCE(get_paidsum(oper.f_id), 0)) AS payment_sum
    FROM veda_spec_invoices oper
    LEFT JOIN veda_categs oper4_specs
        ON oper4_specs.f_objectid = oper.f_id
       AND oper4_specs.f_ctgtype = 24
       AND oper4_specs.f_objecttype = 5
    JOIN veda_specs spec
        ON spec.f_id = CASE oper.f_parenttype
          WHEN 2 THEN oper.f_specid
          WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
          ELSE NULL
        END
    WHERE oper.f_parenttype IN (2, 4)
      AND COALESCE(get_paidsum(oper.f_id), 0) <> 0
    GROUP BY spec.f_id
) pay ON pay.spec_id = filtered_specs.spec_id
LEFT JOIN (
    SELECT
        sales_ops.spec_id,
        SUM(
            CASE
                WHEN sales_ops.reimbursement_id = 1 THEN sales_ops.realiz_sum
                WHEN sales_ops.reimbursement_id NOT IN (1, 2)
                 AND sales_ops.buyer_contract_code <> ''
                 AND sales_ops.operation_contract_code <> sales_ops.buyer_contract_code
                    THEN sales_ops.realiz_sum
                ELSE 0
            END
        ) AS reimbursable_sum,
        SUM(
            CASE
                WHEN sales_ops.reimbursement_id = 2 THEN sales_ops.realiz_sum
                WHEN sales_ops.reimbursement_id NOT IN (1, 2)
                 AND sales_ops.buyer_contract_code <> ''
                 AND sales_ops.operation_contract_code = sales_ops.buyer_contract_code
                    THEN sales_ops.realiz_sum
                ELSE 0
            END
        ) AS non_reimbursable_sum
    FROM (
        SELECT
            spec.f_id AS spec_id,
            COALESCE(oper.f_isvozm, 0) AS reimbursement_id,
            COALESCE(get_realizsum(oper.f_id), 0) AS realiz_sum,
            COALESCE(spec.f_kod1cb, '') AS buyer_contract_code,
            COALESCE(NULLIF(dog.f_kod1c, ''), NULLIF(spec.f_kod1cp, ''), NULLIF(spec.f_kod1cb, ''), '') AS operation_contract_code
        FROM veda_spec_invoices oper
        LEFT JOIN veda_categs oper4_specs
            ON oper4_specs.f_objectid = oper.f_id
           AND oper4_specs.f_ctgtype = 24
           AND oper4_specs.f_objecttype = 5
        JOIN veda_specs spec
            ON spec.f_id = CASE oper.f_parenttype
              WHEN 2 THEN oper.f_specid
              WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
              ELSE NULL
            END
        LEFT JOIN (
            SELECT f_operid, MIN(f_dogid) AS f_dogid
            FROM veda_akts
            GROUP BY f_operid
        ) akt ON akt.f_operid = oper.f_id
        LEFT JOIN veda_dogs dog ON dog.f_id = akt.f_dogid
        WHERE oper.f_parenttype IN (2, 4)
    ) sales_ops
    GROUP BY sales_ops.spec_id
) sales ON sales.spec_id = filtered_specs.spec_id;
"""

SEARCH_DELIVERY_BY_ID = """
SELECT
    s.f_id AS spec_id,
    COALESCE(s.f_num, '') AS spec_number,
    COALESCE(NULLIF(spec_type.f_name, ''), NULLIF(spec_type.f_dopprstr, ''), NULLIF(spec_type.f_uslstr, ''), '') AS spec_type_name,
    s.f_dt AS spec_date,
    d.f_id AS dog_id,
    COALESCE(d.f_dogname, '') AS base_contract_number,
    COALESCE(org.f_abbr, '') AS organization_abbr,
    COALESCE(client.f_id, 0) AS client_id,
    COALESCE(client.f_cname, '') AS client_name,
    COALESCE(client.f_inn, '') AS client_inn,
    CONCAT(
        COALESCE(d.f_dogname, ''), '/',
        COALESCE(s.f_num, ''), '/',
        COALESCE(org.f_abbr, ''), '/',
        COALESCE(client.f_cname, '')
    ) AS delivery_full_name
FROM veda_specs s
JOIN veda_dogs d ON d.f_id = s.f_dogid
LEFT JOIN veda_clients client ON client.f_id = d.f_contrid
LEFT JOIN veda_clients org ON org.f_id = d.f_orgid
LEFT JOIN veda_spr spec_type ON spec_type.f_type = 33 AND spec_type.f_num = s.f_typez
WHERE s.f_id = %(spec_id)s
  AND (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
  AND (%(dog_id)s IS NULL OR d.f_id = %(dog_id)s)
  AND (%(date_from)s IS NULL OR s.f_dt >= %(date_from)s)
  AND (%(date_to)s IS NULL OR s.f_dt <= %(date_to)s)
LIMIT 1;
"""

SEARCH_DELIVERIES = """
SELECT
    s.f_id AS spec_id,
    COALESCE(s.f_num, '') AS spec_number,
    COALESCE(NULLIF(spec_type.f_name, ''), NULLIF(spec_type.f_dopprstr, ''), NULLIF(spec_type.f_uslstr, ''), '') AS spec_type_name,
    s.f_dt AS spec_date,
    d.f_id AS dog_id,
    COALESCE(d.f_dogname, '') AS base_contract_number,
    COALESCE(org.f_abbr, '') AS organization_abbr,
    COALESCE(client.f_id, 0) AS client_id,
    COALESCE(client.f_cname, '') AS client_name,
    COALESCE(client.f_inn, '') AS client_inn,
    CONCAT(
        COALESCE(d.f_dogname, ''), '/',
        COALESCE(s.f_num, ''), '/',
        COALESCE(org.f_abbr, ''), '/',
        COALESCE(client.f_cname, '')
    ) AS delivery_full_name
FROM veda_specs s
JOIN veda_dogs d ON d.f_id = s.f_dogid
LEFT JOIN veda_clients client ON client.f_id = d.f_contrid
LEFT JOIN veda_clients org ON org.f_id = d.f_orgid
LEFT JOIN veda_spr spec_type ON spec_type.f_type = 33 AND spec_type.f_num = s.f_typez
WHERE (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
  AND (%(dog_id)s IS NULL OR d.f_id = %(dog_id)s)
  AND (%(date_from)s IS NULL OR s.f_dt >= %(date_from)s)
  AND (%(date_to)s IS NULL OR s.f_dt <= %(date_to)s)
  AND (
      COALESCE(s.f_num, '') LIKE %(query_like)s
      OR COALESCE(d.f_dogname, '') LIKE %(query_like)s
      OR COALESCE(client.f_cname, '') LIKE %(query_like)s
      OR CONCAT(
          COALESCE(d.f_dogname, ''), '/',
          COALESCE(s.f_num, ''), '/',
          COALESCE(org.f_abbr, ''), '/',
          COALESCE(client.f_cname, '')
      ) LIKE %(query_like)s
  )
ORDER BY
    CASE WHEN COALESCE(s.f_num, '') = %(query)s THEN 0 ELSE 1 END,
    s.f_dt DESC,
    s.f_id DESC
LIMIT %(limit)s;
"""

DELIVERY_BALANCE_BY_SPEC_ID = """
SELECT
    COALESCE(pay.payment_sum, 0) AS payment_sum,
    COALESCE(sales.reimbursable_sum, 0) AS reimbursable_sum,
    COALESCE(sales.non_reimbursable_sum, 0) AS non_reimbursable_sum,
    COALESCE(pay.payment_sum, 0)
      - COALESCE(sales.reimbursable_sum, 0)
      - COALESCE(sales.non_reimbursable_sum, 0) AS balance
FROM (SELECT %(spec_id)s AS spec_id) selected
LEFT JOIN (
    SELECT
        spec.f_id AS spec_id,
        SUM(COALESCE(get_paidsum(oper.f_id), 0)) AS payment_sum
    FROM veda_spec_invoices oper
    LEFT JOIN veda_categs oper4_specs
        ON oper4_specs.f_objectid = oper.f_id
       AND oper4_specs.f_ctgtype = 24
       AND oper4_specs.f_objecttype = 5
    JOIN veda_specs spec
        ON spec.f_id = CASE oper.f_parenttype
          WHEN 2 THEN oper.f_specid
          WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
          ELSE NULL
        END
    WHERE oper.f_parenttype IN (2, 4)
      AND spec.f_id = %(spec_id)s
    GROUP BY spec.f_id
) pay ON pay.spec_id = selected.spec_id
LEFT JOIN (
    SELECT
        sales_ops.spec_id,
        SUM(CASE
            WHEN sales_ops.reimbursement_id = 1 THEN sales_ops.realiz_sum
            WHEN sales_ops.reimbursement_id NOT IN (1, 2)
             AND sales_ops.buyer_contract_code <> ''
             AND sales_ops.operation_contract_code <> sales_ops.buyer_contract_code
                THEN sales_ops.realiz_sum
            ELSE 0
        END) AS reimbursable_sum,
        SUM(CASE
            WHEN sales_ops.reimbursement_id = 2 THEN sales_ops.realiz_sum
            WHEN sales_ops.reimbursement_id NOT IN (1, 2)
             AND sales_ops.buyer_contract_code <> ''
             AND sales_ops.operation_contract_code = sales_ops.buyer_contract_code
                THEN sales_ops.realiz_sum
            ELSE 0
        END) AS non_reimbursable_sum
    FROM (
        SELECT
            spec.f_id AS spec_id,
            COALESCE(oper.f_isvozm, 0) AS reimbursement_id,
            COALESCE(get_realizsum(oper.f_id), 0) AS realiz_sum,
            COALESCE(spec.f_kod1cb, '') AS buyer_contract_code,
            COALESCE(NULLIF(dog.f_kod1c, ''), NULLIF(spec.f_kod1cp, ''), NULLIF(spec.f_kod1cb, ''), '') AS operation_contract_code
        FROM veda_spec_invoices oper
        LEFT JOIN veda_categs oper4_specs
            ON oper4_specs.f_objectid = oper.f_id
           AND oper4_specs.f_ctgtype = 24
           AND oper4_specs.f_objecttype = 5
        JOIN veda_specs spec
            ON spec.f_id = CASE oper.f_parenttype
              WHEN 2 THEN oper.f_specid
              WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
              ELSE NULL
            END
        LEFT JOIN (
            SELECT f_operid, MIN(f_dogid) AS f_dogid
            FROM veda_akts
            GROUP BY f_operid
        ) akt ON akt.f_operid = oper.f_id
        LEFT JOIN veda_dogs dog ON dog.f_id = akt.f_dogid
        WHERE oper.f_parenttype IN (2, 4)
          AND spec.f_id = %(spec_id)s
    ) sales_ops
    GROUP BY sales_ops.spec_id
) sales ON sales.spec_id = selected.spec_id;
"""

SEARCH_CLIENTS = """
SELECT DISTINCT
    COALESCE(client.f_id, 0) AS client_id,
    COALESCE(client.f_cname, '') AS client_name,
    COALESCE(client.f_inn, '') AS client_inn
FROM veda_clients client
WHERE CHAR_LENGTH(%(query)s) >= 3
  AND (
    LOWER(COALESCE(client.f_cname, '')) LIKE LOWER(%(query_like)s)
    OR COALESCE(client.f_inn, '') LIKE %(query_like)s
    OR CAST(client.f_id AS CHAR) LIKE %(query_like)s
  )
ORDER BY client.f_cname
LIMIT %(limit)s;
"""

SEARCH_CONTRACTS = """
SELECT DISTINCT
    COALESCE(d.f_id, 0) AS dog_id,
    COALESCE(d.f_dogname, '') AS contract_number,
    COALESCE(d.f_kod1c, '') AS contract_code1c,
    COALESCE(client.f_id, 0) AS client_id,
    COALESCE(client.f_cname, '') AS client_name,
    COALESCE(client.f_inn, '') AS client_inn
FROM veda_dogs d
LEFT JOIN veda_clients client ON client.f_id = d.f_contrid
WHERE CHAR_LENGTH(%(query)s) >= 2
  AND (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
  AND (
    LOWER(COALESCE(d.f_dogname, '')) LIKE LOWER(%(query_like)s)
    OR COALESCE(d.f_kod1c, '') LIKE %(query_like)s
    OR CAST(d.f_id AS CHAR) LIKE %(query_like)s
  )
ORDER BY d.f_dogname
LIMIT %(limit)s;
"""

DELIVERY_CONTRACT_CODES = """
SELECT
    s.f_id AS spec_id,
    s.f_num AS spec_number,
    s.f_dt AS expected_1c_contract_date,
    s.f_kod1cb AS buyer_contract_code,
    s.f_kod1cp AS committent_contract_code
FROM veda_specs s
WHERE s.f_id = %(spec_id)s
LIMIT 1;
"""

DELIVERY_CUSTOMER_INVOICES = """
SELECT DISTINCT
    %(spec_id)s AS spec_id,
    'customer_invoice' AS document_kind,
    COALESCE(schet.f_kod1c, '') AS code1c,
    COALESCE(schet.f_num, '') AS document_number,
    schet.f_dt AS document_date,
    COALESCE(schet.f_sum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    CASE
        WHEN COALESCE(schet.f_vozm, 0) = 1 THEN COALESCE(NULLIF(spec.f_kod1cp, ''), spec.f_kod1cb, '')
        ELSE COALESCE(spec.f_kod1cb, '')
    END AS contract_code1c,
    COALESCE(schet.f_id, 0) AS source_id,
    COALESCE(schet.f_operid, 0) AS operation_id,
    COALESCE(nds.f_name, '') AS vat_rate,
    '' AS reimbursement_type,
    CASE WHEN schet.f_status = 9 THEN 1 ELSE 0 END AS deleted,
    NULL AS paid_amount
FROM veda_schets schet
JOIN veda_specs spec ON spec.f_id = %(spec_id)s
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = schet.f_val
LEFT JOIN veda_spr nds ON nds.f_type = 10 AND nds.f_num = schet.f_nds
WHERE schet.f_dogtype = 2
  AND schet.f_dogid = %(spec_id)s
  AND COALESCE(schet.f_type, 0) = 1
  AND COALESCE(schet.f_maininv, 0) = 0;
"""

DELIVERY_CUSTOMER_INVOICES_BY_SPEC_IDS = """
SELECT DISTINCT
    spec.f_id AS spec_id,
    'customer_invoice' AS document_kind,
    COALESCE(schet.f_kod1c, '') AS code1c,
    COALESCE(schet.f_num, '') AS document_number,
    schet.f_dt AS document_date,
    COALESCE(schet.f_sum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    CASE
        WHEN COALESCE(schet.f_vozm, 0) = 1 THEN COALESCE(NULLIF(spec.f_kod1cp, ''), spec.f_kod1cb, '')
        ELSE COALESCE(spec.f_kod1cb, '')
    END AS contract_code1c,
    COALESCE(schet.f_id, 0) AS source_id,
    COALESCE(schet.f_operid, 0) AS operation_id,
    COALESCE(nds.f_name, '') AS vat_rate,
    '' AS reimbursement_type,
    CASE WHEN schet.f_status = 9 THEN 1 ELSE 0 END AS deleted,
    NULL AS paid_amount
FROM veda_schets schet
JOIN veda_specs spec ON spec.f_id = schet.f_dogid
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = schet.f_val
LEFT JOIN veda_spr nds ON nds.f_type = 10 AND nds.f_num = schet.f_nds
WHERE schet.f_dogtype = 2
  AND COALESCE(schet.f_type, 0) = 1
  AND COALESCE(schet.f_maininv, 0) = 0
  AND spec.f_id IN ({spec_id_filter});
"""

DELIVERY_OPERATION_DOCUMENTS = """
SELECT
    %(spec_id)s AS spec_id,
    'sale' AS document_kind,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(akt.f_kod1c, '') ORDER BY akt.f_kod1c SEPARATOR ', '), '') AS code1c,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(akt.f_num, '') ORDER BY akt.f_num SEPARATOR ', '), '') AS document_number,
    MAX(CASE WHEN akt.f_dt1c IS NOT NULL AND akt.f_dt1c <> '0000-00-00' THEN akt.f_dt1c ELSE akt.f_dt END) AS document_date,
    COALESCE(get_realizsum(oper.f_id), 0) AS amount_total,
    COALESCE(NULLIF(MAX(val.f_dopprstr), ''), NULLIF(MAX(val.f_uslstr), ''), NULLIF(MAX(val.f_namedop), ''), 'RUB') AS currency,
    CASE
        WHEN COALESCE(oper.f_isvozm, 0) = 2 THEN COALESCE(spec.f_kod1cb, '')
        ELSE COALESCE(NULLIF(MAX(dog.f_kod1c), ''), NULLIF(spec.f_kod1cp, ''), NULLIF(spec.f_kod1cb, ''), '')
    END AS contract_code1c,
    COALESCE(MIN(akt.f_id), 0) AS source_id,
    COALESCE(oper.f_id, 0) AS operation_id,
    COALESCE(nds.f_name, '') AS vat_rate,
    CASE
        WHEN COALESCE(oper.f_isvozm, 0) = 1 THEN 'reimbursable'
        WHEN COALESCE(oper.f_isvozm, 0) = 2 THEN 'non_reimbursable'
        ELSE 'unknown'
    END AS reimbursement_type,
    MAX(CASE WHEN akt.f_status = 9 THEN 1 ELSE 0 END) AS deleted,
    NULL AS paid_amount
FROM veda_spec_invoices oper
JOIN veda_specs spec ON spec.f_id = %(spec_id)s
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
LEFT JOIN veda_akts akt ON akt.f_operid = oper.f_id
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = akt.f_val
LEFT JOIN veda_spr nds ON nds.f_type = 10 AND nds.f_num = oper.f_nds
LEFT JOIN veda_dogs dog ON dog.f_id = akt.f_dogid
WHERE oper.f_parenttype IN (2, 4)
  AND (
    CASE oper.f_parenttype
      WHEN 2 THEN oper.f_specid
      WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
      ELSE NULL
    END
  ) = %(spec_id)s
GROUP BY oper.f_id, spec.f_id, spec.f_kod1cb, spec.f_kod1cp

UNION

SELECT
    %(spec_id)s AS spec_id,
    'payment' AS document_kind,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(h.f_kod1C, '') ORDER BY h.f_kod1C SEPARATOR ', '), '') AS code1c,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(CAST(h.f_ppnum AS CHAR), '') ORDER BY h.f_ppnum SEPARATOR ', '), '') AS document_number,
    MAX(CASE
        WHEN h.f_dt1C IS NOT NULL AND h.f_dt1C <> '0000-00-00 00:00:00' THEN h.f_dt1C
        ELSE h.f_ppdt
    END) AS document_date,
    COALESCE(get_paidsum(oper.f_id), 0) AS amount_total,
    COALESCE(NULLIF(MAX(val.f_dopprstr), ''), NULLIF(MAX(val.f_uslstr), ''), NULLIF(MAX(val.f_namedop), ''), 'RUB') AS currency,
    COALESCE(spec.f_kod1cb, '') AS contract_code1c,
    COALESCE(MIN(h.f_id), 0) AS source_id,
    COALESCE(oper.f_id, 0) AS operation_id,
    '' AS vat_rate,
    '' AS reimbursement_type,
    0 AS deleted,
    NULL AS paid_amount
FROM veda_spec_invoices oper
JOIN veda_specs spec ON spec.f_id = %(spec_id)s
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
LEFT JOIN veda_acchist_docs d
    ON d.f_docid = oper.f_id
   AND d.f_doctype = 3
LEFT JOIN veda_acchist h ON h.f_id = d.f_acchistid
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = h.f_val
WHERE oper.f_parenttype IN (2, 4)
  AND (
    CASE oper.f_parenttype
      WHEN 2 THEN oper.f_specid
      WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
      ELSE NULL
    END
  ) = %(spec_id)s
  AND COALESCE(get_paidsum(oper.f_id), 0) <> 0
GROUP BY oper.f_id, spec.f_id, spec.f_kod1cb;
"""

DELIVERY_OPERATION_DOCUMENTS_BY_SPEC_IDS = """
SELECT
    spec.f_id AS spec_id,
    'sale' AS document_kind,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(akt.f_kod1c, '') ORDER BY akt.f_kod1c SEPARATOR ', '), '') AS code1c,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(akt.f_num, '') ORDER BY akt.f_num SEPARATOR ', '), '') AS document_number,
    MAX(CASE WHEN akt.f_dt1c IS NOT NULL AND akt.f_dt1c <> '0000-00-00' THEN akt.f_dt1c ELSE akt.f_dt END) AS document_date,
    COALESCE(get_realizsum(oper.f_id), 0) AS amount_total,
    COALESCE(NULLIF(MAX(val.f_dopprstr), ''), NULLIF(MAX(val.f_uslstr), ''), NULLIF(MAX(val.f_namedop), ''), 'RUB') AS currency,
    CASE
        WHEN COALESCE(oper.f_isvozm, 0) = 2 THEN COALESCE(spec.f_kod1cb, '')
        ELSE COALESCE(NULLIF(MAX(dog.f_kod1c), ''), NULLIF(spec.f_kod1cp, ''), NULLIF(spec.f_kod1cb, ''), '')
    END AS contract_code1c,
    COALESCE(MIN(akt.f_id), 0) AS source_id,
    COALESCE(oper.f_id, 0) AS operation_id,
    COALESCE(nds.f_name, '') AS vat_rate,
    CASE
        WHEN COALESCE(oper.f_isvozm, 0) = 1 THEN 'reimbursable'
        WHEN COALESCE(oper.f_isvozm, 0) = 2 THEN 'non_reimbursable'
        ELSE 'unknown'
    END AS reimbursement_type,
    MAX(CASE WHEN akt.f_status = 9 THEN 1 ELSE 0 END) AS deleted,
    NULL AS paid_amount
FROM veda_spec_invoices oper
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
JOIN veda_specs spec
    ON spec.f_id = CASE oper.f_parenttype
      WHEN 2 THEN oper.f_specid
      WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
      ELSE NULL
    END
LEFT JOIN veda_akts akt ON akt.f_operid = oper.f_id
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = akt.f_val
LEFT JOIN veda_spr nds ON nds.f_type = 10 AND nds.f_num = oper.f_nds
LEFT JOIN veda_dogs dog ON dog.f_id = akt.f_dogid
WHERE oper.f_parenttype IN (2, 4)
  AND spec.f_id IN ({spec_id_filter})
GROUP BY spec.f_id, oper.f_id, spec.f_kod1cb, spec.f_kod1cp

UNION

SELECT
    spec.f_id AS spec_id,
    'payment' AS document_kind,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(h.f_kod1C, '') ORDER BY h.f_kod1C SEPARATOR ', '), '') AS code1c,
    COALESCE(GROUP_CONCAT(DISTINCT NULLIF(CAST(h.f_ppnum AS CHAR), '') ORDER BY h.f_ppnum SEPARATOR ', '), '') AS document_number,
    MAX(CASE
        WHEN h.f_dt1C IS NOT NULL AND h.f_dt1C <> '0000-00-00 00:00:00' THEN h.f_dt1C
        ELSE h.f_ppdt
    END) AS document_date,
    COALESCE(get_paidsum(oper.f_id), 0) AS amount_total,
    COALESCE(NULLIF(MAX(val.f_dopprstr), ''), NULLIF(MAX(val.f_uslstr), ''), NULLIF(MAX(val.f_namedop), ''), 'RUB') AS currency,
    COALESCE(spec.f_kod1cb, '') AS contract_code1c,
    COALESCE(MIN(h.f_id), 0) AS source_id,
    COALESCE(oper.f_id, 0) AS operation_id,
    '' AS vat_rate,
    '' AS reimbursement_type,
    0 AS deleted,
    NULL AS paid_amount
FROM veda_spec_invoices oper
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
JOIN veda_specs spec
    ON spec.f_id = CASE oper.f_parenttype
      WHEN 2 THEN oper.f_specid
      WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
      ELSE NULL
    END
LEFT JOIN veda_acchist_docs d
    ON d.f_docid = oper.f_id
   AND d.f_doctype = 3
LEFT JOIN veda_acchist h ON h.f_id = d.f_acchistid
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = h.f_val
WHERE oper.f_parenttype IN (2, 4)
  AND spec.f_id IN ({spec_id_filter})
  AND COALESCE(get_paidsum(oper.f_id), 0) <> 0
GROUP BY spec.f_id, oper.f_id, spec.f_kod1cb;
"""

DELIVERY_OPERATIONS_BASE_BY_SPEC_IDS = """
SELECT
    spec.f_id AS spec_id,
    oper.f_id AS operation_id,
    COALESCE(oper.f_isvozm, 0) AS reimbursement_id,
    COALESCE(spec.f_kod1cb, '') AS buyer_contract_code,
    COALESCE(spec.f_kod1cp, '') AS committent_contract_code,
    COALESCE(nds.f_name, '') AS vat_rate
FROM veda_spec_invoices oper
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
JOIN veda_specs spec
    ON spec.f_id = CASE oper.f_parenttype
      WHEN 2 THEN oper.f_specid
      WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
      ELSE NULL
    END
LEFT JOIN veda_spr nds ON nds.f_type = 10 AND nds.f_num = oper.f_nds
WHERE oper.f_parenttype IN (2, 4)
  AND spec.f_id IN ({spec_id_filter});
"""

OPERATION_AMOUNTS_BY_OPERATION_IDS = """
SELECT
    oper.f_id AS operation_id,
    COALESCE(get_paidsum(oper.f_id), 0) AS payment_sum,
    COALESCE(get_realizsum(oper.f_id), 0) AS sale_sum
FROM veda_spec_invoices oper
WHERE oper.f_id IN ({operation_id_filter});
"""

OPERATION_CUSTOMER_INVOICE_LINKS_BY_OPERATION_IDS = """
SELECT DISTINCT schet.f_operid AS operation_id
FROM veda_schets schet
WHERE schet.f_operid IN ({operation_id_filter})
  AND schet.f_type = 1
  AND schet.f_status <> 9

UNION

SELECT DISTINCT details_opers.f_operid AS operation_id
FROM veda_schets_details_opers details_opers
JOIN veda_schets_details details ON details.f_id = details_opers.f_schets_detailsid
JOIN veda_schets schet ON schet.f_id = details.f_schetid
WHERE details_opers.f_operid IN ({operation_id_filter})
  AND schet.f_type = 1
  AND schet.f_status <> 9;
"""

OPERATION_CLOSING_DOCS_BY_OPERATION_IDS = """
SELECT
    akt.f_operid AS operation_id,
    CASE
        WHEN COALESCE(akt.f_type, 0) = 7 THEN 'purchase'
        ELSE 'sale'
    END AS document_kind,
    COALESCE(
        NULLIF(akt.f_kod1c, ''),
        NULLIF(main_akt.f_kod1c, ''),
        CASE
            WHEN main_akt.f_dt1c IS NOT NULL AND main_akt.f_dt1c <> '0000-00-00'
                THEN NULLIF(main_akt.f_num, '')
            ELSE NULL
        END,
        ''
    ) AS code1c,
    COALESCE(NULLIF(main_akt.f_num, ''), NULLIF(akt.f_num, ''), '') AS document_number,
    CASE
        WHEN main_akt.f_dt1c IS NOT NULL AND main_akt.f_dt1c <> '0000-00-00' THEN main_akt.f_dt1c
        WHEN akt.f_dt1c IS NOT NULL AND akt.f_dt1c <> '0000-00-00' THEN akt.f_dt1c
        ELSE COALESCE(main_akt.f_dt, akt.f_dt)
    END AS document_date,
    COALESCE(akt.f_sum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    COALESCE(akt.f_id, 0) AS source_id,
    COALESCE(NULLIF(akt.f_num, ''), '') AS source_number,
    COALESCE(NULLIF(dog.f_kod1c, ''), '') AS dog_code1c,
    CASE WHEN akt.f_status = 9 OR main_akt.f_status = 9 THEN 1 ELSE 0 END AS deleted
FROM veda_akts akt
LEFT JOIN veda_akts main_akt ON main_akt.f_id = NULLIF(akt.f_mainakt, 0)
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = akt.f_val
LEFT JOIN veda_dogs dog ON dog.f_id = akt.f_dogid
WHERE akt.f_operid IN ({operation_id_filter})
  AND COALESCE(akt.f_operid, 0) <> 0

UNION ALL

SELECT
    details_opers.f_operid AS operation_id,
    CASE
        WHEN COALESCE(akt.f_type, 0) = 7 THEN 'purchase'
        ELSE 'sale'
    END AS document_kind,
    COALESCE(
        NULLIF(akt.f_kod1c, ''),
        NULLIF(main_akt.f_kod1c, ''),
        CASE
            WHEN main_akt.f_dt1c IS NOT NULL AND main_akt.f_dt1c <> '0000-00-00'
                THEN NULLIF(main_akt.f_num, '')
            ELSE NULL
        END,
        ''
    ) AS code1c,
    COALESCE(NULLIF(main_akt.f_num, ''), NULLIF(akt.f_num, ''), '') AS document_number,
    CASE
        WHEN main_akt.f_dt1c IS NOT NULL AND main_akt.f_dt1c <> '0000-00-00' THEN main_akt.f_dt1c
        WHEN akt.f_dt1c IS NOT NULL AND akt.f_dt1c <> '0000-00-00' THEN akt.f_dt1c
        ELSE COALESCE(main_akt.f_dt, akt.f_dt)
    END AS document_date,
    COALESCE(details_opers.f_sum, akt.f_sum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    COALESCE(akt.f_id, 0) AS source_id,
    COALESCE(NULLIF(akt.f_num, ''), '') AS source_number,
    COALESCE(NULLIF(dog.f_kod1c, ''), '') AS dog_code1c,
    CASE WHEN akt.f_status = 9 OR main_akt.f_status = 9 THEN 1 ELSE 0 END AS deleted
FROM veda_akts_details_opers details_opers
JOIN veda_akts_details details ON details.f_id = details_opers.f_akts_detailsid
JOIN veda_akts akt ON akt.f_id = details.f_aktid
LEFT JOIN veda_akts main_akt ON main_akt.f_id = NULLIF(akt.f_mainakt, 0)
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = akt.f_val
LEFT JOIN veda_dogs dog ON dog.f_id = akt.f_dogid
WHERE details_opers.f_operid IN ({operation_id_filter})
  AND COALESCE(akt.f_operid, 0) <> details_opers.f_operid
ORDER BY operation_id, document_date, source_id;
"""

OPERATION_PAYMENT_DOCS_BY_OPERATION_IDS = """
SELECT
    d.f_docid AS operation_id,
    COALESCE(NULLIF(h.f_kod1C, ''), '') AS code1c,
    COALESCE(NULLIF(CAST(h.f_ppnum AS CHAR), ''), '') AS document_number,
    CASE
        WHEN h.f_dt1C IS NOT NULL AND h.f_dt1C <> '0000-00-00 00:00:00' THEN h.f_dt1C
        ELSE h.f_ppdt
    END AS document_date,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    COALESCE(h.f_id, 0) AS source_id,
    COALESCE(SUM(d.f_clssum), 0) AS allocated_amount
FROM veda_acchist_docs d
JOIN veda_acchist h ON h.f_id = d.f_acchistid
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = h.f_val
WHERE d.f_doctype = 3
  AND d.f_docid IN ({operation_id_filter})
GROUP BY
    d.f_docid,
    h.f_id,
    h.f_kod1C,
    h.f_ppnum,
    h.f_dt1C,
    h.f_ppdt,
    val.f_dopprstr,
    val.f_uslstr,
    val.f_namedop
ORDER BY d.f_docid, document_date, h.f_id;
"""

GLOBAL_PAYMENT_DOCUMENT_EXISTS = """
SELECT 1
FROM veda_acchist payment
WHERE payment.f_kod1C = %(code1c)s
  AND payment.f_ppdt = %(document_date)s
LIMIT 1;
"""

GLOBAL_CUSTOMER_INVOICE_EXISTS = """
SELECT 1
FROM veda_schets invoice
WHERE invoice.f_kod1c = %(code1c)s
  AND invoice.f_dt = %(document_date)s
  AND invoice.f_status <> 9
LIMIT 1;
"""

GLOBAL_CLOSING_DOCUMENT_EXISTS = """
SELECT 1
FROM veda_akts document
LEFT JOIN veda_akts parent ON parent.f_id = NULLIF(document.f_mainakt, 0)
WHERE COALESCE(NULLIF(document.f_kod1c, ''), NULLIF(parent.f_kod1c, ''), '') = %(code1c)s
  AND CASE
        WHEN document.f_dt1c IS NOT NULL AND document.f_dt1c <> '0000-00-00' THEN document.f_dt1c
        WHEN parent.f_dt1c IS NOT NULL AND parent.f_dt1c <> '0000-00-00' THEN parent.f_dt1c
        ELSE COALESCE(parent.f_dt, document.f_dt)
      END = %(document_date)s
  AND document.f_status <> 9
  AND (%(document_kind)s = 'purchase' AND document.f_type = 7
       OR %(document_kind)s = 'sale' AND COALESCE(document.f_type, 0) <> 7)
LIMIT 1;
"""

DELIVERY_CODE_COVERAGE_AUDIT = """
SELECT
    COUNT(*) AS specs_total,
    SUM(CASE WHEN COALESCE(NULLIF(TRIM(f_kod1cb), ''), '') NOT IN ('', '_', '-', '0') THEN 1 ELSE 0 END) AS with_buyer_code,
    SUM(CASE WHEN COALESCE(NULLIF(TRIM(f_kod1cp), ''), '') NOT IN ('', '_', '-', '0') THEN 1 ELSE 0 END) AS with_committent_code
FROM veda_specs
WHERE f_dt BETWEEN %(date_from)s AND %(date_to)s;
"""

USER_BY_LOGIN = """
SELECT
    u.f_id AS user_id,
    COALESCE(u.f_login, '') AS login,
    COALESCE(u.f_password, '') AS password,
    COALESCE(u.f_authtype, 0) AS auth_type,
    COALESCE(u.f_name1, '') AS first_name,
    COALESCE(u.f_name2, '') AS last_name,
    COALESCE(u.f_alpsort, '') AS display_sort,
    COALESCE(u.f_persmenu, '') AS personal_menu,
    COALESCE(u.f_struct_code, '') AS structure_code
FROM veda_users u
WHERE u.f_login = %(login)s
  AND COALESCE(u.f_isactived, 0) = 1
LIMIT 1;
"""
