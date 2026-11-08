// Dashboard Simplifié - Version épurée et moderne

document.addEventListener('DOMContentLoaded', function() {
  
  // Initialiser les fonctionnalités principales
  initQuickTransactionModal();
  
  // Charger les données
  loadBudgetOverview();
  loadAccountsBalance();
});

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
      <span class="${isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
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
      <div class="text-center text-gray-500 py-12 dark:text-gray-400">
        <i class="fas fa-chart-pie text-gray-300 text-4xl mb-4"></i>
        <p class="text-lg mb-2">Aucun budget configuré</p>
        <p class="text-sm">Créez votre premier budget pour suivre vos dépenses</p>
      </div>
    `;
    return;
  }
  
  // Les 3 budgets actifs les plus consommés (les autres sont sur /budgets/)
  const topBudgets = budgets
    .filter(b => b.active)
    .sort((a, b) => b.raw_percentage - a.raw_percentage)
    .slice(0, 3);
  container.innerHTML = topBudgets.map(budget => `
    <div class="p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors duration-200 dark:bg-gray-700 dark:hover:bg-gray-600">
      <div class="flex items-center justify-between mb-2">
        <h4 class="font-medium text-gray-900 dark:text-white">${escapeHtml(budget.category_name)}</h4>
        <span class="text-sm font-semibold ${budget.is_over_budget ? 'text-red-600 dark:text-red-400' : budget.is_near_limit ? 'text-orange-600 dark:text-orange-400' : 'text-green-600 dark:text-green-400'}">
          ${budget.spent_percentage.toFixed(0)}%
        </span>
      </div>
      
      <div class="flex items-center justify-between text-sm text-gray-600 mb-2 dark:text-gray-400">
        <span>${formatCurrency(budget.spent_amount)} dépensés</span>
        <span>sur ${formatCurrency(budget.available_amount)}</span>
      </div>
      
      <div class="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-600">
        <div class="h-2 rounded-full transition-all duration-300 ${
          budget.is_over_budget ? 'bg-red-500' : 
          budget.is_near_limit ? 'bg-orange-500' : 'bg-green-500'
        }" style="width: ${Math.min(budget.spent_percentage, 100)}%"></div>
      </div>
      
      ${budget.is_over_budget ?
        '<div class="mt-2 text-xs text-red-600 dark:text-red-400">⚠️ Budget dépassé</div>' :
        `<div class="mt-2 text-xs ${budget.projected_amount > budget.available_amount ? 'text-orange-600 dark:text-orange-400' : 'text-gray-500 dark:text-gray-400'}">
          Reste ${formatCurrency(budget.daily_allowance)}/jour · projection ${formatCurrency(budget.projected_amount)}
        </div>`
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

function showAlert(message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) return;
  
  const alertClass = type === 'success' ? 'bg-green-100 border-green-500 text-green-700 dark:bg-green-900/40 dark:text-green-300' :
                    type === 'error' ? 'bg-red-100 border-red-500 text-red-700 dark:bg-red-900/40 dark:text-red-300' :
                    'bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300';
  
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
