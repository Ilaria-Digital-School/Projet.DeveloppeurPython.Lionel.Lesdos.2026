// Page Budgets : suivi de la période en cours, projection, report du reste,
// prévu vs réel et historique des modifications. Données : /api/v1/budgets/*
// (escapeHtml et showConfirmDialog viennent de utils.js)

const PERIOD_LABELS = { monthly: 'Mensuel', yearly: 'Annuel', custom: 'Personnalisé' };
const FIELD_LABELS = {
  category_id: 'Catégorie',
  amount: 'Montant',
  period: 'Période',
  start_date: 'Début',
  end_date: 'Fin',
  notification_threshold: 'Seuil',
  report_actif: 'Report du reste',
};

const state = {
  budgets: [],
  categories: [],
  filter: 'all',
  detailBudget: null,
  chart: null,
};

document.addEventListener('DOMContentLoaded', () => {
  initFilters();
  initForm();
  initDetail();
  initThreshold();
  loadCategories().then(loadBudgets);
  loadAlerts();
});

// ===== UTILITAIRES =====
function formatCurrency(amount) {
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(amount || 0);
}

function formatDate(iso) {
  return iso ? new Date(iso + (iso.length === 10 ? 'T00:00:00' : '')).toLocaleDateString('fr-FR') : '';
}

function showAlert(message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) return;
  const cls = type === 'success' ? 'bg-green-100 border-green-500 text-green-700 dark:bg-green-900/40 dark:text-green-300'
    : type === 'error' ? 'bg-red-100 border-red-500 text-red-700 dark:bg-red-900/40 dark:text-red-300'
    : 'bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
  const icon = type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle';
  container.innerHTML = `
    <div class="${cls} border-l-4 p-4 mb-4 rounded flex items-center">
      <i class="fas fa-${icon} mr-2"></i><span>${escapeHtml(message)}</span>
    </div>`;
  setTimeout(() => { container.innerHTML = ''; }, 5000);
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCSRFToken(),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.status !== 'success') {
    throw new Error(data.message || `Erreur serveur (${response.status})`);
  }
  return data;
}

// Statut d'un budget pour les filtres et les couleurs
function budgetStatus(b) {
  if (!b.active) return 'inactive';
  if (b.is_over_budget) return 'over';
  if (b.is_near_limit || b.projected_amount > b.available_amount) return 'risk';
  return 'ok';
}

