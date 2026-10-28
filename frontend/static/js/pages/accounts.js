/**
 * Script spécifique à la page de gestion des comptes
 * Gère les interactions de l'interface utilisateur pour la gestion des comptes bancaires
 */

// Message de débogage

// Initialisation de la page des comptes
document.addEventListener('DOMContentLoaded', function() {
  
  // Initialisation des composants
  initModals();
  initEventHandlers();
  initNewButtons();
  initImportExportModals();
  
  // Afficher le nombre de boutons trouvés
});

// Fonction pour gérer les modals
function initModals() {
  
  // Sélectionner tous les boutons d'ouverture de modale
  document.querySelectorAll('[data-modal-toggle]').forEach(button => {
    button.addEventListener('click', function() {
      const modalId = this.getAttribute('data-modal-toggle');
      const modal = document.getElementById(modalId);
      
      if (modal) {
        modal.classList.toggle('hidden');
        document.body.classList.toggle('overflow-hidden', !modal.classList.contains('hidden'));
        
        // Mettre le focus sur le premier champ de la modale
        if (!modal.classList.contains('hidden')) {
          const firstInput = modal.querySelector('input, select, textarea');
          if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
          }
        }
      }
    });
  });
  
  // Gérer la fermeture des modales
  document.querySelectorAll('[data-modal-hide]').forEach(button => {
    button.addEventListener('click', function() {
      const modalId = this.getAttribute('data-modal-hide');
      const modal = document.getElementById(modalId);
      
      if (modal) {
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        
        // Si c'est le modal d'ajout de compte, réinitialiser le formulaire
        if (modalId === 'add-account-modal') {
          resetAccountForm();
        }
      }
    });
  });
  
  // Fermer la modale en cliquant en dehors
  document.querySelectorAll('.modal-overlay').forEach(modal => {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        
        // Réinitialiser le formulaire si nécessaire
        const form = modal.querySelector('form');
        if (form) {
          form.reset();
        }
      }
    });
  });
}

// Fonction pour réinitialiser le formulaire d'ajout de compte
function resetAccountForm() {
  const form = document.getElementById('account-form');
  if (!form) return;
  
  
  // Réinitialiser tous les champs
  form.reset();
  
  // Définir des valeurs par défaut appropriées
  const nameField = form.querySelector('[name="name"]');
  const accountTypeField = form.querySelector('[name="account_type"]');
  const currencyField = form.querySelector('[name="currency"]');
  const initialBalanceField = form.querySelector('[name="initial_balance"]');
  const isActiveField = form.querySelector('[name="is_active"]');
  const bankNameField = form.querySelector('[name="bank_name"]');
  const accountNumberField = form.querySelector('[name="account_number"]');
  const ibanField = form.querySelector('[name="iban"]');
  const bicField = form.querySelector('[name="bic"]');
  
  // Définir des valeurs par défaut claires
  if (nameField) nameField.value = '';
  if (accountTypeField) accountTypeField.value = 'checking'; // Valeur par défaut
  if (currencyField) currencyField.value = 'EUR'; // Valeur par défaut
  if (initialBalanceField) initialBalanceField.value = '0.00';
  if (isActiveField) isActiveField.checked = true; // Actif par défaut
  if (bankNameField) bankNameField.value = '';
  if (accountNumberField) accountNumberField.value = '';
  if (ibanField) ibanField.value = '';
  if (bicField) bicField.value = '';
  
  // Supprimer les classes d'erreur et messages d'erreur
  form.querySelectorAll('.border-red-500').forEach(field => {
    field.classList.remove('border-red-500');
    field.setAttribute('aria-invalid', 'false');
  });
  
  form.querySelectorAll('.error-message').forEach(error => {
    error.style.display = 'none';
  });
  
  // Mettre à jour le symbole de devise
  const currencySymbol = form.querySelector('.currency-symbol');
  if (currencySymbol) {
    currencySymbol.textContent = '€';
  }
  
}

