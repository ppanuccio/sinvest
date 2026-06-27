const json = (res) => res.json().catch(() => ({}));

const state = {
  userId: '',
  portfolioId: '',
  investmentId: '',
  analytics: null,
  investments: [],
  portfolio: null,
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
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value));
}

function formatPercent(value) {
  if (isMissing(value)) return '—';
  return `${Number(value).toFixed(2)}%`;
}

async function request(method, path, body = null) {
  const options = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) options.body = JSON.stringify(body);
  const res = await fetch(path, options);
  return { status: res.status, data: await json(res) };
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
  const userId = document.getElementById('portfolio-user-id').value.trim();
  if (!userId) {
    setStatus('Enter a user ID to load portfolios.', true);
    return;
  }
  const portfolios = await loadPortfolios(userId);
  const select = document.getElementById('portfolio-select');
  select.innerHTML = '<option value="" disabled selected>Select portfolio...</option>';
  portfolios.forEach((portfolio) => {
    const option = document.createElement('option');
    option.value = portfolio.id;
    option.textContent = `${portfolio.name} • ${portfolio.description || 'no description'}`;
    select.appendChild(option);
  });
  if (portfolios.length === 0) {
    setStatus('No portfolios found for this user. Create one to get started.');
    state.userId = userId;
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
  state.userId = userId;
  state.portfolioId = '';
  state.analytics = null;
  state.portfolio = null;
  state.investments = [];
  setStatus('Portfolios loaded. Choose one to view holdings.');
  renderPortfolioMeta();
  renderOverview();
  renderComposition();
  renderInvestments();
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
  const userId = document.getElementById('portfolio-user-id').value.trim();
  const name = document.getElementById('portfolio-name').value.trim();
  const description = document.getElementById('portfolio-description').value.trim();
  if (!userId || !name) {
    setStatus('User ID and portfolio name are required.', true);
    return;
  }
  const res = await request('POST', `/users/${userId}/portfolios`, { name, description });
  if (res.status === 201 || res.status === 200) {
    setStatus('Portfolio created successfully.');
    await refreshPortfolios();
  } else {
    setStatus(res.data.detail || 'Failed to create portfolio.', true);
  }
  document.getElementById('out-create-portfolio').textContent = JSON.stringify(res, null, 2);
}

async function createInvestment() {
  const portfolioId = document.getElementById('portfolio-select').value;
  const userId = document.getElementById('portfolio-user-id').value.trim();
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
    setStatus('Username, email, and password are required to create an account.', true);
    return;
  }
  const res = await request('POST', '/users', { username, email, password });
  document.getElementById('out-create-user').textContent = JSON.stringify(res, null, 2);
  if (res.status === 201 || res.status === 200) {
    setStatus('User created. Paste the returned ID into the User ID field to continue.');
    const userId = res.data.id || '';
    if (userId) {
      document.getElementById('portfolio-user-id').value = userId;
    }
  } else {
    setStatus(res.data.detail || 'Failed to create user.', true);
  }
}

async function createTransaction() {
  const userId = document.getElementById('portfolio-user-id').value.trim();
  const investmentId = document.getElementById('tx-investment-id').value.trim();
  const amount = document.getElementById('tx-amount').value.trim();
  const quantity = document.getElementById('tx-quantity').value.trim();
  const broker = document.getElementById('tx-broker').value.trim();
  const date = document.getElementById('tx-date').value.trim();
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
  });
  document.getElementById('out-create-transaction').textContent = JSON.stringify(res, null, 2);
  if (res.status === 201 || res.status === 200) {
    setStatus('Transaction created. Refreshing transaction history.');
    await loadTransactions(userId, investmentId);
    await refreshDashboard();
  } else {
    setStatus(res.data.detail || 'Failed to create transaction.', true);
  }
}

async function loadAnalytics(userId, portfolioId) {
  const res = await request('GET', `/users/${userId}/portfolios/${portfolioId}/analytics`);
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
    // If the API returns InvestmentResponseModel list, convert to minimal analytics-like structure.
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
    .map((item) => `${item.date} • ${item.quantity} @ ${formatMoney(item.amount)} • ${item.broker}`)
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
  tbody.innerHTML = '';
  if (!Array.isArray(state.investments) || state.investments.length === 0) {
    tbody.innerHTML = '<tr><td class="empty-row" colspan="8">No investments found for this portfolio.</td></tr>';
    return;
  }
  state.investments.forEach((inv) => {
    const row = document.createElement('tr');
    const gainClass = Number(inv.yield_amount) >= 0 ? 'positive' : 'negative';
    const shortId = inv.investment_id ? inv.investment_id.slice(0, 8) : 'pending';
    row.innerHTML = `
      <td><strong>${inv.identifier || 'Unknown asset'}</strong><div class="hint">${shortId}</div></td>
      <td><span class="tag">${inv.type || 'other'}</span></td>
      <td>${inv.total_quantity}</td>
      <td>${formatMoney(inv.current_price)}</td>
      <td>${formatMoney(inv.total_invested)}</td>
      <td>${formatMoney(inv.total_value)}</td>
      <td class="${gainClass}">${formatMoney(inv.yield_amount)} (${formatPercent(inv.yield_percentage)})</td>
      <td>${formatPercent(inv.allocation_percentage)}</td>
    `;
    row.addEventListener('click', () => {
      if (!inv.investment_id) return;
      state.investmentId = inv.investment_id;
      document.getElementById('tx-investment-id').value = inv.investment_id;
      loadTransactions(state.userId, inv.investment_id);
      setStatus(`Selected ${inv.identifier}. Add a transaction below.`);
    });
    tbody.appendChild(row);
  });
}

function initializeEventListeners() {
  document.getElementById('btn-list-portfolios').addEventListener('click', refreshPortfolios);
  document.getElementById('btn-refresh-portfolio').addEventListener('click', refreshPortfolios);
  document.getElementById('btn-create-user').addEventListener('click', createUser);
  document.getElementById('btn-create-portfolio').addEventListener('click', createPortfolio);
  document.getElementById('btn-create-investment').addEventListener('click', createInvestment);
  document.getElementById('btn-create-transaction').addEventListener('click', createTransaction);
  document.getElementById('btn-refresh').addEventListener('click', refreshDashboard);
  document.getElementById('portfolio-select').addEventListener('change', async (event) => {
    state.portfolioId = event.target.value;
    if (!state.userId || !state.portfolioId) {
      setStatus('Select a valid portfolio and user first.', true);
      return;
    }
    setStatus('Loading selected portfolio...');
    await loadPortfolioDetails(state.userId, state.portfolioId);
    await loadAnalytics(state.userId, state.portfolioId);
    await loadInvestments(state.userId, state.portfolioId);
  });
}

window.addEventListener('load', () => {
  initializeEventListeners();
  renderPortfolioMeta();
  renderOverview();
  renderComposition();
  renderInvestments();
  const userId = document.getElementById('portfolio-user-id').value.trim();
  if (userId) {
    refreshPortfolios();
  }
});