const STATUS_STYLE = {
  over: { bar: 'bg-red-500', text: 'text-red-600 dark:text-red-400', badge: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200', label: 'Dépassé' },
  risk: { bar: 'bg-orange-500', text: 'text-orange-600 dark:text-orange-400', badge: 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200', label: 'À surveiller' },
  ok: { bar: 'bg-green-500', text: 'text-green-600 dark:text-green-400', badge: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200', label: 'En bonne voie' },
  inactive: { bar: 'bg-gray-400', text: 'text-gray-500 dark:text-gray-400', badge: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300', label: 'Inactif' },
};

// ===== CHARGEMENT =====
async function loadCategories() {
  try {
    const data = await api('/api/v1/categories');
    state.categories = (data.categories || []).filter(c => c.type === 'expense');
    const select = document.getElementById('budget-category');
    select.innerHTML = '<option value="">Sélectionnez une catégorie</option>' +
      state.categories.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
  } catch (e) {
    console.error('Erreur chargement catégories:', e);
  }
}

async function loadBudgets() {
  try {
    const data = await api('/api/v1/budgets/summary');
    state.budgets = data.budgets || [];
    renderKpis(data.summary || {});
    renderBudgets();
  } catch (e) {
    console.error('Erreur chargement budgets:', e);
    document.getElementById('budgets-grid').innerHTML = `
      <div class="col-span-full text-center text-red-500 py-12">
        <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
        <p>Erreur de chargement des budgets</p>
      </div>`;
  }
}

// ===== AFFICHAGE =====
function renderKpis(summary) {
  const budgeted = summary.total_budget_amount || 0;
  const spent = summary.total_spent || 0;
  const projected = summary.total_projected || 0;
  const remaining = budgeted - spent;

  document.getElementById('kpi-budgeted').textContent = formatCurrency(budgeted);
  document.getElementById('kpi-spent').textContent = formatCurrency(spent);
  document.getElementById('kpi-spent-pct').textContent =
    budgeted > 0 ? `${Math.round(spent / budgeted * 100)} % du budget` : '';

  const remainingEl = document.getElementById('kpi-remaining');
  remainingEl.textContent = formatCurrency(remaining);
  remainingEl.classList.toggle('text-red-600', remaining < 0);

  const projectedEl = document.getElementById('kpi-projected');
  projectedEl.textContent = formatCurrency(projected);
  projectedEl.classList.toggle('text-red-600', projected > budgeted);
  document.getElementById('kpi-projected-hint').textContent = budgeted > 0
    ? (projected > budgeted
      ? `dépassement prévu de ${formatCurrency(projected - budgeted)}`
      : `marge prévue de ${formatCurrency(budgeted - projected)}`)
    : "d'après vos habitudes";
}

function renderBudgets() {
  const grid = document.getElementById('budgets-grid');

  // Compteurs des filtres
  const counts = { all: state.budgets.length, over: 0, risk: 0, ok: 0, inactive: 0 };
  state.budgets.forEach(b => { counts[budgetStatus(b)] += 1; });
  document.querySelectorAll('[data-count]').forEach(el => {
    el.textContent = `(${counts[el.dataset.count]})`;
  });

  if (state.budgets.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full text-center text-gray-500 dark:text-gray-400 py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
        <i class="fas fa-piggy-bank text-4xl mb-4 text-gray-300"></i>
        <p class="text-lg">Aucun budget défini</p>
        <p class="text-sm">Cliquez sur « Nouveau budget » pour commencer</p>
      </div>`;
    return;
  }

  const visibles = state.budgets.filter(b => state.filter === 'all' || budgetStatus(b) === state.filter);
  if (visibles.length === 0) {
    grid.innerHTML = '<p class="col-span-full text-center text-gray-500 dark:text-gray-400 py-8">Aucun budget dans ce filtre</p>';
    return;
  }

  // Les plus à risque d'abord
  const ordre = { over: 0, risk: 1, ok: 2, inactive: 3 };
  visibles.sort((a, b) => ordre[budgetStatus(a)] - ordre[budgetStatus(b)] || b.raw_percentage - a.raw_percentage);
  grid.innerHTML = visibles.map(budgetCard).join('');
}

function budgetCard(b) {
  const status = budgetStatus(b);
  const style = STATUS_STYLE[status];
  const category = state.categories.find(c => c.id === b.category_id);
  const color = category ? category.color : '#6c757d';
  const name = escapeHtml(b.category_name || 'Sans catégorie');

  let body;
  if (!b.active) {
    body = `<p class="text-sm text-gray-500 dark:text-gray-400 mt-3">
      ${b.start_date && new Date(b.start_date) > new Date() ? `Commence le ${formatDate(b.start_date)}` : `Terminé le ${formatDate(b.end_date)}`}
    </p>`;
  } else {
    // Repère "où on devrait en être" à ce stade de la période
    const expected = Math.min(b.days_elapsed / b.days_total * 100, 100);
    const projectionDiff = b.projected_amount - b.available_amount;
    body = `
      <div class="flex justify-between items-baseline mt-3">
        <span class="text-xl font-bold text-gray-900 dark:text-white">${formatCurrency(b.spent_amount)}</span>
        <span class="text-sm text-gray-500 dark:text-gray-400">sur ${formatCurrency(b.available_amount)}</span>
      </div>
      <div class="relative w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5 mt-2"
           title="Le trait indique la part de la période écoulée (${Math.round(expected)} %)">
        <div class="h-2.5 rounded-full ${style.bar}" style="width: ${b.spent_percentage}%"></div>
        <div class="absolute -top-1 h-4 w-0.5 bg-gray-700 dark:bg-gray-200" style="left: ${expected}%"></div>
      </div>
      <div class="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
        <span>${Math.round(b.raw_percentage)} % utilisé</span>
        <span>${b.days_remaining} j restant${b.days_remaining > 1 ? 's' : ''}</span>
      </div>
      <dl class="grid grid-cols-2 gap-3 mt-4 text-sm">
        <div>
          <dt class="text-gray-500 dark:text-gray-400">Reste</dt>
          <dd class="font-semibold ${b.remaining < 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white'}">${formatCurrency(b.remaining)}</dd>
        </div>
        <div>
          <dt class="text-gray-500 dark:text-gray-400">Par jour</dt>
          <dd class="font-semibold text-gray-900 dark:text-white">${formatCurrency(b.daily_allowance)}</dd>
        </div>
      </dl>
      <p class="text-sm mt-3 ${projectionDiff > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-600 dark:text-gray-300'}">
        <i class="fas fa-chart-line mr-1"></i>
        <span title="${b.projection_method === 'history'
          ? 'Dépensé + ce que vous dépensez habituellement d\'ici la fin de période (3 périodes précédentes)'
          : 'Au rythme actuel (pas encore d\'historique)'}">Projection</span> : <strong>${formatCurrency(b.projected_amount)}</strong>
        ${projectionDiff > 0 ? `(dépassement de ${formatCurrency(projectionDiff)})` : `(marge de ${formatCurrency(-projectionDiff)})`}
      </p>
      ${b.carryover_amount > 0 ? `
        <p class="text-xs text-blue-600 dark:text-blue-400 mt-2">
          <i class="fas fa-share mr-1"></i>dont ${formatCurrency(b.carryover_amount)} reportés de la période précédente
        </p>` : ''}`;
  }

  return `
    <article class="bg-white dark:bg-gray-800 rounded-lg shadow p-5 border-t-4" style="border-top-color: ${escapeHtml(color)}">
      <div class="flex justify-between items-start gap-2">
        <div>
          <h3 class="font-semibold text-gray-900 dark:text-white">${name}</h3>
          <p class="text-xs text-gray-500 dark:text-gray-400">
            ${PERIOD_LABELS[b.period] || b.period}
            ${b.active ? `· ${formatDate(b.period_start)} → ${formatDate(b.period_end)}` : ''}
            ${b.report_actif ? '· <i class="fas fa-share" title="Report du reste actif"></i>' : ''}
          </p>
        </div>
        <span class="px-2 py-1 text-xs rounded-full whitespace-nowrap ${style.badge}">${style.label}</span>
      </div>
      ${body}
      <div class="flex justify-end gap-1 mt-4 pt-3 border-t border-gray-100 dark:border-gray-700">
        <button data-action="detail" data-id="${b.id}" class="px-2 py-1 text-sm text-gray-600 dark:text-gray-300 hover:text-blue-600" title="Prévu vs réel et historique">
          <i class="fas fa-chart-bar mr-1"></i>Détail
        </button>
        <button data-action="edit" data-id="${b.id}" class="px-2 py-1 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300" aria-label="Modifier ${name}">
          <i class="fas fa-edit"></i>
        </button>
        <button data-action="delete" data-id="${b.id}" class="px-2 py-1 text-sm text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300" aria-label="Supprimer ${name}">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    </article>`;
}

// ===== FILTRES =====
function initFilters() {
  const buttons = document.querySelectorAll('.budget-filter');
  const refresh = () => buttons.forEach(btn => {
    const active = btn.dataset.filter === state.filter;
    btn.setAttribute('aria-pressed', active);
    btn.className = `budget-filter px-3 py-1 rounded-full text-sm border ${active
      ? 'bg-blue-600 border-blue-600 text-white'
      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'}`;
  });
  buttons.forEach(btn => btn.addEventListener('click', () => {
    state.filter = btn.dataset.filter;
    refresh();
    renderBudgets();
  }));
  refresh();

  // Actions des cartes (délégation : la grille est re-rendue)
  document.getElementById('budgets-grid').addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const budget = state.budgets.find(b => b.id === Number(btn.dataset.id));
    if (!budget) return;
    if (btn.dataset.action === 'edit') openForm(budget);
    else if (btn.dataset.action === 'delete') deleteBudget(budget);
    else if (btn.dataset.action === 'detail') openDetail(budget);
  });
}

// ===== FORMULAIRE =====
function initForm() {
  const modal = document.getElementById('budget-form-modal');
  document.getElementById('new-budget-btn').addEventListener('click', () => openForm());
  modal.querySelectorAll('.close-form').forEach(btn => btn.addEventListener('click', closeForm));
  modal.addEventListener('click', (e) => { if (e.target === modal || e.target === modal.firstElementChild) closeForm(); });
  document.getElementById('budget-period').addEventListener('change', syncPeriodFields);
  document.getElementById('budget-form').addEventListener('submit', submitForm);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { closeForm(); closeDetail(); }
  });
}