// Fonction pour formater le montant avec 2 décimales
function formatAmount(value) {
  if (!value) return '0.00';
  
  // Convertir en nombre si ce n'est pas déjà le cas
  const num = typeof value === 'string' ? parseFloat(value) : value;
  
  // Vérifier si c'est un nombre valide
  if (isNaN(num)) return '0.00';
  
  // Formater avec 2 décimales
  return num.toFixed(2);
}

// Fonction pour afficher une notification
function showNotification(message, type = 'success') {
  // Créer l'élément de notification
  const notification = document.createElement('div');
  notification.className = `fixed top-4 right-4 p-4 rounded-md shadow-lg ${
    type === 'success' ? 'bg-green-500' : 'bg-red-500'
  } text-white`;
  
  // Ajouter le message
  notification.textContent = message;
  
  // Ajouter au DOM
  document.body.appendChild(notification);
  
  // Supprimer après 5 secondes
  setTimeout(() => {
    notification.remove();
  }, 5000);
}

// Fonction pour confirmer la suppression
async function confirmDelete(accountId, accountName) {
  return new Promise((resolve) => {
    // Créer la modale de confirmation
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    
    // Contenu de la modale
    modal.innerHTML = `
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">Confirmer la suppression</h3>
        <p class="text-gray-600 dark:text-gray-300 mb-6">
          Êtes-vous sûr de vouloir supprimer le compte <strong>${escapeHtml(accountName)}</strong> ?
          Cette action est irréversible.
        </p>
        <div class="flex justify-end space-x-3">
          <button
            type="button"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-600"
            data-confirm="false"
          >
            Annuler
          </button>
          <button
            type="button"
            class="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            data-confirm="true"
          >
            Supprimer
          </button>
        </div>
      </div>
    `;
    
    // Gérer les clics sur les boutons
    modal.querySelectorAll('button').forEach(button => {
      button.addEventListener('click', () => {
        const confirmed = button.getAttribute('data-confirm') === 'true';
        modal.remove();
        resolve(confirmed);
      });
    });
    
    // Ajouter la modale au DOM
    document.body.appendChild(modal);
  });
}

// Fonction pour gérer la validation du formulaire
function validateForm(form) {
  let isValid = true;
  const requiredFields = form.querySelectorAll('[aria-required="true"]');
  
  requiredFields.forEach(field => {
    const errorId = `${field.id}-error`;
    const errorElement = document.getElementById(errorId);
    
    if (!field.value.trim()) {
      field.setAttribute('aria-invalid', 'true');
      if (errorElement) {
        errorElement.textContent = 'Ce champ est obligatoire';
        errorElement.style.display = 'block';
      }
      isValid = false;
    } else {
      field.setAttribute('aria-invalid', 'false');
      if (errorElement) {
        errorElement.style.display = 'none';
      }
    }
  });
  
  return isValid;
}

