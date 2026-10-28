// Tableau global pour stocker les catégories
let categories = [];

// Charger les catégories depuis l'API
async function loadCategories() {
  try {
    const response = await fetch('/api/v1/categories');
    
    
    if (!response.ok) {
      const errorText = await response.text();
      const errorData = JSON.parse(errorText || '{}');
      throw new Error(errorData.message || `HTTP ${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    
    // Mettre à jour le tableau global des catégories
    // L'API retourne {status: 'success', categories: [...]}
    if (data && data.categories && Array.isArray(data.categories)) {
      categories = data.categories;
    } else if (Array.isArray(data)) {
      categories = data;
    } else {
      categories = [];
      console.warn('Format de données inattendu:', data);
    }
    
    // Sauvegarder dans le stockage local pour une utilisation hors ligne
    saveCategoriesToStorage(categories);
    
    // Mettre à jour l'affichage
    displayCategories(categories);
    
    return categories;
  } catch (error) {
    console.error('Erreur lors du chargement des catégories:', error);
    
    // En cas d'erreur, essayer de charger depuis le stockage local
    try {
      const storedCategories = localStorage.getItem('categories');
      if (storedCategories) {
        categories = JSON.parse(storedCategories);
        displayCategories(categories);
        showAlert('Mode hors ligne: utilisation des données en cache', 'warning');
        return categories;
      }
    } catch (cacheError) {
      console.error('Erreur lors du chargement du cache:', cacheError);
    }
    
    showAlert(error.message || 'Erreur lors du chargement des catégories', 'error');
    return [];
  }
}

// Script spécifique à la page des catégories
document.addEventListener('DOMContentLoaded', function() {
  
  // Vérifier que les éléments nécessaires sont présents
  const addButton = document.getElementById('add-category-btn');
  const categoriesTable = document.getElementById('categories-table');
  const modal = document.getElementById('category-modal');
  
  
  // Initialisation des gestionnaires d'événements
  if (addButton) {
    addButton.addEventListener('click', function(e) {
      e.preventDefault();
      openCategoryModal();
    });
  } else {
    console.error('Bouton d\'ajout de catégorie non trouvé');
  }
  
  // Chargement initial des catégories
  loadCategories();
  
  // Autres initialisations
  initializeEventListeners();
});

/**
 * Initialise les gestionnaires d'événements
 */
function initializeEventListeners() {
  // Gestionnaire pour le bouton d'ajout de catégorie
  const addCategoryBtn = document.getElementById('add-category-btn');
  
  if (addCategoryBtn) {
    addCategoryBtn.addEventListener('click', function(e) {
      e.preventDefault();
      openCategoryModal();
    });
  } else {
    console.error('Le bouton d\'ajout de catégorie n\'a pas été trouvé dans le DOM');
  }
  
  // Gestionnaire pour le formulaire d'ajout/modification de catégorie
  const categoryForm = document.getElementById('category-form');
  if (categoryForm) {
    categoryForm.addEventListener('submit', function(e) {
      e.preventDefault();
      saveCategory();
    });
  }
  
  // Gestionnaire pour la fermeture de la modal
  const closeModalBtns = document.querySelectorAll('.close-modal');
  closeModalBtns.forEach(btn => {
    btn.addEventListener('click', closeCategoryModal);
  });
  
  // Fermer la modal en cliquant en dehors
  const modal = document.getElementById('category-modal');
  if (modal) {
    modal.addEventListener('click', function(e) {
      if (e.target === modal) {
        closeCategoryModal();
      }
    });
  }
  
  // Délégation d'événements pour les boutons d'édition et de suppression
  document.addEventListener('click', function(e) {
    // Édition de catégorie
    const editButton = e.target.closest('.edit-category');
    if (editButton) {
      e.preventDefault();
      const categoryId = editButton.dataset.id;
      editCategory(categoryId);
      return;
    }
    
    // Suppression de catégorie
    const deleteButton = e.target.closest('.delete-category');
    if (deleteButton) {
      e.preventDefault();
      e.stopPropagation(); // Empêcher la propagation de l'événement
      
      const categoryId = deleteButton.getAttribute('data-id');
      
      try {
        deleteCategory(categoryId);
      } catch (error) {
        console.error('Erreur lors de l\'appel à deleteCategory:', error);
      }
      
      return false;
    }
  });
}

// Fonction saveCategory supprimée - dupliquée avec celle plus bas

/**
 * Affiche les catégories dans le tableau
 * @param {Array} categories - Tableau des catégories à afficher
 */
function displayCategories(categories) {
  
  const table = document.querySelector('#categories-table');
  if (!table) {
    console.error('Tableau des catégories non trouvé');
    return;
  }
  
  let tbody = table.querySelector('tbody');
  if (!tbody) {
    tbody = document.createElement('tbody');
    tbody.className = 'bg-white divide-y divide-gray-200';
    table.appendChild(tbody);
  }
  
  // Vider complètement le tbody pour éviter les conflits avec le template Jinja2
  tbody.innerHTML = '';
  
  if (!categories || !Array.isArray(categories) || categories.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4">Aucune catégorie trouvée. Commencez par en ajouter une.</td></tr>';
    return;
  }
  
  
  // Créer un fragment de document pour optimiser les performances
  const fragment = document.createDocumentFragment();
  
  categories.forEach((category, index) => {
    
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-50';
    row.dataset.categoryId = category.id;
    
    // Déterminer le type et les classes CSS
    let typeClass, typeText;
    if (category.type === 'income') {
      typeClass = 'bg-green-100 text-green-800';
      typeText = 'Revenu';
    } else if (category.type === 'transfer' || (category.name && category.name.toLowerCase().includes('virement'))) {
      typeClass = 'bg-blue-100 text-blue-800';
      typeText = 'Virement interne';
    } else {
      typeClass = 'bg-red-100 text-red-800';
      typeText = 'Dépense';
    }
    
    const safeName = escapeHtml(category.name || 'Sans nom');
    const safeDesc = escapeHtml(category.description || '');
    const safeIcon = escapeHtml(category.icon || 'tag');
    const safeColor = escapeHtml(category.color || '#6B7280');
    const safeId = escapeHtml(category.id);
    const safeCount = parseInt(category.transaction_count, 10) || 0;

    row.innerHTML = `
      <td class="px-6 py-4 whitespace-nowrap">
        <div class="flex items-center">
          <div class="flex-shrink-0 h-10 w-10 rounded-full flex items-center justify-center"
               style="background-color: ${safeColor}40">
            <i class="fas fa-${safeIcon} text-lg" style="color: ${safeColor}"></i>
          </div>
          <div class="ml-4">
            <div class="text-sm font-medium text-gray-900">${safeName}</div>
            <div class="text-sm text-gray-500">${safeDesc}</div>
          </div>
        </div>
      </td>
      <td class="px-6 py-4 whitespace-nowrap">
        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${typeClass}">
          ${typeText}
        </span>
      </td>
      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        ${safeCount} transactions
      </td>
      <td class="px-6 py-4 whitespace-nowrap" style="text-align: right !important;">
        <div style="display: flex !important; gap: 0.75rem !important; justify-content: flex-end !important; align-items: center !important;">
          <button type="button" class="text-blue-600 hover:text-blue-900 edit-category" data-id="${safeId}" style="margin: 0 !important;">
            <i class="fas fa-edit"></i> Modifier
          </button>
          <button type="button" class="text-red-600 hover:text-red-900 delete-category" data-id="${safeId}" style="margin: 0 !important;">
            <i class="fas fa-trash"></i> Supprimer
          </button>
        </div>
      </td>
    `;
    
    fragment.appendChild(row);
  });
  
  // Vider le tbody et ajouter toutes les lignes en une seule opération
  tbody.innerHTML = '';
  tbody.appendChild(fragment);
  
}

/**
 * Ouvre la modal d'ajout/modification de catégorie
 * @param {Object} category - Catégorie à modifier (optionnel)
 */
function openCategoryModal(category = null) {
  const modal = document.getElementById('category-modal');
  const modalTitle = document.getElementById('modal-title');
  const categoryForm = document.getElementById('category-form');
  const categoryIdInput = document.getElementById('category-id');

  if (!modal || !modalTitle || !categoryForm || !categoryIdInput) {
    console.error('Un ou plusieurs éléments de la modal sont manquants');
    return;
  }
  
  // S'assurer que la modal est visible avant d'ajouter la classe show
  modal.style.display = 'flex';
  // Forcer le recalcul du style pour préparer la transition
  void modal.offsetWidth;
  
  // Réinitialiser le formulaire
  categoryForm.reset();
  
  if (category) {
    // Mode édition
    modalTitle.textContent = 'Modifier la catégorie';
    categoryForm.dataset.categoryId = category.id;
    document.getElementById('category-name').value = category.name || '';
    
    // Gérer le type de catégorie (dépense ou revenu)
    const categoryType = category.type || 'expense';
    document.getElementById('category-type').value = categoryType;
    
    // Gérer la couleur avec une valeur par défaut si non définie
    document.getElementById('category-color').value = category.color || '#4CAF50';
    document.getElementById('category-icon').value = category.icon || 'tag';
    
    // Mettre à jour l'aperçu de la couleur et de l'icône
    updateCategoryPreview();
  } else {
    // Mode ajout
    modalTitle.textContent = 'Ajouter une catégorie';
    delete categoryForm.dataset.categoryId;
    
    // Réinitialiser l'aperçu
    const preview = document.getElementById('category-preview');
    if (preview) {
      preview.innerHTML = '<i class="fas fa-tag"></i> Nouvelle catégorie';
      preview.style.backgroundColor = '#4CAF50';
    }
  }
  
  // Afficher la modal avec une transition fluide
  modal.classList.add('show');
  document.body.style.overflow = 'hidden';
  
  // Forcer le recalcul du style pour déclencher la transition
  void modal.offsetWidth;
}

/**
 * Ferme la modal de catégorie
 */
function closeCategoryModal() {
  const modal = document.getElementById('category-modal');
  if (modal) {
    // S'assurer que la modal est visible avant de déclencher l'animation
    modal.style.display = 'flex';
    
    // Retirer la classe show pour déclencher la transition de fermeture
    modal.classList.remove('show');
    
    // Attendre la fin de la transition avant de cacher la modal
    setTimeout(() => {
      modal.style.display = 'none';
      document.body.style.overflow = 'auto';
      
      // Réinitialiser le formulaire
      const form = document.getElementById('category-form');
      if (form) {
        form.reset();
      }
      
      // Réinitialiser l'aperçu
      const preview = document.getElementById('category-preview');
      if (preview) {
        preview.innerHTML = '<i class="fas fa-tag"></i> Nouvelle catégorie';
        preview.style.backgroundColor = '#4CAF50';
      }
    }, 300); // Correspond à la durée de la transition CSS (0.3s)
  }
}

/**
 * Met à jour l'aperçu de la catégorie
 */
function updateCategoryPreview() {
  const name = document.getElementById('category-name').value || 'Nouvelle catégorie';
  const color = document.getElementById('category-color').value;
  const icon = document.getElementById('category-icon').value || 'tag';
  
  const preview = document.getElementById('category-preview');
  if (preview) {
    preview.innerHTML = `<i class="fas fa-${escapeHtml(icon)}"></i> ${escapeHtml(name)}`;
    preview.style.backgroundColor = color;
  }
}

/**
 * Sauvegarde une catégorie (ajout ou modification)
 */
async function saveCategory() {
  const form = document.getElementById('category-form');
  if (!form) {
    console.error('Formulaire de catégorie non trouvé');
    return;
  }

  try {
    const formData = new FormData(form);
    const categoryId = form.dataset.categoryId || '';
    const isEditing = !!categoryId;
    
    const url = isEditing ? `/api/v1/categories/${categoryId}` : '/api/v1/categories';
    const method = isEditing ? 'PUT' : 'POST';
    
    // Récupérer les valeurs du formulaire
    const name = formData.get('name');
    const description = formData.get('description') || '';
    const color = formData.get('color') || '#6B7280';
    const icon = formData.get('icon') || 'tag';
    const categoryType = formData.get('type') || 'expense';

    const response = await fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
      },
      body: JSON.stringify({
        name,
        description,
        color,
        icon,
        type: categoryType
      })
    });


    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || 'Erreur lors de la sauvegarde de la catégorie');
    }

    // Recharger la liste des catégories
    await loadCategories();
    
    // Fermer la modal
    closeCategoryModal();
    
    // Afficher un message de succès
    showAlert(
      isEditing ? 'Catégorie mise à jour avec succès' : 'Catégorie créée avec succès',
      'success'
    );
    
  } catch (error) {
    console.error('Erreur lors de la sauvegarde de la catégorie:', error);
    showAlert(error.message || 'Erreur lors de la sauvegarde de la catégorie', 'error');
  }
}

/**
 * Édite une catégorie existante
 * @param {string} categoryId - ID de la catégorie à éditer
 */
async function editCategory(categoryId) {
  
  try {
    // Charger les détails de la catégorie depuis l'API
    const response = await fetch(`/api/v1/categories/${categoryId}`);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || 'Erreur lors du chargement de la catégorie');
    }
    
    const categoryToEdit = await response.json();
    
    if (categoryToEdit) {
      openCategoryModal(categoryToEdit);
    } else {
      throw new Error('Catégorie non trouvée');
    }
  } catch (error) {
    console.error(`Erreur lors du chargement de la catégorie ${categoryId}:`, error);
    showAlert(error.message || 'Impossible de charger la catégorie à modifier.', 'error');
  }
}

/**
 * Supprime une catégorie
 * @param {string} categoryId - ID de la catégorie à supprimer
 */

/**
 * Enregistre les catégories dans le stockage local
 * @param {Array} categories - Tableau des catégories à enregistrer
 */
function saveCategoriesToStorage(categories) {
  try {
    localStorage.setItem('categories', JSON.stringify(categories));
  } catch (error) {
    console.error('Erreur lors de la sauvegarde des catégories dans le stockage local:', error);
  }
}

/**
 * Affiche un message d'alerte
 * @param {string} message - Message à afficher
 * @param {string} type - Type d'alerte (success, error, etc.)
 */
function showAlert(message, type = 'success') {
  const alertContainer = document.getElementById('alert-container');
  if (!alertContainer) return;
  
  const alert = document.createElement('div');
  alert.className = `alert alert-${type} p-4 mb-4 rounded`;
  alert.role = 'alert';
  alert.innerHTML = `
    <div class="flex items-center">
      <span class="mr-2">${escapeHtml(message)}</span>
      <button type="button" class="close" data-dismiss="alert" aria-label="Fermer">
        <span aria-hidden="true">&times;</span>
      </button>
    </div>
  `;
  
  alertContainer.appendChild(alert);
  
  // Supprimer l'alerte après 5 secondes
  setTimeout(() => {
    alert.remove();
  }, 5000);
}

/**
 * Supprime une catégorie avec gestion intelligente d'une seule confirmation
 * @param {string} categoryId - ID de la catégorie à supprimer
 */
async function deleteCategory(categoryId) {
  
  try {
    // Première tentative pour détecter s'il y a des conflits
    const testResponse = await fetch(`/api/v1/categories/${categoryId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
      }
    });

    // Si suppression réussie directement (pas de conflit)
    if (testResponse.ok) {
      showAlert('Catégorie supprimée avec succès', 'success');
      loadCategories();
      return;
    }

    // Si conflit détecté (409), préparer une seule fenêtre intelligente
    if (testResponse.status === 409) {
      const errorData = await testResponse.json().catch(() => ({}));
      const transactionCount = errorData.transaction_count || 'plusieurs';
      
      const title = 'Confirmation de suppression';
      const message = `Cette catégorie est utilisée dans ${transactionCount} transaction(s).\n\n` +
                     `⚠️ La supprimer entraînera aussi la suppression de toutes les transactions associées.\n\n` +
                     `Voulez-vous continuer ?`;
      
      const confirmed = await showConfirmDialog(title, message, 'Supprimer définitivement', 'Annuler');
      
      if (confirmed) {
        // Suppression forcée
        const forceResponse = await fetch(`/api/v1/categories/${categoryId}?force=1`, {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
          }
        });

        if (forceResponse.ok) {
          showAlert('Catégorie et transactions associées supprimées', 'success');
          loadCategories();
        } else {
          const forceErrorData = await forceResponse.json().catch(() => ({}));
          throw new Error(forceErrorData.message || 'Erreur lors de la suppression forcée');
        }
      }
      return;
    }

    // Pour les catégories sans conflit, demander confirmation simple
    const confirmed = await showConfirmDialog(
      'Confirmer la suppression', 
      'Êtes-vous sûr de vouloir supprimer cette catégorie ?'
    );
    
    if (!confirmed) return;

    // Autres erreurs non prévues
    const errorData = await testResponse.json().catch(() => ({}));
    throw new Error(errorData.message || errorData.error || 'Erreur lors de la suppression');

  } catch (error) {
    console.error('Erreur lors de la suppression:', error);
    showAlert(error.message || 'Erreur lors de la suppression', 'error');
  }
}

// Initialisation des écouteurs d'événements pour la prévisualisation en temps réel
document.addEventListener('DOMContentLoaded', function() {
  // Mettre à jour l'aperçu lors de la modification des champs
  const previewInputs = ['category-name', 'category-color', 'category-icon'];
  previewInputs.forEach(inputId => {
    const input = document.getElementById(inputId);
    if (input) {
      input.addEventListener('input', updateCategoryPreview);
    }
  });
  
  // Initialiser les sélecteurs de couleur et d'icônes
  const colorInput = document.getElementById('category-color');
  if (colorInput) {
    colorInput.addEventListener('input', updateCategoryPreview);
  }
  
  const iconSelect = document.getElementById('category-icon');
  if (iconSelect) {
    iconSelect.addEventListener('change', updateCategoryPreview);
  }
});
