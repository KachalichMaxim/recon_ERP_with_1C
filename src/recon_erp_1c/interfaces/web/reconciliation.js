(function () {
  'use strict';

  const initialParams = new URLSearchParams(location.search);
  const routeSpecMatch = location.pathname.match(/\/reconciliation\/spec\/(\d+)\/?$/);
  const initialSpecId = Number((routeSpecMatch && routeSpecMatch[1]) || initialParams.get('spec_id') || 0) || null;
  const initialRunId = (initialParams.get('run_id') || '').trim();

  const feedbackReasons = [
    ['', 'Не выбрано'],
    ['mapping_error', 'Ошибка маппинга'],
    ['not_exported_to_1c', 'Не выгружено в 1С'],
    ['manual_1c_document', 'Ручной документ 1С'],
    ['erp_duplicate', 'Дубль ERP'],
    ['business_exception', 'Бизнес-исключение'],
    ['new_case', 'Новый кейс для развития'],
  ];

  const steps = [
    ['erp_context', 'Читаем контекст поставки из ERP'],
    ['erp_docs', 'Собираем документы ERP'],
    ['onec', 'Запрашиваем документы 1С'],
    ['match', 'Сопоставляем по кодам 1С'],
    ['log', 'Пишем журнал сверки'],
  ];

  const state = {
    token: localStorage.getItem('recon_session') || '',
    profile: JSON.parse(localStorage.getItem('recon_profile') || 'null'),
    view: initialSpecId ? 'recon' : (localStorage.getItem('recon_view') || 'matrix'),
    matrix: [],
    matrixPayload: null,
    matrixMode: '',
    matrixOffset: 0,
    matrixDetailsOpen: localStorage.getItem('recon_matrix_details_open') === '1',
    matrixExpanded: JSON.parse(localStorage.getItem('recon_matrix_expanded_v1') || '{}'),
    sidebarCollapsed: localStorage.getItem('recon_sidebar_collapsed') === '1',
    selectedSpecId: initialSpecId || Number(localStorage.getItem('recon_selected_spec') || 0) || null,
    run: null,
    feedback: JSON.parse(localStorage.getItem('recon_feedback_v1') || '{}'),
    config: null,
  };

  const $ = (id) => document.getElementById(id);
  const els = {
    loginPanel: $('loginPanel'),
    workArea: $('workArea'),
    loginInput: $('loginInput'),
    passwordInput: $('passwordInput'),
    loginBtn: $('loginBtn'),
    loginHint: $('loginHint'),
    loginForm: $('loginForm'),
    loginFootnote: $('loginFootnote'),
    loginMessage: $('loginMessage'),
    userName: $('userName'),
    userLogin: $('userLogin'),
    userAvatar: $('userAvatar'),
    logoutBtn: $('logoutBtn'),
    navMatrixBtn: $('navMatrixBtn'),
    navReconBtn: $('navReconBtn'),
    matrixScreen: $('matrixScreen'),
    reconScreen: $('reconScreen'),
    erpStatusChip: $('erpStatusChip'),
    onecStatusChip: $('onecStatusChip'),
    modeStatusChip: $('modeStatusChip'),
    sidebarToggleBtn: $('sidebarToggleBtn'),
    refreshBtn: $('refreshBtn'),
    clientIdInput: $('clientIdInput'),
    clientSuggestions: $('clientSuggestions'),
    dogIdInput: $('dogIdInput'),
    dogSuggestions: $('dogSuggestions'),
    deliveryInput: $('deliveryInput'),
    deliverySuggestions: $('deliverySuggestions'),
    clientHandoverFromInput: $('clientHandoverFromInput'),
    clientHandoverToInput: $('clientHandoverToInput'),
    limitInput: $('limitInput'),
    matrixStatusFilter: $('matrixStatusFilter'),
    loadMatrixBtn: $('loadMatrixBtn'),
    resetFiltersBtn: $('resetFiltersBtn'),
    matrixMessage: $('matrixMessage'),
    matrixHint: $('matrixHint'),
    matrixRows: $('matrixRows'),
    matrixSummaryCards: $('matrixSummaryCards'),
    matrixSelectionPanel: $('matrixSelectionPanel'),
    matrixSelectionText: $('matrixSelectionText'),
    matrixSelectionReconBtn: $('matrixSelectionReconBtn'),
    matrixSelectionDetailsBtn: $('matrixSelectionDetailsBtn'),
    matrixSelectionExportBtn: $('matrixSelectionExportBtn'),
    matrixExportBtn: $('matrixExportBtn'),
    matrixExportAllBtn: $('matrixExportAllBtn'),
    matrixPagerText: $('matrixPagerText'),
    matrixPrevBtn: $('matrixPrevBtn'),
    matrixNextBtn: $('matrixNextBtn'),
    matrixToReconBtn: $('matrixToReconBtn'),
    selectedContext: $('selectedContext'),
    coveragePanel: $('coveragePanel'),
    coverageRetrievedAt: $('coverageRetrievedAt'),
    coveragePeriod: $('coveragePeriod'),
    coverageContracts: $('coverageContracts'),
    coverageCounts: $('coverageCounts'),
    coverageCompleteness: $('coverageCompleteness'),
    coverageWarnings: $('coverageWarnings'),
    loadingOverlay: $('loadingOverlay'),
    loadingStepText: $('loadingStepText'),
    runBtn: $('runBtn'),
    exportBtn: $('exportBtn'),
    progressBox: $('progressBox'),
    runMessage: $('runMessage'),
    balanceCompare: $('balanceCompare'),
    balanceErp: $('balanceErp'),
    balanceOnecDirect: $('balanceOnecDirect'),
    balanceOnecAdjustment: $('balanceOnecAdjustment'),
    balanceOnec: $('balanceOnec'),
    balanceDifference: $('balanceDifference'),
    balanceStatus: $('balanceStatus'),
    balanceExplanation: $('balanceExplanation'),
    summaryCards: $('summaryCards'),
    resultSearchInput: $('resultSearchInput'),
    statusFilter: $('statusFilter'),
    resultRows: $('resultRows'),
  };

  let clientSearchTimer = 0;
  let dogSearchTimer = 0;
  let deliverySearchTimer = 0;

  function api(path, options = {}) {
    const headers = Object.assign({ Accept: 'application/json' }, options.headers || {});
    if (state.token) headers['X-Recon-Session'] = state.token;
    return fetch(path, Object.assign({}, options, { headers }));
  }

  function setMessage(node, text, isError) {
    if (!node) return;
    node.textContent = text || '';
    node.classList.toggle('error', Boolean(isError));
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtMoneyValue(value, currency = 'RUB') {
    const amount = Number(value || 0);
    if (!Number.isFinite(amount)) return '—';
    return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount) + ' ' + currency;
  }

  function fmtDocMoney(doc) {
    const amount = doc && doc.amount ? doc.amount.amount : 0;
    const currency = doc && doc.amount ? doc.amount.currency || 'RUB' : 'RUB';
    return fmtMoneyValue(amount, currency);
  }

  function fmtDate(value) {
    if (!value) return '—';
    const text = String(value);
    if (/^\d{4}-\d{2}-\d{2}/.test(text)) return `${text.slice(8, 10)}.${text.slice(5, 7)}.${text.slice(0, 4)}`;
    return text;
  }

  function normalizeErrorMessage(err) {
    const text = err && err.message ? err.message : String(err || '');
    if (/ERP MariaDB is not configured/i.test(text)) {
      return 'ERP сейчас недоступна. Проверьте подключение сервиса сверки к ERP.';
    }
    if (/ERP temporarily unavailable|service_unavailable|Name or service not known/i.test(text)) {
      return 'ERP временно недоступна или не отвечает. Повторите запрос через несколько секунд.';
    }
    if (/Direct ERP login is disabled/i.test(text)) return 'Вход по логину и паролю отключен. Откройте модуль из ERP.';
    if (/ERP launch token validation endpoint is not configured/i.test(text)) return 'Не настроена проверка launch token ERP.';
    if (/Invalid ERP login or password/i.test(text)) return 'Неверный логин или пароль ERP.';
    return text.replace(/1C/g, '1С');
  }

  function setView(view) {
    state.view = view;
    localStorage.setItem('recon_view', view);
    const isMatrix = view === 'matrix';
    els.matrixScreen.classList.toggle('hidden', !isMatrix);
    els.reconScreen.classList.toggle('hidden', isMatrix);
    els.navMatrixBtn.classList.toggle('active', isMatrix);
    els.navReconBtn.classList.toggle('active', !isMatrix);
    updateWorkflowState();
    updateActionState();
    if (state.selectedSpecId && location.pathname.startsWith('/reconciliation/spec/')) syncBrowserUrl();
  }

  function syncBrowserUrl(runId = '') {
    if (!state.selectedSpecId) {
      history.replaceState({}, document.title, '/reconciliation.html');
      return;
    }
    const params = new URLSearchParams();
    params.set('view', state.view);
    if (runId || (state.run && state.run.run_id)) params.set('run_id', runId || state.run.run_id);
    const next = `/reconciliation/spec/${state.selectedSpecId}?${params.toString()}`;
    history.replaceState({}, document.title, next);
  }

  function updateWorkflowState() {
    const hasMatrix = Boolean(state.matrix.length);
    const hasSpec = Boolean(state.selectedSpecId);
    const hasRun = Boolean(state.run);
    document.querySelectorAll('[data-workflow-step]').forEach((node) => {
      const step = node.getAttribute('data-workflow-step');
      const active = (state.view === 'matrix' && !hasMatrix && step === 'matrix')
        || (state.view === 'matrix' && hasMatrix && step === 'select')
        || (state.view === 'recon' && !hasRun && step === 'recon')
        || (state.view === 'recon' && hasRun && step === 'review');
      const done = (step === 'matrix' && hasMatrix)
        || (step === 'select' && hasSpec)
        || (step === 'recon' && hasRun);
      node.classList.toggle('active', active);
      node.classList.toggle('done', done);
    });
  }

  function openReconGuarded() {
    if (!state.matrix.length) {
      setView('matrix');
      setMessage(els.matrixMessage, 'Сначала загрузите поставки.', true);
      focusMatrixWorkflow();
      return false;
    }
    if (!state.selectedSpecId) {
      setView('matrix');
      setMessage(els.matrixMessage, 'Отметьте кружок ○ в колонке “Выбор”, чтобы сверить поставку с 1С.', true);
      highlightMatrixSelection();
      return false;
    }
    setMessage(els.matrixMessage, '');
    setView('recon');
    return true;
  }

  function focusMatrixWorkflow() {
    const target = els.matrixRows.closest('.table-wrap') || els.loadMatrixBtn;
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function highlightMatrixSelection() {
    focusMatrixWorkflow();
    const table = els.matrixRows.closest('.table-wrap');
    if (!table) return;
    table.classList.add('selection-required');
    setTimeout(() => table.classList.remove('selection-required'), 1600);
  }

  function applyAuthState() {
    const logged = Boolean(state.token);
    els.loginPanel.classList.toggle('hidden', logged);
    els.workArea.classList.toggle('hidden', !logged);
    const name = state.profile && state.profile.name ? state.profile.name : 'Не авторизован';
    const login = state.profile && state.profile.login ? state.profile.login : '—';
    els.userName.textContent = name;
    els.userLogin.textContent = login;
    els.userAvatar.textContent = name && name !== 'Не авторизован' ? name.slice(0, 1).toUpperCase() : '?';
  }

  async function loadRuntimeConfig() {
    try {
      const resp = await fetch('/api/config/status', { headers: { Accept: 'application/json' } });
      const payload = await resp.json();
      if (resp.ok && payload.ok) state.config = payload;
    } catch (_) {
      state.config = null;
    }
    applyRuntimeConfig();
  }

  function applyRuntimeConfig() {
    const auth = state.config && state.config.auth ? state.config.auth : {};
    const demo = Boolean(auth.demo);
    const directLogin = Boolean(auth.direct_login_enabled);
    if (els.loginFootnote) els.loginFootnote.classList.toggle('hidden', !demo);
    if (els.loginForm) els.loginForm.classList.toggle('hidden', !directLogin);
    if (els.loginHint) {
      els.loginHint.textContent = directLogin
        ? 'Войдите с логином и паролем ERP.'
        : 'Откройте модуль из ERP. Вход выполняется по токену пользователя.';
    }
    if (!state.token && !directLogin) {
      setMessage(els.loginMessage, 'Откройте модуль из ERP. Доступ выполняется по launch token пользователя.');
    }
    if (state.config && state.config.erp_db) {
      els.erpStatusChip.textContent = state.config.erp_db.configured ? 'ERP: подключена' : 'ERP: не подключена';
    }
    if (state.config && state.config.onec_rest) {
      els.onecStatusChip.textContent = state.config.onec_rest.configured ? '1С: подключена' : '1С: не подключена';
    }
    if (auth.required) {
      els.modeStatusChip.textContent = 'Режим: вход из ERP';
    }
  }

  async function consumeLaunchToken() {
    const params = new URLSearchParams(location.search);
    const launchToken = params.get('launch_token') || params.get('token') || '';
    if (!launchToken) return;
    setMessage(els.loginMessage, 'Проверяем launch token ERP...');
    try {
      const resp = await fetch('/api/auth/erp-launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ launch_token: launchToken }),
      });
      const payload = await resp.json();
      if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Ошибка входа через ERP');
      state.token = payload.token;
      state.profile = payload.profile;
      localStorage.setItem('recon_session', state.token);
      localStorage.setItem('recon_profile', JSON.stringify(state.profile));
      params.delete('launch_token');
      params.delete('token');
      const next = `${location.pathname}${params.toString() ? '?' + params.toString() : ''}${location.hash || ''}`;
      history.replaceState({}, document.title, next);
      setMessage(els.loginMessage, '');
    } catch (err) {
      setMessage(els.loginMessage, normalizeErrorMessage(err), true);
    }
  }

  async function validateSession() {
    if (!state.token) return;
    try {
      const resp = await api('/api/auth/me');
      if (!resp.ok) throw new Error('session expired');
      const payload = await resp.json();
      if (payload.profile) {
        state.profile = payload.profile;
        localStorage.setItem('recon_profile', JSON.stringify(state.profile));
      }
    } catch (_) {
      logout(false);
    }
    applyAuthState();
  }

  async function login() {
    const auth = state.config && state.config.auth ? state.config.auth : {};
    if (!auth.direct_login_enabled) {
      setMessage(els.loginMessage, 'Вход по логину и паролю отключен. Откройте модуль из ERP.', true);
      return;
    }
    const loginValue = els.loginInput.value.trim();
    const password = els.passwordInput.value;
    setMessage(els.loginMessage, 'Проверяем логин в ERP...');
    try {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ login: loginValue, password }),
      });
      const payload = await resp.json();
      if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Ошибка входа');
      state.token = payload.token;
      state.profile = payload.profile;
      localStorage.setItem('recon_session', state.token);
      localStorage.setItem('recon_profile', JSON.stringify(state.profile));
      setMessage(els.loginMessage, '');
      applyAuthState();
      if (initialSpecId) {
        state.selectedSpecId = initialSpecId;
        els.deliveryInput.value = String(initialSpecId);
        els.deliveryInput.dataset.specId = String(initialSpecId);
        await loadMatrix(0);
        if (initialRunId) await loadStoredRun(initialRunId);
        setView(state.selectedSpecId ? 'recon' : 'matrix');
      } else {
        setView('matrix');
      }
    } catch (err) {
      setMessage(els.loginMessage, normalizeErrorMessage(err), true);
    }
  }

  function logout(resetMessage = true) {
    state.token = '';
    state.profile = null;
    state.matrix = [];
    state.selectedSpecId = null;
    state.run = null;
    localStorage.removeItem('recon_session');
    localStorage.removeItem('recon_profile');
    localStorage.removeItem('recon_selected_spec');
    applyAuthState();
    renderMatrix();
    renderSelectedContext();
    renderResults();
    if (resetMessage) setMessage(els.loginMessage, '');
  }

  function queryParams() {
    const params = new URLSearchParams();
    const clientId = selectedClientId();
    const dogId = selectedDogId();
    const specId = selectedDeliveryId();
    [
      ['client_id', clientId],
      ['dog_id', dogId],
      ['spec_id', specId],
      ['client_handover_from', els.clientHandoverFromInput.value],
      ['client_handover_to', els.clientHandoverToInput.value],
      ['limit', els.limitInput.value || '50'],
      ['offset', String(state.matrixOffset || 0)],
    ].forEach(([key, value]) => {
      if (String(value || '').trim()) params.set(key, value);
    });
    return params;
  }

  function selectedClientId() {
    const explicit = els.clientIdInput.dataset.clientId || '';
    if (explicit) return explicit;
    const text = (els.clientIdInput.value || '').trim();
    return /^\d+$/.test(text) ? text : '';
  }

  function selectedDogId() {
    const explicit = els.dogIdInput.dataset.dogId || '';
    if (explicit) return explicit;
    const text = (els.dogIdInput.value || '').trim();
    return /^\d+$/.test(text) ? text : '';
  }

  function selectedDeliveryId() {
    const explicit = els.deliveryInput.dataset.specId || '';
    if (explicit) return explicit;
    const text = (els.deliveryInput.value || '').trim();
    return /^\d+$/.test(text) ? text : '';
  }

  async function loadMatrix(offset) {
    if (!validateClientFilter(els.matrixMessage)) return;
    if (!validateDogFilter(els.matrixMessage)) return;
    if (!validateDeliveryFilter(els.matrixMessage)) return;
    state.matrixOffset = Math.max(0, Number(offset == null ? state.matrixOffset : offset) || 0);
    els.loadMatrixBtn.disabled = true;
    els.matrixRows.innerHTML = '<tr><td colspan="11" class="empty-cell">Загружаем ERP-матрицу...</td></tr>';
    setMessage(els.matrixMessage, 'Получаем поставки и агрегаты из ERP...');
    try {
      const resp = await api('/api/reconciliation/matrix?' + queryParams().toString());
      const payload = await resp.json();
      if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Не удалось получить матрицу');
      state.matrix = payload.items || [];
      state.matrixPayload = payload;
      state.matrixMode = payload.mode || 'erp_live';
      state.matrixOffset = Number(payload.offset || state.matrixOffset || 0);
      if (!state.matrix.some((row) => Number(row.spec_id) === Number(state.selectedSpecId))) {
        state.run = null;
        if (state.matrix.length === 1) {
          state.selectedSpecId = Number(state.matrix[0].spec_id);
          localStorage.setItem('recon_selected_spec', String(state.selectedSpecId));
        } else {
          state.selectedSpecId = null;
          localStorage.removeItem('recon_selected_spec');
        }
        state.matrixDetailsOpen = false;
        localStorage.setItem('recon_matrix_details_open', '0');
      }
      const selectionHidden = clearSelectionIfHiddenByFilter();
      const visibleItems = matrixVisibleItems();
      renderMatrix(matrixKpiSummary());
      renderSelectedContext();
      renderResults();
      updateActionState();
      const modeText = state.matrixMode === 'ui_demo' ? 'Локальный UI-пример, не боевые данные.' : 'Данные ERP загружены.';
      const totalCount = Number(payload.total_count || 0);
      const totalText = totalCount && totalCount !== state.matrix.length ? ` Всего найдено: ${totalCount}.` : '';
      const summaryText = payload.total_summary ? ' Итоги сверху рассчитаны по всему фильтру.' : '';
      const selectionText = state.matrix.length === 1 && state.selectedSpecId
        ? ' Найдена одна поставка — она выбрана автоматически.'
        : selectionHidden
          ? ' Выбранная ранее поставка скрыта текущим фильтром.'
          : '';
      setMessage(els.matrixMessage, `${modeText} Показано: ${visibleItems.length} из ${state.matrix.length}.${totalText}${summaryText}${selectionText}`);
      updateMatrixPager();
      els.erpStatusChip.textContent = state.matrixMode === 'ui_demo' ? 'ERP: демо-данные' : 'ERP: данные загружены';
    } catch (err) {
      state.matrix = [];
      renderMatrix();
      setMessage(els.matrixMessage, normalizeErrorMessage(err), true);
      els.erpStatusChip.textContent = 'ERP: ошибка';
    } finally {
      els.loadMatrixBtn.disabled = false;
    }
  }

  function scheduleClientSearch() {
    const text = (els.clientIdInput.value || '').trim();
    if (els.clientIdInput.dataset.clientLabel && text !== els.clientIdInput.dataset.clientLabel) {
      delete els.clientIdInput.dataset.clientId;
      delete els.clientIdInput.dataset.clientLabel;
    }
    clearTimeout(clientSearchTimer);
    if (text.length < 3) {
      renderClientSuggestions([]);
      return;
    }
    clientSearchTimer = setTimeout(() => searchClients(text), 250);
  }

  async function searchClients(text) {
    try {
      const params = new URLSearchParams({ q: text, limit: '12' });
      const resp = await api('/api/reconciliation/clients?' + params.toString());
      const payload = await resp.json();
      if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Не удалось найти клиентов');
      renderClientSuggestions(payload.items || [], text);
    } catch (err) {
      els.clientSuggestions.innerHTML = `<div class="suggestion-empty">${escapeHtml(normalizeErrorMessage(err))}</div>`;
      els.clientSuggestions.classList.remove('hidden');
    }
  }

  function renderClientSuggestions(items, searchText = '') {
    if (!searchText || searchText.length < 3) {
      els.clientSuggestions.classList.add('hidden');
      els.clientSuggestions.innerHTML = '';
      return;
    }
    if (!items.length) {
      els.clientSuggestions.innerHTML = '<div class="suggestion-empty">Клиенты не найдены.</div>';
      els.clientSuggestions.classList.remove('hidden');
      return;
    }
    els.clientSuggestions.innerHTML = items.map((item) => {
      const label = clientLabel(item);
      return `<button class="suggestion-item" type="button" data-client-id="${escapeHtml(item.client_id)}" data-client-label="${escapeHtml(label)}">
        <span class="suggestion-title">${escapeHtml(item.client_name || 'Без названия')}</span>
        <span class="suggestion-meta">ИНН ${escapeHtml(item.client_inn || '—')}</span>
      </button>`;
    }).join('');
    els.clientSuggestions.classList.remove('hidden');
    els.clientSuggestions.querySelectorAll('[data-client-id]').forEach((node) => {
      node.addEventListener('click', () => selectClientSuggestion(node));
    });
  }

  function clientLabel(item) {
    const name = item.client_name || `Клиент ${item.client_id || ''}`;
    const inn = item.client_inn ? ` · ИНН ${item.client_inn}` : '';
    return `${name}${inn}`;
  }

  function selectClientSuggestion(node) {
    const id = node.getAttribute('data-client-id') || '';
    const label = node.getAttribute('data-client-label') || id;
    els.clientIdInput.value = label;
    els.clientIdInput.dataset.clientId = id;
    els.clientIdInput.dataset.clientLabel = label;
    els.clientSuggestions.classList.add('hidden');
    els.clientSuggestions.innerHTML = '';
    clearDogFilter();
    clearDeliveryFilter();
  }

  function scheduleDogSearch() {
    const text = (els.dogIdInput.value || '').trim();
    if (els.dogIdInput.dataset.dogLabel && text !== els.dogIdInput.dataset.dogLabel) {
      delete els.dogIdInput.dataset.dogId;
      delete els.dogIdInput.dataset.dogLabel;
    }
    clearTimeout(dogSearchTimer);
    if (text.length < 2) {
      renderDogSuggestions([]);
      return;
    }
    dogSearchTimer = setTimeout(() => searchContracts(text), 250);
  }

  async function searchContracts(text) {
    try {
      const params = new URLSearchParams({ q: text, limit: '12' });
      const clientId = selectedClientId();
      if (clientId) params.set('client_id', clientId);
      const resp = await api('/api/reconciliation/contracts?' + params.toString());
      const payload = await resp.json();
      if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Не удалось найти договоры');
      renderDogSuggestions(payload.items || [], text);
    } catch (err) {
      els.dogSuggestions.innerHTML = `<div class="suggestion-empty">${escapeHtml(normalizeErrorMessage(err))}</div>`;
      els.dogSuggestions.classList.remove('hidden');
    }
  }

  function renderDogSuggestions(items, searchText = '') {
    if (!searchText || searchText.length < 2) {
      els.dogSuggestions.classList.add('hidden');
      els.dogSuggestions.innerHTML = '';
      return;
    }
    if (!items.length) {
      els.dogSuggestions.innerHTML = '<div class="suggestion-empty">Договоры не найдены.</div>';
      els.dogSuggestions.classList.remove('hidden');
      return;
    }
    els.dogSuggestions.innerHTML = items.map((item) => {
      const label = dogLabel(item);
      return `<button class="suggestion-item" type="button" data-dog-id="${escapeHtml(item.dog_id)}" data-dog-label="${escapeHtml(label)}">
        <span class="suggestion-title">${escapeHtml(item.contract_number || `Договор ${item.dog_id || ''}`)}</span>
        <span class="suggestion-meta">код 1С ${escapeHtml(item.contract_code1c || '—')} · ${escapeHtml(item.client_name || '')}</span>
      </button>`;
    }).join('');
    els.dogSuggestions.classList.remove('hidden');
    els.dogSuggestions.querySelectorAll('[data-dog-id]').forEach((node) => {
      node.addEventListener('click', () => selectDogSuggestion(node));
    });
  }

  function dogLabel(item) {
    const name = item.contract_number || `Договор ${item.dog_id || ''}`;
    const code = item.contract_code1c ? ` · 1С ${item.contract_code1c}` : '';
    return `${name}${code}`;
  }

  function selectDogSuggestion(node) {
    const id = node.getAttribute('data-dog-id') || '';
    const label = node.getAttribute('data-dog-label') || id;
    els.dogIdInput.value = label;
    els.dogIdInput.dataset.dogId = id;
    els.dogIdInput.dataset.dogLabel = label;
    els.dogSuggestions.classList.add('hidden');
    els.dogSuggestions.innerHTML = '';
    clearDeliveryFilter();
  }

  function clearDogFilter() {
    els.dogIdInput.value = '';
    delete els.dogIdInput.dataset.dogId;
    delete els.dogIdInput.dataset.dogLabel;
    renderDogSuggestions([]);
  }

  function clearDeliveryFilter() {
    els.deliveryInput.value = '';
    delete els.deliveryInput.dataset.specId;
    delete els.deliveryInput.dataset.deliveryLabel;
    renderDeliverySuggestions([]);
  }

  function scheduleDeliverySearch() {
    const text = (els.deliveryInput.value || '').trim();
    if (els.deliveryInput.dataset.deliveryLabel && text !== els.deliveryInput.dataset.deliveryLabel) {
      delete els.deliveryInput.dataset.specId;
      delete els.deliveryInput.dataset.deliveryLabel;
    }
    clearTimeout(deliverySearchTimer);
    const minLength = /^\d+$/.test(text) ? 1 : 3;
    if (text.length < minLength) {
      renderDeliverySuggestions([]);
      return;
    }
    deliverySearchTimer = setTimeout(() => searchDeliveries(text), 250);
  }

  async function searchDeliveries(text) {
    try {
      const params = new URLSearchParams({ q: text, limit: '12' });
      const clientId = selectedClientId();
      const dogId = selectedDogId();
      if (clientId) params.set('client_id', clientId);
      if (dogId) params.set('dog_id', dogId);
      if (els.clientHandoverFromInput.value) params.set('client_handover_from', els.clientHandoverFromInput.value);
      if (els.clientHandoverToInput.value) params.set('client_handover_to', els.clientHandoverToInput.value);
      const resp = await api('/api/reconciliation/deliveries?' + params.toString());
      const payload = await resp.json();
      if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Не удалось найти поставки');
      renderDeliverySuggestions(payload.items || [], text);
    } catch (err) {
      els.deliverySuggestions.innerHTML = `<div class="suggestion-empty">${escapeHtml(normalizeErrorMessage(err))}</div>`;
      els.deliverySuggestions.classList.remove('hidden');
    }
  }

  function renderDeliverySuggestions(items, searchText = '') {
    const minLength = /^\d+$/.test(searchText) ? 1 : 3;
    if (!searchText || searchText.length < minLength) {
      els.deliverySuggestions.classList.add('hidden');
      els.deliverySuggestions.innerHTML = '';
      return;
    }
    if (!items.length) {
      els.deliverySuggestions.innerHTML = '<div class="suggestion-empty">Поставки не найдены.</div>';
      els.deliverySuggestions.classList.remove('hidden');
      return;
    }
    els.deliverySuggestions.innerHTML = items.map((item) => {
      const label = item.delivery_full_name || deliveryLabel(item);
      const type = item.spec_type_name || 'Поставка';
      return `<button class="suggestion-item" type="button" data-spec-id="${escapeHtml(item.spec_id)}" data-delivery-label="${escapeHtml(label)}">
        <span class="suggestion-title">${escapeHtml(label)}</span>
        <span class="suggestion-meta">${escapeHtml(type)} №${escapeHtml(item.spec_number || '—')} · ${escapeHtml(fmtDate(item.spec_date))}${item.client_handover_date ? ` · передано ${escapeHtml(fmtDate(item.client_handover_date))}` : ''} · ID ${escapeHtml(item.spec_id || '—')}</span>
      </button>`;
    }).join('');
    els.deliverySuggestions.classList.remove('hidden');
    els.deliverySuggestions.querySelectorAll('[data-spec-id]').forEach((node) => {
      node.addEventListener('click', () => selectDeliverySuggestion(node));
    });
  }

  function selectDeliverySuggestion(node) {
    const specId = node.getAttribute('data-spec-id') || '';
    const label = node.getAttribute('data-delivery-label') || specId;
    els.deliveryInput.value = label;
    els.deliveryInput.dataset.specId = specId;
    els.deliveryInput.dataset.deliveryLabel = label;
    els.deliverySuggestions.classList.add('hidden');
    els.deliverySuggestions.innerHTML = '';
  }

  function buildMatrixSummary(items) {
    const balance = sumField(items, 'balance');
    return {
      deliveries: items.length,
      invoice_sum: sumField(items, 'invoice_sum'),
      payment_sum: sumField(items, 'payment_sum'),
      reimbursable_sum: sumField(items, 'reimbursable_sum'),
      non_reimbursable_sum: sumField(items, 'non_reimbursable_sum'),
      balance,
      debts: items.filter((row) => balanceKind(row) === 'debt').length,
      overpayments: items.filter((row) => balanceKind(row) === 'overpayment').length,
    };
  }

  function matrixKpiSummary() {
    const payload = state.matrixPayload || {};
    return payload.total_summary || payload.summary || buildMatrixSummary(matrixVisibleItems());
  }

  function sumField(items, field) {
    return items.reduce((sum, row) => sum + Number(row[field] || 0), 0).toFixed(2);
  }

  function aggregateItems(items) {
    return {
      invoice_sum: sumField(items, 'invoice_sum'),
      payment_sum: sumField(items, 'payment_sum'),
      reimbursable_sum: sumField(items, 'reimbursable_sum'),
      non_reimbursable_sum: sumField(items, 'non_reimbursable_sum'),
      balance: sumField(items, 'balance'),
    };
  }

  function unique(values) {
    return [...new Set(values.filter(Boolean))];
  }

  function renderMatrix(summary) {
    const items = matrixVisibleItems();
    renderMatrixSummary(summary || matrixKpiSummary());
    renderMatrixSelectionPanel();
    if (!items.length) {
      els.matrixRows.innerHTML = '<tr><td colspan="11" class="empty-cell">Поставки не загружены или не подходят под выбранный фильтр.</td></tr>';
      updateMatrixPager();
      return;
    }
    const byClient = groupBy(items, (row) => `${row.main_client_id || row.client_id || 0}|${row.main_client_name || row.client_name || ''}`);
    const html = [];
    for (const [clientGroupKey, clientItems] of byClient.entries()) {
      const client = clientItems[0];
      const clientKey = `client:${clientGroupKey}`;
      const clientOpen = isMatrixExpanded(clientKey);
      html.push(matrixRowHtml({
        level: 0,
        label: `Клиент: ${client.main_client_name || client.client_name || '—'}`,
        subtext: `${unique(clientItems.map((row) => row.client_id)).length} ЮЛ`,
        aggregate: aggregateItems(clientItems),
        specText: `${clientItems.length} поставок`,
        toggleKey: clientKey,
        expanded: clientOpen,
      }));
      if (!clientOpen) continue;
      const byLegal = groupBy(clientItems, (row) => `${row.client_id || 0}|${row.client_name || ''}`);
      for (const [legalGroupKey, legalItems] of byLegal.entries()) {
        const legal = legalItems[0];
        const legalKey = `${clientKey}:legal:${legalGroupKey}`;
        const legalOpen = isMatrixExpanded(legalKey);
        html.push(matrixRowHtml({
          level: 1,
          label: `ЮЛ: ${legal.client_name || '—'}`,
          subtext: `ИНН ${legal.client_inn || '—'}`,
          aggregate: aggregateItems(legalItems),
          specText: `${legalItems.length} поставок`,
          toggleKey: legalKey,
          expanded: legalOpen,
        }));
        if (!legalOpen) continue;
        const byDog = groupBy(legalItems, (row) => `${row.dog_id || 0}|${row.base_contract_number || ''}`);
        for (const [dogGroupKey, dogItems] of byDog.entries()) {
          const dog = dogItems[0];
          const dogKey = `${legalKey}:contract:${dogGroupKey}`;
          const dogOpen = isMatrixExpanded(dogKey);
          html.push(matrixRowHtml({
            level: 2,
            label: `Договор: ${dog.base_contract_number || '—'}`,
            subtext: 'Основной договор поставки',
            aggregate: aggregateItems(dogItems),
            specText: `${dogItems.length} поставок`,
            toggleKey: dogKey,
            expanded: dogOpen,
          }));
          if (!dogOpen) continue;
          for (const row of dogItems) {
            html.push(matrixRowHtml({
              level: 3,
              label: deliveryLabel(row),
              subtext: [row.delivery_full_name, fmtDate(row.spec_date), row.client_handover_date ? `передано ${fmtDate(row.client_handover_date)}` : ''].filter(Boolean).join(' · '),
              aggregate: row,
              specText: row.spec_number || '—',
              specId: row.spec_id,
              erpUrl: row.erp_url,
            }));
            if (Number(row.spec_id) === Number(state.selectedSpecId) && state.matrixDetailsOpen) {
              html.push(matrixSpecDetailsHtml(row));
            }
          }
        }
      }
    }
    els.matrixRows.innerHTML = html.join('');
    els.matrixRows.querySelectorAll('tr[data-toggle-key]').forEach((tr) => {
      const toggle = () => {
        const key = tr.getAttribute('data-toggle-key') || '';
        state.matrixExpanded[key] = !isMatrixExpanded(key);
        localStorage.setItem('recon_matrix_expanded_v1', JSON.stringify(state.matrixExpanded));
        renderMatrix(matrixKpiSummary());
      };
      tr.addEventListener('click', toggle);
      tr.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          toggle();
        }
      });
    });
    els.matrixRows.querySelectorAll('tr[data-spec-id]').forEach((tr) => {
      tr.addEventListener('click', () => {
        selectSpec(Number(tr.getAttribute('data-spec-id')));
      });
    });
    els.matrixRows.querySelectorAll('[data-select-spec-id]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        selectSpec(Number(button.getAttribute('data-select-spec-id')));
      });
    });
    updateMatrixPager();
  }

  function selectSpec(specId) {
    if (!specId) return;
    state.selectedSpecId = Number(specId);
    localStorage.setItem('recon_selected_spec', String(state.selectedSpecId));
    state.matrixDetailsOpen = false;
    localStorage.setItem('recon_matrix_details_open', '0');
    state.run = null;
    setMessage(els.matrixMessage, 'Поставка выбрана. Можно сверить ее с 1С или скачать поставку XLSX.');
    renderMatrix(matrixKpiSummary());
    renderSelectedContext();
    renderResults();
    updateActionState();
    updateWorkflowState();
    syncBrowserUrl();
  }

  function updateMatrixPager() {
    const payload = state.matrixPayload || {};
    const limit = Number(payload.limit || els.limitInput.value || 50);
    const offset = Number(payload.offset || state.matrixOffset || 0);
    const count = Number(payload.count || state.matrix.length || 0);
    const total = Number(payload.total_count || count || 0);
    const from = count ? offset + 1 : 0;
    const to = offset + count;
    if (els.matrixPagerText) {
      els.matrixPagerText.textContent = total ? `Показано ${from}-${to} из ${total}` : 'Поставки не загружены';
    }
    if (els.matrixPrevBtn) els.matrixPrevBtn.disabled = offset <= 0;
    if (els.matrixNextBtn) els.matrixNextBtn.disabled = !payload.has_more || count <= 0 || limit <= 0;
  }

  function matrixPage(delta) {
    const payload = state.matrixPayload || {};
    const limit = Number(payload.limit || els.limitInput.value || 50);
    const currentOffset = Number(payload.offset || state.matrixOffset || 0);
    loadMatrix(Math.max(0, currentOffset + delta * limit));
  }

  function matrixVisibleItems() {
    const items = state.matrix || [];
    const filter = els.matrixStatusFilter ? els.matrixStatusFilter.value || 'all' : 'all';
    if (filter === 'all') return items;
    if (filter === 'problems') return items.filter((row) => balanceKind(row) !== 'closed');
    return items.filter((row) => balanceKind(row) === filter);
  }

  function clearSelectionIfHiddenByFilter() {
    if (!state.selectedSpecId) return false;
    const visible = matrixVisibleItems().some((row) => Number(row.spec_id) === Number(state.selectedSpecId));
    if (visible) return false;
    state.selectedSpecId = null;
    state.run = null;
    state.matrixDetailsOpen = false;
    localStorage.removeItem('recon_selected_spec');
    localStorage.setItem('recon_matrix_details_open', '0');
    return true;
  }

  function balanceKind(row) {
    const balance = Number(row.balance || 0);
    return row.balance_kind || (balance > 0 ? 'overpayment' : balance < 0 ? 'debt' : 'closed');
  }

  function isMatrixExpanded(key) {
    return state.matrixExpanded[key] !== false;
  }

  function groupBy(items, getKey) {
    const map = new Map();
    for (const item of items) {
      const key = getKey(item);
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(item);
    }
    return map;
  }

  function matrixRowHtml({ level, label, subtext, aggregate, specText, specId, toggleKey, expanded, erpUrl }) {
    const balance = Number(aggregate.balance || 0);
    const kind = aggregate.balance_kind || (balance > 0 ? 'overpayment' : balance < 0 ? 'debt' : 'closed');
    const status = aggregate.balance_label || (balance > 0 ? 'Переплата' : balance < 0 ? 'Долг' : 'Закрыто');
    const selected = specId && Number(specId) === Number(state.selectedSpecId);
    const rowClass = specId ? `matrix-spec ${selected ? 'selected' : ''}` : 'matrix-aggregate matrix-toggle-row';
    const invoiceText = specId ? joinList(aggregate.invoice_numbers) : '—';
    const sfText = specId ? joinList(aggregate.sf_numbers) : '—';
    const rowAttrs = specId
      ? `data-spec-id="${escapeHtml(specId)}"`
      : `data-toggle-key="${escapeHtml(toggleKey || '')}" tabindex="0" role="button" aria-expanded="${expanded ? 'true' : 'false'}"`;
    const marker = toggleKey
      ? `<span class="level-toggle" aria-hidden="true">${expanded ? '⌄' : '›'}</span>`
      : '';
    const selectControl = specId
      ? `<button class="select-spec-btn ${selected ? 'selected' : ''}" type="button" data-select-spec-id="${escapeHtml(specId || '')}" aria-label="${selected ? 'Поставка выбрана' : 'Выбрать поставку'}" title="${selected ? 'Поставка выбрана' : 'Выбрать поставку'}"><span aria-hidden="true">${selected ? '●' : '○'}</span></button>`
      : '';
    const labelHtml = erpUrl
      ? `<a class="matrix-link" href="${escapeHtml(erpUrl)}" target="_blank" rel="noopener noreferrer" title="Открыть в ERP" onclick="event.stopPropagation()">${escapeHtml(label)}</a>`
      : `<span>${escapeHtml(label)}</span>`;
    return `<tr class="${rowClass}" ${rowAttrs}>
      <td class="select-col select-cell">${selectControl}</td>
      <td class="sticky-col">
        <div class="hierarchy-cell level-${level}">
          <div class="hierarchy-title">${marker}${labelHtml}</div>
          <div class="subtext">${escapeHtml(subtext || '')}</div>
        </div>
      </td>
      <td class="mono">${escapeHtml(specText || '—')}</td>
      <td class="wrap-list mono">${escapeHtml(invoiceText)}</td>
      <td class="num">${escapeHtml(fmtMoneyValue(aggregate.invoice_sum))}</td>
      <td class="num">${escapeHtml(fmtMoneyValue(aggregate.payment_sum))}</td>
      <td class="num">${escapeHtml(fmtMoneyValue(aggregate.reimbursable_sum))}</td>
      <td class="num">${escapeHtml(fmtMoneyValue(aggregate.non_reimbursable_sum))}</td>
      <td class="wrap-list mono">${escapeHtml(sfText)}</td>
      <td class="num sticky-right-balance" title="Формула: сумма оплаты - возмещаемые расходы - невозмещаемые расходы">${escapeHtml(fmtMoneyValue(aggregate.balance))}</td>
      <td class="sticky-right-status"><span class="badge ${kind}">${escapeHtml(status)}</span></td>
    </tr>`;
  }

  function matrixSpecDetailsHtml(row) {
    const details = [
      ...documentDetailRows('Счет покупателю', row.invoice_rows || [], row.invoice_numbers || []),
      ...documentDetailRows('Оплата покупателя', row.payment_rows || [], row.payment_numbers || []),
      ...documentDetailRows('Закрывающий документ', row.sf_rows || [], row.sf_numbers || []),
    ];
    if (!details.length) return '';
    return `<tr class="matrix-detail-row">
      <td colspan="11">
        <div class="matrix-detail-box">
          <div class="matrix-detail-title">Документы по выбранной поставке</div>
          <div class="matrix-detail-grid">
            <div class="matrix-detail-head">Тип</div>
            <div class="matrix-detail-head">Номер / код 1С</div>
            <div class="matrix-detail-head">Дата</div>
            <div class="matrix-detail-head">Сумма</div>
            <div class="matrix-detail-head">Оплата по счету</div>
            ${details.map((item) => `
              <div>${escapeHtml(item.type)}</div>
              <div class="mono">${matrixDetailDocumentHtml(item)}</div>
              <div class="mono">${escapeHtml(fmtDate(item.date))}</div>
              <div class="mono">${escapeHtml(fmtMoneyValue(item.amount, item.currency || 'RUB'))}</div>
              <div class="mono">${item.paidAmount === '' ? '—' : escapeHtml(fmtMoneyValue(item.paidAmount, item.paidCurrency || 'RUB'))}</div>
            `).join('')}
          </div>
        </div>
      </td>
    </tr>`;
  }

  function documentDetailRows(type, rows, fallbackNumbers) {
    if (Array.isArray(rows) && rows.length) {
      return rows.map((row) => ({
        type,
        number: [row.number, row.code1c].filter(Boolean).filter((value, index, values) => values.indexOf(value) === index).join(' / ') || '—',
        date: row.date || '',
        amount: row.amount || 0,
        currency: row.currency || 'RUB',
        paidAmount: type === 'Счет покупателю' && row.operation_id ? (row.paid_amount || 0) : '',
        paidCurrency: row.paid_currency || 'RUB',
        erpUrl: row.erp_url || '',
        operationUrl: row.operation_url || '',
      }));
    }
    if (!Array.isArray(fallbackNumbers) || !fallbackNumbers.length) return [];
    return fallbackNumbers.map((number) => ({ type, number, date: '', amount: 0, currency: 'RUB' }));
  }

  function matrixDetailDocumentHtml(item) {
    const title = escapeHtml(item.number || '—');
    const documentLink = item.erpUrl
      ? `<a class="document-link" href="${escapeHtml(item.erpUrl)}" target="_blank" rel="noopener noreferrer" title="Открыть документ в ERP">${title}</a>`
      : `<span>${title}</span>`;
    const operationLink = item.operationUrl
      ? `<a class="operation-link" href="${escapeHtml(item.operationUrl)}" target="_blank" rel="noopener noreferrer" title="Открыть операцию в ERP">Операция ERP</a>`
      : '';
    return `<div class="document-links">${documentLink}${operationLink}</div>`;
  }

  function joinList(values) {
    if (!Array.isArray(values) || !values.length) return '—';
    return values.join('\n');
  }

  function deliveryLabel(row) {
    const type = row.spec_type_name || row.type_name || row.delivery_type || 'Поставка';
    const number = row.spec_number || '—';
    return `${type} №${number}`;
  }

  function renderMatrixSummary(summary) {
    const map = {
      deliveries: summary.deliveries || 0,
      invoice_sum: fmtMoneyValue(summary.invoice_sum),
      payment_sum: fmtMoneyValue(summary.payment_sum),
      reimbursable_sum: fmtMoneyValue(summary.reimbursable_sum),
      non_reimbursable_sum: fmtMoneyValue(summary.non_reimbursable_sum),
      balance: fmtMoneyValue(summary.balance),
    };
    for (const [key, value] of Object.entries(map)) {
      const node = els.matrixSummaryCards.querySelector(`[data-key="${key}"]`);
      if (node) node.textContent = value;
    }
  }

  function selectedSpec() {
    return state.matrix.find((row) => Number(row.spec_id) === Number(state.selectedSpecId)) || null;
  }

  function renderMatrixSelectionPanel() {
    const row = selectedSpec();
    if (!row) {
      els.matrixSelectionPanel.classList.add('hidden');
      els.matrixSelectionText.innerHTML = '';
      if (els.matrixSelectionDetailsBtn) els.matrixSelectionDetailsBtn.disabled = true;
      return;
    }
    const balance = Number(row.balance || 0);
    const balanceLabel = row.balance_label || (balance > 0 ? 'Переплата' : balance < 0 ? 'Долг' : 'Закрыто');
    const balanceClass = balance < 0 ? 'debt' : balance > 0 ? 'overpayment' : 'closed';
    els.matrixSelectionPanel.classList.remove('hidden');
    els.matrixSelectionText.innerHTML = `
      <div class="selected-title">Выбрана поставка: ${escapeHtml(deliveryLabel(row))}</div>
      <div class="selected-path">${escapeHtml(row.delivery_full_name || '')}</div>
      <div class="selected-meta">
        <span>Клиент: ${escapeHtml(row.client_name || '—')}</span>
        <span>Договор: ${escapeHtml(row.base_contract_number || '—')}</span>
        <span>Договор покупателя 1С: <b>${escapeHtml(row.buyer_contract_code || '—')}</b></span>
        <span>Договор комитента 1С: <b>${escapeHtml(row.committent_contract_code || '—')}</b></span>
        <span>Сальдо: <b class="${balanceClass}">${escapeHtml(fmtMoneyValue(row.balance))} · ${escapeHtml(balanceLabel)}</b></span>
      </div>`;
    if (els.matrixSelectionDetailsBtn) {
      els.matrixSelectionDetailsBtn.disabled = false;
      els.matrixSelectionDetailsBtn.textContent = state.matrixDetailsOpen ? 'Скрыть документы' : 'Показать документы';
    }
  }

  function renderSelectedContext() {
    const row = selectedSpec();
    if (!row) {
      els.selectedContext.innerHTML = `
        <div class="empty-state">
          <h3>Поставка не выбрана</h3>
          <p>Чтобы сверить поставку с 1С, загрузите поставки и отметьте нужную строку слева в матрице.</p>
          <ol>
            <li>Нажмите “Найти поставки”.</li>
            <li>Отметьте нужную поставку слева в таблице.</li>
            <li>Нажмите “Сверить с 1С”.</li>
          </ol>
          <button class="btn btn-primary" type="button" data-go-matrix-select>Перейти к выбору поставки</button>
        </div>`;
      return;
    }
    els.selectedContext.innerHTML = `<strong>${escapeHtml(row.client_name || 'Клиент')} · ${escapeHtml(deliveryLabel(row))}</strong>
      <div class="kv">
        <span>дата: <span class="mono">${escapeHtml(fmtDate(row.spec_date))}</span></span>
        <span>договор: ${escapeHtml(row.base_contract_number || '—')}</span>
        <span>договор покупателя 1С: <span class="mono">${escapeHtml(row.buyer_contract_code || '—')}</span></span>
        <span>договор комитента 1С: <span class="mono">${escapeHtml(row.committent_contract_code || '—')}</span></span>
      </div>`;
  }

  function renderProgress(activeKey, errorKey) {
    if (!activeKey) {
      els.loadingOverlay.classList.add('hidden');
      els.progressBox.innerHTML = '';
      els.loadingStepText.textContent = 'Готовим запрос...';
      return;
    }
    els.loadingOverlay.classList.remove('hidden');
    if (activeKey === 'done') {
      els.loadingStepText.textContent = 'Проверка завершена.';
      els.progressBox.innerHTML = steps.map(([, label]) => `<div class="step done"><span class="dot"></span><span>${escapeHtml(label)}</span></div>`).join('');
      return;
    }
    const activeStep = steps.find(([key]) => key === activeKey);
    els.loadingStepText.textContent = activeStep ? activeStep[1] : 'Выполняем проверку...';
    els.progressBox.innerHTML = steps.map(([key, label]) => {
      const activeIndex = steps.findIndex((step) => step[0] === activeKey);
      const currentIndex = steps.findIndex((step) => step[0] === key);
      let cls = '';
      if (errorKey === key) cls = 'error';
      else if (activeIndex >= 0 && currentIndex < activeIndex) cls = 'done';
      else if (key === activeKey) cls = 'active';
      return `<div class="step ${cls}"><span class="dot"></span><span>${escapeHtml(label)}</span></div>`;
    }).join('');
  }

  async function runReconciliation() {
    if (!state.selectedSpecId) return;
    els.runBtn.disabled = true;
    els.exportBtn.disabled = true;
    els.runBtn.textContent = 'Проверяем...';
    setMessage(els.runMessage, 'Запускаем проверку...');
    renderProgress('erp_context');
    const timer = stagedProgress();
    try {
      if (state.matrixMode === 'ui_demo') {
        await wait(1200);
        state.run = demoRun();
      } else {
        const params = new URLSearchParams({ spec_id: state.selectedSpecId, persist_log: '1' });
        const resp = await api('/api/reconciliation/run?' + params.toString());
        const payload = await resp.json();
        if (!resp.ok || payload.ok !== true) throw new Error(payload.message || 'Сверка не выполнена');
        state.run = payload.run;
      }
      renderProgress('done');
      await loadRunComments();
      renderResults();
      renderSummary();
      const elapsed = state.run.metrics && state.run.metrics.total_ms
        ? ` · ${(Number(state.run.metrics.total_ms) / 1000).toFixed(2)} с`
        : '';
      setMessage(els.runMessage, `Проверка доступной области завершена${elapsed}. Номер запуска: ${state.run.run_id}`);
      syncBrowserUrl(state.run.run_id);
      els.onecStatusChip.textContent = state.matrixMode === 'ui_demo' ? '1С: UI demo' : '1С: ответ получен';
    } catch (err) {
      renderProgress('onec', 'onec');
      setMessage(els.runMessage, normalizeErrorMessage(err), true);
      els.onecStatusChip.textContent = '1С: ошибка';
    } finally {
      clearInterval(timer);
      renderProgress(null);
      updateActionState();
    }
  }

  async function loadStoredRun(runId) {
    if (!runId) return false;
    setMessage(els.runMessage, 'Открываем сохраненный запуск...');
    try {
      const response = await api('/api/reconciliation/history/' + encodeURIComponent(runId));
      const payload = await response.json();
      if (!response.ok || payload.ok !== true || !payload.run) {
        throw new Error(payload.message || 'Сохраненный запуск не найден');
      }
      const storedSpecId = Number(payload.run.delivery && payload.run.delivery.erp_spec_id || 0);
      if (storedSpecId && storedSpecId !== Number(state.selectedSpecId)) {
        throw new Error('Сохраненный запуск относится к другой поставке');
      }
      state.run = payload.run;
      await loadRunComments();
      renderResults();
      renderSummary();
      const elapsed = state.run.metrics && state.run.metrics.total_ms
        ? ` · ${(Number(state.run.metrics.total_ms) / 1000).toFixed(2)} с`
        : '';
      setMessage(els.runMessage, `Сохраненная проверка доступной области${elapsed}. Номер запуска: ${state.run.run_id}`);
      updateActionState();
      return true;
    } catch (error) {
      setMessage(els.runMessage, normalizeErrorMessage(error), true);
      return false;
    }
  }

  function stagedProgress() {
    let idx = 1;
    return setInterval(() => {
      if (idx < steps.length - 1) {
        renderProgress(steps[idx][0]);
        idx += 1;
      }
    }, 550);
  }

  function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function demoRun() {
    const row = selectedSpec() || {};
    return {
      run_id: 'ui-demo-' + Date.now(),
      created_at: new Date().toISOString(),
      matched: false,
      execution_status: 'completed',
      coverage_status: 'delivery_snapshot',
      result_status: 'issues_found',
      balance_status: 'amount_mismatch',
      ruleset: { id: 'delivery-document-control', version: '0.3.0', status: 'experimental' },
      delivery: {
        erp_spec_id: row.spec_id,
        spec_number: row.spec_number,
        base_contract_number: row.base_contract_number,
        contract_codes: {
          buyer_contract_code: row.buyer_contract_code,
          committent_contract_code: row.committent_contract_code,
        },
      },
      summary: {
        issues_total: 5,
        by_status: { match: 2, amount_mismatch: 1, not_found_in_1c: 1, contract_mismatch: 1 },
      },
      coverage: {
        requested_scope: 'delivery_snapshot',
        date_from: '2025-07-01',
        date_to: '2025-08-31',
        filters: {
          buyer_contract_code1c: row.buyer_contract_code,
          committent_contract_code1c: row.committent_contract_code,
        },
        returned_blocks: { customer_invoices: 3, payments: 1, sales: 2, purchases: 4, document_lines: 12 },
        warnings: [],
        complete: null,
        retrieved_at: new Date().toISOString(),
        contract_version: 'reconciliation.v1',
      },
      balance_comparison: {
        erp_balance: { amount: '-6666.82', currency: 'RUB' },
        onec_balance: { amount: '-6066.90', currency: 'RUB' },
        difference: { amount: '-599.92', currency: 'RUB' },
        status: 'amount_mismatch',
      },
      issues: [
        issue('match', 'customer_invoice', 'ВА-015695', 'ВА-015695', row.buyer_contract_code, '2025-07-09', '21000.00', 'Документ совпал'),
        issue('match', 'payment', '00БП-010299', '00БП-010299', row.buyer_contract_code, '2025-07-30', '442296.92', 'Документ совпал'),
        issue('amount_mismatch', 'sale', '00БП-000198', '00БП-000198', row.buyer_contract_code, '2025-08-09', '67055.99', 'Расходятся: сумма', ['amount']),
        issue('not_found_in_1c', 'sale', '00БП-003300', '', row.committent_contract_code, '2025-08-12', '445565.75', 'ERP документ не найден в 1С'),
        issue('contract_mismatch', 'sale', '00БП-003301', '00БП-003301', row.committent_contract_code, '2025-08-14', '36648.04', 'Расходятся: договор 1С', ['contract_code1c']),
      ],
    };
  }

  function issue(status, kind, erpCode, onecCode, contractCode, date, amount, message, fields = []) {
    return {
      status,
      message,
      fields,
      erp_document: {
        kind,
        code1c: erpCode,
        number: erpCode,
        date,
        amount: { amount, currency: 'RUB' },
        contract_code1c: contractCode || '',
      },
      onec_document: onecCode ? {
        kind,
        code1c: onecCode,
        number: onecCode,
        date,
        amount: { amount: status === 'amount_mismatch' ? '64000.00' : amount, currency: 'RUB' },
        contract_code1c: status === 'contract_mismatch' ? 'Другой договор' : contractCode || '',
      } : null,
    };
  }

  function renderSummary() {
    const by = state.run && state.run.summary ? state.run.summary.by_status || {} : {};
    const groups = state.run && state.run.summary ? state.run.summary.by_group || buildStatusGroups(by) : {};
    const total = state.run && state.run.summary ? state.run.summary.issues_total || 0 : 0;
    els.summaryCards.querySelector('[data-key="issues_total"]').textContent = total;
    els.summaryCards.querySelectorAll('[data-group]').forEach((node) => {
      node.textContent = groups[node.getAttribute('data-group')] || 0;
    });
    renderCoverage();
    renderBalanceComparison();
    updateWorkflowState();
  }

  function buildStatusGroups(by) {
    const sum = (statuses) => statuses.reduce((total, status) => total + Number(by[status] || 0), 0);
    return {
      matched: sum(['match']),
      cannot_check: sum(['missing_erp_invoice', 'missing_erp_closing_document', 'erp_code1c_missing']),
      not_found: sum(['not_found_in_1c', 'not_found_in_erp']),
      link_problem: sum(['not_linked_to_delivery_in_erp', 'contract_context_missing', 'erp_invoice_link_missing']),
      attribute_mismatch: sum(['amount_mismatch', 'date_mismatch', 'contract_mismatch', 'number_mismatch', 'vat_mismatch', 'duplicate_in_1c', 'ambiguous_match', 'aggregation_conflict', 'not_comparable']),
    };
  }

  function renderCoverage() {
    const coverage = state.run && state.run.coverage;
    if (!coverage) {
      els.coveragePanel.classList.add('hidden');
      return;
    }
    els.coveragePanel.classList.remove('hidden');
    els.coverageRetrievedAt.textContent = coverage.retrieved_at ? `получено ${fmtDateTime(coverage.retrieved_at)}` : '';
    els.coveragePeriod.textContent = `автоматически: ${fmtDate(coverage.date_from)} — ${fmtDate(coverage.date_to)}`;
    const filters = coverage.filters || {};
    els.coverageContracts.textContent = [filters.buyer_contract_code1c, filters.committent_contract_code1c].filter(Boolean).join(', ') || 'не заданы';
    const counts = coverage.returned_blocks || {};
    const countLabels = [
      ['customer_invoices', 'счетов'],
      ['payments', 'оплат'],
      ['sales', 'реализаций'],
      ['purchases', 'поступлений'],
      ['document_lines', 'строк'],
    ].filter(([key]) => Number(counts[key] || 0) > 0).map(([key, label]) => `${counts[key]} ${label}`);
    els.coverageCounts.textContent = countLabels.join(' · ') || `${counts.documents || 0} документов`;
    els.coverageCompleteness.textContent = coverage.complete === true
      ? 'подтверждена источником'
      : coverage.complete === false
        ? 'источник сообщил о неполных данных'
        : 'независимо не подтверждена';
    const warnings = coverage.warnings || [];
    els.coverageWarnings.textContent = warnings.length ? `Предупреждения 1С: ${warnings.join('; ')}` : '';
    els.coverageWarnings.classList.toggle('hidden', !warnings.length);
  }

  function fmtDateTime(value) {
    if (!value) return '—';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' });
  }

  function renderBalanceComparison() {
    const comparison = state.run && state.run.balance_comparison;
    if (!comparison) {
      els.balanceCompare.classList.add('hidden');
      return;
    }
    const erp = comparison.erp_balance || {};
    const direct = comparison.direct_onec_balance || comparison.onec_balance || {};
    const adjustment = comparison.allocated_adjustment || { amount: 0, currency: direct.currency || 'RUB' };
    const onec = comparison.onec_balance || {};
    const difference = comparison.difference || {};
    const matches = comparison.status === 'match';
    const incomplete = comparison.status === 'not_comparable' || comparison.comparable === false;
    els.balanceCompare.classList.remove('hidden');
    els.balanceCompare.classList.toggle('ok', matches);
    els.balanceCompare.classList.toggle('problem', !matches && !incomplete);
    els.balanceCompare.classList.toggle('warning', incomplete);
    els.balanceErp.textContent = fmtMoneyValue(erp.amount, erp.currency || 'RUB');
    els.balanceOnecDirect.textContent = fmtMoneyValue(direct.amount, direct.currency || 'RUB');
    els.balanceOnecAdjustment.textContent = fmtMoneyValue(adjustment.amount, adjustment.currency || 'RUB');
    els.balanceOnec.textContent = fmtMoneyValue(onec.amount, onec.currency || 'RUB');
    els.balanceDifference.textContent = fmtMoneyValue(difference.amount, difference.currency || 'RUB');
    els.balanceStatus.textContent = matches
      ? 'Сальдо совпало'
      : incomplete
        ? 'Не подтверждено документами'
        : 'Сальдо расходится';
    els.balanceExplanation.textContent = comparison.explanation || '';
    els.balanceExplanation.classList.toggle('hidden', !comparison.explanation);
  }

  function renderResults() {
    const issues = state.run && Array.isArray(state.run.issues) ? state.run.issues : [];
    const filter = els.statusFilter.value || 'all';
    const search = (els.resultSearchInput.value || '').trim().toLowerCase();
    syncResultFilterTiles(filter);
    let rows = issues;
    if (filter === 'problems') rows = rows.filter((row) => row.status !== 'match');
    else if (filter === 'cannot_check') rows = rows.filter((row) => ['missing_erp_invoice', 'missing_erp_closing_document', 'erp_code1c_missing'].includes(row.status));
    else if (filter === 'not_found') rows = rows.filter((row) => ['not_found_in_1c', 'not_found_in_erp'].includes(row.status));
    else if (filter === 'link_problem') rows = rows.filter((row) => ['not_linked_to_delivery_in_erp', 'contract_context_missing', 'erp_invoice_link_missing'].includes(row.status));
    else if (filter === 'attribute_mismatch') rows = rows.filter((row) => ['amount_mismatch', 'date_mismatch', 'contract_mismatch', 'number_mismatch', 'vat_mismatch', 'duplicate_in_1c', 'ambiguous_match', 'aggregation_conflict', 'not_comparable'].includes(row.status));
    else if (filter === 'mismatches') rows = rows.filter((row) => [
      'amount_mismatch',
      'date_mismatch',
      'contract_mismatch',
      'number_mismatch',
      'vat_mismatch',
      'duplicate_in_1c',
      'ambiguous_match',
      'aggregation_conflict',
      'not_comparable',
      'contract_context_missing',
      'missing_erp_invoice',
      'missing_erp_closing_document',
      'erp_code1c_missing',
      'not_linked_to_delivery_in_erp',
    ].includes(row.status));
    else if (filter !== 'all') rows = rows.filter((row) => row.status === filter);
    if (search) rows = rows.filter((row) => JSON.stringify(row).toLowerCase().includes(search));
    if (!rows.length) {
      els.resultRows.innerHTML = `<tr><td colspan="9" class="empty-cell">${issues.length ? 'По выбранному фильтру строк нет.' : 'Сверка еще не запускалась.'}</td></tr>`;
      renderSummary();
      return;
    }
    els.resultRows.innerHTML = rows.map((row) => resultRowHtml(row)).join('');
    bindFeedbackControls();
    renderSummary();
  }

  function syncResultFilterTiles(filter) {
    els.summaryCards.querySelectorAll('[data-result-filter]').forEach((node) => {
      node.classList.toggle('active', (node.getAttribute('data-result-filter') || 'all') === filter);
    });
  }

  function resultRowHtml(issueRow) {
    const erp = issueRow.erp_document || {};
    const onec = issueRow.onec_document || {};
    const key = feedbackKey(issueRow);
    const feedback = state.feedback[key] || {};
    return `<tr>
      <td>${statusBadge(issueRow.status)}</td>
      <td>${escapeHtml(issueType(issueRow))}</td>
      <td class="mono">${erpDocumentHtml(erp)}</td>
      <td class="mono">${escapeHtml(documentTitle(onec))}</td>
      <td class="mono">${comparisonDateHtml(erp, onec)}</td>
      <td class="num">${escapeHtml(fmtDocMoney(erp))}</td>
      <td class="num">${escapeHtml(fmtDocMoney(onec))}</td>
      <td>${escapeHtml(issueReason(issueRow))}</td>
      <td class="feedback-cell">
        <select data-feedback-reason="${escapeHtml(key)}">${feedbackReasons.map(([value, label]) => `<option value="${escapeHtml(value)}" ${feedback.reason === value ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('')}</select>
        <textarea data-feedback-comment="${escapeHtml(key)}" placeholder="Комментарий для разбора">${escapeHtml(feedback.comment || '')}</textarea>
        <div class="feedback-actions">
          <button class="btn btn-primary feedback-save" type="button" data-feedback-save="${escapeHtml(key)}">Сохранить</button>
          <span class="feedback-status" data-feedback-status="${escapeHtml(key)}">${escapeHtml(feedback.updated_at ? `Сохранено ${feedback.user_name || feedback.user_login || ''}`.trim() : 'Не сохранено')}</span>
        </div>
      </td>
    </tr>`;
  }

  function comparisonDateHtml(erp, onec) {
    const erpDate = erp && erp.date ? fmtDate(erp.date) : '';
    const onecDate = onec && onec.date ? fmtDate(onec.date) : '';
    if (erpDate && onecDate && erp.date === onec.date) return escapeHtml(erpDate);
    const rows = [];
    if (erpDate) rows.push(`<span><b>ERP, дата 1С:</b> ${escapeHtml(erpDate)}</span>`);
    if (onecDate) rows.push(`<span><b>1С, дата документа:</b> ${escapeHtml(onecDate)}</span>`);
    return rows.length ? `<div class="date-comparison">${rows.join('')}</div>` : '—';
  }

  function bindFeedbackControls() {
    els.resultRows.querySelectorAll('[data-feedback-reason]').forEach((node) => {
      node.addEventListener('change', () => updateFeedbackDraft(node, node.getAttribute('data-feedback-reason'), { reason: node.value }));
    });
    els.resultRows.querySelectorAll('[data-feedback-comment]').forEach((node) => {
      node.addEventListener('input', () => updateFeedbackDraft(node, node.getAttribute('data-feedback-comment'), { comment: node.value }));
    });
    els.resultRows.querySelectorAll('[data-feedback-save]').forEach((node) => {
      node.addEventListener('click', () => postFeedback(node.getAttribute('data-feedback-save'), node));
    });
  }

  function updateFeedbackDraft(node, key, patch) {
    state.feedback[key] = Object.assign({}, state.feedback[key] || {}, patch, { updated_at: '', user_name: '' });
    localStorage.setItem('recon_feedback_v1', JSON.stringify(state.feedback));
    const cell = node.closest('.feedback-cell');
    const status = cell ? cell.querySelector('[data-feedback-status]') : null;
    if (status) {
      status.textContent = 'Не сохранено';
      status.className = 'feedback-status dirty';
    }
  }

  async function postFeedback(key, button) {
    const feedback = state.feedback[key] || {};
    const row = findIssueByFeedbackKey(key);
    const cell = button ? button.closest('.feedback-cell') : null;
    const status = cell ? cell.querySelector('[data-feedback-status]') : null;
    if (button) button.disabled = true;
    if (status) {
      status.textContent = 'Сохраняем...';
      status.className = 'feedback-status saving';
    }
    try {
      const response = await api('/api/reconciliation/comments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          key,
          run_id: state.run ? state.run.run_id : '',
          spec_id: state.selectedSpecId || 0,
          status: row ? row.status : '',
          reason: feedback.reason || '',
          comment: feedback.comment || '',
        }),
      });
      let payload = {};
      try { payload = await response.json(); } catch (_) {}
      if (!response.ok || payload.ok !== true) throw new Error(payload.message || 'Комментарий не сохранен');
      state.feedback[key] = Object.assign({}, feedback, {
        updated_at: payload.updated_at || new Date().toISOString(),
        user_name: payload.user_name || (state.profile && state.profile.name) || '',
        user_login: payload.user_login || (state.profile && state.profile.login) || '',
      });
      localStorage.setItem('recon_feedback_v1', JSON.stringify(state.feedback));
      if (status) {
        status.textContent = `Сохранено${state.feedback[key].user_name ? ` · ${state.feedback[key].user_name}` : ''}`;
        status.className = 'feedback-status saved';
      }
    } catch (err) {
      if (status) {
        status.textContent = `Ошибка: ${normalizeErrorMessage(err)}`;
        status.className = 'feedback-status error';
      }
      setMessage(els.runMessage, 'Не удалось сохранить разбор. Проверьте подключение и повторите.', true);
    } finally {
      if (button) button.disabled = false;
    }
  }

  function findIssueByFeedbackKey(key) {
    const issues = state.run && Array.isArray(state.run.issues) ? state.run.issues : [];
    return issues.find((row) => feedbackKey(row) === key) || null;
  }

  function feedbackKey(row) {
    if (row.issue_key) return row.issue_key;
    const erp = row.erp_document || {};
    const onec = row.onec_document || {};
    return [
      row.status,
      erp.kind || onec.kind || '',
      erp.code1c || erp.number || '',
      onec.code1c || onec.number || '',
      erp.date || onec.date || '',
      erp.contract_code1c || onec.contract_code1c || '',
    ].join('|');
  }

  async function loadRunComments() {
    if (!state.run || !state.run.run_id) return;
    try {
      const params = new URLSearchParams({ spec_id: String(state.selectedSpecId || 0) });
      const response = await api('/api/reconciliation/comments?' + params.toString());
      const payload = await response.json();
      if (!response.ok || payload.ok !== true) return;
      const loadedKeys = new Set();
      for (const item of payload.items || []) {
        if (!item.key || loadedKeys.has(item.key)) continue;
        loadedKeys.add(item.key);
        state.feedback[item.key] = {
          reason: item.reason || '',
          comment: item.comment || '',
          user_name: item.user_name || '',
          updated_at: item.updated_at || '',
        };
      }
      localStorage.setItem('recon_feedback_v1', JSON.stringify(state.feedback));
    } catch (_) {
      // The run remains usable if audit storage is temporarily unavailable.
    }
  }

  function issueType(row) {
    const doc = row.erp_document || row.onec_document || {};
    const map = {
      customer_invoice: 'Счет покупателю',
      payment: 'Оплата покупателя',
      sale: 'Акт / реализация',
      purchase: 'Поступление поставщика',
      closing_document: 'Закрывающий документ',
      account_movement: 'Движение по счету',
    };
    return map[doc.kind] || doc.kind || 'Документ';
  }

  function documentTitle(doc) {
    if (!doc || Object.keys(doc).length === 0) return '—';
    return [
      doc.code1c || doc.number,
      doc.contract_code1c ? `договор: ${doc.contract_code1c}` : '',
    ].filter(Boolean).join('\n') || '—';
  }

  function erpDocumentHtml(doc) {
    if (!doc || Object.keys(doc).length === 0) return '—';
    const primaryNumber = doc.code1c || doc.number || doc.source_number || 'ERP документ';
    const sourceNumber = doc.source_number && doc.source_number !== doc.number
      ? `<span class="source-document-number">${escapeHtml(doc.source_number)}</span>`
      : '';
    const title = `${sourceNumber}<span>${escapeHtml(primaryNumber)}</span>`;
    const documentLink = doc.erp_url
      ? `<a class="document-link" href="${escapeHtml(doc.erp_url)}" target="_blank" rel="noopener noreferrer" title="Открыть документ в ERP">${title}</a>`
      : `<span>${title}</span>`;
    const extraDocumentLinks = (doc.erp_links || []).slice(1).map((link) => (
      `<a class="document-link extra-document-link" href="${escapeHtml(link.url)}" target="_blank" rel="noopener noreferrer" title="Открыть связанную ERP-запись">${escapeHtml(link.label || 'ERP запись')}</a>`
    )).join('');
    const contractContext = doc.contract_code1c
      ? `<span class="document-contract">договор: ${escapeHtml(doc.contract_code1c)}</span>`
      : '';
    const operationLink = doc.operation_url
      ? `<a class="operation-link" href="${escapeHtml(doc.operation_url)}" target="_blank" rel="noopener noreferrer" title="Открыть операцию в ERP">Операция ERP</a>`
      : '';
    const parentOperationLink = doc.parent_operation_url
      ? `<a class="operation-link parent-operation-link" href="${escapeHtml(doc.parent_operation_url)}" target="_blank" rel="noopener noreferrer" title="Открыть клиентскую операцию в ERP">Клиентская операция ERP ${escapeHtml(doc.parent_operation_id)}</a>`
      : '';
    const relatedLinks = (doc.related_erp_links || []).map((related) => {
      const relatedDocument = related.url
        ? `<a class="document-link related-document-link" href="${escapeHtml(related.url)}" target="_blank" rel="noopener noreferrer" title="Открыть документ в ERP">${escapeHtml(related.label || 'ERP документ')}</a>`
        : `<span>${escapeHtml(related.label || 'ERP документ')}</span>`;
      const relatedOperation = related.operation_url
        ? `<a class="operation-link" href="${escapeHtml(related.operation_url)}" target="_blank" rel="noopener noreferrer" title="Открыть операцию в ERP">Операция ERP${related.operation_id ? ` ${escapeHtml(related.operation_id)}` : ''}</a>`
        : '';
      return `<div class="related-document-row">${relatedDocument}${relatedOperation}</div>`;
    }).join('');
    return `<div class="document-links">${documentLink}${extraDocumentLinks}${contractContext}${operationLink}${parentOperationLink}${relatedLinks}</div>`;
  }

  function issueReason(row) {
    if (row.status === 'not_found_in_1c') return 'Документ ERP с заполненным кодом 1С не найден в 1С по типу, коду, дате и точной сумме';
    if (row.status === 'erp_code1c_missing') return 'В документе ERP не заполнен код 1С; точечная проверка выгрузки в 1С невозможна';
    if (row.status === 'not_found_in_erp') return 'Документ 1С не найден в ERP';
    if (row.status === 'not_linked_to_delivery_in_erp') return 'Документ 1С существует, но не связан с выбранной поставкой ERP';
    if (row.status === 'missing_erp_invoice' || row.status === 'erp_invoice_link_missing') return row.message || 'По операции ERP не найдена прямая связь со счетом покупателю';
    if (row.status === 'missing_erp_closing_document') return 'По операции ERP отсутствует закрывающий документ';
    if (row.status === 'vat_mismatch') {
      const erpVat = row.erp_document?.vat_rate || 'не указана';
      const onecVat = row.onec_document?.vat_rate || 'не указана';
      return `Ставка НДС: ERP — ${erpVat}, 1С — ${onecVat}`;
    }
    const erpDate = row.erp_document?.date ? fmtDate(row.erp_document.date) : 'не указана';
    const onecDate = row.onec_document?.date ? fmtDate(row.onec_document.date) : 'не указана';
    const labels = {
      code1c: 'код 1С',
      date: 'дата',
      currency: 'валюта',
      amount: 'сумма',
      contract_code1c: 'договор 1С',
      contract_context: 'аналитика поставки',
      vat_rate: 'ставка НДС',
    };
    const fields = (row.fields || []).map((field) => (
      field === 'date'
        ? `дата: ERP, поле «Дата 1С» — ${erpDate}; документ 1С — ${onecDate}`
        : labels[field] || field
    ));
    const basisLabels = {
      document_header: 'по документу',
      payment_header_allocations: 'по документу и распределениям оплаты',
      payment_allocation: 'по распределению оплаты',
      document_allocation: 'по распределению документа',
      document_line: 'по строке документа',
    };
    const basis = basisLabels[row.match_basis] || '';
    if (fields.length) return `Расходятся: ${fields.join(', ')}${basis ? ` · проверено ${basis}` : ''}`;
    if (row.status === 'match' && basis) {
      if (row.erp_document?.kind === 'purchase' && row.erp_document?.operation_id) {
        const supplierContract = row.onec_document?.contract_code1c
          ? ` · договор поставщика ${row.onec_document.contract_code1c}`
          : '';
        return `Совпало ${basis} · входящий документ связан с поставкой через операцию ERP ${row.erp_document.operation_id}${supplierContract}`;
      }
      const linkedContract = row.erp_document?.contract_code1c
        && row.onec_document?.contract_code1c
        && row.erp_document.contract_code1c !== row.onec_document.contract_code1c;
      return linkedContract
        ? `Совпало ${basis} · в 1С проведен по договору ${row.onec_document.contract_code1c}`
        : `Совпало ${basis}`;
    }
    return row.message || 'Без расхождений';
  }

  function statusBadge(status) {
    const map = {
      match: ['match', 'ОК'],
      not_found_in_1c: ['bad', 'Не найдено в 1С'],
      erp_code1c_missing: ['bad', 'Нет кода 1С в ERP'],
      not_found_in_erp: ['warn', 'Не найдено в ERP'],
      not_linked_to_delivery_in_erp: ['warn', 'Нет связи ERP'],
      amount_mismatch: ['bad', 'Сумма/валюта'],
      date_mismatch: ['warn', 'Дата'],
      contract_mismatch: ['warn', 'Договор'],
      number_mismatch: ['warn', 'Номер'],
      vat_mismatch: ['warn', 'НДС'],
      duplicate_in_1c: ['bad', 'Дубли 1С'],
      ambiguous_match: ['bad', 'Неоднозначно'],
      aggregation_conflict: ['warn', 'Конфликт агрегации'],
      not_comparable: ['warn', 'Не сверяется'],
      contract_context_missing: ['bad', 'Нет аналитики поставки'],
      missing_erp_invoice: ['warn', 'Нет связи со счетом'],
      erp_invoice_link_missing: ['warn', 'Счет на другой операции'],
      missing_erp_closing_document: ['bad', 'Нет закрывающего документа'],
    };
    const value = map[status] || ['warn', status || 'unknown'];
    return `<span class="badge ${value[0]}">${escapeHtml(value[1])}</span>`;
  }

  async function exportXlsx() {
    if (state.view === 'matrix') {
      await exportMatrixXlsx();
      return;
    }
    if (!state.run) return;
    els.exportBtn.disabled = true;
    setMessage(els.runMessage, 'Формируем XLSX по результату проверки...');
    try {
      const resp = await api('/api/reconciliation/run.xlsx', {
        method: 'POST',
        headers: {
          Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ run: state.run }),
      });
      if (!resp.ok) {
        let message = `HTTP ${resp.status}`;
        try { message = (await resp.json()).message || message; } catch (_) {}
        throw new Error(message);
      }
      const blob = await resp.blob();
      if (!blob.size) throw new Error('Сервис вернул пустой XLSX');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      const row = selectedSpec();
      const suffix = row ? String(row.spec_number || row.spec_id).replace(/[^\wа-яА-Я-]+/g, '_') : 'run';
      link.href = url;
      link.download = `sverka-erp-1c-${suffix}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
      setMessage(els.runMessage, 'XLSX сформирован и передан браузеру для скачивания.');
    } catch (err) {
      setMessage(els.runMessage, normalizeErrorMessage(err), true);
    } finally {
      updateActionState();
    }
  }

  async function exportMatrixXlsx() {
    if (!state.matrix.length) return;
    if (!validateClientFilter(els.matrixMessage)) return;
    if (!validateDogFilter(els.matrixMessage)) return;
    const visibleItems = matrixVisibleItems();
    if (!visibleItems.length) {
      setMessage(els.matrixMessage, 'Нет видимых строк для экспорта. Измените фильтр или загрузите поставки.', true);
      updateActionState();
      return;
    }
    await exportMatrixItemsXlsx({
      items: visibleItems,
      filename: `akt-sverki-matrix-${els.clientIdInput.value || 'client'}.xlsx`,
      startMessage: 'Формируем XLSX по текущей матрице...',
      successMessage: 'XLSX матрицы сформирован.',
    });
  }

  async function exportMatrixAllXlsx() {
    if (!validateClientFilter(els.matrixMessage)) return;
    if (!validateDogFilter(els.matrixMessage)) return;
    const params = queryParams();
    params.set('all', '1');
    params.set('offset', '0');
    params.delete('limit');
    setMessage(els.matrixMessage, 'Формируем XLSX по всем поставкам текущего фильтра...');
    try {
      const resp = await api(`/api/reconciliation/matrix.xlsx?${params.toString()}`, {
        headers: { Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
      });
      if (!resp.ok) {
        let message = `HTTP ${resp.status}`;
        try { message = (await resp.json()).message || message; } catch (_) {}
        throw new Error(message);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `akt-sverki-matrix-all-${els.clientIdInput.value || 'client'}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage(els.matrixMessage, 'XLSX по всему фильтру сформирован.');
    } catch (err) {
      setMessage(els.matrixMessage, normalizeErrorMessage(err), true);
    }
  }

  async function exportSelectedSpecXlsx() {
    const row = selectedSpec();
    if (!row) return;
    await exportMatrixItemsXlsx({
      items: [row],
      filename: `postavka-${String(row.spec_number || row.spec_id).replace(/[^\wа-яА-Я-]+/g, '_')}-vzaimoraschety.xlsx`,
      startMessage: 'Формируем XLSX по выбранной поставке...',
      successMessage: 'XLSX поставки сформирован.',
    });
  }

  async function exportMatrixItemsXlsx({ items, filename, startMessage, successMessage }) {
    if (!Array.isArray(items) || !items.length) return;
    setMessage(els.matrixMessage, startMessage);
    try {
      const matrix = Object.assign({}, state.matrixPayload || {}, {
        items,
        count: items.length,
        total_count: items.length,
        has_more: false,
        summary: buildMatrixSummary(items),
      });
      const resp = await api('/api/reconciliation/matrix.xlsx', {
        method: 'POST',
        headers: {
          Accept: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ matrix }),
      });
      if (!resp.ok) {
        let message = `HTTP ${resp.status}`;
        try { message = (await resp.json()).message || message; } catch (_) {}
        throw new Error(message);
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage(els.matrixMessage, successMessage);
    } catch (err) {
      setMessage(els.matrixMessage, normalizeErrorMessage(err), true);
    }
  }

  function updateActionState() {
    const hasSpec = Boolean(state.selectedSpecId);
    const hasRun = Boolean(state.run);
    const hasMatrix = Boolean(state.matrix.length);
    const visibleCount = matrixVisibleItems().length;
    const isMatrixView = state.view === 'matrix';
    els.matrixToReconBtn.disabled = !hasSpec;
    els.matrixToReconBtn.title = hasSpec ? 'Сверить выбранную поставку с 1С' : 'Сначала отметьте кружок в колонке “Выбор”';
    if (els.matrixExportBtn) {
      els.matrixExportBtn.disabled = !visibleCount;
      els.matrixExportBtn.title = visibleCount
        ? 'Экспортирует текущую загруженную страницу с учетом фильтра статуса'
        : (hasMatrix ? 'Нет видимых строк для экспорта' : 'Сначала найдите поставки');
    }
    if (els.matrixExportAllBtn) {
      const totalCount = Number((state.matrixPayload || {}).total_count || 0);
      els.matrixExportAllBtn.disabled = !totalCount;
      els.matrixExportAllBtn.title = totalCount
        ? `Экспортирует все найденные поставки по фильтру: ${totalCount}`
        : 'Сначала найдите поставки';
    }
    if (els.matrixSelectionExportBtn) {
      els.matrixSelectionExportBtn.disabled = !hasSpec;
      els.matrixSelectionExportBtn.title = hasSpec ? 'Скачать XLSX по выбранной поставке' : 'Сначала отметьте поставку';
    }
    if (els.matrixHint) els.matrixHint.classList.toggle('hidden', !visibleCount || hasSpec);
    els.runBtn.disabled = !hasSpec;
    els.runBtn.textContent = hasRun ? 'Обновить проверку' : 'Проверить в 1С';
    els.exportBtn.disabled = !hasRun;
    els.refreshBtn.classList.toggle('hidden', !isMatrixView || !hasMatrix);
    els.refreshBtn.disabled = !isMatrixView || !hasMatrix;
    els.refreshBtn.textContent = '↻ Обновить список';
    els.refreshBtn.title = 'Обновить список поставок';
    updateWorkflowState();
  }

  function toggleSidebar() {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    localStorage.setItem('recon_sidebar_collapsed', state.sidebarCollapsed ? '1' : '0');
    applySidebarState();
  }

  function applySidebarState() {
    els.workArea.classList.toggle('sidebar-collapsed', state.sidebarCollapsed);
    els.sidebarToggleBtn.textContent = state.sidebarCollapsed ? '☰' : '←';
    els.sidebarToggleBtn.title = state.sidebarCollapsed ? 'Показать меню' : 'Скрыть меню';
  }

  function toggleMatrixDetails() {
    if (!state.selectedSpecId) return;
    state.matrixDetailsOpen = !state.matrixDetailsOpen;
    localStorage.setItem('recon_matrix_details_open', state.matrixDetailsOpen ? '1' : '0');
    renderMatrix(matrixKpiSummary());
  }

  function validateClientFilter(messageNode) {
    const text = (els.clientIdInput.value || '').trim();
    if (text && !selectedClientId()) {
      setMessage(messageNode, 'Выберите клиента из выпадающего списка или введите ID клиента.', true);
      return false;
    }
    return true;
  }

  function validateDogFilter(messageNode) {
    const text = (els.dogIdInput.value || '').trim();
    if (text && !selectedDogId()) {
      setMessage(messageNode, 'Выберите договор из выпадающего списка или введите ID договора.', true);
      return false;
    }
    return true;
  }

  function validateDeliveryFilter(messageNode) {
    const text = (els.deliveryInput.value || '').trim();
    if (text && !selectedDeliveryId()) {
      setMessage(messageNode, 'Выберите поставку из выпадающего списка или введите ее ID.', true);
      return false;
    }
    return true;
  }

  function initDefaults() {
    const params = initialParams;
    if (params.get('client_id')) els.clientIdInput.value = params.get('client_id');
    if (params.get('client_id')) els.clientIdInput.dataset.clientId = params.get('client_id');
    if (params.get('dog_id')) els.dogIdInput.value = params.get('dog_id');
    if (initialSpecId) {
      els.deliveryInput.value = String(initialSpecId);
      els.deliveryInput.dataset.specId = String(initialSpecId);
      state.selectedSpecId = initialSpecId;
      localStorage.setItem('recon_selected_spec', String(initialSpecId));
    }
    if (params.get('limit')) els.limitInput.value = params.get('limit');
    if (params.get('client_handover_from')) els.clientHandoverFromInput.value = params.get('client_handover_from');
    if (params.get('client_handover_to')) els.clientHandoverToInput.value = params.get('client_handover_to');
  }

  function resetFilters() {
    els.clientIdInput.value = '';
    delete els.clientIdInput.dataset.clientId;
    delete els.clientIdInput.dataset.clientLabel;
    renderClientSuggestions([]);
    clearDogFilter();
    clearDeliveryFilter();
    els.clientHandoverFromInput.value = '';
    els.clientHandoverToInput.value = '';
    if (els.matrixStatusFilter) els.matrixStatusFilter.value = 'all';
    els.limitInput.value = '50';
    state.matrix = [];
    state.matrixPayload = null;
    state.matrixOffset = 0;
    state.matrixDetailsOpen = false;
    state.selectedSpecId = null;
    state.run = null;
    localStorage.removeItem('recon_selected_spec');
    localStorage.setItem('recon_matrix_details_open', '0');
    renderMatrix();
    renderSelectedContext();
    renderResults();
    updateActionState();
    updateMatrixPager();
    setMessage(els.matrixMessage, 'Фильтры сброшены.');
    setMessage(els.runMessage, '');
    syncBrowserUrl();
  }

  function bind() {
    els.loginBtn.addEventListener('click', login);
    els.passwordInput.addEventListener('keydown', (event) => { if (event.key === 'Enter') login(); });
    els.logoutBtn.addEventListener('click', logout);
    els.navMatrixBtn.addEventListener('click', () => setView('matrix'));
    els.navReconBtn.addEventListener('click', openReconGuarded);
    els.matrixToReconBtn.addEventListener('click', openReconGuarded);
    els.sidebarToggleBtn.addEventListener('click', toggleSidebar);
    els.refreshBtn.addEventListener('click', () => {
      if (state.view === 'matrix') loadMatrix(state.matrixOffset);
      else if (openReconGuarded()) runReconciliation();
    });
    els.loadMatrixBtn.addEventListener('click', () => loadMatrix(0));
    els.clientIdInput.addEventListener('input', scheduleClientSearch);
    els.dogIdInput.addEventListener('input', scheduleDogSearch);
    els.deliveryInput.addEventListener('input', scheduleDeliverySearch);
    els.clientIdInput.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') renderClientSuggestions([]);
    });
    els.dogIdInput.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') renderDogSuggestions([]);
    });
    els.deliveryInput.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') renderDeliverySuggestions([]);
      if (event.key === 'Enter' && selectedDeliveryId()) loadMatrix(0);
    });
    document.addEventListener('click', (event) => {
      if (!els.clientIdInput.contains(event.target) && !els.clientSuggestions.contains(event.target)) {
        els.clientSuggestions.classList.add('hidden');
      }
      if (!els.dogIdInput.contains(event.target) && !els.dogSuggestions.contains(event.target)) {
        els.dogSuggestions.classList.add('hidden');
      }
      if (!els.deliveryInput.contains(event.target) && !els.deliverySuggestions.contains(event.target)) {
        els.deliverySuggestions.classList.add('hidden');
      }
    });
    els.matrixStatusFilter.addEventListener('change', () => {
      const selectionHidden = clearSelectionIfHiddenByFilter();
      const items = matrixVisibleItems();
      renderMatrix(matrixKpiSummary());
      renderSelectedContext();
      renderResults();
      if (selectionHidden) {
        setMessage(els.matrixMessage, 'Выбранная поставка скрыта текущим фильтром. Выберите поставку из видимых строк.', true);
      } else {
        setMessage(els.matrixMessage, `Фильтр статуса применен к текущей странице. Показано: ${items.length} из ${state.matrix.length}.`);
      }
      updateActionState();
    });
    els.resetFiltersBtn.addEventListener('click', resetFilters);
    els.matrixSelectionReconBtn.addEventListener('click', openReconGuarded);
    els.matrixSelectionDetailsBtn.addEventListener('click', toggleMatrixDetails);
    els.matrixSelectionExportBtn.addEventListener('click', exportSelectedSpecXlsx);
    els.matrixExportBtn.addEventListener('click', exportMatrixXlsx);
    if (els.matrixExportAllBtn) els.matrixExportAllBtn.addEventListener('click', exportMatrixAllXlsx);
    els.matrixPrevBtn.addEventListener('click', () => matrixPage(-1));
    els.matrixNextBtn.addEventListener('click', () => matrixPage(1));
    els.runBtn.addEventListener('click', runReconciliation);
    els.exportBtn.addEventListener('click', exportXlsx);
    els.statusFilter.addEventListener('change', renderResults);
    els.resultSearchInput.addEventListener('input', renderResults);
    els.selectedContext.addEventListener('click', (event) => {
      if (event.target && event.target.matches('[data-go-matrix-select]')) {
        setView('matrix');
        highlightMatrixSelection();
      }
    });
    els.summaryCards.querySelectorAll('[data-result-filter]').forEach((node) => {
      node.addEventListener('click', () => {
        els.statusFilter.value = node.getAttribute('data-result-filter') || 'all';
        renderResults();
      });
    });
  }

  async function boot() {
    initDefaults();
    bind();
    applySidebarState();
    await loadRuntimeConfig();
    await consumeLaunchToken();
    applyAuthState();
    await validateSession();
    if (!state.token && initialSpecId) {
      state.selectedSpecId = initialSpecId;
      els.deliveryInput.value = String(initialSpecId);
      els.deliveryInput.dataset.specId = String(initialSpecId);
    }
    if (state.token && initialSpecId) {
      await loadMatrix(0);
      if (initialRunId) await loadStoredRun(initialRunId);
      if (state.selectedSpecId) setView('recon');
      else setView('matrix');
    } else {
      setView('matrix');
    }
    renderMatrix();
    renderSelectedContext();
    renderProgress(null);
  }

  boot();
})();