// Fonction pour initialiser les gestionnaires d'événements
function initEventHandlers() {
  
  // Gestionnaire pour l'ajout d'un compte
  const addAccountBtn = document.getElementById('add-account-btn');
  const addAccountModal = document.getElementById('add-account-modal');
  
  
  if (addAccountBtn && addAccountModal) {
    addAccountBtn.addEventListener('click', (e) => {
      e.preventDefault();
      
      // Réinitialiser le formulaire avant d'ouvrir le modal
      resetAccountForm();
      
      addAccountModal.classList.remove('hidden');
      document.body.classList.add('overflow-hidden');
      
      // Mettre le focus sur le premier champ
      const firstInput = addAccountModal.querySelector('input, select, textarea');
      if (firstInput) {
        setTimeout(() => firstInput.focus(), 100);
      }
    });
  } else {
    console.error('❌ Bouton ou modal non trouvé!');
    if (!addAccountBtn) console.error('  - Bouton #add-account-btn manquant');
    if (!addAccountModal) console.error('  - Modal #add-account-modal manquante');
  }
  
  // Gestionnaire pour la modification d'un compte
  document.querySelectorAll('.edit-account').forEach(button => {
    button.addEventListener('click', async function(e) {
      e.preventDefault();
      const accountId = this.getAttribute('data-account-id');
      
      if (!accountId) {
        showNotification('Erreur: ID de compte manquant', 'error');
        return;
      }
      
      try {
        // Récupérer les données complètes du compte via API
        const response = await fetch(`/api/v1/comptes/${accountId}`);
        
        if (!response.ok) {
          throw new Error('Erreur lors de la récupération des données du compte');
        }
        
        const result = await response.json();
        
        if (result.status !== 'success') {
          throw new Error(result.message || 'Erreur lors de la récupération des données');
        }

        // Remplir le formulaire avec toutes les données
        populateEditForm(accountId, result.account);
        
        // Afficher la modale
        const modal = document.getElementById('edit-account-modal');
        if (modal) {
          modal.classList.remove('hidden');
          document.body.classList.add('overflow-hidden');
          
          // Mettre le focus sur le premier champ
          const firstInput = modal.querySelector('input, select, textarea');
          if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
          }
        }
        
      } catch (error) {
        console.error('Erreur:', error);
        showNotification(error.message || 'Erreur lors du chargement des données du compte', 'error');
      }
    });
  });
  
  // Gestionnaire pour la suppression d'un compte
  document.querySelectorAll('.delete-account').forEach(button => {
    button.addEventListener('click', async function(e) {
      e.preventDefault();
      const accountId = this.getAttribute('data-account-id');
      
      if (!accountId) {
        showNotification('Erreur: ID de compte manquant', 'error');
        return;
      }
      
      // Récupérer le nom du compte pour la confirmation
      const accountRow = this.closest('tr');
      const accountName = accountRow?.querySelector('.account-name')?.textContent || 'ce compte';
      
      // Demander confirmation
      const confirmed = await confirmDelete(accountId, accountName);
      if (!confirmed) return;
      
      try {
        // Vérification du token CSRF
        const csrfToken = document.querySelector('[name=csrf_token]')?.value;
        if (!csrfToken) {
          throw new Error('Token CSRF manquant');
        }
        
        // Préparation des données
        const formData = new URLSearchParams({
          'confirm': 'true',
          'csrf_token': csrfToken
        });
        
        // Appel API de suppression
        const response = await fetch(`/api/v1/comptes/${accountId}`, {
          method: 'DELETE',
          headers: {
            'X-CSRFToken': csrfToken,
          },
        });
        
        if (response.ok) {
          const result = await response.json();
          showNotification(result.message, result.message_type || 'success');
          // Rechargement de la page après un délai pour voir la notification
          setTimeout(() => window.location.reload(), 1000);
        } else {
          const error = await response.json();
          throw new Error(error.message || 'Erreur lors de la suppression');
        }
        
      } catch (error) {
        console.error('Erreur lors de la suppression:', error);
        showNotification(error.message || 'Erreur lors de la suppression du compte', 'error');
      }
    });
  });
  
  // Gestionnaire pour la soumission du formulaire d'ajout
  const addAccountForm = document.getElementById('account-form');
  
  if (addAccountForm) {
    addAccountForm.addEventListener('submit', async function(e) {
      // Validation du formulaire
      if (!validateForm(this)) {
        e.preventDefault();
        // Mettre le focus sur le premier champ en erreur
        const firstError = this.querySelector('[aria-invalid="true"]');
        if (firstError) {
          firstError.focus();
        }
        return;
      }
      e.preventDefault();
      
      // Désactiver le bouton de soumission
      const submitButton = this.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      submitButton.innerHTML = 'Enregistrement...';
      
      try {
        // Récupérer les données du formulaire
        const formData = new FormData(this);
        
        // Assurer qu'on a le bon token CSRF
        const csrfToken = document.querySelector('#account_csrf_token')?.value || 
                         document.querySelector('[name=csrf_token]')?.value || 
                         document.querySelector('meta[name=csrf-token]')?.content;
        
        if (csrfToken) {
            formData.set('csrf_token', csrfToken);
        } else {
            showNotification('Erreur de sécurité : token CSRF introuvable. Rechargez la page.', 'error');
            return;
        }
        
        
        // Envoyer la requête
        const response = await fetch('/api/v1/comptes', {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken
          },
          body: formData
        });
        
        if (response.ok) {
          const result = await response.json();
          if (result.status === 'success') {
            // Afficher un message de succès
            showNotification(result.message || 'Compte créé avec succès', 'success');
            
            // Fermer le modal
            const modal = document.getElementById('add-account-modal');
            if (modal) {
              modal.classList.add('hidden');
              document.body.classList.remove('overflow-hidden');
            }
            
            // Réinitialiser le formulaire pour la prochaine création
            resetAccountForm();
            
            // Recharger la page après un délai pour voir la notification
            setTimeout(() => window.location.reload(), 1000);
          } else {
            throw new Error(result.message || 'Erreur lors de l\'ajout du compte');
          }
        } else {
          const error = await response.json();
          // Créer un objet d'erreur avec les détails de validation
          const errorObj = new Error(error.message || 'Erreur lors de l\'ajout du compte');
          errorObj.errors = error.errors || {};
          throw errorObj;
        }
      } catch (error) {
        console.error('Erreur:', error);
        
        // Si l'erreur contient des détails de validation, les afficher
        if (error.errors) {
          for (const [field, messages] of Object.entries(error.errors)) {
            const input = this.querySelector(`[name="${field}"]`);
            if (input && messages.length > 0) {
              const errorElement = document.getElementById(`${field}-error`);
              if (errorElement) {
                errorElement.textContent = messages[0];
                errorElement.style.display = 'block';
              }
              input.setAttribute('aria-invalid', 'true');
              input.classList.add('border-red-500');
            }
          }
          showNotification('Veuillez corriger les erreurs dans le formulaire', 'error');
        } else {
          showNotification(error.message || 'Erreur lors de l\'ajout du compte', 'error');
        }
      } finally {
        // Réactiver le bouton de soumission
        submitButton.disabled = false;
        submitButton.innerHTML = 'Ajouter le compte';
      }
    });
  }
  
  // Gestionnaire pour la soumission du formulaire de modification
  const editAccountForm = document.getElementById('edit-account-form');
  if (editAccountForm) {
    editAccountForm.addEventListener('submit', async function(e) {
      // Validation du formulaire
      if (!validateForm(this)) {
        e.preventDefault();
        // Mettre le focus sur le premier champ en erreur
        const firstError = this.querySelector('[aria-invalid="true"]');
        if (firstError) {
          firstError.focus();
        }
        return;
      }
      e.preventDefault();
      
      // Désactiver le bouton de soumission
      const submitButton = this.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      submitButton.innerHTML = 'Enregistrement...';
      
      try {
        // Récupérer l'ID du compte
        const accountId = this.elements['account_id'].value;
        
        if (!accountId) {
          throw new Error('ID de compte manquant');
        }
        
        // Récupérer les données du formulaire
        const formData = new FormData(this);
        
        // Assurer qu'on a le bon token CSRF
        const csrfToken = document.querySelector('#edit_account_csrf_token')?.value || 
                         document.querySelector('[name=csrf_token]')?.value;
        
        if (csrfToken) {
          formData.set('csrf_token', csrfToken);
        }
        
        // Envoyer la requête
        const response = await fetch(`/api/v1/comptes/${accountId}`, {
          method: 'PUT',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: formData
        });
        
        if (response.ok) {
          // Debug: afficher la réponse brute
          const responseText = await response.text();
          
          // Essayer de parser le JSON
          let result;
          try {
            result = JSON.parse(responseText);
          } catch (e) {
            console.error('Erreur parsing JSON:', e);
            console.error('Contenu reçu:', responseText);
            throw new Error('Réponse serveur invalide: ' + responseText.substring(0, 100));
          }
          
          if (result.status === 'success') {
            showNotification(result.message || 'Compte mis à jour avec succès', 'success');
            // Fermer la modale
            const modal = document.getElementById('edit-account-modal');
            if (modal) {
              modal.classList.add('hidden');
              document.body.classList.remove('overflow-hidden');
            }
            // Recharger la page après un délai pour voir la notification
            setTimeout(() => window.location.reload(), 1000);
          } else {
            throw new Error(result.message || 'Erreur lors de la mise à jour du compte');
          }
        } else {
          const error = await response.json();
          throw new Error(error.message || 'Erreur lors de la mise à jour du compte');
        }
      } catch (error) {
        console.error('Erreur:', error);
        showNotification(error.message || 'Erreur lors de la mise à jour du compte', 'error');
      } finally {
        // Réactiver le bouton de soumission
        submitButton.disabled = false;
        submitButton.innerHTML = '<span class="flex items-center"><i class="fas fa-save mr-2"></i>Mettre à jour</span>';
      }
    });
  }
  
  // Mise en forme automatique de l'IBAN et validation
  const ibanInput = document.getElementById('iban');
  if (ibanInput) {
    ibanInput.addEventListener('input', function(e) {
      // Mettre à jour l'état de validation ARIA
      this.setAttribute('aria-invalid', 'false');
      const errorElement = document.getElementById('iban-error');
      if (errorElement) {
        errorElement.style.display = 'none';
      }
      // Supprimer tous les espaces existants et mettre en majuscules
      let value = this.value.replace(/\s+/g, '').toUpperCase();
      
      // Ajouter un espace tous les 4 caractères
      value = value.replace(/(.{4})/g, '$1 ').trim();
      
      // Mettre à jour la valeur du champ
      this.value = value;
    });
  }
  
  // Mise à jour du symbole de devise
  const currencySelect = document.getElementById('currency');
  const balanceInput = document.getElementById('initial_balance');
  
  // Gestionnaire d'événement pour le champ de solde
  if (balanceInput) {
    balanceInput.addEventListener('input', function() {
      // Mettre à jour l'état de validation ARIA
      this.setAttribute('aria-invalid', 'false');
      const errorElement = document.getElementById('initial_balance-error');
      if (errorElement) {
        errorElement.style.display = 'none';
      }
    });
  }
  
  if (currencySelect && balanceInput) {
    // Créer un conteneur pour le symbole de devise s'il n'existe pas
    let currencySymbol = balanceInput.previousElementSibling;
    if (!currencySymbol || !currencySymbol.classList.contains('currency-symbol')) {
      currencySymbol = document.createElement('span');
      currencySymbol.className = 'absolute left-2 top-1/2 transform -translate-y-1/2 text-gray-500 dark:text-gray-400 currency-symbol pointer-events-none';
      balanceInput.parentNode.insertBefore(currencySymbol, balanceInput);
    }
    
    // Fonction pour mettre à jour le symbole
    function updateCurrencySymbol() {
      const currency = currencySelect.value;
      let symbol = '€'; // Par défaut, utiliser l'euro
      
      switch (currency) {
        case 'USD':
          symbol = '$';
          break;
        case 'GBP':
          symbol = '£';
          break;
        case 'CHF':
          symbol = 'CHF';
          break;
        // Ajouter d'autres devues si nécessaire
      }
      
      currencySymbol.textContent = symbol;
    }
    
    // Mettre à jour le symbole au chargement
    updateCurrencySymbol();
    
    // Mettre à jour le symbole quand la devise change
    currencySelect.addEventListener('change', updateCurrencySymbol);
  }
  
  // Gestion du formulaire de modification - mise à jour du symbole de devise
  const editCurrencySelect = document.getElementById('edit_currency');
  if (editCurrencySelect) {
    editCurrencySelect.addEventListener('change', updateEditCurrencySymbol);
  }
  
  // Gestion de l'IBAN dans le formulaire de modification
  const editIbanInput = document.getElementById('edit_iban');
  if (editIbanInput) {
    editIbanInput.addEventListener('input', function(e) {
      // Supprimer tous les espaces existants et mettre en majuscules
      let value = this.value.replace(/\s+/g, '').toUpperCase();
      
      // Ajouter un espace tous les 4 caractères
      value = value.replace(/(.{4})/g, '$1 ').trim();
      
      // Mettre à jour la valeur du champ
      this.value = value;
    });
  }
}

