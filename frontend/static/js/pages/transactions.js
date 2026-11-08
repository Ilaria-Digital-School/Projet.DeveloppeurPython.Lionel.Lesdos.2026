/**
 * Gestion des transactions - Script principal
 * Design moderne avec modal, compatible avec les pages comptes et catégories
 */

document.addEventListener('DOMContentLoaded', function() {
  
  // Initialisation
  initializeDatePickers();
  initializeEventListeners();
  initializeBulkSelection();
  
  // Vérification initiale des cases
  setTimeout(() => {
    updateBulkDeleteButton();
  }, 500);
  
  // Masquer les messages flash après 5 secondes
  setTimeout(hideFlashMessages, 5000);
});

/**
 * Initialise les gestionnaires d'événements
 */
function initializeEventListeners() {
  
  // Boutons d'ajout de transaction
  const addButtons = ['add-transaction-btn', 'add-first-transaction'];
  addButtons.forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', () => showTransactionModal());
    }
  });
  
  // Boutons import/export
  const importBtn = document.getElementById('import-btn');
  const exportBtn = document.getElementById('export-btn');
  
  if (importBtn) {
    importBtn.addEventListener('click', function(e) {
      e.preventDefault();
      // Appel direct inline pour éviter les problèmes de hoisting
      
      // Créer la modal d'import si elle n'existe pas
      let importModal = document.getElementById('import-modal');
      if (!importModal) {
        
        // Créer directement la modal HTML
        const modalHTML = `
    <div id="import-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: none; align-items: center; justify-content: center;">
      <div class="modal-content" style="border-radius: 8px; width: 90%; max-width: 600px; max-height: 90vh; position: relative;">
        <div class="modal-header">
          <h3 class="modal-title">Importer des transactions</h3>
          <button type="button" class="close close-import-modal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="mb-4">
            <p class="text-sm text-gray-600 mb-2 dark:text-gray-400">
              Importez vos transactions depuis un fichier CSV. Le fichier doit contenir les colonnes suivantes :
            </p>
            <ul class="text-sm text-gray-500 list-disc list-inside mb-4 dark:text-gray-400">
              <li><strong>Date</strong> : Format DD/MM/YYYY</li>
              <li><strong>Description</strong> : Libellé de la transaction</li>
              <li><strong>Montant</strong> : Montant en euros</li>
            </ul>
          </div>
          <form id="import-form" enctype="multipart/form-data">
            <div class="form-group">
              <label for="import-file">Sélectionner le fichier CSV</label>
              <input type="file" id="import-file" name="file" accept=".csv" class="form-control dark:bg-gray-700 dark:text-white dark:border-gray-600" required>
            </div>
            <div id="import-progress" style="display: none;">
              <div class="bg-gray-200 dark:bg-gray-600" style="border-radius: 4px; height: 8px;">
                <div id="import-progress-bar" style="background: #3b82f6; height: 8px; border-radius: 4px; width: 0%;"></div>
              </div>
              <p id="import-status" style="margin-top: 8px;">Préparation...</p>
            </div>
            <div id="import-results" style="display: none;">
              <div id="import-summary"></div>
              <div id="import-errors" style="display: none;">
                <ul id="import-errors-list"></ul>
              </div>
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary close-import-modal">Annuler</button>
          <button type="submit" form="import-form" class="btn btn-primary" id="import-submit-btn">Importer</button>
        </div>
      </div>
    </div>
        `;
        
        // Ajouter au DOM
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        importModal = document.getElementById('import-modal');
        
        // Ajouter les événements
        const closeButtons = importModal.querySelectorAll('.close-import-modal');
        const importForm = document.getElementById('import-form');
        
        // Fermeture modal
        closeButtons.forEach(btn => {
          btn.addEventListener('click', function() {
            importModal.style.display = 'none';
          });
        });
        
        // Clic dehors
        importModal.addEventListener('click', function(e) {
          if (e.target === importModal) {
            importModal.style.display = 'none';
          }
        });
        
        // Soumission formulaire
        importForm.addEventListener('submit', async function(e) {
          e.preventDefault();
          
          const fileInput = document.getElementById('import-file');
          const progressDiv = document.getElementById('import-progress');
          const progressBar = document.getElementById('import-progress-bar');
          const statusText = document.getElementById('import-status');
          const resultsDiv = document.getElementById('import-results');
          const submitBtn = document.getElementById('import-submit-btn');
          
          try {
            if (!fileInput.files || fileInput.files.length === 0) {
              alert('Veuillez sélectionner un fichier CSV');
              return;
            }
            
            const file = fileInput.files[0];
            if (!file.name.toLowerCase().endsWith('.csv')) {
              alert('Veuillez sélectionner un fichier CSV');
              return;
            }
            
            // Afficher progression
            progressDiv.style.display = 'block';
            submitBtn.disabled = true;
            submitBtn.textContent = 'Import en cours...';
            statusText.textContent = 'Lecture du fichier...';
            
            // Préparer données
            const formData = new FormData();
            formData.append('file', file);
            
            // Envoyer requête (route sans CSRF temporaire)
            const response = await fetch('/api/v1/transactions/import', {
              method: 'POST',
              headers: {
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
              },
              body: formData
            });
            
            const data = await response.json();
            
            // Afficher résultats
            progressBar.style.width = '100%';
            statusText.textContent = 'Terminé';
            resultsDiv.style.display = 'block';
            
            const summary = document.getElementById('import-summary');
            if (response.ok && data.status === 'success') {
              summary.innerHTML = `<h4 style="color: green;">Import réussi !</h4><p>${escapeHtml(data.imported_count)} transaction(s) importée(s)</p>`;
              setTimeout(() => window.location.reload(), 2000);
            } else {
              summary.innerHTML = `<h4 style="color: red;">Erreur</h4><p>${escapeHtml(data.error || 'Erreur lors de l\'import')}</p>`;
            }

          } catch (error) {
            console.error('Erreur import:', error);
            resultsDiv.style.display = 'block';
            document.getElementById('import-summary').innerHTML = `<h4 style="color: red;">Erreur</h4><p>${escapeHtml(error.message)}</p>`;
            
          } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Importer';
          }
        });
        
      }
      
      if (importModal) {
        importModal.style.display = 'flex';
        importModal.classList.add('show');
      } else {
        console.error('❌ Impossible de créer ou trouver la modal d\'import');
      }
    });
  }
  
  if (exportBtn) {
    exportBtn.addEventListener('click', function(e) {
      e.preventDefault();
      showExportModal();
    });
  }
  
  // Fermeture de la modal
  const closeButtons = document.querySelectorAll('.close-modal');
  closeButtons.forEach(btn => {
    btn.addEventListener('click', closeTransactionModal);
  });
  
  // Clic en dehors de la modal pour la fermer
  const modal = document.getElementById('transaction-modal');
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        closeTransactionModal();
      }
    });
  }
  
  // Soumission du formulaire
  const form = document.getElementById('transaction-form');
  if (form) {
    // Retirer l'ancien listener s'il existe
    form.removeEventListener('submit', handleFormSubmit);
    form.addEventListener('submit', handleFormSubmit);
  }
  
  // Gestion du type de transaction (afficher/masquer compte destination)
  const typeSelect = document.getElementById('transaction-type');
  if (typeSelect) {
    typeSelect.addEventListener('change', handleTypeChange);
    // Appeler au chargement pour définir l'état initial
    handleTypeChange();
  }
  
  // Filtrage des catégories par type
  const categorySelect = document.getElementById('transaction-category');
  if (typeSelect && categorySelect) {
    typeSelect.addEventListener('change', filterCategoriesByType);
  }
  
  // Gestion des filtres
  const filtersForm = document.getElementById('filters-form');
  const filtresUrl = appliquerFiltresUrl();
  loadTotaux();
  initParPage(filtresUrl);
  if (filtersForm) {
    filtersForm.addEventListener('submit', function(e) {
      e.preventDefault();
      loadTransactions();
    });
    
    const resetBtn = document.getElementById('reset-filters');
    if (resetBtn) {
      resetBtn.addEventListener('click', function() {
        filtersForm.reset();
        loadTransactions();
      });
    }
  }
  
  // Boutons d'édition et suppression (délégation d'événements)
  document.addEventListener('click', function(e) {
    if (e.target.closest('.edit-transaction')) {
      e.preventDefault();
      const transactionId = e.target.closest('.edit-transaction').dataset.id;
      editTransaction(transactionId);
    }
    
    if (e.target.closest('.delete-transaction')) {
      e.preventDefault();
      const transactionId = e.target.closest('.delete-transaction').dataset.id;
      const transactionElement = e.target.closest('tr');
      const description = transactionElement.querySelector('.text-sm.font-medium.text-gray-900')?.textContent || 'cette transaction';
      
      showConfirmDialog(
        'Supprimer la transaction',
        `Êtes-vous sûr de vouloir supprimer la transaction "${description}" ? Cette action est irréversible.`,
        'Supprimer',
        'Annuler'
      ).then(confirmed => {
        if (confirmed) {
          deleteTransaction(transactionId);
        }
      });
    }
  });
}

