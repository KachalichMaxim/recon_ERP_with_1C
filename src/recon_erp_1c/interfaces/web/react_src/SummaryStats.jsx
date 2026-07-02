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
