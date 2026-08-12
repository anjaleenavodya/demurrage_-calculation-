// Global state
let delayRecords = [];
let currentUser = null;

// Application Initialization
window.addEventListener('DOMContentLoaded', () => {
  // Check active session
  checkSession();

  // Setup default input dates
  initDefaultDates();
});

// Session Management
async function checkSession() {
  try {
    const res = await fetch('/api/auth/me');
    if (res.ok) {
      currentUser = await res.json();
      showApp();
    } else {
      showLogin();
    }
  } catch (err) {
    showLogin();
  }
}

function showLogin() {
  document.getElementById('login-overlay').style.display = 'flex';
  document.getElementById('app-main').style.display = 'none';
  document.getElementById('user-control-bar').style.display = 'none';
  currentUser = null;
}

function showApp() {
  document.getElementById('login-overlay').style.display = 'none';
  document.getElementById('app-main').style.display = 'grid';
  document.getElementById('user-control-bar').style.display = 'flex';
  document.getElementById('current-user-name').textContent = currentUser.username;
  document.getElementById('current-user-role').textContent = currentUser.role;

  // Toggle admin tab visibility
  const adminTab = document.getElementById('btn-admin-tab');
  if (currentUser.role === 'admin') {
    adminTab.style.display = 'block';
    loadUsers();
  } else {
    adminTab.style.display = 'none';
  }

  // Load calculations history
  loadHistory();
}

async function handleLogin() {
  const usernameInput = document.getElementById('login_username');
  const passwordInput = document.getElementById('login_password');

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }

    currentUser = await res.json();
    usernameInput.value = '';
    passwordInput.value = '';
    showApp();
  } catch (err) {
    alert("Login failed: " + err.message);
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch (err) {
    console.error("Logout request error", err);
  }
  showLogin();
}

// Input and Display Tab Swapping
function switchInputTab(tabId) {
  // Hide all input tabs
  document.querySelectorAll('#inputs-panel .tab-content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('#inputs-panel .tab-btn').forEach(b => b.classList.remove('active'));

  // Show active tab
  document.getElementById(tabId).classList.add('active');

  // Update header buttons state
  const btnIdx = { 'tab-vessel': 0, 'tab-times': 1, 'tab-delays': 2 }[tabId];
  document.querySelectorAll('#inputs-panel .tab-btn')[btnIdx].classList.add('active');
}

function switchDisplayTab(tabId) {
  // Hide all display tabs
  document.querySelectorAll('#display-panel .display-tab-content').forEach(c => c.classList.remove('active'));
  document.querySelectorAll('#display-panel .tab-btn').forEach(b => b.classList.remove('active'));

  // Show active tab
  document.getElementById(tabId).classList.add('active');

  // Update header buttons state
  const tabButtons = document.querySelectorAll('#display-panel .tab-btn');
  if (tabId === 'tab-result') tabButtons[0].classList.add('active');
  if (tabId === 'tab-history') tabButtons[1].classList.add('active');
  if (tabId === 'tab-admin') tabButtons[2].classList.add('active');
}

// Helper to set start dates
function initDefaultDates() {
  const today = new Date();
  const formatLocalDate = (date) => date.toISOString().split('T')[0];

  const start = new Date(today);
  const end = new Date(today);
  end.setDate(end.getDate() + 2);

  document.getElementById('laycan_start').value = formatLocalDate(start);
  document.getElementById('laycan_end').value = formatLocalDate(end);

  const arrival = new Date(start);
  arrival.setHours(10, 0, 0, 0);

  const norTendered = new Date(arrival);
  norTendered.setMinutes(15);

  const norAccepted = new Date(arrival);
  norAccepted.setHours(11, 0, 0, 0);

  const disconnected = new Date(arrival);
  disconnected.setDate(disconnected.getDate() + 5);
  disconnected.setHours(14, 30, 0, 0);

  document.getElementById('arrival_time').value = formatLocalDateTime(arrival);
  document.getElementById('nor_tendered').value = formatLocalDateTime(norTendered);
  document.getElementById('nor_accepted').value = formatLocalDateTime(norAccepted);
  document.getElementById('loading_arm_disconnected').value = formatLocalDateTime(disconnected);
}

function formatLocalDateTime(date) {
  const pad = (num) => String(num).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDisplayDateTime(isoStr) {
  if (!isoStr) return '-';
  const date = new Date(isoStr);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  });
}