/**
 * Affiche la modal de transaction
 */
function showTransactionModal(transactionId = null) {
  const modal = document.getElementById('transaction-modal');
  const form = document.getElementById('transaction-form');
  const title = document.getElementById('modal-title');
  
  if (!modal || !form || !title) return;
  
  // Réinitialiser le formulaire
  form.reset();
  document.getElementById('transaction-id').value = transactionId || '';
  
  // Mettre à jour le titre
  title.textContent = transactionId ? 'Modifier la transaction' : 'Nouvelle transaction';
  
  // Définir la date par défaut
  const dateInput = document.getElementById('transaction-date');
  if (dateInput && !transactionId) {
    const today = new Date();
    const formattedDate = today.toLocaleDateString('fr-FR');
    dateInput.value = formattedDate;
    
    if (dateInput._flatpickr) {
      dateInput._flatpickr.setDate(today, false);
    }
  }
  
  // Charger les données si modification
  if (transactionId) {
    loadTransactionForEdit(transactionId);
  } else {
    // Configurer l'interface pour nouvelle transaction
    handleTypeChange(); // Masquer le champ destination par défaut
    filterCategoriesByType(); // Filtrer les catégories
  }
  
  // Afficher la modal
  modal.classList.add('show');
  document.body.style.overflow = 'hidden';
}

/**
 * Ferme la modal de transaction
 */
function closeTransactionModal() {
  const modal = document.getElementById('transaction-modal');
  if (modal) {
    modal.classList.remove('show');
    document.body.style.overflow = '';
  }
}

/**
 * Gère le changement de type de transaction
 */
function handleTypeChange() {
  const typeSelect = document.getElementById('transaction-type');
  const destinationGroup = document.getElementById('destination-account-group');
  
  if (!typeSelect || !destinationGroup) return;
  
  const isTransfer = typeSelect.value === 'transfer';
  destinationGroup.style.display = isTransfer ? 'block' : 'none';
  
  // Filtrer les catégories
  filterCategoriesByType();
}

/**
 * Filtre les catégories en fonction du type de transaction
 */
function filterCategoriesByType() {
  const typeSelect = document.getElementById('transaction-type');
  const categorySelect = document.getElementById('transaction-category');
  
  if (!typeSelect || !categorySelect) return;
  
  const selectedType = typeSelect.value;
  
  // Convertir les types spécifiques vers les types génériques
  let genericType = 'expense'; // défaut
  if (['salaire', 'income'].includes(selectedType.toLowerCase())) {
    genericType = 'income';
  } else if (['achat', 'expense', 'loyer', 'facture'].includes(selectedType.toLowerCase())) {
    genericType = 'expense';
  } else if (['virement', 'transfer'].includes(selectedType.toLowerCase())) {
    genericType = 'transfer';
  }
  
  
  const options = categorySelect.querySelectorAll('option');
  
  options.forEach(option => {
    if (option.value === '') {
      option.hidden = false;
      return;
    }
    
    const categoryType = option.dataset.type;
    // Afficher les catégories qui correspondent au type sélectionné
    option.hidden = categoryType !== genericType;
  });
  
  
  // Réinitialiser la sélection si l'option actuelle est cachée
  if (categorySelect.selectedOptions[0] && categorySelect.selectedOptions[0].hidden) {
    categorySelect.value = '';
  }
}

/**
 * Gère la soumission du formulaire
 */
function handleFormSubmit(e) {
  e.preventDefault();
  
  const form = e.target;
  
  // Protection contre les double-soumissions
  if (form.dataset.submitting === 'true') {
    return;
  }
  form.dataset.submitting = 'true';
  
  const formData = new FormData(form);
  const transactionId = formData.get('id');
  const isEdit = !!transactionId;
  
  // Validation basique
  if (!validateForm(formData)) {
    form.dataset.submitting = 'false';
    return;
  }
  
  // Désactiver le bouton de soumission
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn ? submitBtn.innerHTML : '';
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Enregistrement...';
  }
  
  // Préparer les données
  const data = prepareFormData(formData);
  
  // Envoyer la requête
  const url = isEdit ? `/api/v1/transactions/${transactionId}` : '/api/v1/transactions';
  const method = isEdit ? 'PUT' : 'POST';
  
  fetch(url, {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
    },
    body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(result => {
    if (result.status === 'success') {
      showAlert(`Transaction ${isEdit ? 'modifiée' : 'créée'} avec succès`, 'success');
      closeTransactionModal();
      loadTransactions();
    } else {
      throw new Error(result.message || 'Erreur inconnue');
    }
  })
  .catch(error => {
    console.error('❌ Erreur:', error);
    showAlert(error.message || 'Une erreur est survenue', 'error');
  })
  .finally(() => {
    // Réinitialiser l'état de soumission
    form.dataset.submitting = 'false';
    
    // Réactiver le bouton
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalText;
    }
  });
}

