const json = (r) => r.json().catch(() => ({}));

async function post(path, body) {
  const res = await fetch(path, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const data = await json(res);
  return {status: res.status, data};
}

async function get(path) {
  const res = await fetch(path);
  const data = await json(res);
  return {status: res.status, data};
}

async function listPortfoliosForUser(userId){
  const r = await get(`/users/${userId}/portfolios`);
  return r;
}

document.getElementById('btn-create-user').addEventListener('click', async () => {
  const username = document.getElementById('user-username').value;
  const email = document.getElementById('user-email').value;
  const password = document.getElementById('user-password').value;
  const out = document.getElementById('out-create-user');
  out.textContent = 'Creating...';
  const r = await post('/users', {username, email, password});
  out.textContent = JSON.stringify(r, null, 2);
});

document.getElementById('btn-create-portfolio').addEventListener('click', async () => {
  const user_id = document.getElementById('portfolio-user-id').value;
  const name = document.getElementById('portfolio-name').value;
  const description = document.getElementById('portfolio-description').value || null;
  const out = document.getElementById('out-create-portfolio');
  out.textContent = 'Creating...';
  const r = await post(`/users/${user_id}/portfolios`, {name, description});
  out.textContent = JSON.stringify(r, null, 2);
  // refresh select
  await refreshPortfolioSelect(user_id);
});

document.getElementById('btn-list-portfolios').addEventListener('click', async () => {
  const user_id = document.getElementById('portfolio-user-id').value;
  await refreshPortfolioSelect(user_id);
});

document.getElementById('btn-create-investment').addEventListener('click', async () => {
  const user_id = document.getElementById('portfolio-user-id').value;
  const portfolio_id = document.getElementById('portfolio-select').value;
  const identifier = document.getElementById('inv-identifier').value;
  const identifier_type = document.getElementById('inv-identifier-type').value;
  const type = document.getElementById('inv-type').value;
  const out = document.getElementById('out-create-investment');
  out.textContent = 'Creating...';
  const r = await post(`/users/${user_id}/portfolios/${portfolio_id}/investments`, {identifier, identifier_type, type});
  out.textContent = JSON.stringify(r, null, 2);
  // refresh investments
  await loadInvestments(user_id, portfolio_id);
});

document.getElementById('btn-list-investments').addEventListener('click', async () => {
  const user_id = document.getElementById('portfolio-user-id').value;
  const portfolio_id = document.getElementById('portfolio-select').value;
  await loadInvestments(user_id, portfolio_id);
});

document.getElementById('btn-create-transaction').addEventListener('click', async () => {
  const user_id = document.getElementById('portfolio-user-id').value;
  const investment_id = document.getElementById('tx-investment-id').value;
  const amount = document.getElementById('tx-amount').value;
  const quantity = document.getElementById('tx-quantity').value;
  const broker = document.getElementById('tx-broker').value;
  const date = document.getElementById('tx-date').value;
  const out = document.getElementById('out-create-transaction');
  out.textContent = 'Creating...';
  const r = await post(`/users/${user_id}/investments/${investment_id}/transactions`, {amount, quantity, broker, date});
  out.textContent = JSON.stringify(r, null, 2);
  // refresh transactions view
  await loadTransactions(user_id, investment_id);
});

document.getElementById('btn-list-transactions').addEventListener('click', async () => {
  const user_id = document.getElementById('portfolio-user-id').value;
  const investment_id = document.getElementById('tx-investment-id').value;
  await loadTransactions(user_id, investment_id);
});


async function refreshPortfolioSelect(userId){
  const sel = document.getElementById('portfolio-select');
  sel.innerHTML = '';
  if(!userId) return;
  const r = await listPortfoliosForUser(userId);
  if(r.status!==200) return;
  for(const p of r.data){
    const opt = document.createElement('option');
    opt.value = p.id; opt.textContent = `${p.name} (${p.id.slice(0,8)})`;
    sel.appendChild(opt);
  }
  // trigger load investments for first portfolio
  if(sel.options.length) {
    sel.selectedIndex = 0;
    const pid = sel.value;
    await loadInvestments(userId, pid);
    await loadAnalytics(userId, pid);
  }
}

async function loadInvestments(userId, portfolioId){
  const ul = document.getElementById('out-list-investments');
  ul.innerHTML = 'Loading...';
  if(!userId || !portfolioId) { ul.innerHTML='No portfolio selected'; return; }
  const r = await get(`/users/${userId}/portfolios/${portfolioId}/investments`);
  if(r.status!==200){ ul.innerHTML = JSON.stringify(r); return; }
  ul.innerHTML = '';
  for(const inv of r.data){
    const li = document.createElement('li');
    li.innerHTML = `<button data-inv-id="${inv.id}" class="select-inv">Select</button> <strong>${inv.identifier}</strong> — ${inv.type} <small>(${inv.id.slice(0,8)})</small>`;
    ul.appendChild(li);
  }
  document.querySelectorAll('.select-inv').forEach(btn=>btn.addEventListener('click', (e)=>{
    const id = e.currentTarget.getAttribute('data-inv-id');
    document.getElementById('tx-investment-id').value = id;
  }));
}

async function loadTransactions(userId, investmentId){
  const out = document.getElementById('out-list-transactions');
  out.textContent = 'Loading...';
  if(!userId || !investmentId){ out.textContent='Select investment first'; return; }
  const r = await get(`/users/${userId}/investments/${investmentId}/transactions`);
  if(r.status!==200){ out.textContent = JSON.stringify(r); return; }
  out.textContent = JSON.stringify(r.data, null, 2);
}

async function loadAnalytics(userId, portfolioId){
  const summary = document.getElementById('analytics-summary');
  summary.innerHTML = 'Loading...';
  if(!userId || !portfolioId){ summary.innerHTML='-'; return; }
  const r = await get(`/users/${userId}/portfolios/${portfolioId}/analytics`);
  if(r.status!==200){ summary.innerHTML = 'Error'; return; }
  const d = r.data;
  summary.innerHTML = '';
  const items = [
    ['Total Invested', d.total_invested],
    ['Total Value', d.total_value],
    ['Total Yield', `${d.total_yield} (${d.total_yield_percentage})`],
  ];
  for(const it of items){
    const div = document.createElement('div'); div.className='item'; div.innerHTML=`<strong>${it[0]}</strong><div>${it[1]}</div>`; summary.appendChild(div);
  }
}

// wire portfolio select change
document.getElementById('portfolio-select').addEventListener('change', async (e)=>{
  const pid = e.target.value; const uid=document.getElementById('portfolio-user-id').value; await loadInvestments(uid,pid); await loadAnalytics(uid,pid);
});

// when page loads, try to populate if user id present
window.addEventListener('load', ()=>{
  const uid = document.getElementById('portfolio-user-id').value;
  if(uid) refreshPortfolioSelect(uid);
});


document.getElementById('btn-get-analytics').addEventListener('click', async () => {
  const user_id = document.getElementById('analytics-user-id').value;
  const portfolio_id = document.getElementById('analytics-portfolio-id').value;
  const out = document.getElementById('out-analytics');
  out.innerHTML = 'Loading analytics...';
  const res = await get(`/users/${user_id}/portfolios/${portfolio_id}/analytics`);
  if (res.status !== 200) {
    out.textContent = JSON.stringify(res, null, 2);
    return;
  }
  const data = res.data;
  const html = [];
  html.push(`<div><strong>Total Invested:</strong> ${data.total_invested}</div>`);
  html.push(`<div><strong>Total Value:</strong> ${data.total_value}</div>`);
  html.push(`<div><strong>Total Yield:</strong> ${data.total_yield} (${data.total_yield_percentage})</div>`);
  html.push('<h4>Investments</h4>');
  html.push('<ul>');
  for (const inv of data.investments) {
    html.push(`<li><button data-inv-id="${inv.investment_id}" class="prefill-inv">Select</button> <strong>${inv.identifier}</strong> — qty: ${inv.total_quantity} — value: ${inv.total_value} — yield: ${inv.yield_amount} (${inv.yield_percentage})</li>`);
  }
  html.push('</ul>');
  out.innerHTML = html.join('');

  // add listeners to prefill buttons
  document.querySelectorAll('.prefill-inv').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const invId = e.currentTarget.getAttribute('data-inv-id');
      document.getElementById('tx-investment-id').value = invId;
      document.getElementById('list-tx-investment-id').value = invId;
      document.getElementById('inv-portfolio-id').value = portfolio_id;
      // if identifier present we won't prefill that here; user can select investment
    })
  });
});
