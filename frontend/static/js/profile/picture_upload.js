/**
 * Gestion du téléchargement et de la prévisualisation de la photo de profil
 */

document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('profile_picture');
    const previewContainer = document.getElementById('profile-picture-preview');
    const previewImage = document.getElementById('profile-image');
    const removeButton = document.getElementById('remove-picture');
    const uploadForm = document.getElementById('profile-picture-form');
    
    if (!fileInput || !previewContainer || !previewImage) return;
    
    // Afficher la prévisualisation lors de la sélection d'un fichier
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Vérification côté client de la taille et du type
        const validImageTypes = ['image/jpeg', 'image/png', 'image/gif'];
        const maxSize = 5 * 1024 * 1024; // 5MB
        
        if (!validImageTypes.includes(file.type)) {
            showError('Type de fichier non supporté. Veuillez choisir une image (JPEG, PNG ou GIF).');
            return;
        }
        
        if (file.size > maxSize) {
            showError('La taille du fichier ne doit pas dépasser 5MB.');
            return;
        }
        
        // Créer un aperçu de l'image
        const reader = new FileReader();
        reader.onload = function(e) {
            previewImage.src = e.target.result;
            previewContainer.classList.remove('d-none');
            
            // Ajuster la taille de l'image pour l'aperçu
            const img = new Image();
            img.onload = function() {
                if (this.width < 100 || this.height < 100) {
                    showError('Les dimensions minimales sont de 100x100 pixels.');
                    previewContainer.classList.add('d-none');
                    fileInput.value = '';
                } else {
                    // Redimensionner l'image pour l'aperçu si nécessaire
                    const maxDimension = 300;
                    let width = this.width;
                    let height = this.height;
                    
                    if (width > height) {
                        if (width > maxDimension) {
                            height *= maxDimension / width;
                            width = maxDimension;
                        }
                    } else {
                        if (height > maxDimension) {
                            width *= maxDimension / height;
                            height = maxDimension;
                        }
                    }
                    
                    previewImage.width = width;
                    previewImage.height = height;
                    
                    // Afficher les dimensions réelles
                    document.getElementById('image-dimensions').textContent = 
                        `${this.width} × ${this.height} pixels`;
                }
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    });
    
    // Gestion du bouton de suppression
    if (removeButton) {
        removeButton.addEventListener('click', function(e) {
            e.preventDefault();
            fileInput.value = '';
            previewImage.src = '';
            previewContainer.classList.add('d-none');
            
            // Envoyer une requête pour supprimer la photo de profil
            if (confirm('Voulez-vous vraiment supprimer votre photo de profil ?')) {
                fetch('/api/v1/profil/picture', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showSuccess('Photo de profil supprimée avec succès');
                    } else {
                        showError(data.message || 'Erreur lors de la suppression de la photo');
                    }
                })
                .catch(error => {
                    console.error('Erreur:', error);
                    showError('Une erreur est survenue lors de la suppression de la photo');
                });
            }
        });
    }
    
    // Gestion de la soumission du formulaire
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(uploadForm);
            
            // Afficher un indicateur de chargement
            const submitButton = uploadForm.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Envoi en cours...';
            
            fetch(uploadForm.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showSuccess('Photo de profil mise à jour avec succès');
                    // Mettre à jour l'image de profil dans la barre de navigation si elle existe
                    const navProfileImage = document.querySelector('.navbar .profile-image');
                    if (navProfileImage) {
                        // Ajouter un timestamp pour forcer le rechargement de l'image
                        const timestamp = new Date().getTime();
                        navProfileImage.src = `${data.image_url}?t=${timestamp}`;
                    }
                } else {
                    showError(data.message || 'Erreur lors de la mise à jour de la photo');
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                showError('Une erreur est survenue lors de l\'envoi du fichier');
            })
            .finally(() => {
                submitButton.disabled = false;
                submitButton.innerHTML = originalButtonText;
            });
        });
    }
    
    // Fonctions utilitaires
    function showError(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-danger alert-dismissible fade show';
        alertDiv.role = 'alert';
        alertDiv.textContent = message;
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.setAttribute('data-bs-dismiss', 'alert');
        closeBtn.setAttribute('aria-label', 'Fermer');
        alertDiv.appendChild(closeBtn);

        const container = document.querySelector('.container.mt-4') || document.body;
        container.insertBefore(alertDiv, container.firstChild);

        // Fermer automatiquement après 5 secondes
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }

    function showSuccess(message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = 'alert alert-success alert-dismissible fade show';
        alertDiv.role = 'alert';
        alertDiv.textContent = message;
        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'btn-close';
        closeBtn.setAttribute('data-bs-dismiss', 'alert');
        closeBtn.setAttribute('aria-label', 'Fermer');
        alertDiv.appendChild(closeBtn);
        
        const container = document.querySelector('.container.mt-4') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // Fermer automatiquement après 5 secondes
        setTimeout(() => {
            alertDiv.classList.remove('show');
            setTimeout(() => alertDiv.remove(), 150);
        }, 5000);
    }
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