/**
 * Valide les données du formulaire
 */
function validateForm(formData) {
  const errors = [];
  
  if (!formData.get('type')) {
    errors.push('Le type de transaction est requis');
  }
  
  const amount = parseFloat(formData.get('amount'));
  if (!amount || amount <= 0) {
    errors.push('Le montant doit être supérieur à zéro');
  }
  
  if (!formData.get('date')) {
    errors.push('La date est requise');
  }
  
  if (!formData.get('account')) {
    errors.push('Le compte est requis');
  }
  
  if (!formData.get('description')?.trim()) {
    errors.push('La description est requise');
  }
  
  if (errors.length > 0) {
    showAlert(errors.join('\n'), 'error');
    return false;
  }
  
  return true;
}

/**
 * Prépare les données du formulaire pour l'API
 */
function prepareFormData(formData) {
  const type = formData.get('type');
  const amount = parseFloat(formData.get('amount'));
  
  // Convertir la date du format français vers ISO avec heure intelligente
  let dateStr = formData.get('date');
  if (dateStr) {
    try {
      // Nouveau format: "DD/MM/YYYY HH:mm"
      if (dateStr.includes('/') && dateStr.includes(' ')) {
        const [datePart, timePart] = dateStr.split(' ');
        const dateParts = datePart.split('/');
        if (dateParts.length === 3) {
          const day = dateParts[0].padStart(2, '0');
          const month = dateParts[1].padStart(2, '0');
          const year = dateParts[2];
          dateStr = `${year}-${month}-${day} ${timePart}:00`; // Ajouter secondes
        }
      }
      // Format ancien (compatibilité): "DD/MM/YYYY" sans heure
      else if (dateStr.includes('/')) {
        const parts = dateStr.split('/');
        if (parts.length === 3) {
          const day = parts[0].padStart(2, '0');
          const month = parts[1].padStart(2, '0');
          const year = parts[2];
          
          // Utiliser l'heure ACTUELLE au lieu de midi
          const now = new Date();
          const hours = now.getHours().toString().padStart(2, '0');
          const minutes = now.getMinutes().toString().padStart(2, '0');
          dateStr = `${year}-${month}-${day} ${hours}:${minutes}:00`;
        }
      }
    } catch (error) {
      console.error('Erreur parsing date:', error);
      // Fallback avec heure actuelle
      const now = new Date();
      dateStr = now.toISOString().slice(0, 19).replace('T', ' ');
    }
  }
  
  // Convertir le type générique vers enum spécifique
  let enumType = type;
  if (type === 'income') {
    enumType = 'salaire';
  } else if (type === 'expense') {
    enumType = 'achat';
  } else if (type === 'transfer') {
    enumType = 'virement';
  }
  
  return {
    type: enumType,
    amount: Math.abs(amount),
    date: dateStr,
    description: formData.get('description').trim(),
    category_id: formData.get('category') || null,
    account_id: formData.get('account'),
    destination_account_id: formData.get('destination_account') || null,
    notes: (formData.get('notes') || '').trim(),
    status: 'completed'
  };
}

/**
 * Pré-remplit les filtres depuis l'adresse de la page
 * (ex. /transactions/?category=12&type=expense&date_from=01/06/2026).
 * @returns {boolean} true si au moins un filtre a été appliqué
 */
function appliquerFiltresUrl() {
  const params = new URLSearchParams(window.location.search);
  const champs = {
    account: 'filter-account',
    category: 'filter-category',
    type: 'filter-type',
    search: 'filter-search',
    date_from: 'filter-date-from',
    date_to: 'filter-date-to',
  };
  let applique = false;
  for (const [cle, id] of Object.entries(champs)) {
    const valeur = params.get(cle);
    const champ = document.getElementById(id);
    if (!valeur || !champ) continue;
    if (champ._flatpickr) {
      champ._flatpickr.setDate(valeur, false, 'd/m/Y');
    } else if (champ.tagName === 'SELECT' && ![...champ.options].some(o => o.value === valeur)) {
      continue;
    } else {
      champ.value = valeur;
    }
    applique = true;
  }
  return applique;
}

/**
 * Paramètres de requête issus du formulaire de filtres
 */
function filtresCourants() {
  const filtersForm = document.getElementById('filters-form');
  const params = new URLSearchParams();
  if (filtersForm) {
    for (const [key, value] of new FormData(filtersForm).entries()) {
      if (value) params.append(key, value);
    }
  }
  return params;
}

const CLE_PAR_PAGE = 'transactions-par-page';

/**
 * Nombre de transactions par page choisi ("all" = toutes)
 */
function parPage() {
  return document.getElementById('per-page')?.value || '10';
}

/**
 * Sélecteur "Afficher N par page" : restaure le dernier choix et recharge
 * la liste quand il change
 */
function initParPage(rechargerAuDemarrage = false) {
  const select = document.getElementById('per-page');
  if (!select) return;
  let memorise = null;
  try {
    memorise = localStorage.getItem(CLE_PAR_PAGE);
  } catch {
    // stockage indisponible : on garde 10
  }
  if (memorise && [...select.options].some(o => o.value === memorise)) {
    select.value = memorise;
  }
  select.addEventListener('change', () => {
    try {
      localStorage.setItem(CLE_PAR_PAGE, select.value);
    } catch {
      // stockage indisponible : le choix vaut pour cette page seulement
    }
    loadTransactions(1);
  });
  // La liste initiale du serveur est par 10 et sans filtre : la recharger
  if (select.value !== '10' || rechargerAuDemarrage) loadTransactions(1);
}

/**
 * Affiche les totaux (toutes pages) des transactions filtrées
 */
function renderTotaux(totaux) {
  if (!totaux) return;
  const euros = (v) => Number(v).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });
  const champs = { 'total-depenses': totaux.depenses, 'total-revenus': totaux.revenus, 'total-solde': totaux.solde };
  for (const [id, valeur] of Object.entries(champs)) {
    const el = document.getElementById(id);
    if (el) el.textContent = euros(valeur);
  }
  const solde = document.getElementById('total-solde');
  if (solde) {
    const negatif = totaux.solde < 0;
    solde.classList.toggle('text-red-600', negatif);
    solde.classList.toggle('dark:text-red-400', negatif);
    solde.classList.toggle('text-gray-900', !negatif);
    solde.classList.toggle('dark:text-gray-100', !negatif);
  }
}

