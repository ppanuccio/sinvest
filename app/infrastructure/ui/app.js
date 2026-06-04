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
});

document.getElementById('btn-list-portfolios').addEventListener('click', async () => {
  const user_id = document.getElementById('list-portfolios-user-id').value;
  const out = document.getElementById('out-list-portfolios');
  out.textContent = 'Loading...';
  const r = await get(`/users/${user_id}/portfolios`);
  out.textContent = JSON.stringify(r, null, 2);
});

document.getElementById('btn-create-investment').addEventListener('click', async () => {
  const user_id = document.getElementById('inv-user-id').value;
  const portfolio_id = document.getElementById('inv-portfolio-id').value;
  const identifier = document.getElementById('inv-identifier').value;
  const identifier_type = document.getElementById('inv-identifier-type').value;
  const type = document.getElementById('inv-type').value;
  const out = document.getElementById('out-create-investment');
  out.textContent = 'Creating...';
  const r = await post(`/users/${user_id}/portfolios/${portfolio_id}/investments`, {identifier, identifier_type, type});
  out.textContent = JSON.stringify(r, null, 2);
});

document.getElementById('btn-list-investments').addEventListener('click', async () => {
  const user_id = document.getElementById('list-inv-user-id').value;
  const portfolio_id = document.getElementById('list-inv-portfolio-id').value;
  const out = document.getElementById('out-list-investments');
  out.textContent = 'Loading...';
  const r = await get(`/users/${user_id}/portfolios/${portfolio_id}/investments`);
  out.textContent = JSON.stringify(r, null, 2);
});

document.getElementById('btn-create-transaction').addEventListener('click', async () => {
  const user_id = document.getElementById('tx-user-id').value;
  const investment_id = document.getElementById('tx-investment-id').value;
  const amount = document.getElementById('tx-amount').value;
  const quantity = document.getElementById('tx-quantity').value;
  const broker = document.getElementById('tx-broker').value;
  const date = document.getElementById('tx-date').value;
  const out = document.getElementById('out-create-transaction');
  out.textContent = 'Creating...';
  const r = await post(`/users/${user_id}/investments/${investment_id}/transactions`, {amount, quantity, broker, date});
  out.textContent = JSON.stringify(r, null, 2);
});

document.getElementById('btn-list-transactions').addEventListener('click', async () => {
  const user_id = document.getElementById('list-tx-user-id').value;
  const investment_id = document.getElementById('list-tx-investment-id').value;
  const out = document.getElementById('out-list-transactions');
  out.textContent = 'Loading...';
  const r = await get(`/users/${user_id}/investments/${investment_id}/transactions`);
  out.textContent = JSON.stringify(r, null, 2);
});
