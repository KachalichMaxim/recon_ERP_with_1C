// Mock data for reconciliation prototype

const DELIVERY = {
  id: 'SPEC-2026/04-1187',
  number: 'Спец. 1187/04',
  date: '03.04.2026',
  principal: 'ООО «Восточный Путь»',
  principalInn: '7728123456',
  client: 'АО «Металлторг-Урал»',
  clientInn: '6658987112',
  route: 'Шанхай (CN) → Екатеринбург (RU)',
  container: 'MSKU 7841293',
  incoterms: 'FCA Шанхай',
  currency: 'RUB',
  totalAmount: 4_872_400,
  manager: 'Е. Соколова',
  status: 'Закрывается',
};

// Status keys: match, miss-erp, miss-1c, sum, vat
const DOCS = [
  {
    id: 'r1',
    type: 'act',
    typeLabel: 'Акт',
    opId: 'OP-45821',
    opTitle: 'Морская перевозка · FAK',
    status: 'match',
    erp: { num: 'АКТ-3482', date: '14.03.2026', amount: 2_140_000, kod1c: 'АК-000482-26', vat: 'да' },
    rc:  { num: 'АКТ-3482', date: '14.03.2026', amount: 2_140_000, kod1c: 'АК-000482-26', vat: 'да', doctype: 'Акт' },
  },
  {
    id: 'r2',
    type: 'invoice',
    typeLabel: 'Счёт-фактура',
    opId: 'OP-45821',
    opTitle: 'Морская перевозка · FAK',
    status: 'sum',
    erp: { num: 'СФ-9140', date: '14.03.2026', amount: 428_000, kod1c: 'СФ-000914-26', vat: 'да' },
    rc:  { num: 'СФ-9140', date: '14.03.2026', amount: 428_800, kod1c: 'СФ-000914-26', vat: 'да', doctype: 'Счёт-фактура' },
    diffFields: ['amount'],
    diffNote: 'Разница 800 ₽ — вероятно, банковская комиссия или округление НДС',
  },
  {
    id: 'r3',
    type: 'act',
    typeLabel: 'Акт',
    opId: 'OP-45822',
    opTitle: 'Ж/д доставка · Забайкальск → Екатеринбург',
    status: 'miss-erp',
    erp: null,
    rc:  { num: 'АКТ-3510', date: '21.03.2026', amount: 1_085_000, kod1c: 'АК-000510-26', vat: 'да', doctype: 'Акт' },
    diffNote: 'Документ есть в 1С, но не привязан к операции в ЕРП',
  },
  {
    id: 'r4',
    type: 'bill',
    typeLabel: 'Счёт на оплату',
    opId: 'OP-45822',
    opTitle: 'Ж/д доставка · Забайкальск → Екатеринбург',
    status: 'match',
    erp: { num: 'СЧЁТ-7721', date: '18.03.2026', amount: 1_085_000, kod1c: 'СЧ-007721-26', vat: 'да' },
    rc:  { num: 'СЧЁТ-7721', date: '18.03.2026', amount: 1_085_000, kod1c: 'СЧ-007721-26', vat: 'да', doctype: 'Счёт на оплату' },
  },
  {
    id: 'r5',
    type: 'op',
    typeLabel: 'Операция',
    opId: 'OP-45823',
    opTitle: 'СВХ · Хранение 4 дня',
    status: 'miss-1c',
    erp: { num: 'ОП-10021', date: '25.03.2026', amount: 62_000, kod1c: 'ОП-010021-26', vat: 'да' },
    rc:  null,
    diffNote: 'Проводка создана в ЕРП, но в 1С по коду ОП-010021-26 документ не найден',
  },
  {
    id: 'r6',
    type: 'act',
    typeLabel: 'Акт',
    opId: 'OP-45824',
    opTitle: 'Таможенное оформление · экспортная декларация',
    status: 'vat',
    erp: { num: 'АКТ-3560', date: '27.03.2026', amount: 184_500, kod1c: 'АК-000560-26', vat: 'нет' },
    rc:  { num: 'АКТ-3560', date: '27.03.2026', amount: 184_500, kod1c: 'АК-000560-26', vat: 'да', doctype: 'Акт' },
    diffFields: ['vat'],
    diffNote: 'В ЕРП услуга помечена как без НДС, в 1С — с НДС. Проверить возмещаемость',
  },
  {
    id: 'r7',
    type: 'invoice',
    typeLabel: 'Счёт-фактура',
    opId: 'OP-45824',
    opTitle: 'Таможенное оформление · экспортная декларация',
    status: 'match',
    erp: { num: 'СФ-9188', date: '27.03.2026', amount: 36_900, kod1c: 'СФ-000918-26', vat: 'да' },
    rc:  { num: 'СФ-9188', date: '27.03.2026', amount: 36_900, kod1c: 'СФ-000918-26', vat: 'да', doctype: 'Счёт-фактура' },
  },
  {
    id: 'r8',
    type: 'cominv',
    typeLabel: 'Ком. инвойс',
    opId: 'OP-45825',
    opTitle: 'Поставка товара (внешнеэк.)',
    status: 'miss-erp',
    erp: null,
    rc:  { num: 'CI-SH2026-0471', date: '02.04.2026', amount: 48_200, kod1c: 'CI-SH2026-0471', vat: '—', doctype: 'Ком. инвойс' },
    skipReason: 'На текущий момент ком. инвойсы в ЕРП не ведутся',
    diffNote: 'Документ товарный, не сверяется в ЕРП',
  },
  {
    id: 'r9',
    type: 'act',
    typeLabel: 'Акт',
    opId: 'OP-45826',
    opTitle: 'Автодоставка · Екатеринбург — склад получателя',
    status: 'match',
    erp: { num: 'АКТ-3601', date: '05.04.2026', amount: 78_500, kod1c: 'АК-000601-26', vat: 'да' },
    rc:  { num: 'АКТ-3601', date: '05.04.2026', amount: 78_500, kod1c: 'АК-000601-26', vat: 'да', doctype: 'Акт' },
  },
  {
    id: 'r10',
    type: 'bill',
    typeLabel: 'Счёт на оплату',
    opId: 'OP-45827',
    opTitle: 'Страхование груза',
    status: 'miss-1c',
    erp: { num: 'СЧЁТ-7802', date: '02.04.2026', amount: 42_300, kod1c: 'СЧ-007802-26', vat: 'да' },
    rc:  null,
    diffNote: 'В 1С по коду не найдено — возможно, документ ещё не проведён контрагентом',
  },
  {
    id: 'r11',
    type: 'invoice',
    typeLabel: 'Счёт-фактура',
    opId: 'OP-45826',
    opTitle: 'Автодоставка · Екатеринбург — склад получателя',
    status: 'match',
    erp: { num: 'СФ-9201', date: '05.04.2026', amount: 15_700, kod1c: 'СФ-000920-26', vat: 'да' },
    rc:  { num: 'СФ-9201', date: '05.04.2026', amount: 15_700, kod1c: 'СФ-000920-26', vat: 'да', doctype: 'Счёт-фактура' },
  },
  {
    id: 'r12',
    type: 'act',
    typeLabel: 'Акт',
    opId: 'OP-45821',
    opTitle: 'Морская перевозка · FAK',
    status: 'sum',
    erp: { num: 'АКТ-3488', date: '16.03.2026', amount: 326_000, kod1c: 'АК-000488-26', vat: 'да' },
    rc:  { num: 'АКТ-3488', date: '16.03.2026', amount: 328_450, kod1c: 'АК-000488-26', vat: 'да', doctype: 'Акт' },
    diffFields: ['amount'],
    diffNote: 'Расхождение 2 450 ₽ — скорее всего доп. расход по маршруту',
  },
];