// Delay Rows Management
function addDelayRow() {
  const reasonInput = document.getElementById('delay_reason');
  const durationInput = document.getElementById('delay_duration');
  const partyInput = document.getElementById('delay_party');

  const reason = reasonInput.value.trim();
  const duration = parseFloat(durationInput.value);
  const party = partyInput.value;

  if (!reason || isNaN(duration) || duration <= 0) {
    alert("Please enter a valid delay reason and duration in hours.");
    return;
  }

  delayRecords.push({ reason, duration, party });

  reasonInput.value = '';
  durationInput.value = '';
  renderDelays();
}

function removeDelayRow(index) {
  delayRecords.splice(index, 1);
  renderDelays();
}

function renderDelays() {
  const tbody = document.getElementById('delay-table-body');
  tbody.innerHTML = '';

  delayRecords.forEach((item, index) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(item.reason)}</td>
      <td><span class="version" style="background: ${item.party === 'vessel' ? 'var(--accent-bg)' : 'var(--success-bg)'}; color: ${item.party === 'vessel' ? 'var(--accent)' : 'var(--success)'}">${item.party.toUpperCase()}</span></td>
      <td>${item.duration.toFixed(1)} hrs</td>
      <td><button class="btn-remove" onclick="removeDelayRow(${index})">✕</button></td>
    `;
    tbody.appendChild(tr);
  });
}

// Submit Calculations to FastAPI
async function submitCalculation() {
  const requestData = {
    vessel_name: document.getElementById('vessel_name').value,
    cargo_type: document.getElementById('cargo_type').value,
    berth_type: document.getElementById('berth_type').value,
    laycan_start: document.getElementById('laycan_start').value,
    laycan_end: document.getElementById('laycan_end').value,
    arrival_time: document.getElementById('arrival_time').value,
    nor_tendered: document.getElementById('nor_tendered').value,
    nor_accepted: document.getElementById('nor_accepted').value,
    loading_arm_disconnected: document.getElementById('loading_arm_disconnected').value,
    terminal_requested_early: document.getElementById('terminal_requested_early').checked,
    terminal_granted_permission_late: document.getElementById('terminal_granted_permission_late').checked,
    berths_count: parseInt(document.getElementById('berths_count').value) || 1,
    vessel_delays: delayRecords.filter(d => d.party === 'vessel').map(d => ({ reason: d.reason, duration: d.duration })),
    terminal_delays: delayRecords.filter(d => d.party === 'terminal').map(d => ({ reason: d.reason, duration: d.duration }))
  };

  try {
    const response = await fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestData)
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Calculation failed.");
    }

    const data = await response.json();

    // Switch to results tab & render it
    switchDisplayTab('tab-result');
    renderResults(data);

    // Reload history log to show the saved record
    loadHistory();
  } catch (error) {
    alert("Error performing calculation: " + error.message);
  }
}

// Render calculation outputs
function renderResults(res) {
  document.getElementById('results-empty').style.display = 'none';
  document.getElementById('results-content').style.display = 'flex';

  const badge = document.getElementById('demurrage-badge');
  const title = document.getElementById('badge-title');
  const subtitle = document.getElementById('badge-subtitle');

  if (res.demurrage_payable) {
    badge.className = 'result-status demurrage-due';
    title.textContent = `DEMURRAGE PAYABLE: ${res.demurrage_hours.toFixed(2)} HOURS`;
    subtitle.textContent = `Vessel exceeded allowed laytime of ${res.allowed_laytime_hours} hours.`;
  } else {
    badge.className = 'result-status no-demurrage';
    title.textContent = 'NO DEMURRAGE';
    subtitle.textContent = `Operations completed within allowed laytime.`;
  }

  document.getElementById('rule-explanation').textContent = res.rule_applied;
  document.getElementById('calculated-start-time').textContent = formatDisplayDateTime(res.laycan_start_time);

  document.getElementById('elapsed-hours').textContent = res.actual_elapsed_hours.toFixed(2);
  document.getElementById('operational-hours').textContent = res.operational_time_hours.toFixed(2);

  const netOpWrapper = document.getElementById('net-operational-wrapper');
  if (res.operational_time_hours > res.allowed_laytime_hours) {
    netOpWrapper.style.color = 'var(--danger)';
  } else {
    netOpWrapper.style.color = 'var(--success)';
  }

  document.getElementById('vessel-delay-sum').textContent = `${res.total_vessel_delays_hours.toFixed(1)}h`;
  document.getElementById('terminal-delay-sum').textContent = `${res.total_terminal_delays_hours.toFixed(1)}h`;

  const totalDelays = res.total_vessel_delays_hours + res.total_terminal_delays_hours;
  let vesselPct = 0;
  let terminalPct = 0;
  if (totalDelays > 0) {
    vesselPct = (res.total_vessel_delays_hours / totalDelays) * 100;
    terminalPct = (res.total_terminal_delays_hours / totalDelays) * 100;
  }
  document.getElementById('vessel-bar-fill').style.width = `${vesselPct}%`;
  document.getElementById('terminal-bar-fill').style.width = `${terminalPct}%`;

  const nettingExpl = document.getElementById('netting-explanation');
  if (res.total_vessel_delays_hours > res.total_terminal_delays_hours) {
    nettingExpl.innerHTML = `Vessel delays exceed terminal delays. Net Vessel Delay: <strong>${res.net_vessel_delays_hours.toFixed(1)}h</strong> (deducted).`;
  } else if (res.total_terminal_delays_hours > res.total_vessel_delays_hours) {
    nettingExpl.innerHTML = `Terminal delays exceed vessel delays. Net Terminal Delay: <strong>${res.net_terminal_delays_hours.toFixed(1)}h</strong> (laytime).`;
  } else {
    nettingExpl.innerHTML = `Delays perfectly offset. Net deduction: <strong>0h</strong>.`;
  }

  document.getElementById('val-elapsed').textContent = `${res.actual_elapsed_hours.toFixed(2)} hrs`;
  document.getElementById('val-allowed').textContent = `${res.allowed_laytime_hours.toFixed(2)} hrs`;
  document.getElementById('val-shifting').textContent = `-${res.shifting_deduction_hours.toFixed(2)} hrs`;
  document.getElementById('val-net-vessel-delay').textContent = `-${res.net_vessel_delays_hours.toFixed(2)} hrs`;
  document.getElementById('val-operational').textContent = `${res.operational_time_hours.toFixed(2)} hrs`;
  document.getElementById('val-demurrage').textContent = `${res.demurrage_hours.toFixed(2)} hrs`;
}

// Load and render history items
async function loadHistory() {
  try {
    const res = await fetch('/api/calculations');
    if (!res.ok) throw new Error("Could not load history");
    const items = await res.json();
    renderHistory(items);
  } catch (err) {
    console.error("Error loading history", err);
  }
}

function renderHistory(items) {
  const container = document.getElementById('history-list-body');
  container.innerHTML = '';

  if (items.length === 0) {
    container.innerHTML = `<div class="welcome-msg"><h3>No calculations saved</h3><p>Calculations you perform will appear here.</p></div>`;
    return;
  }

  items.forEach(item => {
    const li = document.createElement('li');
    li.className = 'history-item';
    li.onclick = () => loadCalculationIntoForm(item);

    const isDem = item.result.demurrage_payable;
    const demHours = item.result.demurrage_hours.toFixed(1);

    li.innerHTML = `
      <div class="history-meta">
        <h4>${escapeHtml(item.vessel_name)}</h4>
        <span>Cargo: ${item.cargo_type} | ${formatDisplayDateTime(item.arrival_time)}</span>
      </div>
      <div class="history-right" onclick="event.stopPropagation();">
        <span class="history-badge ${isDem ? 'yes' : 'no'}">
          ${isDem ? `${demHours}h Demurrage` : 'No Demurrage'}
        </span>
        <button class="btn-remove" onclick="handleDeleteHistory(${item.id})">✕</button>
      </div>
    `;
    container.appendChild(li);
  });
}

function loadCalculationIntoForm(item) {
  // Populate text and dropdown values
  document.getElementById('vessel_name').value = item.vessel_name;
  document.getElementById('cargo_type').value = item.cargo_type;
  document.getElementById('berth_type').value = item.berth_type;
  document.getElementById('berths_count').value = item.berths_count;
  document.getElementById('laycan_start').value = item.laycan_start;
  document.getElementById('laycan_end').value = item.laycan_end;

  // Format datetime strings to fit browser datetime-local format
  document.getElementById('arrival_time').value = item.arrival_time.slice(0, 16);
  document.getElementById('nor_tendered').value = item.nor_tendered.slice(0, 16);
  document.getElementById('nor_accepted').value = item.nor_accepted.slice(0, 16);
  document.getElementById('loading_arm_disconnected').value = item.loading_arm_disconnected.slice(0, 16);

  // Set toggle state switches
  document.getElementById('terminal_requested_early').checked = !!item.terminal_requested_early;
  document.getElementById('terminal_granted_permission_late').checked = !!item.terminal_granted_permission_late;

  // Restore delays records
  delayRecords = [];
  if (item.vessel_delays) {
    item.vessel_delays.forEach(d => delayRecords.push({ reason: d.reason, duration: d.duration, party: 'vessel' }));
  }
  if (item.terminal_delays) {
    item.terminal_delays.forEach(d => delayRecords.push({ reason: d.reason, duration: d.duration, party: 'terminal' }));
  }
  renderDelays();

  // Render the pre-calculated outputs
  switchDisplayTab('tab-result');
  renderResults(item.result);

  // Switch input tab to Vessel Info to review parameters
  switchInputTab('tab-vessel');
}

async function handleDeleteHistory(calcId) {
  if (!confirm("Are you sure you want to delete this calculation from history?")) return;
  try {
    const res = await fetch(`/api/calculations/${calcId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error("Could not delete item");
    loadHistory();

    // If the active result was the one deleted, clear it
    document.getElementById('results-empty').style.display = 'flex';
    document.getElementById('results-content').style.display = 'none';
  } catch (err) {
    alert("Delete failed: " + err.message);
  }
}