// Fonction pour remplir le formulaire de modification
function populateEditForm(accountId, accountData) {
  const form = document.getElementById('edit-account-form');
  if (!form) return;
  
  // Remplir les champs avec toutes les données de l'API
  form.elements['account_id'].value = accountId;
  form.elements['name'].value = accountData.name || '';
  form.elements['account_type'].value = accountData.account_type || 'checking';
  form.elements['initial_balance'].value = accountData.balance || '0.00';
  form.elements['currency'].value = accountData.currency || 'EUR';
  form.elements['bank_name'].value = accountData.bank_name || '';
  form.elements['account_number'].value = accountData.account_number || '';
  form.elements['iban'].value = accountData.iban || '';
  form.elements['bic'].value = accountData.bic_swift || '';
  form.elements['is_active'].checked = accountData.is_active !== false;
  
  // Mettre à jour le symbole de devise
  updateEditCurrencySymbol();
}

// Fonction pour initialiser les nouveaux boutons
function initNewButtons() {
  
  // Bouton Import géré par initImportExportModals()
  
  // Bouton Export géré par initImportExportModals()
  
  // Bouton "Créer votre premier compte" (alternatif)
  const addFirstAccountBtn = document.getElementById('add-first-account');
  if (addFirstAccountBtn) {
    addFirstAccountBtn.addEventListener('click', function(e) {
      e.preventDefault();
      
      // Réinitialiser le formulaire avant d'ouvrir le modal
      resetAccountForm();
      
      // Ouvrir la modal d'ajout
      const modal = document.getElementById('add-account-modal');
      if (modal) {
        modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        
        // Focus sur le premier champ
        const firstInput = modal.querySelector('input[name="name"]');
        if (firstInput) {
          setTimeout(() => firstInput.focus(), 100);
        }
      }
    });
  }
}