// Candidate 1С documents for "linking" modal (when ERP has no match)
const CANDIDATES_1C = [
  { num: 'АКТ-3510', date: '21.03.2026', amount: 1_085_000, kod1c: 'АК-000510-26', doctype: 'Акт', contractor: 'ООО «ТрансСибЭкспресс»', score: 0.98 },
  { num: 'АКТ-3509', date: '20.03.2026', amount: 1_082_000, kod1c: 'АК-000509-26', doctype: 'Акт', contractor: 'ООО «ТрансСибЭкспресс»', score: 0.74 },
  { num: 'АКТ-3515', date: '22.03.2026', amount: 985_000, kod1c: 'АК-000515-26', doctype: 'Акт', contractor: 'ООО «ТрансСибЭкспресс»', score: 0.61 },
];

// Progress-screen log sequence
const PROGRESS_LOG = [
  { tag: 'info', t: '0.00s', msg: 'Запуск сверки по поставке SPEC-2026/04-1187' },
  { tag: 'info', t: '0.08s', msg: 'Собираем коды 1С: принципал ООО «Восточный Путь» (ИНН 7728123456)' },
  { tag: 'info', t: '0.15s', msg: 'Собираем коды 1С: покупатель АО «Металлторг-Урал» (ИНН 6658987112)' },
  { tag: 'ok',   t: '0.42s', msg: 'Найдено 12 привязанных операций, 19 фин.документов' },
  { tag: 'info', t: '0.58s', msg: 'Формируем read-only REST-запрос к 1С' },
  { tag: 'info', t: '1.12s', msg: 'Запрос отправлен в 1С: 19 кодов' },
  { tag: 'info', t: '1.34s', msg: '1С подтвердила: получение кодов' },
  { tag: 'info', t: '2.20s', msg: 'Ожидание ответа от 1С...' },
  { tag: 'ok',   t: '3.42s', msg: '1С вернула 18 документов (1 не найден)' },
  { tag: 'info', t: '3.60s', msg: 'Сопоставление по коду договора 1С' },
  { tag: 'info', t: '3.78s', msg: 'Контроль номера и даты документа' },
  { tag: 'warn', t: '4.02s', msg: '2 документа найдены только в 1С — не привязаны к ЕРП' },
  { tag: 'warn', t: '4.04s', msg: '1 документ найден только в ЕРП — в 1С не проведён' },
  { tag: 'warn', t: '4.06s', msg: '2 расхождения по сумме, 1 по возмещаемости НДС' },
  { tag: 'ok',   t: '4.18s', msg: 'Отчёт сформирован и сохранён в акт_сверки.reports' },
];

Object.assign(window, { DELIVERY, DOCS, CANDIDATES_1C, PROGRESS_LOG });

const fmtMoney = (n, cur = 'RUB') => {
  if (n == null) return '—';
  const s = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(n);
  return `${s}\u00a0₽`;
};
const groupBy = (arr, fn) => arr.reduce((m, x) => { const k = fn(x); (m[k] ||= []).push(x); return m; }, {});
window.fmtMoney = fmtMoney;
window.groupBy = groupBy;

const STATUS_META = {
  match:    { label: 'Совпадает',            color: 'match',    short: 'OK' },
  'miss-erp': { label: 'Нет в ЕРП',           color: 'miss-erp', short: 'ERP' },
  'miss-1c':  { label: 'Нет в 1С',            color: 'miss-1c',  short: '1C' },
  sum:      { label: 'Расхождение по сумме', color: 'sum',      short: '≠' },
  vat:      { label: 'Возмещаемость НДС',    color: 'vat',      short: 'НДС' },
};
window.STATUS_META = STATUS_META;