/**
 * Totaux au chargement de la page (la liste initiale est rendue par le serveur)
 */
function loadTotaux() {
  const params = filtresCourants();
  params.append('per_page', 1);
  fetch(`/api/v1/transactions?${params.toString()}`, {
    headers: { 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(response => (response.ok ? response.json() : null))
    .then(data => renderTotaux(data?.totaux))
    .catch(error => console.error('Erreur lors du calcul des totaux:', error));
}

/**
 * Charge les transactions avec filtres
 */
function loadTransactions(page = 1) {
  
  const tbody = document.getElementById('transactions-list');
  if (!tbody) return;
  
  // Afficher un indicateur de chargement
  tbody.innerHTML = `
    <tr>
      <td colspan="6" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
        <i class="fas fa-spinner fa-spin text-2xl mb-2"></i>
        <p>Chargement des transactions...</p>
      </td>
    </tr>
  `;
  
  // Récupérer les filtres
  const params = filtresCourants();
  params.append('page', page);
  params.append('per_page', parPage());
  
  // Faire la requête
  fetch(`/api/v1/transactions?${params.toString()}`, {
    headers: {
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.status === 'success' && Array.isArray(data.transactions)) {
      displayTransactions(data.transactions);
      renderPagination(data.pagination);
      renderTotaux(data.totaux);
    } else {
      throw new Error(data.message || 'Format de réponse invalide');
    }
  })
  .catch(error => {
    console.error('❌ Erreur lors du chargement:', error);
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="px-6 py-8 text-center text-red-500">
          <i class="fas fa-exclamation-triangle text-2xl mb-2"></i>
          <p>Erreur lors du chargement des transactions</p>
          <p class="text-sm">${escapeHtml(error.message)}</p>
        </td>
      </tr>
    `;
  });
}

/**
 * Pagination de la liste rechargée par les filtres : celle rendue par le
 * serveur ne connaît pas les filtres et ramènerait à la liste complète
 */
function renderPagination(pagination) {
  const container = document.getElementById('transactions-pagination');
  if (!container) return;
  if (!pagination || pagination.pages <= 1) {
    const total = pagination?.total || 0;
    container.innerHTML = total ? `
      <p class="mt-4 text-sm text-gray-700 dark:text-gray-300">
        <span class="font-medium">${total}</span> transaction${total > 1 ? 's' : ''}
      </p>` : '';
    return;
  }

  const { page, per_page: perPage, total, pages } = pagination;
  const first = (page - 1) * perPage + 1;
  const last = Math.min(page * perPage, total);
  const bouton = (cible, contenu, label) => `
    <button type="button" data-page="${cible}" aria-label="${label}"
            class="px-3 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:bg-gray-700">
      ${contenu}
    </button>`;

  container.innerHTML = `
    <div class="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6 mt-4 rounded-lg shadow dark:bg-gray-800 dark:border-gray-700">
      <p class="text-sm text-gray-700 dark:text-gray-300">
        Affichage de <span class="font-medium">${first}</span> à <span class="font-medium">${last}</span>
        sur <span class="font-medium">${total}</span> transactions
      </p>
      <div class="flex items-center space-x-1">
        ${page > 1 ? bouton(page - 1, '<i class="fas fa-chevron-left"></i>', 'Page précédente') : ''}
        <span class="px-3 py-2 text-sm font-medium text-blue-600 bg-blue-50 border border-blue-300 rounded-md dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800">
          ${page} / ${pages}
        </span>
        ${page < pages ? bouton(page + 1, '<i class="fas fa-chevron-right"></i>', 'Page suivante') : ''}
      </div>
    </div>`;

  container.querySelectorAll('button[data-page]').forEach(btn => {
    btn.addEventListener('click', () => loadTransactions(parseInt(btn.dataset.page, 10)));
  });
}

/**
 * Affiche les transactions dans le tableau
 */
function displayTransactions(transactions) {
  const tbody = document.getElementById('transactions-list');
  if (!tbody) return;
  
  
  if (transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
          <i class="fas fa-receipt text-3xl block mb-2"></i>
          <p>Aucune transaction trouvée</p>
          <button id="add-first-transaction" class="mt-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">
            <i class="fas fa-plus mr-2"></i>Ajouter votre première transaction
          </button>
        </td>
      </tr>
    `;
    return;
  }
  
  let html = '';
  transactions.forEach(transaction => {
    // Mapper les types français vers les types anglais
    const typeMapping = {
      'achat': 'expense',
      'expense': 'expense',
      'salaire': 'income', 
      'income': 'income',
      'virement': 'transfer',
      'transfer': 'transfer'
    };
    
    const rawType = transaction.type || 'achat';
    const transactionType = typeMapping[rawType.toLowerCase()] || 'expense';
    
    const isIncome = transactionType === 'income';
    const isTransfer = transactionType === 'transfer';
    
    const formattedAmount = Math.abs(transaction.amount).toLocaleString('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
    
    // Parser le format français DD/MM/YYYY vers un objet Date valide
    let date, formattedDate, formattedTime;
    
    if (transaction.date && transaction.date.includes('/')) {
      // Format français DD/MM/YYYY
      const parts = transaction.date.split('/');
      if (parts.length === 3) {
        const day = parseInt(parts[0], 10);
        const month = parseInt(parts[1], 10) - 1; // Mois 0-11 en JavaScript
        const year = parseInt(parts[2], 10);
        date = new Date(year, month, day);
      } else {
        date = new Date(); // fallback
      }
    } else {
      // Essayer d'autres formats
      date = new Date(transaction.date);
    }
    
    // Vérifier si la date est valide
    if (isNaN(date.getTime())) {
      console.warn(`⚠️ Date invalide pour transaction ${transaction.id}: ${transaction.date}`);
      formattedDate = transaction.date || 'Date invalide';
      formattedTime = '--:--';
    } else {
      formattedDate = date.toLocaleDateString('fr-FR');
      formattedTime = date.toLocaleTimeString('fr-FR', { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    }
    
    const safeDesc = escapeHtml(transaction.description || 'Sans description');
    const safeNotes = escapeHtml(transaction.notes || '');
    const safeCategory = escapeHtml(transaction.category || '');
    const safeAccount = escapeHtml(transaction.account || 'N/A');
    const safeId = escapeHtml(transaction.id);

    html += `
      <tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
        <td class="px-6 py-4 whitespace-nowrap">
          <div class="text-sm font-medium text-gray-900 dark:text-white">${formattedDate}</div>
          <div class="text-sm text-gray-500 dark:text-gray-400">${formattedTime}</div>
        </td>
        <td class="px-6 py-4">
          <div class="flex items-center">
            <div class="transaction-icon-container mr-3">
              ${isTransfer ?
                '<i class="fas fa-exchange-alt text-blue-600 dark:text-blue-400"></i>' :
                `<i class="fas fa-${isIncome ? 'plus' : 'minus'} text-${isIncome ? 'green' : 'red'}-600"></i>`
              }
            </div>
            <div>
              <div class="text-sm font-medium text-gray-900 dark:text-white">${safeDesc}</div>
              ${safeNotes ? `<div class="text-sm text-gray-500 dark:text-gray-400">${safeNotes}</div>` : ''}
            </div>
          </div>
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
          ${safeCategory ?
            `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">
               ${safeCategory}
             </span>` :
            `<span class="text-sm text-gray-500 dark:text-gray-400">Non catégorisé</span>`
          }
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
          ${safeAccount}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-right">
          ${isTransfer ?
            `<span class="text-sm font-medium text-blue-600 dark:text-blue-400">
              ↔ ${formattedAmount} €
            </span>` :
            `<span class="text-sm font-medium text-${isIncome ? 'green' : 'red'}-600">
              ${isIncome ? '+' : '-'}${formattedAmount} €
            </span>`
          }
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
          <button type="button" class="text-blue-600 hover:text-blue-900 mr-4 edit-transaction dark:text-blue-400 dark:hover:text-blue-300" data-id="${safeId}">
            <i class="fas fa-edit"></i> Modifier
          </button>
          <button type="button" class="text-red-600 hover:text-red-900 delete-transaction dark:text-red-400 dark:hover:text-red-300" data-id="${safeId}">
            <i class="fas fa-trash"></i> Supprimer
          </button>
        </td>
      </tr>
    `;
  });
  
  tbody.innerHTML = html;
}

/**
 * Charge une transaction pour modification
 */
function loadTransactionForEdit(transactionId) {
  
  fetch(`/api/v1/transactions/${transactionId}`, {
    headers: {
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.id) {
      // L'API retourne directement les données de la transaction
      populateForm(data);
    } else {
      throw new Error('Transaction non trouvée');
    }
  })
  .catch(error => {
    console.error('❌ Erreur chargement transaction:', error);
    console.error('❌ Détails erreur:', error.message);
    showAlert('Erreur lors du chargement de la transaction: ' + error.message, 'error');
    closeTransactionModal();
  });
}

/**
 * Remplit le formulaire avec les données de la transaction
 */
function populateForm(transaction) {
  
  try {
    const elements = {
      'transaction-id': transaction.id || '',
      'transaction-type': transaction.type || 'expense',
      'transaction-amount': Math.abs(transaction.amount || 0),
      'transaction-date': transaction.date || '',
      'transaction-account': transaction.account_id || '',
      'transaction-description': transaction.description || '',
      'transaction-notes': transaction.notes || ''
    };
    
    // Remplir les champs de base
    for (const [elementId, value] of Object.entries(elements)) {
      const element = document.getElementById(elementId);
      if (element) {
        element.value = value;
      } else {
        console.warn(`⚠️ Élément ${elementId} non trouvé`);
      }
    }
    
    // Destination pour virements
    if (transaction.destination_account_id) {
      const destElement = document.getElementById('transaction-destination');
      if (destElement) {
        destElement.value = transaction.destination_account_id;
      }
    }
    
    // IMPORTANT: Filtrer les catégories AVANT d'assigner la catégorie
    handleTypeChange();
    filterCategoriesByType();
    
    // Assigner la catégorie APRÈS avoir filtré
    if (transaction.category_id) {
      const categoryElement = document.getElementById('transaction-category');
      if (categoryElement) {
        categoryElement.value = transaction.category_id;
      }
    }
    
    
  } catch (error) {
    console.error('❌ Erreur lors du remplissage du formulaire:', error);
    throw error; // Propager l'erreur pour que la modal se ferme en cas de problème grave
  }
}

/**
 * Édite une transaction
 */
function editTransaction(transactionId) {
  showTransactionModal(transactionId);
}

/**
 * Supprime une transaction
 */
function deleteTransaction(transactionId) {
  
  const deleteBtn = document.querySelector(`.delete-transaction[data-id="${transactionId}"]`);
  const originalContent = deleteBtn ? deleteBtn.innerHTML : '';
  
  if (deleteBtn) {
    deleteBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    deleteBtn.disabled = true;
  }
  
  fetch(`/api/v1/transactions/${transactionId}`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
    }
  })
  .then(response => {
    if (!response.ok) {
      throw new Error(`Erreur HTTP: ${response.status}`);
    }
    return response.json();
  })
  .then(data => {
    if (data.status === 'success') {
      showAlert('Transaction supprimée avec succès', 'success');
      loadTransactions();
    } else {
      throw new Error(data.message || 'Erreur lors de la suppression');
    }
  })
  .catch(error => {
    console.error('❌ Erreur suppression:', error);
    showAlert(error.message || 'Erreur lors de la suppression', 'error');
    
    // Restaurer le bouton
    if (deleteBtn) {
      deleteBtn.innerHTML = originalContent;
      deleteBtn.disabled = false;
    }
  });
}

/**
 * Initialise les sélecteurs de date Flatpickr
 */
function initializeDatePickers() {
  if (typeof flatpickr === 'undefined') {
    console.warn('⚠️ Flatpickr non chargé');
    return;
  }
  
  // Configuration commune avec heure actuelle
  const now = new Date();
  const config = {
    dateFormat: 'd/m/Y H:i',
    locale: 'fr',
    allowInput: true,
    clickOpens: true,
    static: true,
    enableTime: true,
    time_24hr: true,
    defaultDate: now,
    defaultHour: now.getHours(),
    defaultMinute: now.getMinutes()
  };
  
  // Datepicker du formulaire
  const transactionDate = document.getElementById('transaction-date');
  if (transactionDate) {
    flatpickr(transactionDate, {
      ...config,
      maxDate: 'today'
    });
  }
  
  // Datepickers des filtres (début et fin)
  const filterDateFrom = document.getElementById('filter-date-from');
  const filterDateTo = document.getElementById('filter-date-to');
  
  // Les filtres portent sur des jours : l'API attend JJ/MM/AAAA, sans heure
  const filterConfig = { ...config, dateFormat: 'd/m/Y', enableTime: false };

  if (filterDateFrom) {
    flatpickr(filterDateFrom, {
      ...filterConfig,
      defaultDate: null, // Pas de date par défaut pour les filtres
      onChange: function(selectedDates) {
        // Mettre à jour la date minimale du champ "date de fin"
        if (filterDateTo && filterDateTo._flatpickr && selectedDates[0]) {
          filterDateTo._flatpickr.set('minDate', selectedDates[0]);
        }
      }
    });
  }
  
  if (filterDateTo) {
    flatpickr(filterDateTo, {
      ...filterConfig,
      defaultDate: null, // Pas de date par défaut pour les filtres
      onChange: function(selectedDates) {
        // Mettre à jour la date maximale du champ "date de début"
        if (filterDateFrom && filterDateFrom._flatpickr && selectedDates[0]) {
          filterDateFrom._flatpickr.set('maxDate', selectedDates[0]);
        }
      }
    });
  }
}

/**
 * Affiche une alerte
 */
function showAlert(message, type = 'info') {
  const container = document.getElementById('alert-container');
  if (!container) {
    return;
  }
  
  const alertClass = {
    success: 'bg-green-50 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-200 dark:border-green-800',
    error: 'bg-red-50 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-200 dark:border-red-800',
    warning: 'bg-yellow-50 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-200 dark:border-yellow-800',
    info: 'bg-blue-50 text-blue-800 border-blue-300 dark:bg-blue-900/30 dark:text-blue-200 dark:border-blue-800'
  }[type] || 'bg-gray-50 text-gray-800 border-gray-300 dark:bg-gray-700 dark:text-gray-100 dark:border-gray-600';
  
  const iconClass = {
    success: 'fa-check-circle text-green-600 dark:text-green-400',
    error: 'fa-exclamation-circle text-red-600 dark:text-red-400', 
    warning: 'fa-exclamation-triangle text-yellow-600 dark:text-yellow-400',
    info: 'fa-info-circle text-blue-600 dark:text-blue-400'
  }[type] || 'fa-info-circle text-gray-600 dark:text-gray-400';
  
  const alert = document.createElement('div');
  alert.className = `${alertClass} border px-4 py-3 rounded mb-4 flex items-center`;
  alert.innerHTML = `
    <i class="fas ${iconClass} mr-3"></i>
    <span>${escapeHtml(message)}</span>
  `;

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.className = 'ml-auto pl-3';
  closeBtn.innerHTML = '<i class="fas fa-times text-current opacity-50 hover:opacity-75"></i>';
  closeBtn.addEventListener('click', () => alert.remove());
  alert.appendChild(closeBtn);
  
  container.appendChild(alert);
  
  // Auto-suppression après 5 secondes
  setTimeout(() => {
    if (alert.parentElement) {
      alert.remove();
    }
  }, 5000);
}

/**
 * Masque les messages flash
 */
function hideFlashMessages() {
  const flashMessages = document.querySelectorAll('.alert, .flash-message');
  flashMessages.forEach(msg => {
    msg.style.opacity = '0';
    setTimeout(() => msg.remove(), 300);
  });
}

/**
 * Affiche une modale de confirmation moderne
 */
/**
 * =====================================
 * GESTION DE LA SÉLECTION MULTIPLE
 * =====================================
 */

/**
 * Initialise la gestion de sélection multiple
 */
function initializeBulkSelection() {
  
  // Gestionnaire pour cases individuelles
  document.addEventListener('change', function(e) {
    if (e.target.classList.contains('transaction-checkbox')) {
      updateBulkDeleteButton();
    }
  });
  
  // Gestionnaire pour bouton suppression en lot
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  if (bulkDeleteBtn) {
    bulkDeleteBtn.addEventListener('click', handleBulkDelete);
  }
  
  // Observer les changements dans le tableau pour maintenir les cases
  const tableBody = document.getElementById('transactions-list');
  if (tableBody) {
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'childList') {
          setTimeout(() => {
            reinitializeBulkSelection();
          }, 100);
        }
      });
    });
    
    observer.observe(tableBody, {
      childList: true,
      subtree: true
    });
    
  }
  
  // Vérification périodique pour maintenir les cases
  setInterval(() => {
    const checkboxes = document.querySelectorAll('.transaction-checkbox');
    const tableRows = document.querySelectorAll('#transactions-list tr');
    
    // Si il y a des lignes mais pas de cases, quelque chose s'est mal passé
    if (tableRows.length > 0 && checkboxes.length === 0) {
      // Ne pas recharger automatiquement pour éviter une boucle
    }
  }, 2000);
}