// Fonction pour mettre à jour le symbole de devise dans le formulaire de modification
function updateEditCurrencySymbol() {
  const currencySelect = document.getElementById('edit_currency');
  const currencySymbol = document.getElementById('edit-currency-symbol');
  
  if (!currencySelect || !currencySymbol) return;
  
  const currency = currencySelect.value;
  let symbol = '€'; // Par défaut
  
  switch (currency) {
    case 'USD':
      symbol = '$';
      break;
    case 'GBP':
      symbol = '£';
      break;
    case 'CHF':
      symbol = 'CHF';
      break;
    default:
      symbol = '€';
  }
  
  currencySymbol.textContent = symbol;
}

// Fonction pour afficher les messages d'erreur
function showError(input, message) {
  const wrapper = input.closest('div');
  if (!wrapper) return;
  
  // Ajouter la classe d'erreur au champ
  input.classList.add('border-red-500');
  
  // Créer le message d'erreur s'il n'existe pas déjà
  let errorElement = wrapper.querySelector('.error-message');
  if (!errorElement) {
    errorElement = document.createElement('p');
    errorElement.className = 'mt-1 text-xs text-red-600 dark:text-red-500 error-message';
    wrapper.appendChild(errorElement);
  }
  
  // Mettre à jour le message d'erreur
  errorElement.textContent = message;
}

