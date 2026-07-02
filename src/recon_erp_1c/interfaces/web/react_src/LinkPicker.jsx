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