/**
 * Met à jour la visibilité et le compteur du bouton de suppression
 */
function updateBulkDeleteButton() {
  const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
  const selectedCountSpan = document.getElementById('selected-count');
  const checkedBoxes = document.querySelectorAll('.transaction-checkbox:checked');
  
  if (bulkDeleteBtn && selectedCountSpan) {
    const count = checkedBoxes.length;
    selectedCountSpan.textContent = count;
    
    if (count > 0) {
      bulkDeleteBtn.style.display = 'block';
    } else {
      bulkDeleteBtn.style.display = 'none';
    }
  }
}

/**
 * Réinitialise les gestionnaires d'événements après rechargement du contenu
 */
function reinitializeBulkSelection() {
  
  // Remettre à zéro le bouton
  updateBulkDeleteButton();
  
  // Les gestionnaires d'événements sont déjà en place via document.addEventListener
  // donc pas besoin de les re-ajouter
}

/**
 * Gère la suppression en lot
 */
async function handleBulkDelete() {
  const checkedBoxes = document.querySelectorAll('.transaction-checkbox:checked');
  const transactionIds = Array.from(checkedBoxes).map(cb => cb.dataset.id);
  
  if (transactionIds.length === 0) {
    showAlert('Aucune transaction sélectionnée', 'warning');
    return;
  }
  
  // Confirmation
  const confirmed = await showConfirmDialog(
    'Confirmer la suppression',
    `Êtes-vous sûr de vouloir supprimer ${transactionIds.length} transaction(s) sélectionnée(s) ?`,
    'Cette action est irréversible.'
  );
  
  if (!confirmed) {
    return;
  }
  
  try {
    
    const response = await fetch('/api/v1/transactions/bulk-delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
      },
      body: JSON.stringify({
        transaction_ids: transactionIds
      })
    });
    
    const data = await response.json();
    
    if (response.ok && data.status === 'success') {
      // Afficher le résultat
      let message = data.message;
      if (data.errors && data.errors.length > 0) {
        message += '\n\nErreurs :\n' + data.errors.join('\n');
        showAlert(message, 'warning');
      } else {
        showAlert(message, 'success');
      }
      
      // Recharger la page pour voir les changements
      setTimeout(() => {
        window.location.reload();
      }, 1500);
      
    } else {
      throw new Error(data.error || 'Erreur lors de la suppression');
    }
    
  } catch (error) {
    console.error('❌ Erreur suppression en lot:', error);
    showAlert('Erreur lors de la suppression en lot: ' + error.message, 'error');
  }
}

