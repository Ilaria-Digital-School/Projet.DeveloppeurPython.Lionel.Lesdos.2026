// Dashboard Simplifié - Version épurée et moderne

// Fonction d'échappement HTML pour prévenir les XSS
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {
  
  // Initialiser les fonctionnalités principales
  initDashboard();
  initQuickTransactionModal();
  initBudgetModal();
  initThresholdSlider();
  
  // Charger les données
  loadBudgetOverview();
  loadAccountsBalance();
});

// ===== INITIALISATION PRINCIPALE =====
function initDashboard() {
  
  // Bouton "Gérer tous les budgets"
  const manageBudgetsBtn = document.getElementById('manage-budgets-btn');
  if (manageBudgetsBtn) {
    manageBudgetsBtn.addEventListener('click', openBudgetModal);
  }
}

// ===== CHARGEMENT DES SOLDES =====
async function loadAccountsBalance() {
  try {
    
    const response = await fetch('/api/v1/comptes', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success' && data.accounts) {
        updateBalanceDisplay(data.accounts);
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement soldes:', error);
  }
}

function updateBalanceDisplay(accounts) {
  // Calculer le solde total
  const totalBalance = accounts.reduce((sum, account) => {
    return sum + (parseFloat(account.balance) || 0);
  }, 0);
  
  
  // Mettre à jour l'affichage
  const balanceElement = document.getElementById('kpi-balance');
  if (balanceElement) {
    balanceElement.textContent = formatCurrency(totalBalance);
  }
  
  // Calculer et afficher l'évolution (pour l'instant, simulation)
  const evolutionElement = balanceElement?.parentElement?.querySelector('.text-sm');
  if (evolutionElement) {
    const evolution = totalBalance < 0 ? -15 : +2.5;
    const isPositive = evolution >= 0;
    evolutionElement.innerHTML = `
      <i class="fas fa-${isPositive ? 'arrow-up text-green-500' : 'arrow-down text-red-500'} mr-1"></i>
      <span class="${isPositive ? 'text-green-600' : 'text-red-600'}">
        ${evolution > 0 ? '+' : ''}${evolution.toFixed(1)}% ce mois
      </span>
    `;
  }
}

// ===== GESTION DES BUDGETS =====
async function loadBudgetOverview() {
  try {
    
    const response = await fetch('/api/v1/budgets/summary', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        displayBudgetOverview(data.budgets || []);
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement budgets:', error);
    showErrorMessage('budget-list', 'Erreur de chargement des budgets');
  }
}

function displayBudgetOverview(budgets) {
  const container = document.getElementById('budget-list');
  if (!container) return;
  
  
  if (budgets.length === 0) {
    container.innerHTML = `
      <div class="text-center text-gray-500 py-12">
        <i class="fas fa-chart-pie text-gray-300 text-4xl mb-4"></i>
        <p class="text-lg mb-2">Aucun budget configuré</p>
        <p class="text-sm">Créez votre premier budget pour suivre vos dépenses</p>
      </div>
    `;
    return;
  }
  
  // Afficher les 3 premiers budgets
  const topBudgets = budgets.slice(0, 3);
  container.innerHTML = topBudgets.map(budget => `
    <div class="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200">
      <div class="flex items-center justify-between mb-2">
        <h4 class="font-medium text-gray-900">${escapeHtml(budget.category_name)}</h4>
        <span class="text-sm font-semibold ${budget.is_over_budget ? 'text-red-600' : budget.is_near_limit ? 'text-orange-600' : 'text-green-600'}">
          ${budget.spent_percentage.toFixed(0)}%
        </span>
      </div>
      
      <div class="flex items-center justify-between text-sm text-gray-600 mb-2">
        <span>${formatCurrency(budget.spent_amount)} dépensés</span>
        <span>sur ${formatCurrency(budget.amount)}</span>
      </div>
      
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div class="h-2 rounded-full transition-all duration-300 ${
          budget.is_over_budget ? 'bg-red-500' : 
          budget.is_near_limit ? 'bg-orange-500' : 'bg-green-500'
        }" style="width: ${Math.min(budget.spent_percentage, 100)}%"></div>
      </div>
      
      ${budget.is_over_budget ? 
        '<div class="mt-2 text-xs text-red-600">⚠️ Budget dépassé</div>' : 
        budget.is_near_limit ? 
        '<div class="mt-2 text-xs text-orange-600">🔔 Proche de la limite</div>' : ''
      }
    </div>
  `).join('');
}

// ===== MODAL TRANSACTION RAPIDE =====
function initQuickTransactionModal() {
  
  const modal = document.getElementById('quick-transaction-modal');
  if (!modal) return;
  const closeButtons = modal.querySelectorAll('.close-modal');
  const form = document.getElementById('quick-transaction-form');
  
  // Fermeture modal
  closeButtons.forEach(btn => {
    btn.addEventListener('click', closeQuickTransactionModal);
  });
  
  // Fermeture par clic extérieur
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeQuickTransactionModal();
    }
  });
  
  // Soumission formulaire
  if (form) {
    form.addEventListener('submit', handleQuickTransactionSubmit);
  } else {
    console.error('❌ Formulaire non trouvé pour ajouter l\'event listener');
  }
  
  // Chargement initial des comptes et catégories
  loadModalData();
}

