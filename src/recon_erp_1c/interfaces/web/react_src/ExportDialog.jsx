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
