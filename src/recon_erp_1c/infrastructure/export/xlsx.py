from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


def reconciliation_run_xlsx(run: dict[str, Any]) -> bytes:
    issues = run.get("issues") if isinstance(run.get("issues"), list) else []
    delivery = run.get("delivery") if isinstance(run.get("delivery"), dict) else {}
    summary = run.get("summary") if isinstance(run.get("summary"), dict) else {}
    rows = [
        [
            "Статус",
            "Сообщение",
            "Поля",
            "ERP тип",
            "ERP код 1С",
            "ERP номер",
            "ERP дата",
            "ERP сумма",
            "ERP валюта",
            "1С тип",
            "1С код",
            "1С номер",
            "1С дата",
            "1С сумма",
            "1С валюта",
        ]
    ]
    for issue in issues:
        erp = issue.get("erp_document") or {}
        onec = issue.get("onec_document") or {}
        rows.append(
            [
                issue.get("status") or "",
                issue.get("message") or "",
                ", ".join(issue.get("fields") or []),
                erp.get("kind") or "",
                erp.get("code1c") or "",
                erp.get("number") or "",
                erp.get("date") or "",
                _money_amount(erp),
                _money_currency(erp),
                onec.get("kind") or "",
                onec.get("code1c") or "",
                onec.get("number") or "",
                onec.get("date") or "",
                _money_amount(onec),
                _money_currency(onec),
            ]
        )

    params = [
        ["Параметр", "Значение"],
        ["Run ID", run.get("run_id") or ""],
        ["Дата запуска", run.get("created_at") or ""],
        ["Поставка ERP", delivery.get("erp_spec_id") or ""],
        ["Номер поставки", delivery.get("spec_number") or ""],
        ["Базовый договор", delivery.get("base_contract_number") or ""],
        ["Код договора покупателя 1С", ((delivery.get("contract_codes") or {}).get("buyer_contract_code") or "")],
        ["Код договора комитента 1С", ((delivery.get("contract_codes") or {}).get("committent_contract_code") or "")],
        ["Всего расхождений", summary.get("issues_total") or 0],
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Сверка"
    _append_rows(ws, rows)
    _style_simple_sheet(ws)

    params_ws = wb.create_sheet("Параметры")
    _append_rows(params_ws, params)
    _style_simple_sheet(params_ws)

    return _save_workbook(wb)


def reconciliation_matrix_xlsx(matrix: dict[str, Any]) -> bytes:
    items = matrix.get("items") if isinstance(matrix.get("items"), list) else []
    summary = matrix.get("summary") if isinstance(matrix.get("summary"), dict) else {}
    rows = [
        [
            "№ спецификации",
            "",
            "Счет",
            "Сумма по счету",
            "Сумма оплаты",
            "",
            "Возмещаемые расходы",
            "Невозмещаемые расходы",
            "",
            "№ счф",
            "(+/-)",
        ]
    ]
    merges: list[str] = []
    balances_by_row: dict[int, Decimal] = {}

    current_row = 2
    for item in items:
        invoice_rows = _invoice_rows(item)
        start_row = current_row
        balance = _to_decimal(item.get("balance"))
        for idx, invoice in enumerate(invoice_rows):
            rows.append(
                [
                    _spec_label(item) if idx == 0 else "",
                    "",
                    invoice.get("number") or "—",
                    _to_decimal(invoice.get("amount")) if invoice.get("amount") not in (None, "") else "",
                    _to_decimal(item.get("payment_sum")) if idx == 0 else "",
                    "",
                    _to_decimal(item.get("reimbursable_sum")) if idx == 0 else "",
                    _to_decimal(item.get("non_reimbursable_sum")) if idx == 0 else "",
                    "",
                    "\n".join(item.get("sf_numbers") or []) if idx == 0 else "",
                    _to_decimal(item.get("balance")) if idx == 0 else "",
                ]
            )
            balances_by_row[current_row] = balance
            current_row += 1
        end_row = current_row - 1
        if end_row > start_row:
            for col_idx in [1, 5, 7, 8, 10, 11]:
                col = _col(col_idx)
                merges.append(f"{col}{start_row}:{col}{end_row}")

    totals = summary if summary else _matrix_totals(items)
    total_row = current_row + 1
    rows.append([""] * 11)
    rows.append(
        [
            "ИТОГО",
            "",
            "",
            _to_decimal(totals.get("invoice_sum")),
            _to_decimal(totals.get("payment_sum")),
            "",
            _to_decimal(totals.get("reimbursable_sum")),
            _to_decimal(totals.get("non_reimbursable_sum")),
            "",
            "",
            _to_decimal(totals.get("balance")),
        ]
    )

    rules = [
        ["Поле", "Источник", "Правило"],
        [
            "№ спецификации",
            "ERP veda_specs + veda_spr(f_type=33/130)",
            "Тип и номер поставки из исходных таблиц ERP; view_specinv/view_specs не использовать.",
        ],
        [
            "Счет",
            "ERP veda_schets, f_type=1",
            "Только счета покупателю; по каждому счету отдельная строка. Если backend не передал invoice_rows, номер берется из invoice_numbers, а агрегатная сумма ставится в первую строку блока.",
        ],
        ["Сумма по счету", "ERP veda_schets.f_sum", "Сумма конкретного счета покупателю."],
        ["Сумма оплаты", "ERP get_paidsum / veda_acchist_docs.f_clssum", "Сумма оплат клиента по поставке; объединяется по строкам счетов."],
        ["Возмещаемые расходы", "ERP get_realizsum по операциям f_isvozm=1", "Итог по поставке; объединяется по строкам счетов."],
        ["Невозмещаемые расходы", "ERP get_realizsum по операциям f_isvozm=2", "Итог по поставке; объединяется по строкам счетов."],
        ["№ счф", "ERP/1С закрывающие документы", "Каждый номер документа внутри объединенной ячейки с переносом строки."],
        ["(+/-)", "Сумма оплаты - возмещаемые - невозмещаемые", "Сальдо взаиморасчетов по поставке."],
        ["Дата формирования", "Сервис сверки", datetime.now().isoformat(timespec="seconds")],
        ["Режим", "Сервис сверки", matrix.get("mode") or ""],
    ]

    wb = Workbook()
    ws = wb.active
    ws.title = "Выгрузка"
    _append_rows(ws, rows)
    _style_matrix_sheet(ws, merges, balances_by_row, total_row)

    rules_ws = wb.create_sheet("Правила")
    _append_rows(rules_ws, rules)
    _style_rules_sheet(rules_ws)

    return _save_workbook(wb)


def _save_workbook(wb: Workbook) -> bytes:
    with BytesIO() as buffer:
        wb.save(buffer)
        return buffer.getvalue()


def _append_rows(ws: Worksheet, rows: list[list[Any]]) -> None:
    for row in rows:
        ws.append([_cell_value(value) for value in row])


def _cell_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _style_matrix_sheet(ws: Worksheet, merges: list[str], balances_by_row: dict[int, Decimal], total_row: int) -> None:
    widths = {1: 24, 2: 3, 3: 18, 4: 18, 5: 18, 6: 3, 7: 20, 8: 22, 9: 3, 10: 48, 11: 18}
    for col_idx, width in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:K{ws.max_row}"
    ws.sheet_view.showGridLines = False

    header_fill = PatternFill("solid", fgColor="D9D7D2")
    spec_fill = PatternFill("solid", fgColor="F3F1ED")
    invoice_fill = PatternFill("solid", fgColor="EEF6FF")
    payment_fill = PatternFill("solid", fgColor="EEF8F0")
    expense_fill = PatternFill("solid", fgColor="FFF5DF")
    sf_fill = PatternFill("solid", fgColor="F7F4EF")
    positive_fill = PatternFill("solid", fgColor="E2F0D9")
    negative_fill = PatternFill("solid", fgColor="FCE4D6")
    muted_fill = PatternFill("solid", fgColor="FAF9F6")
    border = _thin_border()

    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    money_cols = {4, 5, 7, 8, 11}
    for row_idx in range(2, ws.max_row + 1):
        if row_idx == total_row:
            fills = {4: header_fill, 5: header_fill, 7: header_fill, 8: header_fill, 11: header_fill}
            for col_idx in range(1, 12):
                cell = ws.cell(row_idx, col_idx)
                cell.font = Font(bold=True)
                cell.fill = fills.get(col_idx, header_fill)
                cell.border = border
                cell.alignment = Alignment(
                    horizontal="right" if col_idx in money_cols else "left", vertical="center", wrap_text=True
                )
                if col_idx in money_cols:
                    cell.number_format = _money_format()
            continue

        balance = balances_by_row.get(row_idx, Decimal("0"))
        for col_idx in range(1, 12):
            cell = ws.cell(row_idx, col_idx)
            cell.border = border
            cell.alignment = Alignment(
                horizontal="right" if col_idx in money_cols else "left", vertical="center", wrap_text=True
            )
            if col_idx == 1:
                cell.font = Font(bold=True if cell.value else False)
                cell.fill = spec_fill
            elif col_idx in {2, 6, 9}:
                cell.fill = muted_fill
            elif col_idx in {3, 4}:
                cell.fill = invoice_fill
            elif col_idx == 5:
                cell.fill = payment_fill
            elif col_idx in {7, 8}:
                cell.fill = expense_fill
            elif col_idx == 10:
                cell.fill = sf_fill
            elif col_idx == 11:
                cell.fill = positive_fill if balance >= 0 else negative_fill
                cell.font = Font(color="9C0006" if balance < 0 else "006100")
            if col_idx in money_cols:
                cell.number_format = _money_format()

    for ref in merges:
        ws.merge_cells(ref)

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        ws.row_dimensions[row[0].row].height = 28


def _style_rules_sheet(ws: Worksheet) -> None:
    widths = {1: 24, 2: 38, 3: 92}
    for col_idx, width in widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    _style_simple_sheet(ws)


def _style_simple_sheet(ws: Worksheet) -> None:
    ws.sheet_view.showGridLines = False
    border = _thin_border()
    header_fill = PatternFill("solid", fgColor="D9D7D2")
    for row in ws.iter_rows():
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if cell.row == 1:
                cell.font = Font(bold=True)
                cell.fill = header_fill
    for col_idx in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(18, col_idx * 8), 42)