function openQuickTransactionModal() {
  
  const modal = document.getElementById('quick-transaction-modal');
  
  // Afficher la modal
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  
  // Initialiser Flatpickr pour la date si pas déjà fait
  const dateInput = document.getElementById('transaction-date');
  if (dateInput && !dateInput._flatpickr) {
    flatpickr(dateInput, {
      locale: "fr",
      dateFormat: "d/m/Y",
      defaultDate: "today",
      allowInput: false
    });
  }
  
  // Focus sur le premier champ
  setTimeout(() => {
    const typeSelect = document.getElementById('transaction-type');
    if (typeSelect) typeSelect.focus();
  }, 100);
}

function closeQuickTransactionModal() {
  
  const modal = document.getElementById('quick-transaction-modal');
  const form = document.getElementById('quick-transaction-form');
  
  if (modal) {
    
    // Masquer la modal avec force
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    modal.style.display = 'none'; // Force en CSS direct aussi
    
  } else {
    console.error('❌ Modal non trouvée avec ID: quick-transaction-modal');
  }
  
  // Réinitialiser le formulaire
  if (form) {
    form.reset();
  } else {
    console.error('❌ Formulaire non trouvé avec ID: quick-transaction-form');
  }
  
}

async function loadModalData() {
  try {
    // Charger les comptes
    const accountsResponse = await fetch('/api/v1/comptes', {
      credentials: 'same-origin'
    });
    
    if (accountsResponse.ok) {
      const accountsData = await accountsResponse.json();
      populateAccountSelect(accountsData.accounts || []);
    }
    
    // Charger les catégories
    const categoriesResponse = await fetch('/api/v1/categories', {
      credentials: 'same-origin'
    });
    
    if (categoriesResponse.ok) {
      const categoriesData = await categoriesResponse.json();
      populateCategorySelect(categoriesData.categories || []);
    }
  } catch (error) {
    console.error('❌ Erreur chargement données modal:', error);
  }
}

function populateAccountSelect(accounts) {
  const select = document.getElementById('transaction-account');
  if (!select) return;
  
  // Garder l'option par défaut et ajouter les comptes
  const defaultOption = select.querySelector('option[value=""]');
  select.innerHTML = '';
  if (defaultOption) select.appendChild(defaultOption);
  
  accounts.forEach(account => {
    const option = document.createElement('option');
    option.value = account.id;
    option.textContent = `${account.name} (${formatCurrency(account.balance)})`;
    select.appendChild(option);
  });
}

