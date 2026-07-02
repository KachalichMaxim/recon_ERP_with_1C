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