/**
 * Gère l'export des transactions avec les filtres actuels
 */
async function handleExport() {
  
  try {
    // Version simplifiée avec lien direct pour éviter les problèmes CORS/Auth
    const filtersForm = document.getElementById('filters-form');
    if (!filtersForm) {
      console.warn('⚠️ Formulaire de filtres non trouvé, export sans filtres');
    }
    
    // Construire les paramètres d'URL
    const params = new URLSearchParams();
    
    if (filtersForm) {
      const formData = new FormData(filtersForm);
      // Ajouter les filtres non vides
      for (let [key, value] of formData.entries()) {
        if (value && value.trim() !== '') {
          params.append(key, value);
        }
      }
    }
    
    // Construire l'URL d'export
    const exportUrl = `/api/v1/transactions/export?${params.toString()}`;
    
    // Afficher un message de chargement
    showAlert('Téléchargement du fichier en cours...', 'info');
    
    // Méthode directe pour télécharger le fichier
    const link = document.createElement('a');
    link.href = exportUrl;
    link.download = `transactions_export_${new Date().toISOString().slice(0, 10)}.csv`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Message de succès avec délai
    setTimeout(() => {
      showAlert('Export lancé ! Le téléchargement devrait commencer automatiquement.', 'success');
    }, 500);
    
  } catch (error) {
    console.error('❌ Erreur lors de l\'export:', error);
    showAlert('Erreur lors de l\'export: ' + error.message, 'error');
  }
}

