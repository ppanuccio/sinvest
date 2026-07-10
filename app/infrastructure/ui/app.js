const json = (res) => res.json().catch(() => ({}));
const AUTH_STORAGE_KEY = 'sinvest.auth';

const state = {
  userId: '',
  portfolioId: '',
  investmentId: '',
  analytics: null,
  investments: [],
  portfolio: null,
  authToken: '',
  authUsername: '',
  referenceCurrency: 'USD',
};

function setStatus(message, isError = false) {
  const banner = document.getElementById('status-message');
  banner.textContent = message;
  banner.style.background = isError ? '#fee2e2' : '#e5f3f1';
  banner.style.borderColor = isError ? '#fecaca' : '#d8e1ea';
  banner.style.color = isError ? '#991b1b' : '#0b555b';
}

function isMissing(value) {
  return (
    value === null
    || value === undefined
    || value === ''
    || value === '—'
    || Number.isNaN(Number(value))
  );
}

function formatMoney(value) {
  if (isMissing(value)) return '—';
  const currency = state.referenceCurrency || 'USD';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(Number(value));
}

function formatPercent(value) {
  if (isMissing(value)) return '—';
  return `${Number(value).toFixed(2)}%`;
}

async function request(method, path, body = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (state.authToken) {
    options.headers.Authorization = `Bearer ${state.authToken}`;
  }
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(path, options);
  return { status: res.status, data: await json(res) };
}

function saveAuth(tokenData) {
  state.authToken = tokenData.access_token;
  state.authUsername = tokenData.username;
  state.userId = tokenData.user_id;
  localStorage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({
      access_token: tokenData.access_token,
      username: tokenData.username,
      user_id: tokenData.user_id,
    }),
  );
  renderAuthState();
  updateStepIndicator(2);
  refreshPortfolios();
}

