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