function syncPeriodFields() {
  const custom = document.getElementById('budget-period').value === 'custom';
  document.getElementById('custom-dates').classList.toggle('hidden', !custom);
  document.getElementById('budget-start-date').required = custom;
  document.getElementById('budget-end-date').required = custom;
  // Pas de report sur une période unique
  document.getElementById('rollover-field').classList.toggle('hidden', custom);
}

function openForm(budget = null) {
  const form = document.getElementById('budget-form');
  form.reset();
  document.getElementById('budget-form-title').textContent = budget ? 'Modifier le budget' : 'Nouveau budget';
  document.getElementById('budget-id').value = budget ? budget.id : '';
  const suggestion = document.getElementById('budget-suggestion');
  suggestion.classList.add('hidden');

  if (budget) {
    document.getElementById('budget-category').value = budget.category_id || '';
    document.getElementById('budget-amount').value = budget.amount;
    document.getElementById('budget-period').value = budget.period;
    document.getElementById('budget-start-date').value = budget.start_date || '';
    document.getElementById('budget-end-date').value = budget.end_date || '';
    document.getElementById('budget-threshold').value = budget.notification_threshold || 90;
    document.getElementById('budget-rollover').checked = !!budget.report_actif;
    showSuggestion(budget);
  }
  syncPeriodFields();
  document.getElementById('budget-form-modal').classList.remove('hidden');
  document.getElementById(budget ? 'budget-amount' : 'budget-category').focus();
}