// Rendre la fonction accessible globalement pour les attributs onclick
window.handleExport = handleExport;

/**
 * Affiche la modal d'export
 */
function showExportModal() {
  
  // Créer la modal d'export si elle n'existe pas
  let exportModal = document.getElementById('export-modal');
  if (!exportModal) {
    createExportModal();
    exportModal = document.getElementById('export-modal');
  }
  
  if (exportModal) {
    // Afficher la modal avec styles inline pour garantir la visibilité
    exportModal.style.display = 'flex';
    exportModal.classList.add('show');
    
    // Mettre à jour le résumé des filtres
    updateExportSummary();
  } else {
    console.error('❌ Impossible de créer ou trouver la modal d\'export');
  }
}

/**
 * Crée la modal d'export dynamiquement
 */
function createExportModal() {
  const modalHTML = `
    <div id="export-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: none; align-items: center; justify-content: center;">
      <div class="modal-content" style="border-radius: 8px; width: 90%; max-width: 600px; max-height: 90vh; position: relative;">
        <div class="modal-header" style="padding: 1rem 1.5rem; border-bottom: 1px solid #E5E7EB; display: flex; align-items: center; justify-content: space-between;">
          <h3 class="modal-title" style="margin: 0; font-size: 1.25rem; font-weight: 600;">Exporter les transactions</h3>
          <button type="button" class="close close-export-modal" style="background: none; border: none; font-size: 1.5rem; font-weight: 700; color: #6B7280; cursor: pointer; padding: 0.25rem; line-height: 1;">&times;</button>
        </div>
        <div class="modal-body" style="padding: 1.5rem; overflow-y: auto; flex: 1;">
          <div class="mb-4">
            <h4 class="text-gray-700 dark:text-gray-300" style="font-weight: 600; margin-bottom: 0.5rem;">Résumé de l'export</h4>
            <div id="export-summary" class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4 dark:bg-blue-900/30">
              <p class="text-sm text-blue-700 dark:text-blue-300" id="export-summary-text">
                <strong>Filtres appliqués :</strong> Chargement...
              </p>
            </div>
          </div>
          
          <div class="mb-4">
            <h4 class="text-gray-700 dark:text-gray-300" style="font-weight: 600; margin-bottom: 0.5rem;">Options d'export</h4>
            <div class="space-y-3">
              <div>
                <label style="display: flex; align-items: center; cursor: pointer;">
                  <input type="radio" name="export-format" value="csv" checked style="margin-right: 0.5rem;">
                  <span style="font-weight: 500;">CSV (Excel)</span>
                  <span style="margin-left: 0.5rem; color: #6B7280; font-size: 0.875rem;">- Recommandé pour Excel</span>
                </label>
              </div>
              
              <div>
                <label style="display: flex; align-items: center; cursor: pointer;">
                  <input type="radio" name="export-format" value="xlsx" style="margin-right: 0.5rem;">
                  <span style="font-weight: 500;">Excel (.xlsx)</span>
                  <span style="margin-left: 0.5rem; color: #16A34A; font-size: 0.875rem;">- Avec mise en forme</span>
                </label>
              </div>
              
              <div>
                <label style="display: flex; align-items: center; cursor: pointer;">
                  <input type="radio" name="export-format" value="pdf" style="margin-right: 0.5rem;">
                  <span style="font-weight: 500;">PDF</span>
                  <span style="margin-left: 0.5rem; color: #DC2626; font-size: 0.875rem;">- Format imprimable</span>
                </label>
              </div>
            </div>
          </div>
          
          <div class="mb-4">
            <h4 class="text-gray-700 dark:text-gray-300" style="font-weight: 600; margin-bottom: 0.5rem;">Colonnes à inclure</h4>
            <div class="grid grid-cols-2 gap-2" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.5rem;">
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="date" checked style="margin-right: 0.5rem;">
                <span>Date</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="description" checked style="margin-right: 0.5rem;">
                <span>Description</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="amount" checked style="margin-right: 0.5rem;">
                <span>Montant</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="type" checked style="margin-right: 0.5rem;">
                <span>Type</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="account" checked style="margin-right: 0.5rem;">
                <span>Compte</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="category" checked style="margin-right: 0.5rem;">
                <span>Catégorie</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="notes" style="margin-right: 0.5rem;">
                <span>Notes</span>
              </label>
              <label style="display: flex; align-items: center; cursor: pointer;">
                <input type="checkbox" name="export-columns" value="fees" style="margin-right: 0.5rem;">
                <span>Frais</span>
              </label>
            </div>
          </div>
          
          <div id="export-progress" class="mt-4" style="display: none;">
            <div class="bg-gray-200 rounded-full h-2 dark:bg-gray-600" style="background-color: #E5E7EB; border-radius: 9999px; height: 0.5rem;">
              <div id="export-progress-bar" class="bg-blue-600 h-2 rounded-full" style="background-color: #2563EB; height: 0.5rem; border-radius: 9999px; width: 0%; transition: width 0.3s ease;"></div>
            </div>
            <p id="export-status" class="text-sm text-gray-600 mt-2 dark:text-gray-400" style="color: #4B5563; font-size: 0.875rem; margin-top: 0.5rem;">Préparation de l'export...</p>
          </div>
        </div>
        <div class="modal-footer" style="padding: 1rem 1.5rem; border-top: 1px solid #E5E7EB; display: flex; justify-content: flex-end; gap: 0.5rem;">
          <button type="button" class="btn btn-secondary close-export-modal" style="border-width: 1px; border-style: solid; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer;">Annuler</button>
          <button type="button" class="btn btn-primary" id="export-download-btn" style="background-color: #3b82f6; color: white; border: 1px solid #3b82f6; padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer;">
            <i class="fas fa-download" style="margin-right: 0.5rem;"></i>Télécharger
          </button>
        </div>
      </div>
    </div>
  `;
  
  // Ajouter la modal au DOM
  document.body.insertAdjacentHTML('beforeend', modalHTML);
  
  // Ajouter les événements
  const exportModal = document.getElementById('export-modal');
  const closeButtons = exportModal.querySelectorAll('.close-export-modal');
  const downloadBtn = document.getElementById('export-download-btn');
  
  // Fermeture de la modal
  closeButtons.forEach(btn => {
    btn.addEventListener('click', closeExportModal);
  });
  
  // Clic en dehors de la modal
  exportModal.addEventListener('click', function(e) {
    if (e.target === exportModal) {
      closeExportModal();
    }
  });
  
  // Bouton de téléchargement
  downloadBtn.addEventListener('click', performExport);
}