// ===== GESTION IMPORT/EXPORT =====

// Initialiser les modals d'import/export
function initImportExportModals() {
  
  // Boutons d'ouverture des modals
  const importBtn = document.getElementById('import-btn');
  const exportBtn = document.getElementById('export-btn');
  
  if (importBtn) {
    importBtn.addEventListener('click', openImportModal);
  }
  
  if (exportBtn) {
    exportBtn.addEventListener('click', openExportModal);
  }
  
  // Initialiser les event listeners pour les modals
  initImportModal();
  initExportModal();
}

// Modal d'import
function initImportModal() {
  const modal = document.getElementById('import-modal');
  const closeBtn = document.getElementById('close-import-modal');
  const cancelBtn = document.getElementById('cancel-import');
  const form = document.getElementById('import-form');
  
  if (closeBtn) {
    closeBtn.addEventListener('click', closeImportModal);
  }
  
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeImportModal);
  }
  
  // Fermeture par clic extérieur
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeImportModal();
      }
    });
  }
  
  // Soumission du formulaire d'import
  if (form) {
    form.addEventListener('submit', handleImportSubmit);
  }
  
  // Affichage du nom de fichier sélectionné
  const fileInput = document.getElementById('import-file');
  if (fileInput) {
    fileInput.addEventListener('change', function(e) {
      const fileInfo = document.getElementById('selected-file-info');
      const fileName = document.getElementById('selected-file-name');
      
      if (e.target.files.length > 0) {
        const file = e.target.files[0];
        fileName.textContent = file.name;
        fileInfo.classList.remove('hidden');
      } else {
        fileInfo.classList.add('hidden');
      }
    });
  }
}