// Moyenne réelle des 3 dernières périodes terminées, pour calibrer le montant
async function showSuggestion(budget) {
  if (budget.period === 'custom') return;
  try {
    const data = await api(`/api/v1/budgets/${budget.id}/periods?count=4`);
    const passees = (data.periods || []).filter(p => !p.is_current);
    if (passees.length === 0) return;
    const moyenne = passees.reduce((s, p) => s + p.spent_amount, 0) / passees.length;
    const el = document.getElementById('budget-suggestion');
    el.textContent = `Dépense moyenne sur les ${passees.length} dernières périodes : ${formatCurrency(moyenne)}`;
    el.classList.remove('hidden');
  } catch (e) {
    console.error('Erreur suggestion:', e);
  }
}

function closeForm() {
  document.getElementById('budget-form-modal').classList.add('hidden');
}

async function submitForm(e) {
  e.preventDefault();
  const id = document.getElementById('budget-id').value;
  const period = document.getElementById('budget-period').value;
  const payload = {
    category_id: Number(document.getElementById('budget-category').value),
    amount: parseFloat(document.getElementById('budget-amount').value),
    period,
    notification_threshold: parseInt(document.getElementById('budget-threshold').value, 10) || 90,
    report_actif: period !== 'custom' && document.getElementById('budget-rollover').checked,
  };
  if (period === 'custom') {
    payload.start_date = document.getElementById('budget-start-date').value;
    payload.end_date = document.getElementById('budget-end-date').value;
    if (payload.end_date < payload.start_date) {
      showAlert('La date de fin doit être postérieure à la date de début', 'error');
      return;
    }
  }
  if (!payload.category_id || !(payload.amount > 0)) {
    showAlert('Choisissez une catégorie et un montant positif', 'error');
    return;
  }

  try {
    await api(id ? `/api/v1/budgets/${id}` : '/api/v1/budgets', {
      method: id ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
    });
    closeForm();
    showAlert(id ? 'Budget modifié' : 'Budget créé', 'success');
    loadBudgets();
  } catch (err) {
    showAlert(err.message, 'error');
  }
}