/**
 * Ferme la modal d'export
 */
function closeExportModal() {
  const exportModal = document.getElementById('export-modal');
  if (exportModal) {
    exportModal.style.display = 'none';
    exportModal.classList.remove('show');
    
    // Masquer la progression
    const progress = document.getElementById('export-progress');
    if (progress) progress.style.display = 'none';
  }
}

/**
 * Met à jour le résumé des filtres dans la modal d'export
 */
function updateExportSummary() {
  const summaryText = document.getElementById('export-summary-text');
  if (!summaryText) return;
  
  const filtersForm = document.getElementById('filters-form');
  if (!filtersForm) {
    summaryText.innerHTML = '<strong>Toutes les transactions</strong> seront exportées.';
    return;
  }
  
  const formData = new FormData(filtersForm);
  const filters = [];
  
  for (let [key, value] of formData.entries()) {
    if (value && value.trim() !== '') {
      let filterName;
      switch(key) {
        case 'account': filterName = 'Compte'; break;
        case 'category': filterName = 'Catégorie'; break;
        case 'type': filterName = 'Type'; break;
        case 'date_from': filterName = 'À partir du'; break;
        case 'date_to': filterName = 'Jusqu\'au'; break;
        case 'search': filterName = 'Libellé contient'; break;
        default: filterName = key;
      }
      
      let displayValue = value;
      if (key === 'account') {
        const accountSelect = document.getElementById('filter-account');
        const selectedOption = accountSelect.querySelector(`option[value="${value}"]`);
        displayValue = selectedOption ? selectedOption.textContent : value;
      } else if (key === 'category') {
        const categorySelect = document.getElementById('filter-category');
        const selectedOption = categorySelect.querySelector(`option[value="${value}"]`);
        displayValue = selectedOption ? selectedOption.textContent : value;
      } else if (key === 'type') {
        const typeNames = { 'income': 'Revenus', 'expense': 'Dépenses', 'transfer': 'Virements internes' };
        displayValue = typeNames[value] || value;
      }
      
      filters.push(`${escapeHtml(filterName)}: ${escapeHtml(displayValue)}`);
    }
  }
  
  if (filters.length > 0) {
    summaryText.innerHTML = `<strong>Filtres appliqués :</strong><br>${filters.join('<br>')}`;
  } else {
    summaryText.innerHTML = '<strong>Toutes les transactions</strong> seront exportées.';
  }
}

/**
 * Lance l'export avec les options sélectionnées
 */
async function performExport() {
  
  const progressDiv = document.getElementById('export-progress');
  const progressBar = document.getElementById('export-progress-bar');
  const statusText = document.getElementById('export-status');
  const downloadBtn = document.getElementById('export-download-btn');
  
  try {
    // Afficher la barre de progression
    progressDiv.style.display = 'block';
    downloadBtn.disabled = true;
    downloadBtn.textContent = 'Export en cours...';
    
    // Simulation de progression
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress += 15;
      progressBar.style.width = progress + '%';
      if (progress >= 90) {
        clearInterval(progressInterval);
      }
    }, 200);
    
    statusText.textContent = 'Récupération des transactions...';
    
    // Récupérer le format sélectionné
    const selectedFormat = document.querySelector('input[name="export-format"]:checked');
    const exportFormat = selectedFormat ? selectedFormat.value : 'csv';
    
    // Construire l'URL d'export avec les filtres
    const filtersForm = document.getElementById('filters-form');
    const params = new URLSearchParams();
    
    // Ajouter le format d'export
    params.append('format', exportFormat);
    
    if (filtersForm) {
      const formData = new FormData(filtersForm);
      for (let [key, value] of formData.entries()) {
        if (value && value.trim() !== '') {
          params.append(key, value);
        }
      }
    }
    
    const exportUrl = `/api/v1/transactions/export?${params.toString()}`;
    
    statusText.textContent = 'Génération du fichier...';
    
    // Télécharger le fichier
    const link = document.createElement('a');
    link.href = exportUrl;
    
    // Définir l'extension selon le format
    let fileExtension = 'csv';
    if (exportFormat === 'xlsx') {
      fileExtension = 'xlsx';
    } else if (exportFormat === 'pdf') {
      fileExtension = 'pdf';
    }
    
    link.download = `transactions_export_${new Date().toISOString().slice(0, 10)}.${fileExtension}`;
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Terminer la progression
    clearInterval(progressInterval);
    progressBar.style.width = '100%';
    statusText.textContent = 'Export terminé !';
    
    // Message de succès
    setTimeout(() => {
      showAlert('Export réussi ! Le fichier a été téléchargé.', 'success');
      closeExportModal();
    }, 1000);
    
  } catch (error) {
    console.error('❌ Erreur lors de l\'export:', error);
    statusText.textContent = 'Erreur lors de l\'export';
    showAlert('Erreur lors de l\'export: ' + error.message, 'error');
  } finally {
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = '<i class="fas fa-download" style="margin-right: 0.5rem;"></i>Télécharger';
  }
}

/**
 * Affiche la modal d'import
 */

/**
 * Crée la modal d'import dynamiquement
 */

/**
 * Ferme la modal d'import
 */

/**
 * Gère l'import des transactions
 */