function populateCategorySelect(categories) {
  const select = document.getElementById('transaction-category');
  if (!select) return;
  
  // Garder l'option par défaut et ajouter les catégories
  const defaultOption = select.querySelector('option[value=""]');
  select.innerHTML = '';
  if (defaultOption) select.appendChild(defaultOption);
  
  categories.forEach(category => {
    const option = document.createElement('option');
    option.value = category.id;
    option.textContent = category.name;
    select.appendChild(option);
  });
}

async function handleQuickTransactionSubmit(e) {
  e.preventDefault();
  
  
  const form = e.target;
  if (!form) {
    console.error('❌ Formulaire non trouvé dans handleQuickTransactionSubmit');
    return;
  }
  
  const formData = new FormData(form);
  
  // Préparer les données
  let dateStr = formData.get('date');
  let isoDate = dateStr;
  
  // Convertir la date française DD/MM/YYYY vers ISO YYYY-MM-DD
  if (dateStr && dateStr.includes('/')) {
    const parts = dateStr.split('/');
    const day = parts[0].padStart(2, '0');
    const month = parts[1].padStart(2, '0');
    const year = parts[2];
    isoDate = `${year}-${month}-${day}`;
  }
  
  const transactionData = {
    type: formData.get('type'),
    amount: parseFloat(formData.get('amount')),
    description: formData.get('description'),
    category_id: formData.get('category') || null,
    account_id: formData.get('account'),
    date: isoDate
  };
  
  
  // Validation
  if (!transactionData.amount || transactionData.amount <= 0) {
    showAlert('Veuillez saisir un montant valide', 'error');
    return;
  }
  
  if (!transactionData.account_id) {
    showAlert('Veuillez sélectionner un compte', 'error');
    return;
  }
  
  
  try {
    const response = await fetch('/api/v1/transactions', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify(transactionData)
    });
    
    const result = await response.json();
    
    
    if (response.ok) {
      // Vérifier différents formats de réponse
      if (result.status === 'success' || result.message === 'Transaction créée avec succès' || response.status === 201) {
        showAlert('Transaction créée avec succès !', 'success');
        
        // Fermer la modal immédiatement
        closeQuickTransactionModal();
        
        // Recharger les données du dashboard sans recharger la page
        loadAccountsBalance();
        loadBudgetOverview();
      } else {
        showAlert(result.message || 'Réponse inattendue du serveur', 'error');
      }
    } else {
      showAlert(result.message || 'Erreur lors de la création', 'error');
    }
  } catch (error) {
    console.error('❌ Erreur création transaction:', error);
    showAlert('Erreur de connexion', 'error');
  }
}

// ===== UTILITAIRES =====
function formatCurrency(amount) {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount || 0);
}

function getCSRFToken() {
  const token = document.querySelector('meta[name="csrf-token"]');
  return token ? token.getAttribute('content') : '';
}

function showAlert(message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) return;
  
  const alertClass = type === 'success' ? 'bg-green-100 border-green-500 text-green-700' :
                    type === 'error' ? 'bg-red-100 border-red-500 text-red-700' :
                    'bg-blue-100 border-blue-500 text-blue-700';
  
  const alert = document.createElement('div');
  alert.className = `${alertClass} border-l-4 p-4 mb-4 rounded`;
  alert.innerHTML = `
    <div class="flex items-center">
      <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'} mr-2"></i>
      <span>${message}</span>
    </div>
  `;
  
  container.innerHTML = '';
  container.appendChild(alert);
  
  // Auto-suppression après 5 secondes
  setTimeout(() => {
    if (alert.parentNode) {
      alert.remove();
    }
  }, 5000);
}

function showErrorMessage(containerId, message) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  container.innerHTML = `
    <div class="text-center text-red-500 py-8">
      <i class="fas fa-exclamation-triangle text-red-400 text-2xl mb-2"></i>
      <p>${message}</p>
    </div>
  `;
}

