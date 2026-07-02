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