def _thin_border() -> Border:
    side = Side(style="thin", color="D6D3CD")
    return Border(left=side, right=side, top=side, bottom=side)


def _money_format() -> str:
    return '#,##0.00" р.";[Red]-#,##0.00" р.";0.00" р."'


def _matrix_totals(items: list[dict[str, Any]]) -> dict[str, str]:
    fields = ["invoice_sum", "payment_sum", "reimbursable_sum", "non_reimbursable_sum", "balance"]
    return {field: str(sum((_to_decimal(item.get(field)) for item in items), _to_decimal("0"))) for field in fields}


def _to_decimal(value: Any):
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def _spec_label(item: dict[str, Any]) -> str:
    spec_type = str(item.get("spec_type_name") or item.get("type_name") or item.get("delivery_type") or "").strip()
    spec_number = item.get("spec_number") or item.get("spec_id") or ""
    if spec_type:
        return f"{spec_type} №{spec_number}"
    return f"Поставка №{spec_number}"


def _invoice_rows(item: dict[str, Any]) -> list[dict[str, Any]]:
    rows = item.get("invoice_rows")
    if isinstance(rows, list) and rows:
        return [row for row in rows if isinstance(row, dict)] or [{"number": "—", "amount": item.get("invoice_sum")}]
    numbers = item.get("invoice_numbers") if isinstance(item.get("invoice_numbers"), list) else []
    if not numbers:
        return [{"number": "—", "amount": item.get("invoice_sum")}]
    return [
        {"number": number, "amount": item.get("invoice_sum") if idx == 0 else ""}
        for idx, number in enumerate(numbers)
    ]