// ===== GESTION MODAL BUDGET =====
function initBudgetModal() {
  
  const modal = document.getElementById('budgets-management-modal');
  const closeBtn = document.getElementById('close-budgets-modal');
  const formModal = document.getElementById('budget-form-modal');
  const closeFormBtn = document.getElementById('close-budget-form');
  const cancelFormBtn = document.getElementById('cancel-budget-form');
  
  if (closeBtn) {
    closeBtn.addEventListener('click', closeBudgetModal);
  }
  
  if (closeFormBtn) {
    closeFormBtn.addEventListener('click', closeBudgetFormModal);
  }
  
  if (cancelFormBtn) {
    cancelFormBtn.addEventListener('click', closeBudgetFormModal);
  }
  
  // Fermeture par clic extérieur
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeBudgetModal();
      }
    });
  }
  
  if (formModal) {
    formModal.addEventListener('click', (e) => {
      if (e.target === formModal) {
        closeBudgetFormModal();
      }
    });
  }
  
  // Gestion des onglets
  initBudgetTabs();
  
  // Bouton nouveau budget
  const newBudgetBtn = document.getElementById('new-budget-btn');
  if (newBudgetBtn) {
    newBudgetBtn.addEventListener('click', () => {
      openBudgetFormModal();
    });
  }
  
  // Bouton actualiser
  const refreshBtn = document.getElementById('refresh-budgets-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadBudgetsList);
  }
  
  // Formulaire de budget
  const budgetForm = document.getElementById('budget-form');
  if (budgetForm) {
    budgetForm.addEventListener('submit', handleBudgetSubmit);
  } else {
    console.error('❌ Formulaire budget non trouvé pour ajouter l\'event listener');
  }
}

function openBudgetModal() {
  
  const modal = document.getElementById('budgets-management-modal');
  if (modal) {
    modal.classList.remove('hidden');
    loadBudgetsList();
    loadBudgetCategories();
  }
}

function closeBudgetModal() {
  
  const modal = document.getElementById('budgets-management-modal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

function openBudgetFormModal(budgetData = null) {
  
  const modal = document.getElementById('budget-form-modal');
  const title = document.getElementById('budget-form-title');
  const form = document.getElementById('budget-form');
  
  if (modal && form) {
    // Réinitialiser le formulaire
    form.reset();
    
    if (budgetData) {
      // Mode modification
      
      title.textContent = 'Modifier le budget';
      document.getElementById('budget-id').value = budgetData.id;
      document.getElementById('budget-name').value = budgetData.name || budgetData.category_name || '';
      document.getElementById('budget-amount').value = budgetData.amount || '';
      document.getElementById('budget-category').value = budgetData.category_id || '';
      document.getElementById('budget-period').value = budgetData.period || 'monthly';
      document.getElementById('budget-threshold').value = budgetData.notification_threshold || 90;
      document.getElementById('budget-notes').value = budgetData.notes || '';
      
      // Log des valeurs remplies
    } else {
      // Mode création
      title.textContent = 'Nouveau Budget';
      document.getElementById('budget-id').value = '';
    }
    
    modal.classList.remove('hidden');
  } else {
    console.error('❌ Impossible de trouver la modal ou le formulaire budget');
  }
}

function closeBudgetFormModal() {
  
  const modal = document.getElementById('budget-form-modal');
  if (modal) {
    modal.classList.add('hidden');
  }
}

function initBudgetTabs() {
  const tabButtons = document.querySelectorAll('.budget-tab-btn');
  const tabContents = document.querySelectorAll('.budget-tab-content');
  
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const tabName = button.dataset.tab;
      
      // Désactiver tous les onglets
      tabButtons.forEach(btn => {
        btn.classList.remove('active', 'text-blue-600', 'border-blue-600');
        btn.classList.add('text-gray-500');
      });
      
      tabContents.forEach(content => {
        content.classList.add('hidden');
      });
      
      // Activer l'onglet cliqué
      button.classList.add('active', 'text-blue-600', 'border-blue-600');
      button.classList.remove('text-gray-500');
      
      const targetContent = document.getElementById(`budget-tab-${tabName}`);
      if (targetContent) {
        targetContent.classList.remove('hidden');
      }
      
      // Charger les données spécifiques à l'onglet
      if (tabName === 'budgets') {
        loadBudgetsList();
      } else if (tabName === 'alerts') {
        loadBudgetAlerts();
        loadDefaultThreshold();
      }
    });
  });
}