async function deleteBudget(budget) {
  const ok = await showConfirmDialog(
    'Supprimer le budget',
    `Supprimer le budget « ${budget.category_name} » ? Cette action est irréversible.`
  );
  if (!ok) return;
  try {
    await api(`/api/v1/budgets/${budget.id}`, { method: 'DELETE' });
    showAlert('Budget supprimé', 'success');
    loadBudgets();
  } catch (err) {
    showAlert(err.message, 'error');
  }
}

// ===== DÉTAIL : PRÉVU VS RÉEL + HISTORIQUE =====
function initDetail() {
  const modal = document.getElementById('budget-detail-modal');
  modal.querySelectorAll('.close-detail').forEach(btn => btn.addEventListener('click', closeDetail));
  modal.addEventListener('click', (e) => { if (e.target === modal || e.target === modal.firstElementChild) closeDetail(); });
  document.getElementById('periods-count').addEventListener('change', () => {
    if (state.detailBudget) loadPeriods(state.detailBudget);
  });
}

function openDetail(budget) {
  state.detailBudget = budget;
  document.getElementById('budget-detail-title').textContent =
    `${budget.category_name} — ${formatCurrency(budget.amount)} (${(PERIOD_LABELS[budget.period] || '').toLowerCase()})`;
  const countSelect = document.getElementById('periods-count');
  countSelect.disabled = budget.period === 'custom';
  document.getElementById('budget-detail-modal').classList.remove('hidden');
  loadPeriods(budget);
  loadHistory(budget);
}

function closeDetail() {
  document.getElementById('budget-detail-modal').classList.add('hidden');
  state.detailBudget = null;
}

async function loadPeriods(budget) {
  const count = document.getElementById('periods-count').value;
  try {
    const data = await api(`/api/v1/budgets/${budget.id}/periods?count=${count}`);
    renderPeriodsChart(data.periods || []);
  } catch {
    document.getElementById('periods-summary').textContent = 'Impossible de charger les périodes';
  }
}

