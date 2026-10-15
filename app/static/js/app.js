let activeGroupId = null;
let allGroups = [];
let allUsers = [];
let currentMembers = [];
let currentExpenses = [];
let currentSplitType = 'EQUAL';
let categoryChartInstance = null;
let userSpendingChartInstance = null;

// Toast helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  const bgColors = {
    success: 'bg-emerald-600 text-white',
    error: 'bg-rose-600 text-white',
    info: 'bg-indigo-600 text-white'
  };
  toast.className = `px-4 py-3 rounded-2xl shadow-lg flex items-center gap-2 text-sm font-medium transition-all transform duration-300 translate-y-2 opacity-0 ${bgColors[type] || bgColors.info}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  }, 10);

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Modal management
function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('hidden');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add('hidden');
}

// Tab switcher
function switchTab(tabKey) {
  const tabs = ['balances', 'expenses', 'analytics', 'members'];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`tabBtn-${t}`);
    if (t === tabKey) {
      el.classList.remove('hidden');
      btn.className = 'pb-3 border-b-2 border-indigo-600 text-indigo-600 flex items-center gap-2 font-semibold';
    } else {
      el.classList.add('hidden');
      btn.className = 'pb-3 border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center gap-2 font-semibold';
    }
  });

  if (tabKey === 'analytics' && activeGroupId) {
    loadAnalytics(activeGroupId);
  }
}

// Initial bootstrap
document.addEventListener('DOMContentLoaded', async () => {
  await loadInitialData();
});

async function loadInitialData() {
  await fetchUsers();
  await fetchGroups();
}

async function fetchUsers() {
  try {
    const res = await fetch('/users');
    allUsers = await res.json();
    populateUserDropdowns();
  } catch (err) {
    console.error("Error fetching users:", err);
  }
}

function populateUserDropdowns() {
  const userToAddSelect = document.getElementById('userToAddSelect');
  if (userToAddSelect) {
    userToAddSelect.innerHTML = '<option value="">Select existing user...</option>' +
      allUsers.map(u => `<option value="${u.id}">${u.name} (id: ${u.id})</option>`).join('');
  }
}

async function fetchGroups() {
  try {
    const res = await fetch('/groups');
    allGroups = await res.json();
    const groupSelect = document.getElementById('groupSelect');

    if (allGroups.length === 0) {
      groupSelect.innerHTML = '<option value="">No groups found. Seed demo or create one!</option>';
      activeGroupId = null;
      clearDashboard();
      return;
    }

    groupSelect.innerHTML = allGroups.map(g =>
      `<option value="${g.id}" ${g.id === activeGroupId ? 'selected' : ''}>${g.name}</option>`
    ).join('');

    if (!activeGroupId || !allGroups.some(g => g.id === activeGroupId)) {
      activeGroupId = allGroups[0].id;
      groupSelect.value = activeGroupId;
    }

    await loadGroupData(activeGroupId);
  } catch (err) {
    console.error("Error fetching groups:", err);
  }
}

async function onGroupChange() {
  const select = document.getElementById('groupSelect');
  activeGroupId = parseInt(select.value);
  if (activeGroupId) {
    await loadGroupData(activeGroupId);
  }
}

async function loadGroupData(groupId) {
  try {
    // 1. Group details & members
    const groupRes = await fetch(`/groups/${groupId}`);
    const group = await groupRes.json();
    currentMembers = group.members || [];
    renderGroupMembers(currentMembers);
    populatePayerDropdown(currentMembers);

    // 2. Group balances
    const balRes = await fetch(`/groups/${groupId}/balances`);
    const balanceData = await balRes.json();

    // 3. Group expenses
    const expRes = await fetch(`/groups/${groupId}/expenses`);
    currentExpenses = await expRes.json();

    // 4. Group settlements
    const setRes = await fetch(`/groups/${groupId}/settlements`);
    const settlements = await setRes.json();

    // Render components
    renderKPIs(balanceData, currentMembers, currentExpenses);
    renderPairwiseBalances(balanceData.balances);
    renderSimplifiedDebts(balanceData.simplified_debts);
    renderSettlements(settlements);
    renderExpensesFeed(currentExpenses);

    // If analytics tab is open, update analytics
    const analyticsTab = document.getElementById('tab-analytics');
    if (!analyticsTab.classList.contains('hidden')) {
      loadAnalytics(groupId);
    }
  } catch (err) {
    console.error("Error loading group data:", err);
  }
}

function clearDashboard() {
  document.getElementById('kpiTotalSpend').textContent = '₹0.00';
  document.getElementById('kpiMembers').textContent = '0';
  document.getElementById('kpiExpenseCount').textContent = '0';
  document.getElementById('kpiPendingDebts').textContent = '0';
  document.getElementById('pairwiseBalancesList').innerHTML = '<div class="col-span-full py-8 text-center text-slate-400">No active group selected.</div>';
  document.getElementById('simplifiedDebtsList').innerHTML = '<div class="col-span-full py-8 text-center text-slate-300">No active debts to simplify.</div>';
  document.getElementById('expensesFeed').innerHTML = '<div class="py-8 text-center text-slate-400">No expenses recorded.</div>';
  document.getElementById('groupMembersList').innerHTML = '';
}

function renderKPIs(balanceData, members, expenses) {
  document.getElementById('kpiTotalSpend').textContent = `₹${balanceData.total_group_spending.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  document.getElementById('kpiMembers').textContent = members.length;
  
  const avg = members.length > 0 ? (balanceData.total_group_spending / members.length) : 0;
  document.getElementById('kpiAvgShare').textContent = `Avg ₹${avg.toFixed(2)} / member`;

  document.getElementById('kpiExpenseCount').textContent = expenses.length;

  let directDebtCount = 0;
  for (const debtor in balanceData.balances) {
    directDebtCount += Object.keys(balanceData.balances[debtor].owes || {}).length;
  }
  document.getElementById('kpiPendingDebts').textContent = directDebtCount;
  document.getElementById('kpiSimplifiedDebts').textContent = `${balanceData.simplified_debts.length} simplified transactions`;
}