async function loadBudgetsList() {
  try {
    
    const response = await fetch('/api/v1/budgets', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        displayBudgetsList(data.budgets || []);
        updateBudgetStats(data.budgets || []);
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement budgets:', error);
  }
}

async function loadBudgetsForEdit() {
  try {
    
    const response = await fetch('/api/v1/budgets', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        return data.budgets || [];
      }
    }
    return [];
  } catch (error) {
    console.error('❌ Erreur chargement budgets pour modification:', error);
    return [];
  }
}

function displayBudgetsList(budgets) {
  const tbody = document.getElementById('budgets-table-body');
  const noBudgets = document.getElementById('no-budgets');
  
  if (!tbody) return;
  
  if (budgets.length === 0) {
    tbody.innerHTML = '';
    if (noBudgets) noBudgets.classList.remove('hidden');
    return;
  }
  
  if (noBudgets) noBudgets.classList.add('hidden');
  
  tbody.innerHTML = budgets.map(budget => `
    <tr class="hover:bg-gray-50">
      <td class="px-6 py-4 whitespace-nowrap">
        <div class="text-sm font-medium text-gray-900">${budget.category_name || 'Sans catégorie'}</div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap">
        <div class="text-sm text-gray-900">${formatCurrency(budget.amount)}</div>
        <div class="text-sm text-gray-500">${formatCurrency(budget.spent_amount || 0)} dépensés</div>
        <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
          <div class="h-2 rounded-full ${budget.spent_percentage >= 90 ? 'bg-red-500' : budget.spent_percentage >= 70 ? 'bg-orange-500' : 'bg-green-500'}" style="width: ${Math.min(budget.spent_percentage || 0, 100)}%"></div>
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        ${budget.period === 'monthly' ? 'Mensuel' : 'Annuel'}
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        ${budget.notification_threshold || 90}%
      </td>
      <td class="px-6 py-4 whitespace-nowrap">
        <span class="px-2 py-1 text-xs rounded-full ${budget.spent_percentage >= 90 ? 'bg-red-100 text-red-800' : budget.spent_percentage >= 70 ? 'bg-orange-100 text-orange-800' : 'bg-green-100 text-green-800'}">
          ${budget.spent_percentage >= 90 ? 'Dépassé' : budget.spent_percentage >= 70 ? 'Alerte' : 'Normal'}
        </span>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        <button data-budget-id="${budget.id}" class="edit-budget-btn text-blue-600 hover:text-blue-900 mr-3">
          <i class="fas fa-edit"></i>
        </button>
        <button data-budget-id="${budget.id}" class="delete-budget-btn text-red-600 hover:text-red-900">
          <i class="fas fa-trash"></i>
        </button>
      </td>
    </tr>
  `).join('');
  
  // Ajouter les event listeners pour les boutons d'action
  addBudgetActionListeners();
}

function addBudgetActionListeners() {
  // Event listeners pour les boutons de modification
  document.querySelectorAll('.edit-budget-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const budgetId = e.currentTarget.getAttribute('data-budget-id');
      editBudget(budgetId);
    });
  });
  
  // Event listeners pour les boutons de suppression  
  document.querySelectorAll('.delete-budget-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const budgetId = e.currentTarget.getAttribute('data-budget-id');
      deleteBudget(budgetId);
    });
  });
  
}