function restoreAuth() {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return;
  try {
    const tokenData = JSON.parse(raw);
    if (tokenData.access_token && tokenData.user_id) {
      saveAuth(tokenData);
    }
  } catch (error) {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

function clearAuth() {
  state.authToken = '';
  state.authUsername = '';
  state.userId = '';
  state.portfolioId = '';
  state.analytics = null;
  state.portfolio = null;
  state.investments = [];
  localStorage.removeItem(AUTH_STORAGE_KEY);
  renderAuthState();
  renderPortfolioMeta();
  renderOverview();
  renderComposition();
  renderInvestments();
  updateStepIndicator(1);
  setStatus('Signed out.');
}

function renderAuthState() {
  const authState = document.getElementById('auth-state');
  const userInfo = document.getElementById('user-info');
  const displayUsername = document.getElementById('display-username');
  const authForm = document.getElementById('auth-form');
  const loginForm = document.getElementById('login-form');

  if (state.authToken) {
    authState.classList.add('hidden');
    userInfo.classList.remove('hidden');
    authForm.classList.add('hidden');
    loginForm.classList.add('hidden');
    displayUsername.textContent = state.authUsername;
    document.getElementById('portfolio-section').classList.remove('hidden');
    document.getElementById('quick-add-section').style.display = 'grid';
  } else {
    authState.classList.add('hidden');
    userInfo.classList.add('hidden');
    authForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
    document.getElementById('portfolio-section').classList.add('hidden');
    document.getElementById('quick-add-section').style.display = 'none';
  }
}

function updateStepIndicator(step) {
  document.querySelectorAll('.step').forEach(el => {
    const s = parseInt(el.dataset.step, 10);
    el.classList.remove('active', 'complete');
    if (s < step) el.classList.add('complete');
    else if (s === step) el.classList.add('active');
  });
}

async function loadPortfolios(userId) {
  const res = await request('GET', `/users/${userId}/portfolios`);
  if (res.status !== 200) {
    setStatus('Failed to load portfolios.', true);
    return [];
  }
  return res.data;
}

async function refreshPortfolios() {
  const userId = state.userId;
  if (!userId) {
    setStatus('Not authenticated.', true);
    return;
  }
  const portfolios = await loadPortfolios(userId);
  const select = document.getElementById('portfolio-select');
  select.innerHTML = '<option value="" disabled selected>Select a portfolio...</option>';
  portfolios.forEach((portfolio) => {
    const option = document.createElement('option');
    option.value = portfolio.id;
    option.textContent = `${portfolio.name} • ${portfolio.description || 'no description'}`;
    select.appendChild(option);
  });
  if (portfolios.length === 0) {
    setStatus('No portfolios found. Create one to get started.');
    state.portfolioId = '';
    state.analytics = null;
    state.portfolio = null;
    state.investments = [];
    renderPortfolioMeta();
    renderOverview();
    renderComposition();
    renderInvestments();
    return;
  }
  setStatus('Portfolios loaded. Select one to continue.');
}

async function refreshDashboard() {
  if (!state.userId || !state.portfolioId) return;
  await loadPortfolioDetails(state.userId, state.portfolioId);
  await loadAnalytics(state.userId, state.portfolioId);
  await loadInvestments(state.userId, state.portfolioId);
}

async function loadPortfolioDetails(userId, portfolioId) {
  const res = await request('GET', `/users/${userId}/portfolios/${portfolioId}`);
  if (res.status !== 200) {
    state.portfolio = null;
    return;
  }
  state.portfolio = res.data;
  renderPortfolioMeta();
}

function renderPortfolioMeta() {
  const meta = document.getElementById('portfolio-meta');
  if (!state.portfolio) {
    meta.innerHTML = 'No portfolio selected.';
    return;
  }
  meta.innerHTML = `
    <div><strong>${state.portfolio.name}</strong></div>
    <div class="hint">${state.portfolio.description || 'No description provided'}</div>
  `;
}

async function createPortfolio() {
  const userId = state.userId;
  const name = document.getElementById('portfolio-name').value.trim();
  const description = document.getElementById('portfolio-description').value.trim();
  if (!userId || !name) {
    setStatus('Portfolio name is required.', true);
    return;
  }
  const res = await request('POST', `/users/${userId}/portfolios`, { name, description });
  if (res.status === 201 || res.status === 200) {
    setStatus('Portfolio created successfully.');
    document.getElementById('portfolio-name').value = '';
    document.getElementById('portfolio-description').value = '';
    toggleCreatePortfolioForm(false);
    await refreshPortfolios();
  } else {
    setStatus(res.data.detail || 'Failed to create portfolio.', true);
  }
  document.getElementById('out-create-portfolio').textContent = JSON.stringify(res, null, 2);
}

function toggleCreatePortfolioForm(show) {
  const form = document.getElementById('create-portfolio-form');
  const showBtn = document.getElementById('btn-show-create-portfolio');
  const hideBtn = document.getElementById('btn-hide-create-portfolio');
  if (show) {
    form.classList.remove('hidden');
    showBtn.classList.add('hidden');
    hideBtn.classList.remove('hidden');
  } else {
    form.classList.add('hidden');
    showBtn.classList.remove('hidden');
    hideBtn.classList.add('hidden');
  }
}

async function createInvestment() {
  const portfolioId = state.portfolioId;
  const userId = state.userId;
  const identifier = document.getElementById('inv-identifier').value.trim();
  const identifierType = document.getElementById('inv-identifier-type').value;
  const type = document.getElementById('inv-type').value;
  if (!userId || !portfolioId || !identifier) {
    setStatus('Select a portfolio and enter an investment identifier.', true);
    return;
  }
  const res = await request('POST', `/users/${userId}/portfolios/${portfolioId}/investments`, {
    portfolio_id: portfolioId,
    identifier,
    identifier_type: identifierType,
    type,
  });
  document.getElementById('out-create-investment').textContent = JSON.stringify(res, null, 2);
  if (res.status === 201 || res.status === 200) {
    setStatus('Investment added. Refreshing holdings.');
    document.getElementById('inv-identifier').value = '';
    await refreshDashboard();
  } else {
    setStatus(res.data.detail || 'Failed to add investment.', true);
  }
}

async function createUser() {
  const username = document.getElementById('user-username').value.trim();
  const email = document.getElementById('user-email').value.trim();
  const password = document.getElementById('user-password').value.trim();
  if (!username || !email || !password) {
    setStatus('Username, email, and password are required.', true);
    return;
  }
  const res = await request('POST', '/users', { username, email, password });
  document.getElementById('out-create-user').textContent = JSON.stringify(res, null, 2);
  if (res.status === 201 || res.status === 200) {
    setStatus('Account created. Signing in...');
    document.getElementById('login-username').value = username;
    document.getElementById('login-password').value = password;
    await login();
  } else {
    setStatus(res.data.detail || 'Failed to create account.', true);
  }
}

async function login() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value.trim();
  if (!username || !password) {
    setStatus('Username and password are required.', true);
    return;
  }

  const res = await request('POST', '/auth/login', { username, password });
  if (res.status === 200) {
    saveAuth(res.data);
    setStatus('Sign in successful.');
  } else {
    setStatus(res.data.detail || 'Sign in failed.', true);
  }
}

async function createTransaction() {
  const userId = state.userId;
  const investmentId = document.getElementById('tx-investment-id').value.trim();
  const amount = document.getElementById('tx-amount').value.trim();
  const quantity = document.getElementById('tx-quantity').value.trim();
  const broker = document.getElementById('tx-broker').value.trim();
  const date = document.getElementById('tx-date').value.trim();
  const currency = document.getElementById('tx-currency').value;
  if (!userId || !investmentId || !amount || !quantity || !broker || !date) {
    setStatus('All transaction fields are required.', true);
    return;
  }
  const res = await request('POST', `/users/${userId}/investments/${investmentId}/transactions`, {
    investment_id: investmentId,
    amount,
    quantity,
    broker,
    date,
    currency,
  });
  document.getElementById('out-create-transaction').textContent = JSON.stringify(res, null, 2);
  if (res.status === 201 || res.status === 200) {
    setStatus('Transaction created. Refreshing...');
    document.getElementById('tx-quantity').value = '';
    document.getElementById('tx-amount').value = '';
    document.getElementById('tx-broker').value = '';
    await loadTransactions(userId, investmentId);
    await refreshDashboard();
  } else {
    setStatus(res.data.detail || 'Failed to create transaction.', true);
  }
}

async function loadAnalytics(userId, portfolioId) {
  const refCurrency = state.referenceCurrency || 'USD';
  const res = await request('GET', `/users/${userId}/portfolios/${portfolioId}/analytics?reference_currency=${refCurrency}`);
  if (res.status !== 200) {
    setStatus('Unable to load portfolio analytics.', true);
    state.analytics = null;
    renderOverview();
    return;
  }
  state.analytics = res.data;
  if (Array.isArray(res.data.investments)) {
    state.investments = res.data.investments;
    renderInvestments();
  }
  renderOverview();
  renderComposition();
}

async function loadInvestments(userId, portfolioId) {
  const res = await request('GET', `/users/${userId}/portfolios/${portfolioId}/investments`);
  if (res.status !== 200) {
    setStatus('Unable to load investment holdings.', true);
    state.investments = [];
    renderInvestments();
    return;
  }
  const analyticsRows = Array.isArray(state.analytics?.investments) ? state.analytics.investments : [];
  if (analyticsRows.length > 0) {
    const rawById = new Map(res.data.map((inv) => [inv.id, inv]));
    state.investments = analyticsRows.map((inv) => {
      const raw = rawById.get(inv.investment_id) || {};
      return {
        ...inv,
        identifier: inv.identifier || raw.identifier,
        type: inv.type || raw.type,
      };
    });
  } else {
    state.investments = res.data.map((inv) => ({
      investment_id: inv.id,
      identifier: inv.identifier,
      type: inv.type,
      total_quantity: '—',
      current_price: '—',
      total_invested: '—',
      total_value: '—',
      yield_amount: '—',
      yield_percentage: '—',
      allocation_percentage: '—',
    }));
  }
  renderInvestments();
}

async function fetchPrice(investmentId, identifier) {
  const userId = state.userId;
  if (!userId || !investmentId) {
    setStatus('Select an investment first.', true);
    return;
  }
  setStatus(`Fetching live price for ${identifier} from Yahoo Finance...`);
  const res = await request('POST', `/users/${userId}/investments/${investmentId}/prices/fetch`);
  if (res.status === 201) {
    setStatus(`✅ ${identifier}: ${formatMoney(res.data.price)} as of ${res.data.date}`);
    await refreshDashboard();
  } else {
    setStatus(res.data.detail || `Failed to fetch price for ${identifier}.`, true);
  }
}

async function deleteInvestment(investmentId, identifier) {
  const userId = state.userId;
  if (!userId || !investmentId) return;

  if (!confirm(`Delete ${identifier} and all its transactions and price history?`)) return;

  const res = await request('DELETE', `/users/${userId}/investments/${investmentId}`);
  if (res.status === 204) {
    setStatus(`🗑️ Deleted ${identifier}.`);
    await refreshDashboard();
  } else {
    setStatus(res.data.detail || `Failed to delete ${identifier}.`, true);
  }
}

async function fetchAllPrices() {
  const userId = state.userId;
  const portfolioId = state.portfolioId;
  if (!userId || !portfolioId) {
    setStatus('Select a portfolio first.', true);
    return;
  }

  // Get all investment IDs from the analytics
  const investments = state.investments;
  if (!investments || investments.length === 0) {
    setStatus('No investments to fetch prices for.', true);
    return;
  }

  const investmentIds = investments
    .map(inv => inv.investment_id)
    .filter(id => id);

  if (investmentIds.length === 0) {
    setStatus('No valid investment IDs found.', true);
    return;
  }

  setStatus(`Fetching live prices for ${investmentIds.length} investment(s) from Yahoo Finance...`);
  const res = await request('POST', `/users/${userId}/investments/prices/fetch-batch`, investmentIds);
  if (res.status === 201) {
    const count = Array.isArray(res.data) ? res.data.length : 0;
    setStatus(`✅ Fetched ${count} price(s) successfully.`);
    await refreshDashboard();
  } else {
    setStatus(res.data.detail || 'Failed to fetch prices.', true);
  }
}
  async function loadTransactions(userId, investmentId) {
  const output = document.getElementById('out-list-transactions');
  if (!investmentId) {
    output.textContent = 'Select an investment to view transaction history.';
    return;
  }
  const res = await request('GET', `/users/${userId}/investments/${investmentId}/transactions`);
  if (res.status !== 200) {
    output.textContent = 'Unable to load transactions.';
    return;
  }
  const list = res.data;
  if (!Array.isArray(list) || list.length === 0) {
    output.textContent = 'No transactions found for this investment.';
    return;
  }
  output.textContent = list
    .map((item) => `${item.date} • ${item.quantity} @ ${formatMoney(item.amount)} ${item.currency || 'USD'} • ${item.broker}`)
    .join('\n');
}

function renderOverview() {
  const valueEl = document.getElementById('summary-value');
  const investedEl = document.getElementById('summary-invested');
  const yieldEl = document.getElementById('summary-yield');
  if (!state.analytics) {
    valueEl.textContent = '–';
    investedEl.textContent = '–';
    yieldEl.textContent = '–';
    return;
  }
  valueEl.textContent = formatMoney(state.analytics.total_value);
  investedEl.textContent = formatMoney(state.analytics.total_invested);
  yieldEl.textContent = `${formatMoney(state.analytics.total_yield)} (${formatPercent(state.analytics.total_yield_percentage)})`;
  yieldEl.className = Number(state.analytics.total_yield) >= 0 ? 'positive' : 'negative';
}

function renderComposition() {
  const list = document.getElementById('composition-list');
  list.innerHTML = '';
  if (
    !state.analytics
    || !Array.isArray(state.analytics.investments)
    || state.analytics.investments.length === 0
  ) {
    list.innerHTML = '<li class="composition-item"><div><strong>No allocation yet</strong><div class="hint">Add investments and transactions to build the asset mix.</div></div><div class="bar"><span style="width:0%"></span></div></li>';
    return;
  }
  const groups = state.analytics.investments.reduce((acc, inv) => {
    acc[inv.type] = (acc[inv.type] || 0) + Number(inv.total_value || 0);
    return acc;
  }, {});
  const total = Object.values(groups).reduce((sum, value) => sum + value, 0);
  Object.entries(groups).sort((a, b) => b[1] - a[1]).forEach(([type, value]) => {
    const percent = total ? (value / total) * 100 : 0;
    const item = document.createElement('li');
    item.className = 'composition-item';
    item.innerHTML = `
      <div>
        <div><strong>${type.toUpperCase()}</strong></div>
        <div>${formatMoney(value)} • ${percent.toFixed(1)}%</div>
      </div>
      <div class="bar"><span style="width:${percent}%"></span></div>
    `;
    list.appendChild(item);
  });
  if (list.children.length === 0) {
    list.innerHTML = '<li class="composition-item">No holdings yet. Add an investment to see composition.</li>';
  }
}

function renderInvestments() {
  const tbody = document.getElementById('investments-table');
  const countEl = document.getElementById('holdings-count');
  tbody.innerHTML = '';
  if (!Array.isArray(state.investments) || state.investments.length === 0) {
    tbody.innerHTML = '<tr><td class="empty-row" colspan="10">No investments found. Add your first investment using the form on the left.</td></tr>';
    countEl.textContent = '';
    return;
  }
  countEl.textContent = `${state.investments.length} holding${state.investments.length !== 1 ? 's' : ''}`;
  state.investments.forEach((inv) => {
    const row = document.createElement('tr');
    const gainClass = Number(inv.yield_amount) >= 0 ? 'positive' : 'negative';
    const shortId = inv.investment_id ? inv.investment_id.slice(0, 8) : 'pending';
    const hasPrice = inv.current_price !== null && inv.current_price !== undefined && inv.current_price !== '—' && !Number.isNaN(Number(inv.current_price));
    row.innerHTML = `
      <td><strong>${inv.identifier || 'Unknown asset'}</strong><div class="hint">${shortId}</div></td>
      <td><span class="tag">${inv.type || 'other'}</span></td>
      <td>${inv.total_quantity}</td>
      <td>${formatMoney(inv.current_price)}</td>
      <td>${formatMoney(inv.total_invested)}</td>
      <td>${formatMoney(inv.total_value)}</td>
      <td class="${gainClass}">${formatMoney(inv.yield_amount)} (${formatPercent(inv.yield_percentage)})</td>
      <td>${formatPercent(inv.allocation_percentage)}</td>
      <td style="white-space: nowrap;">
        <button class="fetch-price-btn" data-investment-id="${inv.investment_id}" data-identifier="${inv.identifier || ''}" title="Fetch live price from Yahoo Finance">
          ${hasPrice ? '↻' : 'Fetch'}
        </button>
        <button class="delete-btn" data-investment-id="${inv.investment_id}" data-identifier="${inv.identifier || ''}" title="Delete investment">🗑</button>
      </td>
    `;
    row.dataset.investmentId = inv.investment_id || '';
    row.dataset.identifier = inv.identifier || '';
    row.addEventListener('click', () => selectInvestment(inv));
    row.addEventListener('dblclick', () => {
      if (inv.investment_id) loadTransactions(state.userId, inv.investment_id);
    });
    if (inv.investment_id === state.investmentId) {
      row.classList.add('selected');
    }
    tbody.appendChild(row);
  });

  // Attach click handlers to fetch-price buttons
  document.querySelectorAll('.fetch-price-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const invId = btn.dataset.investmentId;
      const identifier = btn.dataset.identifier;
      if (invId) fetchPrice(invId, identifier);
    });
  });

  // Attach click handlers to delete buttons
  document.querySelectorAll('.delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const invId = btn.dataset.investmentId;
      const identifier = btn.dataset.identifier;
      if (invId) deleteInvestment(invId, identifier);
    });
  });
}

