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