function updateBudgetStats(budgets) {
  const countEl = document.getElementById('budget-count');
  const totalEl = document.getElementById('total-budget');
  
  if (countEl) countEl.textContent = budgets.length;
  if (totalEl) {
    const total = budgets.reduce((sum, b) => sum + (b.amount || 0), 0);
    totalEl.textContent = formatCurrency(total);
  }
}

async function loadBudgetCategories() {
  try {
    const response = await fetch('/api/v1/categories', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        populateBudgetCategorySelect(data.categories || []);
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement catégories:', error);
  }
}

function populateBudgetCategorySelect(categories) {
  const select = document.getElementById('budget-category');
  if (!select) return;
  
  // Garder l'option par défaut et ajouter les catégories de dépenses
  const defaultOption = select.querySelector('option[value=""]');
  select.innerHTML = '';
  if (defaultOption) select.appendChild(defaultOption);
  
  categories.filter(cat => cat.type === 'expense').forEach(category => {
    const option = document.createElement('option');
    option.value = category.id;
    option.textContent = category.name;
    select.appendChild(option);
  });
}

async function handleBudgetSubmit(e) {
  e.preventDefault();
  
  
  const form = e.target;
  const formData = new FormData(form);
  const budgetId = document.getElementById('budget-id').value;
  
  const budgetData = {
    name: formData.get('name'),
    category_id: formData.get('category_id'),
    amount: parseFloat(formData.get('amount')),
    period: formData.get('period'),
    notification_threshold: parseInt(formData.get('notification_threshold')),
    notes: formData.get('notes')
  };
  
  
  // Validation spéciale pour création
  if (!budgetId) {
    if (!budgetData.name || budgetData.name.trim() === '') {
      showAlert('Veuillez saisir un nom pour le budget', 'error');
      return;
    }
    if (!budgetData.category_id) {
      showAlert('Veuillez sélectionner une catégorie', 'error');
      return;
    }
    if (!budgetData.amount || budgetData.amount <= 0) {
      showAlert('Veuillez saisir un montant valide', 'error');
      return;
    }
  }
  
  try {
    // WORKAROUND: L'API PUT a un problème, essayons d'abord avec POST même pour les modifications
    let url, method;
    
    if (budgetId) {
      // Tentative 1: PUT normal
      url = `/api/v1/budgets/${budgetId}`;
      method = 'PUT';
    } else {
      // Création normale
      url = '/api/v1/budgets';
      method = 'POST';
    }
    
    
    const response = await fetch(url, {
      method: method,
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify(budgetData)
    });
    
    
    if (response.ok) {
      const result = await response.json();
      
      if (result.status === 'success') {
        showAlert(budgetId ? 'Budget modifié avec succès!' : 'Budget créé avec succès!', 'success');
        closeBudgetFormModal();
        loadBudgetsList();
        loadBudgetOverview(); // Recharger le widget du dashboard
      } else {
        showAlert(result.message || 'Erreur lors de la sauvegarde', 'error');
      }
    } else {
      // Si c'est une modification qui échoue, essayer le workaround
      if (budgetId && response.status === 500) {
        const workaroundSuccess = await tryBudgetUpdateWorkaround(budgetId, budgetData);
        if (workaroundSuccess) {
          showAlert('Budget modifié avec succès!', 'success');
          closeBudgetFormModal();
          loadBudgetsList();
          loadBudgetOverview();
          return;
        }
      }
      
      // Gérer l'erreur 500 normale
      const errorResult = await response.json().catch(() => ({}));
      showAlert(`Erreur serveur (${response.status}): ${errorResult.message || 'Erreur interne du serveur'}`, 'error');
      
      // Fermer la modal même en cas d'erreur pour permettre à l'utilisateur de réessayer
      closeBudgetFormModal();
    }
  } catch (error) {
    console.error('❌ Erreur soumission budget:', error);
    showAlert('Erreur de connexion', 'error');
  }
}

// ===== WORKAROUND MODIFICATION BUDGET =====
async function tryBudgetUpdateWorkaround(budgetId, budgetData) {
  try {
    
    // Étape 1: Supprimer l'ancien budget
    const deleteResponse = await fetch(`/api/v1/budgets/${budgetId}`, {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCSRFToken()
      }
    });
    
    if (!deleteResponse.ok) {
      return false;
    }
    
    
    // Étape 2: Créer le nouveau budget avec les données modifiées
    const createResponse = await fetch('/api/v1/budgets', {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
      },
      body: JSON.stringify(budgetData)
    });
    
    if (createResponse.ok) {
      const result = await createResponse.json();
      if (result.status === 'success') {
        return true;
      }
    }
    
    return false;
    
  } catch (error) {
    console.error('❌ Erreur dans workaround:', error);
    return false;
  }
}