function renderPairwiseBalances(balances) {
  const container = document.getElementById('pairwiseBalancesList');
  const items = [];

  for (const debtor in balances) {
    const owes = balances[debtor].owes || {};
    for (const creditor in owes) {
      const amount = owes[creditor];
      items.push({ debtor, creditor, amount });
    }
  }

  if (items.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-8 text-center">
        <div class="inline-flex p-3 rounded-full bg-emerald-50 text-emerald-600 mb-2">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
        </div>
        <p class="text-sm font-semibold text-slate-700">All Settled Up!</p>
        <p class="text-xs text-slate-400">No member owes money to anyone in this group.</p>
      </div>`;
    return;
  }

  container.innerHTML = items.map(item => {
    // Look up user IDs for prefilling modal
    const debtorUser = currentMembers.find(m => m.name === item.debtor);
    const creditorUser = currentMembers.find(m => m.name === item.creditor);
    const debtorId = debtorUser ? debtorUser.id : '';
    const creditorId = creditorUser ? creditorUser.id : '';

    return `
      <div class="p-4 rounded-2xl border border-slate-200/90 hover:border-indigo-200 hover:shadow-sm bg-slate-50/50 flex flex-col justify-between transition">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <div class="w-8 h-8 rounded-full bg-rose-100 text-rose-700 font-bold text-xs flex items-center justify-center">
              ${item.debtor.charAt(0)}
            </div>
            <span class="text-xs font-semibold text-slate-500">owes</span>
            <div class="w-8 h-8 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center">
              ${item.creditor.charAt(0)}
            </div>
          </div>
          <span class="text-base font-extrabold text-slate-900">₹${item.amount.toFixed(2)}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-sm font-medium text-slate-700">
            <span class="font-bold text-rose-600">${item.debtor}</span> → <span class="font-bold text-emerald-600">${item.creditor}</span>
          </span>
          <button onclick="openSettleModal(${debtorId}, ${creditorId}, ${item.amount})" class="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 transition">
            Settle Up
          </button>
        </div>
      </div>
    `;
  }).join('');
}

function renderSimplifiedDebts(simplified) {
  const container = document.getElementById('simplifiedDebtsList');
  if (!simplified || simplified.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-6 text-center text-slate-400 text-sm">
        No transactions needed. Everyone is balanced!
      </div>`;
    return;
  }

  container.innerHTML = simplified.map(s => `
    <div class="p-4 rounded-2xl bg-white/10 backdrop-blur border border-white/15 flex items-center justify-between hover:bg-white/15 transition">
      <div>
        <div class="text-xs text-indigo-200 uppercase font-semibold">Suggested Payment</div>
        <div class="text-sm font-bold text-white mt-0.5">
          <span class="text-rose-300">${s.from_user_name}</span> pays <span class="text-emerald-300">${s.to_user_name}</span>
        </div>
      </div>
      <div class="text-right">
        <div class="text-lg font-black text-white">₹${s.amount.toFixed(2)}</div>
        <button onclick="openSettleModal(${s.from_user_id}, ${s.to_user_id}, ${s.amount})" class="mt-1 px-2.5 py-0.5 text-xs font-bold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition">
          Settle ₹${s.amount.toFixed(0)}
        </button>
      </div>
    </div>
  `).join('');
}

