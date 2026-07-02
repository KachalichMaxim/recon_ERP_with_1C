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