async function editBudget(budgetId) {
  try {
    
    // D'abord essayer de récupérer depuis la liste des budgets déjà chargés
    const budgetsList = await loadBudgetsForEdit();
    const budget = budgetsList.find(b => b.id == budgetId);
    
    if (budget) {
      openBudgetFormModal(budget);
      return;
    }
    
    // Si pas trouvé dans la liste, essayer l'API individuelle
    const response = await fetch(`/api/v1/budgets/${budgetId}`, {
      credentials: 'same-origin'
    });
    
    
    if (response.ok) {
      const data = await response.json();
      
      if (data.status === 'success' && data.budget) {
        openBudgetFormModal(data.budget);
      } else {
        showAlert('Format de réponse inattendu', 'error');
      }
    } else {
      const errorData = await response.json().catch(() => ({}));
      showAlert(`Erreur serveur (${response.status}): ${errorData.message || 'Erreur interne'}`, 'error');
    }
  } catch (error) {
    console.error('❌ Erreur récupération budget:', error);
    showAlert('Erreur lors de la récupération du budget', 'error');
  }
}

async function deleteBudget(budgetId) {
  // Créer une modal de confirmation personnalisée
  showConfirmModal(
    'Supprimer le budget',
    'Êtes-vous sûr de vouloir supprimer ce budget ? Cette action est irréversible.',
    'Supprimer',
    'btn-danger',
    () => confirmDeleteBudget(budgetId)
  );
}

async function confirmDeleteBudget(budgetId) {
  try {
    
    const response = await fetch(`/api/v1/budgets/${budgetId}`, {
      method: 'DELETE',
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': getCSRFToken()
      }
    });
    
    const result = await response.json();
    
    if (response.ok && result.status === 'success') {
      showAlert('Budget supprimé avec succès!', 'success');
      loadBudgetsList();
      loadBudgetOverview(); // Recharger le widget du dashboard
    } else {
      showAlert(result.message || 'Erreur lors de la suppression', 'error');
    }
  } catch (error) {
    console.error('❌ Erreur suppression budget:', error);
    showAlert('Erreur de connexion', 'error');
  }
}

