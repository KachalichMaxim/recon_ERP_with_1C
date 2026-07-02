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