function selectInvestment(inv) {
  if (!inv.investment_id) return;
  state.investmentId = inv.investment_id;

  // Update UI selection
  document.querySelectorAll('#investments-table tr').forEach(r => r.classList.remove('selected'));
  const selectedRow = document.querySelector(`#investments-table tr[data-investment-id="${inv.investment_id}"]`);
  if (selectedRow) selectedRow.classList.add('selected');

  // Show and prefill transaction form
  document.getElementById('tx-no-selection').classList.add('hidden');
  document.getElementById('tx-form').classList.remove('hidden');
  document.getElementById('tx-investment-id').value = inv.investment_id;
  document.getElementById('tx-quantity').value = '';
  document.getElementById('tx-amount').value = '';
  document.getElementById('tx-currency').value = 'USD';
  document.getElementById('tx-broker').value = '';
  document.getElementById('tx-date').value = new Date().toISOString().slice(0, 16);

  // Update badge
  const badge = document.getElementById('tx-investment-badge');
  badge.textContent = inv.identifier;
  badge.classList.remove('hidden');

  loadTransactions(state.userId, inv.investment_id);
  setStatus(`Selected ${inv.identifier}. Fill in transaction details and click "Add Transaction".`);
}

function initializeEventListeners() {
  // Auth toggles
  document.getElementById('btn-show-login').addEventListener('click', () => {
    document.getElementById('auth-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
  });
  document.getElementById('btn-show-create').addEventListener('click', () => {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('auth-form').classList.remove('hidden');
  });

  // Auth actions
  document.getElementById('btn-create-user').addEventListener('click', createUser);
  document.getElementById('btn-login').addEventListener('click', login);
  document.getElementById('btn-logout').addEventListener('click', clearAuth);

  // Portfolio actions
  document.getElementById('btn-create-portfolio').addEventListener('click', createPortfolio);
  document.getElementById('btn-show-create-portfolio').addEventListener('click', () => toggleCreatePortfolioForm(true));
  document.getElementById('btn-hide-create-portfolio').addEventListener('click', () => toggleCreatePortfolioForm(false));

  document.getElementById('portfolio-select').addEventListener('change', async (event) => {
    state.portfolioId = event.target.value;
    if (!state.userId || !state.portfolioId) {
      setStatus('Select a valid portfolio first.', true);
      return;
    }
    updateStepIndicator(3);
    setStatus('Loading portfolio...');
    await loadPortfolioDetails(state.userId, state.portfolioId);
    await loadAnalytics(state.userId, state.portfolioId);
    await loadInvestments(state.userId, state.portfolioId);
  });

  // Quick actions
  document.getElementById('btn-create-investment').addEventListener('click', createInvestment);
  document.getElementById('btn-create-transaction').addEventListener('click', createTransaction);
  document.getElementById('btn-refresh').addEventListener('click', refreshDashboard);
  document.getElementById('btn-fetch-all-prices').addEventListener('click', fetchAllPrices);

  // Reference currency selector
  document.getElementById('ref-currency').addEventListener('change', async (event) => {
    state.referenceCurrency = event.target.value;
    if (state.userId && state.portfolioId) {
      setStatus(`Reloading analytics in ${state.referenceCurrency}...`);
      await loadAnalytics(state.userId, state.portfolioId);
      await loadInvestments(state.userId, state.portfolioId);
    }
  });

  // Ticker validation on input
  let tickerCheckTimeout = null;
  const tickerInput = document.getElementById('inv-identifier');
  const tickerWarning = document.getElementById('ticker-warning');
  const tickerHint = document.getElementById('ticker-hint');
  const addInvBtn = document.getElementById('btn-create-investment');
  const idTypeSelect = document.getElementById('inv-identifier-type');

  function clearTickerWarning() {
    tickerWarning.classList.add('hidden');
    tickerWarning.className = 'ticker-warning hidden';
    tickerWarning.innerHTML = '';
    addInvBtn.disabled = false;
    if (tickerHint) tickerHint.classList.remove('hidden');
  }

  async function checkTicker(value) {
    if (!value || value.length < 2 || idTypeSelect.value !== 'TICKER') {
      clearTickerWarning();
      return;
    }
    // If already has a suffix, we still check but with different messaging
    try {
      const res = await fetch(`/ticker/check?symbol=${encodeURIComponent(value)}`);
      const data = await res.json();
      if (data.exact) {
        // Ticker is valid and unambiguous
        tickerWarning.className = 'ticker-warning valid';
        tickerWarning.innerHTML = `✅ "${value}" is valid.`;
        tickerWarning.classList.remove('hidden');
        addInvBtn.disabled = false;
        if (tickerHint) tickerHint.classList.add('hidden');
      } else if (data.suggestions && data.suggestions.length > 0) {
        // Ticker is ambiguous — show suggestions
        let html = `⚠️ "<strong>${value}</strong>" is ambiguous. Use one of these:<br>`;
        data.suggestions.slice(0, 6).forEach(s => {
          const exchange = s.exchange ? `<span class="exchange-tag">${s.exchange}</span>` : '';
          const name = s.shortName || '';
          html += `<span class="suggestion-item">• <strong>${s.symbol}</strong> — ${name} ${exchange}</span>`;
        });
        tickerWarning.className = 'ticker-warning';
        tickerWarning.innerHTML = html;
        tickerWarning.classList.remove('hidden');
        addInvBtn.disabled = true;
        if (tickerHint) tickerHint.classList.add('hidden');
      } else if (data.suggestions && data.suggestions.length === 0 && !data.exact) {
        // No results at all - show error
        tickerWarning.className = 'ticker-warning error';
        tickerWarning.innerHTML = `❌ No exchange listings found for "<strong>${value}</strong>".`;
        tickerWarning.classList.remove('hidden');
        addInvBtn.disabled = true;
        if (tickerHint) tickerHint.classList.add('hidden');
      } else {
        clearTickerWarning();
      }
    } catch (err) {
      // Silently fail — don't block the user from adding investments
      clearTickerWarning();
    }
  }

  tickerInput.addEventListener('input', () => {
    clearTimeout(tickerCheckTimeout);
    const value = tickerInput.value.trim();
    if (value.length < 2) {
      clearTickerWarning();
      return;
    }
    tickerCheckTimeout = setTimeout(() => checkTicker(value), 350);
  });

  idTypeSelect.addEventListener('change', () => {
    if (idTypeSelect.value !== 'TICKER') {
      clearTickerWarning();
    }
  });

  // Set default date to now
  document.getElementById('tx-date').value = new Date().toISOString().slice(0, 16);
}

window.addEventListener('load', () => {
  initializeEventListeners();
  restoreAuth();
  renderPortfolioMeta();
  renderOverview();
  renderComposition();
  renderInvestments();
  updateStepIndicator(state.authToken ? 2 : 1);
});