async function loadBudgetAlerts() {
  try {
    const response = await fetch('/api/v1/budgets/alerts', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        displayBudgetAlerts(data.alerts || []);
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement alertes:', error);
  }
}

function displayBudgetAlerts(alerts) {
  const container = document.getElementById('active-alerts');
  if (!container) return;
  
  if (alerts.length === 0) {
    container.innerHTML = '<p class="text-sm text-gray-500">Aucune alerte active</p>';
    return;
  }
  
  container.innerHTML = alerts.map(alert => `
    <div class="p-3 bg-orange-50 border border-orange-200 rounded-md">
      <div class="flex items-center">
        <i class="fas fa-exclamation-triangle text-orange-600 mr-2"></i>
        <div class="text-sm">
          <p class="font-medium text-orange-800">${escapeHtml(alert.category_name)}</p>
          <p class="text-orange-600">${escapeHtml(alert.message)}</p>
        </div>
      </div>
    </div>
  `).join('');
}

// ===== MODAL DE CONFIRMATION =====
function showConfirmModal(title, message, confirmText, confirmClass, onConfirm) {
  // Supprimer toute modal de confirmation existante
  const existingModal = document.getElementById('confirm-modal');
  if (existingModal) {
    existingModal.remove();
  }
  
  // Créer la modal de confirmation
  const modal = document.createElement('div');
  modal.id = 'confirm-modal';
  modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
  
  modal.innerHTML = `
    <div class="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
      <div class="p-6 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold text-gray-900">${title}</h3>
          <button type="button" class="text-gray-400 hover:text-gray-600 close-confirm-modal">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      
      <div class="p-6">
        <p class="text-gray-600 mb-6">${message}</p>
        
        <div class="flex gap-3">
          <button type="button" class="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 close-confirm-modal">
            Annuler
          </button>
          <button type="button" class="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 confirm-action">
            ${confirmText}
          </button>
        </div>
      </div>
    </div>
  `;
  
  // Ajouter la modal au DOM
  document.body.appendChild(modal);
  
  // Event listeners
  modal.querySelectorAll('.close-confirm-modal').forEach(btn => {
    btn.addEventListener('click', closeConfirmModal);
  });
  
  modal.querySelector('.confirm-action').addEventListener('click', () => {
    closeConfirmModal();
    onConfirm();
  });
  
  // Fermeture par clic extérieur
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      closeConfirmModal();
    }
  });
}

function closeConfirmModal() {
  const modal = document.getElementById('confirm-modal');
  if (modal) {
    modal.remove();
  }
}

// ===== GESTION DU SLIDER DE SEUIL =====
function initThresholdSlider() {
  const thresholdSlider = document.getElementById('default-threshold');
  const thresholdValue = document.getElementById('threshold-value');
  const saveBtn = document.getElementById('save-threshold-config');
  
  if (thresholdSlider && thresholdValue) {
    // Mettre à jour l'affichage lors du changement
    thresholdSlider.addEventListener('input', function() {
      const value = this.value;
      thresholdValue.textContent = value + '%';
    });
    
    // Initialiser avec la valeur par défaut
    thresholdValue.textContent = thresholdSlider.value + '%';
  }
  
  // Event listener pour sauvegarder le seuil
  if (saveBtn) {
    saveBtn.addEventListener('click', async function() {
      
      const threshold = thresholdSlider ? thresholdSlider.value : 90;
      
      try {
        const csrfToken = getCSRFToken();
        
        const response = await fetch('/api/v1/budgets/threshold', {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
          },
          body: JSON.stringify({
            default_threshold: parseInt(threshold),
            update_existing: true
          })
        });
        
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
          showAlert('Seuil par défaut sauvegardé avec succès !', 'success');
        } else {
          showAlert(result.message || 'Erreur lors de la sauvegarde', 'error');
        }
      } catch (error) {
        console.error('❌ Erreur sauvegarde seuil:', error);
        showAlert('Erreur de connexion lors de la sauvegarde', 'error');
      }
    });
    
  } else {
    console.warn('⚠️ Bouton save-threshold-config non trouvé');
  }
}

// ===== CHARGEMENT SEUIL PAR DÉFAUT =====
async function loadDefaultThreshold() {
  try {
    
    const response = await fetch('/api/v1/budgets/threshold', {
      method: 'GET',
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success') {
        const threshold = data.default_threshold || 90;
        
        // Mettre à jour le slider et l'affichage
        const thresholdSlider = document.getElementById('default-threshold');
        const thresholdValue = document.getElementById('threshold-value');
        
        if (thresholdSlider) {
          thresholdSlider.value = threshold;
        }
        
        if (thresholdValue) {
          thresholdValue.textContent = threshold + '%';
        }
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement seuil par défaut:', error);
  }
}