// User Management (Admin Only)
async function loadUsers() {
  try {
    const res = await fetch('/api/users');
    if (!res.ok) throw new Error("Could not load users list");
    const items = await res.json();
    renderUsers(items);
  } catch (err) {
    console.error("Error loading users list", err);
  }
}

function renderUsers(items) {
  const tbody = document.getElementById('user-table-body');
  tbody.innerHTML = '';

  items.forEach(user => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(user.username)}</td>
      <td><span class="version" style="background: ${user.role === 'admin' ? 'var(--accent-bg)' : 'var(--border-color)'}; color: ${user.role === 'admin' ? 'var(--accent)' : 'var(--text-main)'}">${user.role.toUpperCase()}</span></td>
      <td>
        ${user.username !== 'admin' ? `<button class="btn-remove" onclick="handleRemoveUser('${user.username}')">✕</button>` : ''}
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function handleAddUser() {
  const usernameInput = document.getElementById('new_username');
  const passwordInput = document.getElementById('new_password');
  const roleInput = document.getElementById('new_role');

  const username = usernameInput.value.trim();
  const password = passwordInput.value;
  const role = roleInput.value;

  try {
    const res = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Account creation failed");
    }

    usernameInput.value = '';
    passwordInput.value = '';
    loadUsers();
  } catch (err) {
    alert("Create user failed: " + err.message);
  }
}

async function handleRemoveUser(username) {
  if (!confirm(`Are you sure you want to delete user account: ${username}?`)) return;
  try {
    const res = await fetch(`/api/users/${username}`, { method: 'DELETE' });
    if (!res.ok) throw new Error("Could not delete user account");
    loadUsers();
  } catch (err) {
    alert("Delete account failed: " + err.message);
  }
}

// Simple HTML escaping helper
function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}