// Modal d'export
function initExportModal() {
  const modal = document.getElementById('export-modal');
  const closeBtn = document.getElementById('close-export-modal');
  const cancelBtn = document.getElementById('cancel-export');
  const form = document.getElementById('export-form');
  
  if (closeBtn) {
    closeBtn.addEventListener('click', closeExportModal);
  }
  
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeExportModal);
  }
  
  // Fermeture par clic extérieur
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeExportModal();
      }
    });
  }
  
  // Soumission du formulaire d'export
  if (form) {
    form.addEventListener('submit', handleExportSubmit);
  }
}

// Ouvrir modal d'import
async function openImportModal() {
  
  const modal = document.getElementById('import-modal');
  if (modal) {
    // Charger la liste des comptes
    await loadAccountsForImportExport('import-account');
    
    modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }
}

// Ouvrir modal d'export
async function openExportModal() {
  
  const modal = document.getElementById('export-modal');
  if (modal) {
    // Charger la liste des comptes
    await loadAccountsForImportExport('export-account');
    
    // Définir les dates par défaut
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    
    document.getElementById('export-date-from').value = firstDayOfMonth.toISOString().split('T')[0];
    document.getElementById('export-date-to').value = today.toISOString().split('T')[0];
    
    modal.classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
  }
}

// Fermer modal d'import
function closeImportModal() {
  const modal = document.getElementById('import-modal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    
    // Réinitialiser le formulaire
    const form = document.getElementById('import-form');
    if (form) {
      form.reset();
    }
  }
}

// Fermer modal d'export
function closeExportModal() {
  const modal = document.getElementById('export-modal');
  if (modal) {
    modal.classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    
    // Réinitialiser le formulaire
    const form = document.getElementById('export-form');
    if (form) {
      form.reset();
    }
  }
}

// Charger les comptes pour les selects
async function loadAccountsForImportExport(selectId) {
  try {
    const response = await fetch('/api/v1/comptes', {
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.status === 'success' && data.accounts) {
        populateAccountSelect(selectId, data.accounts);
      }
    }
  } catch (error) {
    console.error('❌ Erreur chargement comptes:', error);
  }
}