function renderSettlements(settlements) {
  const tbody = document.getElementById('settlementsTableBody');
  if (!settlements || settlements.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" class="py-4 text-center text-slate-400">No settlements recorded yet.</td></tr>';
    return;
  }

  tbody.innerHTML = settlements.map(s => {
    const d = s.created_at ? new Date(s.created_at).toLocaleDateString() : 'Recent';
    return `
      <tr class="hover:bg-slate-50 transition">
        <td class="py-3 px-4 text-xs text-slate-400">${d}</td>
        <td class="py-3 px-4 font-semibold text-slate-800">${s.payer_name}</td>
        <td class="py-3 px-4 font-semibold text-emerald-700">${s.payee_name}</td>
        <td class="py-3 px-4 font-extrabold text-slate-900">₹${s.amount.toFixed(2)}</td>
        <td class="py-3 px-4 text-xs text-slate-500">${s.notes || '-'}</td>
      </tr>
    `;
  }).join('');
}

function renderExpensesFeed(expenses) {
  const container = document.getElementById('expensesFeed');
  if (!expenses || expenses.length === 0) {
    container.innerHTML = `
      <div class="bg-white rounded-2xl p-8 border border-slate-200/80 text-center">
        <p class="text-slate-500 font-medium">No expenses found for this group.</p>
        <button onclick="openModal('addExpenseModal')" class="mt-2 text-indigo-600 font-semibold text-sm hover:underline">+ Record the first expense</button>
      </div>`;
    return;
  }

  const categoryIcons = {
    Food: '🍔',
    Transport: '🚕',
    Stay: '🏨',
    Activities: '🏄',
    Shopping: '🛍️',
    General: '📦'
  };

  container.innerHTML = expenses.map(e => {
    const icon = categoryIcons[e.category] || '📦';
    const dateStr = e.created_at ? new Date(e.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '';
    const splitDetails = (e.splits || []).map(s => `
      <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 text-xs text-slate-600">
        <span class="font-medium">${s.user_name}:</span> ₹${s.amount.toFixed(2)}
      </span>
    `).join(' ');

    return `
      <div class="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/80 shadow-sm hover:border-indigo-200 transition space-y-3">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-slate-100 text-xl flex items-center justify-center flex-shrink-0">
              ${icon}
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h4 class="font-bold text-slate-900 text-base">${e.description}</h4>
                <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-600">${e.category}</span>
                <span class="px-2 py-0.5 text-xs font-medium rounded-full ${e.split_type === 'EXACT' ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-indigo-50 text-indigo-700'}">${e.split_type === 'EXACT' ? 'Custom Split' : 'Equal Split'}</span>
              </div>
              <p class="text-xs text-slate-500 mt-0.5">
                Paid by <span class="font-semibold text-slate-800">${e.paid_by}</span> • ${dateStr}
              </p>
            </div>
          </div>
          <div class="text-right">
            <span class="text-xl font-extrabold text-slate-900">₹${e.amount.toFixed(2)}</span>
          </div>
        </div>

        <div class="pt-2 border-t border-slate-100 flex flex-wrap items-center gap-1.5">
          <span class="text-xs font-semibold text-slate-400 mr-1">Participants:</span>
          ${splitDetails}
        </div>
      </div>
    `;
  }).join('');
}

function renderGroupMembers(members) {
  const container = document.getElementById('groupMembersList');
  if (!members || members.length === 0) {
    container.innerHTML = '<div class="col-span-full py-4 text-center text-slate-400">No members in this group yet.</div>';
    return;
  }

  container.innerHTML = members.map(m => `
    <div class="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center">
          ${m.name.charAt(0)}
        </div>
        <div>
          <div class="font-bold text-slate-900">${m.name}</div>
          <div class="text-xs text-slate-400">ID: ${m.id} ${m.email ? '• ' + m.email : ''}</div>
        </div>
      </div>
      <span class="px-2 py-1 text-xs rounded-lg bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">Active</span>
    </div>
  `).join('');
}

function populatePayerDropdown(members) {
  const expPaidBy = document.getElementById('expPaidBy');
  if (expPaidBy) {
    expPaidBy.innerHTML = members.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
  }
}

// Custom split handling
function setSplitType(type) {
  currentSplitType = type;
  const equalBtn = document.getElementById('splitTypeEqualBtn');
  const exactBtn = document.getElementById('splitTypeExactBtn');
  const customContainer = document.getElementById('customSplitsContainer');

  if (type === 'EQUAL') {
    equalBtn.className = 'py-2 text-xs font-bold rounded-xl border border-indigo-600 bg-indigo-50 text-indigo-700 transition';
    exactBtn.className = 'py-2 text-xs font-bold rounded-xl border border-slate-300 bg-slate-50 text-slate-600 transition';
    customContainer.classList.add('hidden');
  } else {
    exactBtn.className = 'py-2 text-xs font-bold rounded-xl border border-indigo-600 bg-indigo-50 text-indigo-700 transition';
    equalBtn.className = 'py-2 text-xs font-bold rounded-xl border border-slate-300 bg-slate-50 text-slate-600 transition';
    customContainer.classList.remove('hidden');
    renderCustomSplitInputs();
  }
}

function renderCustomSplitInputs() {
  const container = document.getElementById('customSplitsInputs');
  const totalAmount = parseFloat(document.getElementById('expAmount').value) || 0;
  const defaultEach = currentMembers.length > 0 ? (totalAmount / currentMembers.length).toFixed(2) : 0;

  container.innerHTML = currentMembers.map(m => `
    <div class="flex items-center justify-between gap-3">
      <span class="text-xs font-semibold text-slate-800">${m.name}:</span>
      <div class="relative w-32">
        <span class="absolute left-2.5 top-2 text-xs text-slate-400">₹</span>
        <input type="number" step="0.01" min="0" data-user-id="${m.id}" value="${defaultEach}" oninput="validateCustomSplits()" class="custom-split-val w-full pl-6 pr-2 py-1.5 text-xs bg-white border border-slate-300 rounded-lg focus:ring-1 focus:ring-indigo-500">
      </div>
    </div>
  `).join('');

  validateCustomSplits();
}

function onAmountOrSplitChange() {
  if (currentSplitType === 'EXACT') {
    renderCustomSplitInputs();
  }
}

function validateCustomSplits() {
  const target = parseFloat(document.getElementById('expAmount').value) || 0;
  const inputs = document.querySelectorAll('.custom-split-val');
  let currentSum = 0;
  inputs.forEach(inp => {
    currentSum += parseFloat(inp.value) || 0;
  });

  const valText = document.getElementById('customSplitValidationText');
  const diff = Math.abs(currentSum - target);

  if (diff <= 0.01 && target > 0) {
    valText.className = 'text-emerald-600';
    valText.textContent = `Sum: ₹${currentSum.toFixed(2)} (Matched ✓)`;
  } else {
    valText.className = 'text-rose-500 font-semibold';
    valText.textContent = `Sum: ₹${currentSum.toFixed(2)} / Target: ₹${target.toFixed(2)} (Diff: ₹${(target - currentSum).toFixed(2)})`;
  }
}

// Analytics loader
async function loadAnalytics(groupId) {
  try {
    const res = await fetch(`/groups/${groupId}/analytics`);
    const data = await res.json();

    // 1. Category Chart
    const catCanvas = document.getElementById('categoryChart');
    if (catCanvas && data.categories) {
      if (categoryChartInstance) categoryChartInstance.destroy();

      const labels = data.categories.map(c => c.category);
      const amounts = data.categories.map(c => c.total_amount);
      const bgColors = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#64748b'];

      categoryChartInstance = new Chart(catCanvas, {
        type: 'doughnut',
        data: {
          labels: labels.length > 0 ? labels : ['None'],
          datasets: [{
            data: amounts.length > 0 ? amounts : [1],
            backgroundColor: bgColors.slice(0, labels.length || 1),
            borderWidth: 2,
            borderColor: '#ffffff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' }
          }
        }
      });
    }

    // 2. User Spending Chart (Paid vs Share)
    const userCanvas = document.getElementById('userSpendingChart');
    if (userCanvas && data.user_summaries) {
      if (userSpendingChartInstance) userSpendingChartInstance.destroy();

      const uLabels = data.user_summaries.map(u => u.user_name);
      const uPaid = data.user_summaries.map(u => u.total_paid);
      const uShares = data.user_summaries.map(u => u.total_share);

      userSpendingChartInstance = new Chart(userCanvas, {
        type: 'bar',
        data: {
          labels: uLabels,
          datasets: [
            {
              label: 'Paid Upfront (₹)',
              data: uPaid,
              backgroundColor: '#10b981',
              borderRadius: 6
            },
            {
              label: 'Consumed Share (₹)',
              data: uShares,
              backgroundColor: '#6366f1',
              borderRadius: 6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' }
          },
          scales: {
            y: { beginAtZero: true }
          }
        }
      });
    }

    // 3. Member Financial Scorecard
    const scorecardsContainer = document.getElementById('memberScorecards');
    if (scorecardsContainer && data.user_summaries) {
      scorecardsContainer.innerHTML = data.user_summaries.map(u => {
        const isCreditor = u.net_balance > 0.005;
        const isDebtor = u.net_balance < -0.005;

        let statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">Settled (₹0.00)</span>';
        if (isCreditor) {
          statusBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">Gets back +₹${u.net_balance.toFixed(2)}</span>`;
        } else if (isDebtor) {
          statusBadge = `<span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">Owes -₹${Math.abs(u.net_balance).toFixed(2)}</span>`;
        }

        return `
          <div class="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col justify-between space-y-3">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="font-bold text-slate-900">${u.user_name}</span>
                ${statusBadge}
              </div>
              <div class="text-xs text-slate-500 space-y-1">
                <div class="flex justify-between"><span>Paid upfront:</span> <span class="font-semibold text-slate-700">₹${u.total_paid.toFixed(2)}</span></div>
                <div class="flex justify-between"><span>Consumed share:</span> <span class="font-semibold text-slate-700">₹${u.total_share.toFixed(2)}</span></div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }

  } catch (err) {
    console.error("Error loading analytics:", err);
  }
}

// Settlement modal pre-fill
function openSettleModal(payerId, payeeId, amount) {
  const payerSelect = document.getElementById('settlePayer');
  const payeeSelect = document.getElementById('settlePayee');
  const amtInput = document.getElementById('settleAmount');
  const notesInput = document.getElementById('settleNotes');

  // Populate options with current members
  const optionsHtml = currentMembers.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
  payerSelect.innerHTML = optionsHtml;
  payeeSelect.innerHTML = optionsHtml;

  if (payerId) payerSelect.value = payerId;
  if (payeeId) payeeSelect.value = payeeId;
  if (amount) amtInput.value = amount.toFixed(2);
  notesInput.value = 'Settlement payment';

  openModal('settleModal');
}

// Actions & Form Submissions
async function submitExpense(e) {
  e.preventDefault();
  if (!activeGroupId) {
    showToast("Please select or create a group first", "error");
    return;
  }

  const description = document.getElementById('expDescription').value;
  const amount = parseFloat(document.getElementById('expAmount').value);
  const category = document.getElementById('expCategory').value;
  const paid_by = parseInt(document.getElementById('expPaidBy').value);

  const payload = {
    group_id: activeGroupId,
    paid_by: paid_by,
    amount: amount,
    description: description,
    category: category,
    split_type: currentSplitType
  };

  if (currentSplitType === 'EXACT') {
    const splitInputs = document.querySelectorAll('.custom-split-val');
    const splits = [];
    splitInputs.forEach(inp => {
      splits.push({
        user_id: parseInt(inp.getAttribute('data-user-id')),
        amount: parseFloat(inp.value) || 0
      });
    });
    payload.splits = splits;
  }

  try {
    const res = await fetch('/expenses', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to record expense');
    }

    showToast("Expense recorded successfully! Balances updated.", "success");
    closeModal('addExpenseModal');
    document.getElementById('addExpenseForm').reset();
    setSplitType('EQUAL');
    await loadGroupData(activeGroupId);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitSettlement(e) {
  e.preventDefault();
  if (!activeGroupId) return;

  const payer_id = parseInt(document.getElementById('settlePayer').value);
  const payee_id = parseInt(document.getElementById('settlePayee').value);
  const amount = parseFloat(document.getElementById('settleAmount').value);
  const notes = document.getElementById('settleNotes').value;

  if (payer_id === payee_id) {
    showToast("Payer and payee cannot be the same user", "error");
    return;
  }

  try {
    const res = await fetch('/settlements', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        group_id: activeGroupId,
        payer_id,
        payee_id,
        amount,
        notes
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to record settlement');
    }

    showToast("Settlement recorded successfully! Balances updated.", "success");
    closeModal('settleModal');
    await loadGroupData(activeGroupId);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitNewGroup(e) {
  e.preventDefault();
  const name = document.getElementById('newGroupName').value;
  const description = document.getElementById('newGroupDesc').value;

  try {
    const res = await fetch('/groups', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create group');
    }

    const newGroup = await res.json();
    showToast(`Group '${newGroup.name}' created!`, "success");
    closeModal('createGroupModal');
    document.getElementById('createGroupForm').reset();
    activeGroupId = newGroup.id;
    await fetchGroups();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function submitNewUser(e) {
  e.preventDefault();
  const name = document.getElementById('newUserName').value;
  const email = document.getElementById('newUserEmail').value;

  try {
    const res = await fetch('/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create user');
    }

    const newUser = await res.json();
    showToast(`User '${newUser.name}' created!`, "success");
    closeModal('createUserModal');
    document.getElementById('createUserForm').reset();
    await fetchUsers();

    // If active group exists, optionally add user directly
    if (activeGroupId) {
      await fetch(`/groups/${activeGroupId}/members`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: newUser.id })
      });
      await loadGroupData(activeGroupId);
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function addUserToActiveGroup() {
  if (!activeGroupId) {
    showToast("No active group selected", "error");
    return;
  }
  const select = document.getElementById('userToAddSelect');
  const userId = parseInt(select.value);
  if (!userId) {
    showToast("Please choose a user to add", "error");
    return;
  }

  try {
    const res = await fetch(`/groups/${activeGroupId}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add user to group');
    }

    showToast("User added to group!", "success");
    await loadGroupData(activeGroupId);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function seedDemoData() {
  try {
    showToast("Seeding Goa Trip benchmark scenario...", "info");
    const res = await fetch('/api/demo/seed', { method: 'POST' });
    const data = await res.json();
    showToast(data.message, "success");
    activeGroupId = data.group_id;
    await fetchUsers();
    await fetchGroups();
  } catch (err) {
    showToast("Failed to seed demo data", "error");
  }
}

async function resetData() {
  if (!confirm("Are you sure you want to reset all data?")) return;
  try {
    await fetch('/api/demo/reset', { method: 'POST' });
    showToast("All data cleared", "info");
    activeGroupId = null;
    await fetchUsers();
    await fetchGroups();
  } catch (err) {
    showToast("Failed to reset data", "error");
  }
}

function filterExpenses() {
  const query = (document.getElementById('expenseSearchInput').value || '').toLowerCase();
  const category = document.getElementById('expenseCategoryFilter').value;

  const filtered = currentExpenses.filter(e => {
    const matchesSearch = e.description.toLowerCase().includes(query) || e.paid_by.toLowerCase().includes(query);
    const matchesCat = (category === 'All' || e.category.toLowerCase() === category.toLowerCase());
    return matchesSearch && matchesCat;
  });

  renderExpensesFeed(filtered);
}

function exportData(format) {
  if (!activeGroupId) {
    showToast("Please select a group first", "error");
    return;
  }
  window.open(`/groups/${activeGroupId}/export?format=${format}`, '_blank');
}
