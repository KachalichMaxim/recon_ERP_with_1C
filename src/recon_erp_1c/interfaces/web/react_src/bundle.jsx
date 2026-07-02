
/* ===== src/icons.jsx ===== */
// Minimal line icons — inline SVG, stroke-based, 1.75 weight
const Icon = ({ d, size = 16, stroke = 'currentColor', fill = 'none', sw = 1.75, viewBox = '0 0 24 24', children }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox={viewBox} fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    {d ? <path d={d} /> : children}
  </svg>
);

const IconCheck = (p) => <Icon {...p} d="M4 12l5 5L20 6" />;
const IconX = (p) => <Icon {...p} d="M6 6l12 12M18 6L6 18" />;
const IconAlert = (p) => <Icon {...p}><path d="M12 9v4M12 17h0"/><path d="M10.3 3.9L2.4 17a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/></Icon>;
const IconInfo = (p) => <Icon {...p}><circle cx="12" cy="12" r="9"/><path d="M12 8h0M11 12h1v5h1"/></Icon>;
const IconCopy = (p) => <Icon {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></Icon>;
const IconExternal = (p) => <Icon {...p}><path d="M14 4h6v6"/><path d="M20 4L10 14"/><path d="M20 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5a1 1 0 011-1h5"/></Icon>;
const IconLink = (p) => <Icon {...p}><path d="M10 14a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1"/><path d="M14 10a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1"/></Icon>;
const IconDownload = (p) => <Icon {...p}><path d="M12 3v13M7 12l5 5 5-5"/><path d="M5 21h14"/></Icon>;
const IconSearch = (p) => <Icon {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></Icon>;
const IconFilter = (p) => <Icon {...p}><path d="M3 5h18M6 12h12M10 19h4"/></Icon>;
const IconRefresh = (p) => <Icon {...p}><path d="M3 12a9 9 0 0115-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 01-15 6.7L3 16"/><path d="M3 21v-5h5"/></Icon>;
const IconDoc = (p) => <Icon {...p}><path d="M7 3h8l5 5v11a2 2 0 01-2 2H7a2 2 0 01-2-2V5a2 2 0 012-2z"/><path d="M14 3v5h5"/></Icon>;
const IconReceipt = (p) => <Icon {...p}><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3z"/><path d="M9 8h6M9 12h6M9 16h3"/></Icon>;
const IconMoney = (p) => <Icon {...p}><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h0M18 12h0"/></Icon>;
const IconPlay = (p) => <Icon {...p} d="M7 4v16l13-8z" fill="currentColor" stroke="none"/>;
const IconPause = (p) => <Icon {...p}><rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/></Icon>;
const IconMore = (p) => <Icon {...p}><circle cx="6" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="18" cy="12" r="1.3" fill="currentColor"/></Icon>;
const IconPlus = (p) => <Icon {...p} d="M12 5v14M5 12h14"/>;
const IconArrowRight = (p) => <Icon {...p}><path d="M5 12h14M13 6l6 6-6 6"/></Icon>;
const IconArrowLeft = (p) => <Icon {...p}><path d="M19 12H5M11 6l-6 6 6 6"/></Icon>;
const IconChevron = (p) => <Icon {...p} d="M6 9l6 6 6-6"/>;
const IconSparkle = (p) => <Icon {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/></Icon>;
const IconBell = (p) => <Icon {...p}><path d="M6 9a6 6 0 0112 0v4l2 3H4l2-3V9z"/><path d="M10 19a2 2 0 004 0"/></Icon>;
const IconSettings = (p) => <Icon {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 01-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 014 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z"/></Icon>;
const IconBox = (p) => <Icon {...p}><path d="M3 7l9-4 9 4v10l-9 4-9-4V7z"/><path d="M3 7l9 4 9-4M12 11v10"/></Icon>;
const IconList = (p) => <Icon {...p}><path d="M8 6h13M8 12h13M8 18h13M3 6h0M3 12h0M3 18h0"/></Icon>;
const IconChart = (p) => <Icon {...p}><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/></Icon>;
const IconSpinner = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2.5"/>
    <path d="M21 12a9 9 0 00-9-9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
  </svg>
);

// Inject spinner keyframes once
if (typeof document !== 'undefined' && !document.getElementById('__spin_kf')) {
  const s = document.createElement('style');
  s.id = '__spin_kf';
  s.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(s);
}

Object.assign(window, {
  IconCheck, IconX, IconAlert, IconInfo, IconCopy, IconExternal, IconLink, IconDownload,
  IconSearch, IconFilter, IconRefresh, IconDoc, IconReceipt, IconMoney,
  IconPlay, IconPause, IconMore, IconPlus, IconArrowRight, IconArrowLeft, IconChevron,
  IconSparkle, IconBell, IconSettings, IconBox, IconList, IconChart, IconSpinner,
});


/* ===== src/data.js ===== */
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


/* ===== src/DeliveryCard.jsx ===== */
// Delivery card screen — entry point with "Сверить с 1С" CTA
const DeliveryCard = ({ onStart, lastReport }) => {
  const d = window.DELIVERY;
  const docs = window.DOCS;
  const stats = {
    ops: new Set(docs.map(x => x.opId)).size,
    erpDocs: docs.filter(x => x.erp).length,
    expected1c: docs.filter(x => x.rc).length,
    matched: lastReport ? docs.filter(x => x.status === 'match').length : null,
  };

  return (
    <div className="page">
      <div className="delivery-head">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span className="pill-sm">Поставка</span>
            <span className="mono muted" style={{ fontSize: 12 }}>{d.id}</span>
            <span className="chip neutral"><span className="dot"/>{d.status}</span>
          </div>
          <div className="delivery-title">{d.number} · {d.client}</div>
          <div className="delivery-sub">{d.route} · контейнер <span className="mono">{d.container}</span> · {d.incoterms} · менеджер {d.manager}</div>
        </div>
        <div className="delivery-cta">
          <button className="btn"><IconExternal size={14}/>Открыть в ЕРП</button>
          <button className="btn brand" onClick={onStart}>
            <IconRefresh size={15}/>
            Сверить с 1С
          </button>
        </div>
      </div>

      <div className="delivery-grid">
        <div className="card">
          <div className="card-head">
            <IconList size={16}/>
            <div>
              <div className="card-title">Финансовые документы поставки</div>
              <div className="card-sub">Привязаны к операциям в ЕРП — {docs.filter(x => x.erp).length} шт.</div>
            </div>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
              <button className="btn sm"><IconFilter size={13}/>Фильтр</button>
              <button className="btn sm"><IconPlus size={13}/>Добавить документ</button>
            </div>
          </div>
          <table className="doc-list">
            <thead>
              <tr>
                <th>Документ</th>
                <th>Операция</th>
                <th>Дата</th>
                <th style={{ textAlign: 'right' }}>Сумма</th>
                <th>Код 1С</th>
                <th style={{ width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {docs.filter(x => x.erp).slice(0, 9).map(x => (
                <tr key={x.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span className="pill-sm">{x.typeLabel}</span>
                      <span className="mono" style={{ fontWeight: 600 }}>{x.erp.num}</span>
                    </div>
                  </td>
                  <td className="muted" style={{ fontSize: 12 }}>{x.opTitle}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{x.erp.date}</td>
                  <td className="mono" style={{ textAlign: 'right', fontWeight: 600 }}>{fmtMoney(x.erp.amount)}</td>
                  <td><span className="code1c">{x.erp.kod1c}</span></td>
                  <td><button className="icon-btn"><IconMore size={14}/></button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="last-sync">
            <IconInfo size={13}/>
            Всего {docs.filter(x => x.erp).length} документов · показано 9 · <a className="link">открыть все</a>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="card">
            <div className="card-head">
              <IconBox size={16}/>
              <div className="card-title">Сводка</div>
            </div>
            <div className="stat-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
              <div className="stat">
                <div className="stat-val">{stats.ops}</div>
                <div className="stat-label">Операций</div>
              </div>
              <div className="stat">
                <div className="stat-val">{stats.erpDocs}</div>
                <div className="stat-label">Фин.документов в ЕРП</div>
              </div>
              <div className="stat">
                <div className="stat-val mono" style={{ fontSize: 18, lineHeight: 1.7 }}>{fmtMoney(d.totalAmount)}</div>
                <div className="stat-label">Сумма поставки</div>
              </div>
              <div className="stat">
                <div className="stat-val">{stats.expected1c}</div>
                <div className="stat-label">Ожидается в 1С</div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <IconRefresh size={16}/>
              <div>
                <div className="card-title">Последняя сверка</div>
                <div className="card-sub">{lastReport ? `${lastReport.when} · ${lastReport.user}` : 'Ещё не проводилась'}</div>
              </div>
            </div>
            <div style={{ padding: 16 }}>
              {lastReport ? (
                <>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                    <span className="chip match"><span className="dot"/>{docs.filter(x => x.status === 'match').length} совпало</span>
                    <span className="chip miss-erp"><span className="dot"/>{docs.filter(x => x.status === 'miss-erp').length} нет в ЕРП</span>
                    <span className="chip miss-1c"><span className="dot"/>{docs.filter(x => x.status === 'miss-1c').length} нет в 1С</span>
                    <span className="chip sum"><span className="dot"/>{docs.filter(x => x.status === 'sum').length} по сумме</span>
                    <span className="chip vat"><span className="dot"/>{docs.filter(x => x.status === 'vat').length} НДС</span>
                  </div>
                  <a className="link" onClick={() => onStart(true)}>Открыть отчёт →</a>
                </>
              ) : (
                <div style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6 }}>
                  Запустите сверку, чтобы увидеть какие документы из 1С отсутствуют или отличаются от ЕРП.
                  <br/>
                  <button className="btn brand" style={{ marginTop: 12 }} onClick={onStart}>
                    <IconRefresh size={15}/>Запустить сверку
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <IconInfo size={16}/>
              <div className="card-title">Контрагенты</div>
            </div>
            <div style={{ padding: 16 }}>
              <dl className="kv">
                <dt>Принципал</dt><dd>{d.principal}<br/><span className="mono muted" style={{ fontSize: 11.5 }}>ИНН {d.principalInn}</span></dd>
                <dt>Клиент</dt><dd>{d.client}<br/><span className="mono muted" style={{ fontSize: 11.5 }}>ИНН {d.clientInn}</span></dd>
                <dt>Дата</dt><dd>{d.date}</dd>
                <dt>Валюта</dt><dd>{d.currency}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

window.DeliveryCard = DeliveryCard;


/* ===== src/ReconcileProgress.jsx ===== */
// Progress screen — 3 stages (collect codes → request 1C → match)
const ReconcileProgress = ({ onDone, onCancel }) => {
  const [stage, setStage] = React.useState(0); // 0,1,2
  const [stageProg, setStageProg] = React.useState(0); // 0..100 for current
  const [logCount, setLogCount] = React.useState(0);
  const log = window.PROGRESS_LOG;

  React.useEffect(() => {
    if (stage >= 3) { const t = setTimeout(onDone, 600); return () => clearTimeout(t); }
    const tick = setInterval(() => {
      setStageProg(p => {
        if (p >= 100) {
          clearInterval(tick);
          setStage(s => s + 1);
          return 0;
        }
        return p + (stage === 2 ? 4 : stage === 1 ? 2.8 : 6);
      });
    }, 55);
    return () => clearInterval(tick);
  }, [stage]);

  React.useEffect(() => {
    if (logCount >= log.length) return;
    const delay = 140 + Math.random() * 140;
    const t = setTimeout(() => setLogCount(c => c + 1), delay);
    return () => clearTimeout(t);
  }, [logCount]);

  const stages = [
    { num: '01', title: 'Сбор кодов 1С', desc: 'Из спецификации и привязанных операций' },
    { num: '02', title: 'Запрос в 1С', desc: 'Read-only REST, получение документов по кодам' },
    { num: '03', title: 'Сопоставление', desc: 'Поиск совпадений и расхождений' },
  ];

  return (
    <div className="page">
      <div className="progress-wrap">
        <div className="progress-head">
          <div className="progress-title">Сверяем документы с 1С</div>
          <div className="progress-sub">Поставка {window.DELIVERY.number} · {window.DELIVERY.client}</div>
        </div>

        <div className="stages">
          {stages.map((s, i) => {
            const done = i < stage;
            const active = i === stage;
            const width = done ? 100 : active ? stageProg : 0;
            return (
              <div key={i} className={`stage ${done ? 'done' : ''} ${active ? 'active' : ''}`}>
                <div className="stage-icon">
                  {done ? <IconCheck size={18}/> : active ? <IconSpinner size={18}/> : <span className="mono" style={{ fontSize: 13, fontWeight: 600 }}>{s.num}</span>}
                </div>
                <div className="stage-num mono">Этап {s.num}</div>
                <div className="stage-title">{s.title}</div>
                <div className="stage-desc">{s.desc}</div>
                <div className="stage-progress"><span style={{ width: `${width}%` }}/></div>
              </div>
            );
          })}
        </div>

        <div className="progress-log">
          {log.slice(0, logCount).map((l, i) => (
            <div key={i} className="line">
              <span className="ts">[{l.t}]</span>
              <span className={l.tag === 'ok' ? 'tag-ok' : l.tag === 'warn' ? 'tag-warn' : 'tag-info'}>
                {l.tag === 'ok' ? '✓' : l.tag === 'warn' ? '⚠' : '›'}
              </span>
              <span>{l.msg}</span>
            </div>
          ))}
          {logCount < log.length && <div className="line" style={{ color: 'var(--muted-2)' }}><span className="ts">...</span><span/></div>}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 18 }}>
          <button className="btn ghost" onClick={onCancel}>Отменить</button>
          <div className="muted" style={{ fontSize: 12, alignSelf: 'center' }}>
            {stage >= 3 ? 'Готово' : `Этап ${Math.min(stage + 1, 3)} из 3`}
          </div>
        </div>
      </div>
    </div>
  );
};

window.ReconcileProgress = ReconcileProgress;


/* ===== src/ReportRow.jsx ===== */
// Single reconciliation row — two-column layout with connecting line
const ReportRow = ({ rec, expanded, onToggle, onOpenDrawer, onCopy, onGotoOp, onLink }) => {
  const meta = window.STATUS_META[rec.status];
  const hasErp = !!rec.erp;
  const has1c = !!rec.rc;
  const diff = rec.diffFields || [];
  const showLines = document.body.getAttribute('data-show-lines') !== 'false';

  const LineSVG = () => {
    // connector between ERP and 1C panels
    const stroke =
      rec.status === 'match' ? 'var(--match)' :
      rec.status === 'miss-erp' ? 'var(--miss-erp)' :
      rec.status === 'miss-1c' ? 'var(--miss-1c)' :
      rec.status === 'sum' ? 'var(--sum-mismatch)' :
      rec.status === 'vat' ? 'var(--vat)' : 'var(--border-strong)';
    const dash = rec.status === 'match' ? '' : '4 4';
    return (
      <svg width="72" height="50" viewBox="0 0 72 50">
        <line x1="0" y1="25" x2="72" y2="25" stroke={stroke} strokeWidth="1.5" strokeDasharray={dash}/>
        <circle cx="36" cy="25" r="10" fill="var(--surface)" stroke={stroke} strokeWidth="1.5"/>
        {rec.status === 'match' ? (
          <path d="M31 25 l4 4 l7 -8" stroke={stroke} strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        ) : rec.status === 'miss-erp' || rec.status === 'miss-1c' ? (
          <>
            <path d="M32 20 l8 10 M40 20 l-8 10" stroke={stroke} strokeWidth="1.8" strokeLinecap="round"/>
          </>
        ) : rec.status === 'sum' ? (
          <text x="36" y="29" textAnchor="middle" fontSize="12" fontWeight="700" fill={stroke} fontFamily="JetBrains Mono">≠</text>
        ) : (
          <text x="36" y="29" textAnchor="middle" fontSize="9" fontWeight="700" fill={stroke} fontFamily="Inter Tight">?</text>
        )}
      </svg>
    );
  };

  const Side = ({ side, data }) => {
    if (!data) {
      const msg = side === 'erp'
        ? (rec.skipReason || 'Не найдено в ЕРП')
        : 'Не найдено в 1С';
      return (
        <div className={`rec-side ${side === 'erp' ? 'left' : 'right'} empty`}>
          <div className="empty-msg">
            <IconAlert size={14} stroke={side === 'erp' ? 'oklch(0.58 0.13 75)' : 'oklch(0.56 0.15 45)'}/>
            <strong style={{ color: 'var(--ink-2)', fontSize: 12 }}>{side === 'erp' ? 'Нет в ЕРП' : 'Нет в 1С'}</strong>
          </div>
          <div style={{ fontSize: 11.5, lineHeight: 1.5 }}>{msg}</div>
          {side === 'erp' && rec.rc && (
            <button className="btn xs" style={{ marginTop: 4 }} onClick={(e) => { e.stopPropagation(); onLink(rec); }}>
              <IconLink size={11}/> Привязать к операции
            </button>
          )}
        </div>
      );
    }
    const isDiff = (f) => diff.includes(f);
    return (
      <div className={`rec-side ${side === 'erp' ? 'left' : 'right'}`}>
        <div className="doc-line-head">
          <span className="pill-sm">{data.doctype || rec.typeLabel}</span>
          <span className="doc-num mono">{data.num}</span>
        </div>
        <div className="doc-meta">
          <span>
            <span className="k">дата:</span>
            <span className={`v ${isDiff('date') ? 'diff' : ''}`}>{data.date}</span>
          </span>
          <span>
            <span className="k">сумма:</span>
            <span className={`v ${isDiff('amount') && side === 'erp' ? 'diff' : isDiff('amount') && side === 'rc' ? 'fix' : ''}`}>{fmtMoney(data.amount)}</span>
          </span>
          <span>
            <span className="k">НДС:</span>
            <span className={`v ${isDiff('vat') ? (side === 'erp' ? 'diff' : 'fix') : ''}`}>{data.vat}</span>
          </span>
          <span>
            <span className="code1c">
              {data.kod1c}
              <span className="copy" onClick={(e) => { e.stopPropagation(); onCopy(data.kod1c); }} title="Скопировать код 1С"><IconCopy size={11}/></span>
            </span>
          </span>
        </div>
      </div>
    );
  };

  return (
    <>
      <div className={`rec-row ${expanded ? 'expanded' : ''}`} onClick={onToggle}>
        <Side side="erp" data={rec.erp}/>
        <div className="rec-link">{showLines ? <LineSVG/> : <div style={{ width: 1, height: 36, background: 'var(--border)' }}/>}</div>
        <Side side="rc" data={rec.rc}/>

        <div className="rec-status-cell">
          <span className={`chip ${meta.color}`}><span className="dot"/>{meta.label}</span>
          {rec.diffNote && <span className="detail">{rec.diffNote}</span>}
        </div>

        <div className="rec-actions" onClick={(e) => e.stopPropagation()}>
          {hasErp && (
            <button className="icon-btn" title="Открыть операцию в ЕРП" onClick={() => onGotoOp(rec.opId)}><IconExternal size={14}/></button>
          )}
          {has1c && (
            <button className="icon-btn" title="Скопировать код 1С" onClick={() => onCopy(rec.rc.kod1c)}><IconCopy size={14}/></button>
          )}
          <button className="icon-btn" title="Подробнее" onClick={onOpenDrawer}><IconMore size={14}/></button>
          <button className="icon-btn" title={expanded ? 'Свернуть' : 'Развернуть'} onClick={onToggle}><IconChevron size={14} style={{ transform: expanded ? 'rotate(180deg)' : '', transition: 'transform 0.15s' }}/></button>
        </div>
      </div>

      {expanded && (
        <div className="rec-detail">
          <div>
            <h4><IconBox size={12}/> ЕРП (операция {rec.opId})</h4>
            {rec.erp ? (
              <dl className="kv">
                <dt>Операция</dt><dd>{rec.opTitle}</dd>
                <dt>Документ</dt><dd>{rec.typeLabel} <span className="mono">{rec.erp.num}</span></dd>
                <dt>Дата</dt><dd className="mono">{rec.erp.date}</dd>
                <dt>Сумма</dt><dd className="mono">{fmtMoney(rec.erp.amount)}</dd>
                <dt>НДС</dt><dd>{rec.erp.vat}</dd>
                <dt>Код 1С</dt><dd><span className="code1c">{rec.erp.kod1c}</span></dd>
              </dl>
            ) : (
              <div className="muted" style={{ fontSize: 12 }}>Документ в ЕРП отсутствует</div>
            )}
          </div>
          <div>
            <h4><IconReceipt size={12}/> 1С</h4>
            {rec.rc ? (
              <dl className="kv">
                <dt>Документ</dt><dd>{rec.rc.doctype} <span className="mono">{rec.rc.num}</span></dd>
                <dt>Дата</dt><dd className="mono">{rec.rc.date}</dd>
                <dt>Сумма</dt><dd className="mono">{fmtMoney(rec.rc.amount)}</dd>
                <dt>НДС</dt><dd>{rec.rc.vat}</dd>
                <dt>Код 1С</dt><dd><span className="code1c">{rec.rc.kod1c} <span className="copy" onClick={() => onCopy(rec.rc.kod1c)} style={{ opacity: 1 }}><IconCopy size={11}/></span></span></dd>
              </dl>
            ) : (
              <div className="muted" style={{ fontSize: 12 }}>В 1С по коду не найдено</div>
            )}
          </div>
          <div className="detail-actions">
            {hasErp && <button className="btn sm" onClick={() => onGotoOp(rec.opId)}><IconExternal size={13}/>Открыть операцию {rec.opId}</button>}
            {!hasErp && rec.rc && <button className="btn sm brand" onClick={() => onLink(rec)}><IconLink size={13}/>Привязать документ к операции</button>}
            {rec.status === 'sum' && <button className="btn sm"><IconCheck size={13}/>Отметить проверено вручную</button>}
            {rec.status === 'vat' && <button className="btn sm"><IconSparkle size={13}/>Проверить возмещаемость</button>}
            {rec.skipReason && <span className="chip neutral" style={{ alignSelf: 'center' }}><span className="dot"/>Не сверяется</span>}
            <button className="btn sm ghost" style={{ marginLeft: 'auto' }}>Игнорировать с комментарием</button>
          </div>
        </div>
      )}
    </>
  );
};

window.ReportRow = ReportRow;


/* ===== src/SummaryStats.jsx ===== */
// Summary stats bar — mini counters; clicking filters the report
const SummaryStats = ({ docs, activeFilter, onFilter }) => {
  const by = window.groupBy(docs, x => x.status);
  const tiles = [
    { key: 'all',      label: 'Всего документов',     count: docs.length,                    swatch: 'var(--ink-2)' },
    { key: 'match',    label: 'Совпадает полностью',  count: (by['match'] || []).length,     swatch: 'var(--match)' },
    { key: 'miss-erp', label: 'Нет в ЕРП',            count: (by['miss-erp'] || []).length,  swatch: 'var(--miss-erp)' },
    { key: 'miss-1c',  label: 'Нет в 1С',             count: (by['miss-1c'] || []).length,   swatch: 'var(--miss-1c)' },
    { key: 'sum',      label: 'Расхождение по сумме', count: (by['sum'] || []).length,       swatch: 'var(--sum-mismatch)' },
    { key: 'vat',      label: 'Вопрос по НДС',        count: (by['vat'] || []).length,       swatch: 'var(--vat)' },
  ];
  return (
    <div className="summary-row">
      {tiles.map(t => (
        <div key={t.key}
             className={`summary-tile ${activeFilter === t.key ? 'active' : ''}`}
             onClick={() => onFilter(t.key)}>
          <div className="val"><span className="swatch" style={{ background: t.swatch }}/>{t.count}</div>
          <div className="label">{t.label}</div>
        </div>
      ))}
    </div>
  );
};

window.SummaryStats = SummaryStats;


/* ===== src/ExportDialog.jsx ===== */
// Export dialog — Excel template or PDF report
const ExportDialog = ({ onClose, onDone }) => {
  const [fmt, setFmt] = React.useState('xlsx');
  const [scope, setScope] = React.useState('all');
  const [template, setTemplate] = React.useState('metaltorg');

  const submit = () => {
    onDone(`Экспорт сформирован: ${fmt === 'xlsx' ? 'Excel' : 'PDF'} · ${
      scope === 'all' ? 'все строки' : 'только расхождения'
    }`);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <IconDownload size={16}/>
          <div className="modal-title">Выгрузить отчёт</div>
          <button className="btn ghost sm modal-close" onClick={onClose}><IconX size={13}/></button>
        </div>
        <div className="modal-body">
          <div style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>Формат</div>
          <div className="fmt-grid" style={{ marginBottom: 18 }}>
            <div className={`fmt-tile ${fmt === 'xlsx' ? 'selected' : ''}`} onClick={() => setFmt('xlsx')}>
              <div className="fmt-head">
                <div className="fmt-icon" style={{ background: 'oklch(0.97 0.04 155)', borderColor: 'oklch(0.85 0.08 155)', color: 'oklch(0.35 0.1 155)' }}>
                  <span className="mono" style={{ fontWeight: 700, fontSize: 11 }}>XLS</span>
                </div>
                <div>
                  <div className="fmt-name">Excel</div>
                  <div className="fmt-sub">Шаблон для копирования в файл клиента</div>
                </div>
              </div>
            </div>
            <div className={`fmt-tile ${fmt === 'pdf' ? 'selected' : ''}`} onClick={() => setFmt('pdf')}>
              <div className="fmt-head">
                <div className="fmt-icon" style={{ background: 'oklch(0.97 0.04 25)', borderColor: 'oklch(0.86 0.1 25)', color: 'oklch(0.42 0.15 25)' }}>
                  <span className="mono" style={{ fontWeight: 700, fontSize: 11 }}>PDF</span>
                </div>
                <div>
                  <div className="fmt-name">PDF-отчёт</div>
                  <div className="fmt-sub">Для отправки клиенту / архива</div>
                </div>
              </div>
            </div>
          </div>

          {fmt === 'xlsx' && (
            <>
              <div style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>Шаблон сверки клиента</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 18 }}>
                {[
                  { k: 'metaltorg',  n: 'АО «Металлторг-Урал»', d: 'Шаблон клиента (4 листа, с формулами)' },
                  { k: 'universal',  n: 'Универсальный',        d: 'Типизированный вид для любого клиента' },
                  { k: 'raw',        n: 'Сырая выгрузка',       d: 'Без форматирования, плоская таблица' },
                ].map(t => (
                  <label key={t.k} style={{ display: 'flex', gap: 10, padding: '10px 12px', border: `1px solid ${template === t.k ? 'var(--ink)' : 'var(--border)'}`, borderRadius: 10, cursor: 'pointer', background: template === t.k ? 'var(--bg-sunken)' : 'var(--surface)' }}>
                    <input type="radio" checked={template === t.k} onChange={() => setTemplate(t.k)} style={{ marginTop: 2 }}/>
                    <div>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{t.n}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>{t.d}</div>
                    </div>
                  </label>
                ))}
              </div>
            </>
          )}

          <div style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>Содержание</div>
          <div className="seg" style={{ marginBottom: 4 }}>
            <button className={scope === 'all' ? 'on' : ''} onClick={() => setScope('all')}>Все строки</button>
            <button className={scope === 'issues' ? 'on' : ''} onClick={() => setScope('issues')}>Только расхождения</button>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" onClick={onClose}>Отмена</button>
          <button className="btn sm" style={{ padding: '7px 12px' }}><IconCopy size={13}/>Скопировать в буфер</button>
          <button className="btn brand" onClick={submit}><IconDownload size={14}/>Скачать</button>
        </div>
      </div>
    </div>
  );
};

window.ExportDialog = ExportDialog;


/* ===== src/LinkPicker.jsx ===== */
// Link 1C doc to ERP operation — picker modal
const LinkPicker = ({ rec, onClose, onDone }) => {
  const [selOp, setSelOp] = React.useState('OP-45822');
  const [selCand, setSelCand] = React.useState('АК-000510-26');
  const cands = window.CANDIDATES_1C;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal wide" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <IconLink size={16}/>
          <div className="modal-title">Привязать документ 1С к операции ЕРП</div>
          <button className="btn ghost sm modal-close" onClick={onClose}><IconX size={13}/></button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            <div>
              <div style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 8, fontWeight: 600 }}>Документ из 1С</div>
              <div className="card" style={{ padding: 14, borderRadius: 10 }}>
                <div className="doc-line-head">
                  <span className="pill-sm">{rec.rc.doctype}</span>
                  <span className="doc-num mono">{rec.rc.num}</span>
                </div>
                <div className="doc-meta" style={{ marginTop: 4 }}>
                  <span><span className="k">дата:</span><span className="v">{rec.rc.date}</span></span>
                  <span><span className="k">сумма:</span><span className="v">{fmtMoney(rec.rc.amount)}</span></span>
                </div>
                <div style={{ marginTop: 8 }}><span className="code1c">{rec.rc.kod1c}</span></div>
              </div>

              <div style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginTop: 18, marginBottom: 8, fontWeight: 600 }}>Выберите операцию в ЕРП</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {['OP-45821', 'OP-45822', 'OP-45826'].map(op => {
                  const title = ({ 'OP-45821': 'Морская перевозка · FAK', 'OP-45822': 'Ж/д доставка · Забайкальск → Екатеринбург', 'OP-45826': 'Автодоставка · Екатеринбург — склад' })[op];
                  return (
                    <label key={op} style={{ display: 'flex', gap: 10, padding: '9px 12px', border: `1px solid ${selOp === op ? 'var(--ink)' : 'var(--border)'}`, borderRadius: 10, cursor: 'pointer', background: selOp === op ? 'var(--bg-sunken)' : 'var(--surface)' }}>
                      <input type="radio" checked={selOp === op} onChange={() => setSelOp(op)} style={{ marginTop: 2 }}/>
                      <div>
                        <div style={{ fontSize: 13 }}><span className="mono muted" style={{ fontSize: 11.5 }}>{op}</span> · {title}</div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11.5, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--muted)', marginBottom: 8, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
                <IconSparkle size={12}/> Предложенные совпадения
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {cands.map(c => (
                  <label key={c.kod1c} style={{ display: 'flex', gap: 10, padding: '10px 12px', border: `1px solid ${selCand === c.kod1c ? 'var(--ink)' : 'var(--border)'}`, borderRadius: 10, cursor: 'pointer', background: selCand === c.kod1c ? 'var(--bg-sunken)' : 'var(--surface)' }}>
                    <input type="radio" checked={selCand === c.kod1c} onChange={() => setSelCand(c.kod1c)} style={{ marginTop: 3 }}/>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span className="mono" style={{ fontWeight: 600, fontSize: 13 }}>{c.num}</span>
                        <span className="pill-sm">{c.doctype}</span>
                        <span style={{ marginLeft: 'auto', fontSize: 11, color: c.score > 0.9 ? 'oklch(0.4 0.12 155)' : 'var(--muted)' }}>
                          {Math.round(c.score * 100)}% совпадение
                        </span>
                      </div>
                      <div className="doc-meta" style={{ marginTop: 4, gap: 10 }}>
                        <span><span className="k">дата:</span><span className="v">{c.date}</span></span>
                        <span><span className="k">сумма:</span><span className="v">{fmtMoney(c.amount)}</span></span>
                      </div>
                      <div style={{ marginTop: 4 }}><span className="code1c">{c.kod1c}</span></div>
                    </div>
                  </label>
                ))}
              </div>
              <div style={{ marginTop: 12, padding: 10, background: 'var(--brand-bg)', borderRadius: 10, fontSize: 11.5, color: 'oklch(0.32 0.13 235)', display: 'flex', gap: 8 }}>
                <IconInfo size={13}/>
                После привязки документ автоматически попадёт в повторную сверку.
              </div>
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" onClick={onClose}>Отмена</button>
          <button className="btn brand" onClick={() => onDone(`Документ ${rec.rc.num} привязан к операции ${selOp}`)}>
            <IconCheck size={14}/>Привязать
          </button>
        </div>
      </div>
    </div>
  );
};

window.LinkPicker = LinkPicker;


/* ===== src/ReportScreen.jsx ===== */
// Report screen — two-column ERP ↔ 1C with group-by-operation
const ReportScreen = ({ onBack, onOpenExport, onOpenLink, onToast }) => {
  const [filter, setFilter] = React.useState('all');
  const [group, setGroup] = React.useState('op'); // 'op' | 'status' | 'flat'
  const [expanded, setExpanded] = React.useState(() => {
    const auto = window.__tweakState?.autoExpandIssues;
    if (!auto) return new Set();
    return new Set(window.DOCS.filter(x => x.status !== 'match').slice(0, 1).map(x => x.id));
  });
  const [search, setSearch] = React.useState('');
  const [drawerRec, setDrawerRec] = React.useState(null);

  const docs = window.DOCS.filter(d => {
    if (filter !== 'all' && d.status !== filter) return false;
    if (search) {
      const q = search.toLowerCase();
      const blob = [d.erp?.num, d.rc?.num, d.erp?.kod1c, d.rc?.kod1c, d.opTitle].filter(Boolean).join(' ').toLowerCase();
      if (!blob.includes(q)) return false;
    }
    return true;
  });

  const toggleRow = (id) => {
    setExpanded(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const copyToClipboard = (text) => {
    try { navigator.clipboard.writeText(text); } catch {}
    onToast(`Скопировано: ${text}`);
  };

  const gotoOp = (opId) => onToast(`Переход в операцию ${opId} в ЕРП`);

  let grouped;
  if (group === 'op') {
    grouped = window.groupBy(docs, d => `${d.opId}|${d.opTitle}`);
  } else if (group === 'status') {
    grouped = window.groupBy(docs, d => d.status);
  } else {
    grouped = { '': docs };
  }

  const d = window.DELIVERY;

  return (
    <div className="page">
      <div className="report-head">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <button className="btn ghost sm" onClick={onBack}><IconArrowLeft size={13}/>К поставке</button>
            <span className="pill-sm">Отчёт сверки</span>
            <span className="mono muted" style={{ fontSize: 11.5 }}>{d.id} · №2026-04-17-011</span>
            <span className="chip match"><span className="dot"/>Отчёт сохранён</span>
          </div>
          <div className="report-title">Сверка с 1С · {d.number}</div>
          <div className="report-sub">
            Сформирован 17.04.2026 в 14:23 · {window.DOCS.length} документов · принципал {d.principal} · клиент {d.client}
          </div>
        </div>
        <div className="report-actions">
          <button className="btn sm"><IconRefresh size={13}/>Пересверить</button>
          <button className="btn sm"><IconCopy size={13}/>Скопировать</button>
          <button className="btn brand" onClick={onOpenExport}><IconDownload size={14}/>Выгрузить</button>
        </div>
      </div>

      <SummaryStats docs={window.DOCS} activeFilter={filter} onFilter={setFilter}/>

      <div className="filters-row">
        <div className="search">
          <IconSearch size={14}/>
          <input placeholder="Поиск по номеру, коду 1С, операции..." value={search} onChange={e => setSearch(e.target.value)}/>
        </div>
        <div className="seg">
          <button className={group === 'op' ? 'on' : ''} onClick={() => setGroup('op')}>По операциям</button>
          <button className={group === 'status' ? 'on' : ''} onClick={() => setGroup('status')}>По статусам</button>
          <button className={group === 'flat' ? 'on' : ''} onClick={() => setGroup('flat')}>Списком</button>
        </div>
        <button className="btn sm"><IconFilter size={13}/>Фильтры</button>
      </div>

      <div className="rec-wrap">
        <div className="rec-header">
          <div className="col-erp">
            <span className="badge-sys" style={{ background: 'oklch(0.96 0.03 235)', borderColor: 'oklch(0.85 0.08 235)', color: 'oklch(0.35 0.13 235)' }}>
              <IconBox size={11}/> ЕРП
            </span>
            <span>Документ ЕРП</span>
          </div>
          <div style={{ textAlign: 'center' }}>↔</div>
          <div className="col-1c">
            <span className="badge-sys" style={{ background: 'oklch(0.96 0.03 80)', borderColor: 'oklch(0.85 0.1 80)', color: 'oklch(0.4 0.12 75)' }}>
              <IconReceipt size={11}/> 1С
            </span>
            <span>Документ 1С</span>
          </div>
          <div>Статус сверки</div>
          <div style={{ textAlign: 'right' }}>Действия</div>
        </div>

        {Object.entries(grouped).map(([k, rows]) => {
          if (group === 'flat') {
            return rows.map(rec => (
              <ReportRow key={rec.id} rec={rec}
                expanded={expanded.has(rec.id)}
                onToggle={() => toggleRow(rec.id)}
                onOpenDrawer={() => setDrawerRec(rec)}
                onCopy={copyToClipboard}
                onGotoOp={gotoOp}
                onLink={(r) => onOpenLink(r)}
              />
            ));
          }
          const [opId, opTitle] = group === 'op' ? k.split('|') : [null, null];
          const label = group === 'op'
            ? <>
                <span className="mono" style={{ fontSize: 11.5, color: 'var(--muted)' }}>{opId}</span>
                <span>{opTitle}</span>
                <span className="c">· {rows.length} документ(ов)</span>
              </>
            : <>
                <span className={`chip ${window.STATUS_META[k].color}`}><span className="dot"/>{window.STATUS_META[k].label}</span>
                <span className="c">{rows.length} шт.</span>
              </>;
          return (
            <React.Fragment key={k}>
              <div className="rec-group-head">{label}</div>
              {rows.map(rec => (
                <ReportRow key={rec.id} rec={rec}
                  expanded={expanded.has(rec.id)}
                  onToggle={() => toggleRow(rec.id)}
                  onOpenDrawer={() => setDrawerRec(rec)}
                  onCopy={copyToClipboard}
                  onGotoOp={gotoOp}
                  onLink={(r) => onOpenLink(r)}
                />
              ))}
            </React.Fragment>
          );
        })}

        {docs.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--muted)', fontSize: 13 }}>
            Нет документов по выбранному фильтру
          </div>
        )}
      </div>

      <div style={{ marginTop: 18, display: 'flex', gap: 10, alignItems: 'center', padding: '12px 14px', background: 'var(--brand-bg)', borderRadius: 12, fontSize: 12.5, color: 'oklch(0.3 0.13 235)' }}>
        <IconInfo size={14}/>
        Отчёт сохранён в базе данных ЕРП (<span className="mono">акт_сверки.reports</span>) — будет использован для аналитики по частоте расхождений.
      </div>

      {drawerRec && (
        <>
          <div className="drawer-overlay" onClick={() => setDrawerRec(null)}/>
          <aside className="drawer">
            <div className="drawer-head">
              <div>
                <div style={{ fontFamily: 'Inter Tight', fontWeight: 600, fontSize: 15 }}>
                  {drawerRec.typeLabel} {drawerRec.erp?.num || drawerRec.rc?.num}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                  {drawerRec.opId} · {drawerRec.opTitle}
                </div>
              </div>
              <button className="btn ghost sm" style={{ marginLeft: 'auto' }} onClick={() => setDrawerRec(null)}><IconX size={13}/></button>
            </div>
            <div className="drawer-body">
              <span className={`chip ${window.STATUS_META[drawerRec.status].color}`} style={{ marginBottom: 14 }}>
                <span className="dot"/>{window.STATUS_META[drawerRec.status].label}
              </span>
              {drawerRec.diffNote && <div style={{ marginTop: 12, padding: 10, background: 'var(--bg-sunken)', borderRadius: 10, fontSize: 12.5 }}>{drawerRec.diffNote}</div>}

              <h4 style={{ fontFamily: 'Inter Tight', fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginTop: 22, marginBottom: 10 }}>Сторона ЕРП</h4>
              {drawerRec.erp ? <dl className="kv">
                <dt>Документ</dt><dd>{drawerRec.typeLabel} <span className="mono">{drawerRec.erp.num}</span></dd>
                <dt>Дата</dt><dd className="mono">{drawerRec.erp.date}</dd>
                <dt>Сумма</dt><dd className="mono">{fmtMoney(drawerRec.erp.amount)}</dd>
                <dt>НДС</dt><dd>{drawerRec.erp.vat}</dd>
                <dt>Код 1С</dt><dd><span className="code1c">{drawerRec.erp.kod1c}</span></dd>
              </dl> : <div className="muted">Документ в ЕРП не заведён</div>}

              <h4 style={{ fontFamily: 'Inter Tight', fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginTop: 22, marginBottom: 10 }}>Сторона 1С</h4>
              {drawerRec.rc ? <dl className="kv">
                <dt>Документ</dt><dd>{drawerRec.rc.doctype} <span className="mono">{drawerRec.rc.num}</span></dd>
                <dt>Дата</dt><dd className="mono">{drawerRec.rc.date}</dd>
                <dt>Сумма</dt><dd className="mono">{fmtMoney(drawerRec.rc.amount)}</dd>
                <dt>НДС</dt><dd>{drawerRec.rc.vat}</dd>
                <dt>Код 1С</dt><dd>
                  <span className="code1c">{drawerRec.rc.kod1c}
                    <span className="copy" style={{ opacity: 1 }} onClick={() => copyToClipboard(drawerRec.rc.kod1c)}><IconCopy size={11}/></span>
                  </span>
                </dd>
              </dl> : <div className="muted">В 1С не найдено</div>}

              <h4 style={{ fontFamily: 'Inter Tight', fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--muted)', marginTop: 22, marginBottom: 10 }}>История</h4>
              <div style={{ fontSize: 12.5, lineHeight: 1.8, color: 'var(--ink-2)' }}>
                <div>17.04.2026 14:23 — автоматическая сверка · <span className="muted">Е. Соколова</span></div>
                <div>02.04.2026 10:12 — документ создан в ЕРП</div>
              </div>
            </div>
            <div className="drawer-foot">
              {drawerRec.erp && <button className="btn" onClick={() => gotoOp(drawerRec.opId)}><IconExternal size={13}/>В операцию</button>}
              {!drawerRec.erp && drawerRec.rc && <button className="btn brand" onClick={() => { setDrawerRec(null); onOpenLink(drawerRec); }}><IconLink size={13}/>Привязать</button>}
              <button className="btn sm ghost" style={{ marginLeft: 'auto' }}>Игнорировать</button>
            </div>
          </aside>
        </>
      )}
    </div>
  );
};

window.ReportScreen = ReportScreen;


/* ===== src/Tweaks.jsx ===== */
// Tweaks panel — conservative vs bold variant
const Tweaks = ({ state, setState }) => {
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const handler = (e) => {
      const t = e.data?.type;
      if (t === '__activate_edit_mode') setVisible(true);
      else if (t === '__deactivate_edit_mode') setVisible(false);
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', handler);
  }, []);

  const persist = (patch) => {
    setState(s => ({ ...s, ...patch }));
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: patch }, '*');
  };

  if (!visible) return null;

  return (
    <div className="tweaks">
      <div className="tweaks-head">
        <IconSettings size={14}/> Tweaks
        <button className="btn ghost xs" style={{ marginLeft: 'auto' }} onClick={() => setVisible(false)}><IconX size={12}/></button>
      </div>
      <div className="tweaks-body">
        <div className="tweak-row">
          <div className="tweak-label">Визуальный вариант</div>
          <div className="tweak-seg">
            <button className={state.variant === 'conservative' ? 'on' : ''} onClick={() => persist({ variant: 'conservative' })}>Консервативный</button>
            <button className={state.variant === 'bold' ? 'on' : ''} onClick={() => persist({ variant: 'bold' })}>Смелый</button>
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>
            {state.variant === 'conservative' ? 'Плотный, бухгалтерский, крупный Inter' : 'Крупнее шрифт, больше воздуха, мягче углы'}
          </div>
        </div>
        <div className="tweak-row">
          <div className="tweak-label">Плотность</div>
          <div className="tweak-seg">
            <button className={state.density === 'compact' ? 'on' : ''} onClick={() => persist({ density: 'compact' })}>Плотно</button>
            <button className={state.density === 'normal' ? 'on' : ''} onClick={() => persist({ density: 'normal' })}>Средне</button>
            <button className={state.density === 'roomy' ? 'on' : ''} onClick={() => persist({ density: 'roomy' })}>Просторно</button>
          </div>
        </div>
        <div className="tweak-row">
          <div className="tweak-label">Линии связи ЕРП↔1С</div>
          <div className="tweak-seg">
            <button className={state.showLinkLines ? 'on' : ''} onClick={() => persist({ showLinkLines: true })}>Показать</button>
            <button className={!state.showLinkLines ? 'on' : ''} onClick={() => persist({ showLinkLines: false })}>Скрыть</button>
          </div>
        </div>
        <div className="tweak-row">
          <div className="tweak-label">Авто-раскрытие расхождений</div>
          <div className="tweak-seg">
            <button className={state.autoExpandIssues ? 'on' : ''} onClick={() => persist({ autoExpandIssues: true })}>Вкл</button>
            <button className={!state.autoExpandIssues ? 'on' : ''} onClick={() => persist({ autoExpandIssues: false })}>Выкл</button>
          </div>
        </div>
      </div>
    </div>
  );
};

window.Tweaks = Tweaks;


/* ===== src/app.jsx ===== */
// Root app — manages screens + modals + tweaks
const SCREEN_KEY = 'akt_sverki_screen_v1';

const App = () => {
  const [screen, setScreen] = React.useState(() => localStorage.getItem(SCREEN_KEY) || 'delivery');
  const [lastReport, setLastReport] = React.useState(null);
  const [showExport, setShowExport] = React.useState(false);
  const [linkingRec, setLinkingRec] = React.useState(null);
  const [toast, setToast] = React.useState(null);
  const [tweakState, setTweakState] = React.useState(window.__TWEAK_DEFAULTS);

  React.useEffect(() => { localStorage.setItem(SCREEN_KEY, screen); }, [screen]);

  // Apply tweaks to body
  React.useEffect(() => {
    document.body.setAttribute('data-variant', tweakState.variant);
    document.body.setAttribute('data-density', tweakState.density);
    document.body.setAttribute('data-show-lines', String(tweakState.showLinkLines));
    window.__tweakState = tweakState;
  }, [tweakState]);

  const goReport = (skipProgress) => {
    if (skipProgress && lastReport) { setScreen('report'); return; }
    setScreen('progress');
  };

  const fireToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  };

  const activeNav = screen === 'delivery' ? 'delivery' : screen === 'progress' || screen === 'report' ? 'recon' : 'other';

  return (
    <>
      <div className="app-root">
        <aside className="sidebar">
          <div className="logo">
            <div className="logo-mark">АС</div>
            <div>
              <div className="logo-name">Акт сверки</div>
              <div className="logo-sub">ЕРП ↔ 1С</div>
            </div>
          </div>
          <nav className="nav-section">
            <div className="nav-title">Работа</div>
            <div className={`nav-item ${activeNav === 'delivery' ? 'active' : ''}`} onClick={() => setScreen('delivery')}>
              <IconBox size={14}/>Поставки<span className="count">12</span>
            </div>
            <div className={`nav-item ${activeNav === 'recon' ? 'active' : ''}`} onClick={() => lastReport ? setScreen('report') : setScreen('delivery')}>
              <IconRefresh size={14}/>Сверки<span className="count">84</span>
            </div>
            <div className="nav-item"><IconChart size={14}/>Аналитика</div>
            <div className="nav-item"><IconDoc size={14}/>Документы</div>
          </nav>
          <nav className="nav-section">
            <div className="nav-title">Справочники</div>
            <div className="nav-item"><IconList size={14}/>Контрагенты</div>
            <div className="nav-item"><IconSettings size={14}/>Интеграция с 1С</div>
          </nav>
          <div style={{ marginTop: 'auto', padding: '10px 8px', fontSize: 11, color: 'var(--muted)', borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'oklch(0.7 0.15 155)' }}/>
              1С: Enterprise 8.3
            </div>
            <div className="mono muted" style={{ fontSize: 10.5, marginTop: 4 }}>sync v2.4 · 14:23</div>
          </div>
        </aside>

        <main className="content">
          <header className="topbar">
            <div className="crumbs">
              <span>Поставки</span>
              <span className="sep">/</span>
              <span>{window.DELIVERY.id}</span>
              {screen !== 'delivery' && <><span className="sep">/</span>
                <span className="current">{screen === 'progress' ? 'Сверка с 1С (в процессе)' : 'Отчёт сверки'}</span></>}
            </div>
            <div className="top-actions">
              <button className="btn ghost sm"><IconBell size={14}/></button>
              <div className="user-chip">
                <span className="avatar">ЕС</span>
                Е. Соколова
              </div>
            </div>
          </header>

          {screen === 'delivery' && (
            <DeliveryCard
              onStart={(jump) => { if (jump === true && lastReport) setScreen('report'); else setScreen('progress'); }}
              lastReport={lastReport}
            />
          )}
          {screen === 'progress' && (
            <ReconcileProgress
              onDone={() => {
                setLastReport({ when: '17.04.2026 14:23', user: 'Е. Соколова' });
                setScreen('report');
                fireToast('Отчёт сформирован и сохранён');
              }}
              onCancel={() => setScreen('delivery')}
            />
          )}
          {screen === 'report' && (
            <ReportScreen
              onBack={() => setScreen('delivery')}
              onOpenExport={() => setShowExport(true)}
              onOpenLink={(rec) => setLinkingRec(rec)}
              onToast={fireToast}
            />
          )}
        </main>
      </div>

      {showExport && <ExportDialog onClose={() => setShowExport(false)} onDone={(msg) => { setShowExport(false); fireToast(msg); }}/>}
      {linkingRec && <LinkPicker rec={linkingRec} onClose={() => setLinkingRec(null)} onDone={(msg) => { setLinkingRec(null); fireToast(msg); }}/>}

      <Tweaks state={tweakState} setState={setTweakState}/>

      {toast && <div className="toast"><IconCheck size={14}/>{toast}</div>}
    </>
  );
};

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