function renderPeriodsChart(periods) {
  const canvas = document.getElementById('periods-chart');
  if (state.chart) state.chart.destroy();
  if (typeof Chart === 'undefined') return;

  const barColors = periods.map(p => p.before_start ? '#9ca3af'
    : p.spent_amount > p.budget_amount ? '#ef4444' : '#22c55e');

  state.chart = new Chart(canvas, {
    data: {
      labels: periods.map(p => p.label + (p.is_current ? ' (en cours)' : '')),
      datasets: [
        {
          type: 'bar',
          label: 'Réel',
          data: periods.map(p => p.spent_amount),
          backgroundColor: barColors,
          borderRadius: 4,
          order: 2,
        },
        {
          type: 'line',
          label: 'Prévu',
          data: periods.map(p => p.budget_amount),
          borderColor: '#3b82f6',
          borderDash: [6, 4],
          pointRadius: 0,
          fill: false,
          order: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.dataset.label} : ${formatCurrency(ctx.parsed.y)}`,
            afterBody: (items) => {
              const p = periods[items[0].dataIndex];
              const lines = [`Écart : ${formatCurrency(p.difference)}`];
              if (p.before_start) lines.push('Avant la création du budget');
              return lines;
            },
          },
        },
      },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { callback: (v) => formatCurrency(v) } },
      },
    },
  });

  // Synthèse sur les périodes terminées depuis la création du budget
  const terminees = periods.filter(p => !p.is_current && !p.before_start);
  const summary = document.getElementById('periods-summary');
  if (terminees.length === 0) {
    summary.textContent = 'Pas encore de période terminée depuis la création du budget. Les barres grises montrent les dépenses des périodes antérieures.';
    return;
  }
  const respectees = terminees.filter(p => p.spent_amount <= p.budget_amount).length;
  const moyenne = terminees.reduce((s, p) => s + p.spent_amount, 0) / terminees.length;
  summary.textContent = `Budget respecté ${respectees} fois sur ${terminees.length} · dépense moyenne ${formatCurrency(moyenne)}.`;
}

async function loadHistory(budget) {
  const list = document.getElementById('budget-history');
  list.innerHTML = '<li class="py-2 text-gray-500 dark:text-gray-400">Chargement...</li>';
  try {
    const data = await api(`/api/v1/budgets/${budget.id}/history?per_page=50`);
    const entries = data.history || [];
    if (entries.length === 0) {
      list.innerHTML = '<li class="py-2 text-gray-500 dark:text-gray-400">Aucune modification enregistrée</li>';
      return;
    }
    list.innerHTML = entries.map(historyItem).join('');
  } catch {
    list.innerHTML = '<li class="py-2 text-red-500">Impossible de charger l\'historique</li>';
  }
}

function formatHistoryValue(field, value) {
  if (value === null || value === undefined || value === '') return '—';
  if (field === 'amount') return formatCurrency(value);
  if (field === 'period') return PERIOD_LABELS[value] || value;
  if (field === 'notification_threshold') return `${value} %`;
  if (field === 'report_actif') return value ? 'oui' : 'non';
  if (field === 'start_date' || field === 'end_date') return formatDate(value);
  if (field === 'category_id') {
    const c = state.categories.find(cat => cat.id === Number(value));
    return c ? c.name : `#${value}`;
  }
  return String(value);
}

function historyItem(entry) {
  const when = new Date(entry.changed_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  const action = { create: 'Création', update: 'Modification', delete: 'Suppression' }[entry.action] || entry.action;
  const changes = entry.changes || {};
  let details = '';
  if (entry.action === 'update') {
    // Nouveau format { champ: {old, new} } ; anciennes entrées : { champ: valeur }
    details = Object.entries(changes).map(([field, v]) => {
      const label = FIELD_LABELS[field] || field;
      if (v && typeof v === 'object' && 'new' in v) {
        return `${label} : ${escapeHtml(formatHistoryValue(field, v.old))} → ${escapeHtml(formatHistoryValue(field, v.new))}`;
      }
      return `${label} : ${escapeHtml(formatHistoryValue(field, v))}`;
    }).join('<br>');
  } else if (entry.action === 'create') {
    details = `${escapeHtml(formatHistoryValue('amount', changes.amount))} · ${escapeHtml(formatHistoryValue('period', changes.period))}`;
  }
  return `
    <li class="py-2 flex gap-4">
      <span class="text-gray-500 dark:text-gray-400 whitespace-nowrap">${when}</span>
      <span class="font-medium text-gray-800 dark:text-gray-200 w-28 shrink-0">${action}</span>
      <span class="text-gray-600 dark:text-gray-300">${details}</span>
    </li>`;
}

// ===== SEUIL PAR DÉFAUT & ALERTES =====
async function initThreshold() {
  const slider = document.getElementById('default-threshold');
  const value = document.getElementById('threshold-value');
  slider.addEventListener('input', () => { value.textContent = `${slider.value}%`; });

  try {
    const data = await api('/api/v1/budgets/threshold');
    slider.value = data.default_threshold || 90;
    value.textContent = `${slider.value}%`;
  } catch (e) {
    console.error('Erreur chargement seuil:', e);
  }

  document.getElementById('save-threshold').addEventListener('click', async () => {
    try {
      const data = await api('/api/v1/budgets/threshold', {
        method: 'POST',
        body: JSON.stringify({ default_threshold: parseInt(slider.value, 10), update_existing: true }),
      });
      showAlert(`Seuil de ${data.threshold} % appliqué à ${data.budgets_updated} budget(s)`, 'success');
      loadBudgets();
    } catch (err) {
      showAlert(err.message, 'error');
    }
  });
}

async function loadAlerts() {
  const container = document.getElementById('active-alerts');
  try {
    const data = await api('/api/v1/budgets/alerts');
    const alerts = data.alerts || [];
    container.innerHTML = alerts.length === 0
      ? '<p class="text-sm text-gray-500 dark:text-gray-400">Aucune alerte non lue</p>'
      : alerts.map(a => `
        <div class="p-3 bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 rounded-md text-sm">
          <p class="font-medium text-orange-800 dark:text-orange-200">${escapeHtml(a.category_name)}</p>
          <p class="text-orange-700 dark:text-orange-300">${escapeHtml(a.message)}</p>
          <p class="text-xs text-orange-500 mt-1">${new Date(a.created_at).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</p>
        </div>`).join('');
  } catch {
    container.innerHTML = '<p class="text-sm text-red-500">Impossible de charger les alertes</p>';
  }
}