def _style_accounting_row(styles: dict[str, int], row_idx: int, balance: Decimal) -> None:
    row_styles = {
        1: 3,
        2: 11,
        3: 4,
        4: 5,
        5: 6,
        6: 11,
        7: 7,
        8: 7,
        9: 11,
        10: 8,
        11: 9 if balance == 0 else 10,
    }
    for col_idx, style_id in row_styles.items():
        styles[f"{_col(col_idx)}{row_idx}"] = style_id


def _balance_label(value: Any) -> str:
    balance = _to_decimal(value)
    if balance > 0:
        return "Переплата"
    if balance < 0:
        return "Долг"
    return "Закрыто"


def _write_package(zf: ZipFile, sheets: dict[str, Any]) -> None:
    zf.writestr("[Content_Types].xml", _content_types(len(sheets)))
    zf.writestr("_rels/.rels", _root_rels())
    zf.writestr("xl/workbook.xml", _workbook(list(sheets.keys())))
    zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
    zf.writestr("xl/styles.xml", _styles())
    for idx, sheet in enumerate(sheets.values(), start=1):
        if isinstance(sheet, dict):
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _worksheet(sheet.get("rows") or [], sheet))
        else:
            zf.writestr(f"xl/worksheets/sheet{idx}.xml", _worksheet(sheet))


