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
    COALESCE(s.f_kod1cb, '') AS buyer_contract_code,
    COALESCE(s.f_kod1cp, '') AS committent_contract_code,
    d.f_id AS dog_id,
    COALESCE(d.f_dogname, '') AS base_contract_number,
    COALESCE(client.f_id, 0) AS client_id,
    COALESCE(client.f_cname, '') AS client_name,
    COALESCE(client.f_inn, '') AS client_inn
FROM veda_specs s
JOIN veda_dogs d ON d.f_id = s.f_dogid
LEFT JOIN veda_clients client ON client.f_id = d.f_contrid
LEFT JOIN veda_spr spec_type ON spec_type.f_type = 33 AND spec_type.f_num = s.f_typez
WHERE (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
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
WHERE (%(client_id)s IS NULL OR d.f_contrid = %(client_id)s)
  AND (%(dog_id)s IS NULL OR d.f_id = %(dog_id)s)
  AND (%(date_from)s IS NULL OR s.f_dt >= %(date_from)s)
  AND (%(date_to)s IS NULL OR s.f_dt <= %(date_to)s);
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
    'customer_invoice' AS document_kind,
    COALESCE(schet.f_kod1c, '') AS code1c,
    COALESCE(schet.f_num, '') AS document_number,
    schet.f_dt AS document_date,
    COALESCE(schet.f_sum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    COALESCE(spec.f_kod1cb, '') AS contract_code1c,
    COALESCE(schet.f_id, 0) AS source_id,
    NULL AS operation_id,
    COALESCE(nds.f_name, '') AS vat_rate,
    '' AS reimbursement_type,
    CASE WHEN schet.f_status = 9 THEN 1 ELSE 0 END AS deleted
FROM veda_schets schet
JOIN veda_specs spec ON spec.f_id = %(spec_id)s
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = schet.f_val
LEFT JOIN veda_spr nds ON nds.f_type = 10 AND nds.f_num = schet.f_nds
WHERE schet.f_dogtype = 2
  AND schet.f_dogid = %(spec_id)s
  AND COALESCE(schet.f_type, 0) = 1;
"""

DELIVERY_OPERATION_DOCUMENTS = """
SELECT
    'sale' AS document_kind,
    COALESCE(akt.f_kod1c, '') AS code1c,
    COALESCE(akt.f_num, '') AS document_number,
    CASE
        WHEN akt.f_dt1c IS NOT NULL AND akt.f_dt1c <> '0000-00-00' THEN akt.f_dt1c
        ELSE akt.f_dt
    END AS document_date,
    COALESCE(akt.f_sum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    CASE
        WHEN COALESCE(oper.f_isvozm, 0) = 2 THEN COALESCE(spec.f_kod1cb, '')
        ELSE COALESCE(NULLIF(dog.f_kod1c, ''), NULLIF(spec.f_kod1cp, ''), NULLIF(spec.f_kod1cb, ''), '')
    END AS contract_code1c,
    COALESCE(akt.f_id, 0) AS source_id,
    COALESCE(oper.f_id, 0) AS operation_id,
    COALESCE(nds.f_name, '') AS vat_rate,
    CASE
        WHEN COALESCE(oper.f_isvozm, 0) = 1 THEN 'reimbursable'
        WHEN COALESCE(oper.f_isvozm, 0) = 2 THEN 'non_reimbursable'
        ELSE 'unknown'
    END AS reimbursement_type,
    CASE WHEN akt.f_status = 9 THEN 1 ELSE 0 END AS deleted
FROM veda_spec_invoices oper
JOIN veda_specs spec ON spec.f_id = %(spec_id)s
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
JOIN veda_akts akt ON akt.f_operid = oper.f_id
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

UNION

SELECT
    'payment' AS document_kind,
    COALESCE(h.f_kod1C, '') AS code1c,
    COALESCE(h.f_ppnum, '') AS document_number,
    CASE
        WHEN h.f_dt1C IS NOT NULL AND h.f_dt1C <> '0000-00-00 00:00:00' THEN h.f_dt1C
        ELSE h.f_ppdt
    END AS document_date,
    COALESCE(d.f_clssum, 0) AS amount_total,
    COALESCE(NULLIF(val.f_dopprstr, ''), NULLIF(val.f_uslstr, ''), NULLIF(val.f_namedop, ''), 'RUB') AS currency,
    COALESCE(spec.f_kod1cb, '') AS contract_code1c,
    COALESCE(h.f_id, 0) AS source_id,
    COALESCE(oper.f_id, 0) AS operation_id,
    '' AS vat_rate,
    '' AS reimbursement_type,
    0 AS deleted
FROM veda_acchist_docs d
JOIN veda_acchist h ON h.f_id = d.f_acchistid
JOIN veda_spec_invoices oper ON oper.f_id = d.f_docid
JOIN veda_specs spec ON spec.f_id = %(spec_id)s
LEFT JOIN veda_categs oper4_specs
    ON oper4_specs.f_objectid = oper.f_id
   AND oper4_specs.f_ctgtype = 24
   AND oper4_specs.f_objecttype = 5
LEFT JOIN veda_spr val ON val.f_type = 4 AND val.f_num = h.f_val
WHERE d.f_doctype = 3
  AND oper.f_parenttype IN (2, 4)
  AND (
    CASE oper.f_parenttype
      WHEN 2 THEN oper.f_specid
      WHEN 4 THEN CAST(oper4_specs.f_valstr AS SIGNED)
      ELSE NULL
    END
  ) = %(spec_id)s;
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