// Remplir le select des comptes
function populateAccountSelect(selectId, accounts) {
  const select = document.getElementById(selectId);
  if (!select) return;
  
  // Garder l'option par défaut
  const defaultOption = select.querySelector('option[value=""]');
  select.innerHTML = '';
  if (defaultOption) {
    select.appendChild(defaultOption);
  }
  
  // Ajouter les comptes
  accounts.forEach(account => {
    const option = document.createElement('option');
    option.value = account.id;
    option.textContent = `${account.name} (${formatCurrency(account.balance)})`;
    select.appendChild(option);
  });
}

// Gérer la soumission d'import
async function handleImportSubmit(e) {
  e.preventDefault();
  
  
  const form = e.target;
  const formData = new FormData(form);
  const submitBtn = form.querySelector('button[type="submit"]');
  
  // Validation
  const accountId = formData.get('account_id');
  const file = formData.get('file');
  
  if (!accountId) {
    showNotification('Veuillez sélectionner un compte', 'error');
    return;
  }
  
  if (!file || file.size === 0) {
    showNotification('Veuillez sélectionner un fichier', 'error');
    return;
  }
  
  // Désactiver le bouton
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Import en cours...';
  
  try {
    const response = await fetch('/api/v1/comptes/import', {
      method: 'POST',
      body: formData,
      credentials: 'same-origin'
    });
    
    const result = await response.json();
    
    if (response.ok && result.status === 'success') {
      showNotification(result.message || 'Import réussi', 'success');
      closeImportModal();
      
      // Recharger la page pour voir les nouvelles données
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } else {
      // Import refusé (tout ou rien) : montrer les premières lignes en erreur
      let message = result.message || 'Erreur lors de l\'import';
      if (Array.isArray(result.errors) && result.errors.length) {
        const extrait = result.errors.slice(0, 5).join(' — ');
        const reste = result.errors.length > 5 ? ` (et ${result.errors.length - 5} autre(s))` : '';
        message += ` ${extrait}${reste}`;
      }
      showNotification(message, 'error');
    }
  } catch (error) {
    console.error('❌ Erreur import:', error);
    showNotification('Erreur de connexion lors de l\'import', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-upload mr-2"></i>Importer';
  }
}

// Gérer la soumission d'export
async function handleExportSubmit(e) {
  e.preventDefault();
  
  
  const form = e.target;
  const formData = new FormData(form);
  const submitBtn = form.querySelector('button[type="submit"]');
  
  // Construire les paramètres d'export
  const params = new URLSearchParams();
  
  // Ajouter tous les paramètres du formulaire
  for (let [key, value] of formData.entries()) {
    if (value && key !== 'csrf_token') {
      params.append(key, value);
    }
  }
  
  // Désactiver le bouton
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Export en cours...';
  
  try {
    const response = await fetch(`/api/v1/comptes/export?${params.toString()}`, {
      method: 'GET',
      credentials: 'same-origin'
    });
    
    if (response.ok) {
      // Télécharger le fichier
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      
      // Déterminer le nom du fichier
      const format = formData.get('format') || 'csv';
      const accountId = formData.get('account_id');
      const accountName = accountId ? 
        document.querySelector(`#export-account option[value="${accountId}"]`)?.textContent || 'compte' :
        'tous-comptes';
      
      a.download = `export-${accountName}-${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      showNotification('Export téléchargé avec succès', 'success');
      closeExportModal();
    } else {
      const result = await response.json();
      showNotification(result.message || 'Erreur lors de l\'export', 'error');
    }
  } catch (error) {
    console.error('❌ Erreur export:', error);
    showNotification('Erreur de connexion lors de l\'export', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-download mr-2"></i>Exporter';
  }
}

// Formater la devise
function formatCurrency(amount) {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'EUR'
  }).format(amount || 0);
}