def _worksheet(rows: list[list[Any]], config: dict[str, Any] | None = None) -> str:
    config = config or {}
    styles = config.get("styles") if isinstance(config.get("styles"), dict) else {}
    widths = config.get("widths") if isinstance(config.get("widths"), dict) else {}
    xml_rows = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, value in enumerate(row, start=1):
            ref = f"{_col(c_idx)}{r_idx}"
            style_id = styles.get(ref, 1 if r_idx == 1 else None)
            cells.append(_cell(ref, value, style_id))
        xml_rows.append(f'<row r="{r_idx}">{"".join(cells)}</row>')
    max_col = max((len(row) for row in rows), default=1)
    cols = "".join(
        f'<col min="{idx}" max="{idx}" width="{escape(str(width))}" customWidth="1"/>'
        for idx, width in sorted(widths.items())
    ) or f'<col min="1" max="{max_col}" width="18" customWidth="1"/>'
    freeze = ""
    if config.get("freeze"):
        freeze = f'''<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="{escape(str(config["freeze"]))}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'''
    merges = config.get("merges") if isinstance(config.get("merges"), list) else []
    merge_xml = ""
    if merges:
        merge_xml = f'<mergeCells count="{len(merges)}">' + "".join(f'<mergeCell ref="{escape(str(ref))}"/>' for ref in merges) + "</mergeCells>"
    auto_filter = f'<autoFilter ref="{escape(str(config["auto_filter"]))}"/>' if config.get("auto_filter") else ""
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  {freeze}
  <cols>{cols}</cols>
  <sheetData>{"".join(xml_rows)}</sheetData>
  {merge_xml}
  {auto_filter}
</worksheet>'''


def _cell(ref: str, value: Any, style_id: int | None) -> str:
    style = f' s="{style_id}"' if style_id is not None else ""
    if isinstance(value, int | float | Decimal) and not isinstance(value, bool):
        return f'<c r="{ref}"{style}><v>{value}</v></c>'
    text = escape(str(value or ""))
    return f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>'


def _col(index: int) -> str:
    out = ""
    while index:
        index, rem = divmod(index - 1, 26)
        out = chr(65 + rem) + out
    return out


def _money_amount(document: dict[str, Any]) -> str:
    amount = document.get("amount") if isinstance(document.get("amount"), dict) else {}
    return amount.get("amount") or ""


def _money_currency(document: dict[str, Any]) -> str:
    amount = document.get("amount") if isinstance(document.get("amount"), dict) else {}
    return amount.get("currency") or ""


def _content_types(sheet_count: int) -> str:
    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {overrides}
</Types>'''


def _root_rels() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''


def _workbook(sheet_names: list[str]) -> str:
    sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{idx}" r:id="rId{idx}"/>'
        for idx, name in enumerate(sheet_names, start=1)
    )
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheets}</sheets>
</workbook>'''


def _workbook_rels(sheet_count: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, sheet_count + 1)
    )
    rels += f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>'''


def _styles() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00&quot; р.&quot;;[Red]-#,##0.00&quot; р.&quot;;0.00&quot; р.&quot;"/></numFmts>
  <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>
  <fills count="10">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFD9D7D2"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF3F1ED"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFEEF6FF"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFEEF8F0"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFFF5DF"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF7F4EF"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE2F0D9"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFFCE4D6"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD6D3CD"/></left><right style="thin"><color rgb="FFD6D3CD"/></right><top style="thin"><color rgb="FFD6D3CD"/></top><bottom style="thin"><color rgb="FFD6D3CD"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="13">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="0" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="0" fillId="5" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="0" fillId="6" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="7" borderId="1" xfId="0" applyFill="1" applyBorder="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="0" fillId="8" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="0" fillId="9" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="164" fontId="1" fillId="2" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="right" vertical="center" wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
