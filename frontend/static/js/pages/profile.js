/**
 * Gestion de la page de profil utilisateur
 * Gère la validation des formulaires, les interactions utilisateur et les appels API
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Le mode sombre est géré via le menu principal, pas besoin de gestion ici
    
    // Éléments du DOM
    const profileForm = document.getElementById('profile-form');
    const passwordForm = document.getElementById('password-form');
    const deleteAccountBtn = document.getElementById('delete-account-btn');
    const exportDataBtn = document.getElementById('export-data-btn');

    // Initialisation des composants
    initFormValidation();
    // initAvatarUpload(); // Désactivé car géré par l'upload AJAX plus bas
    initPasswordVisibilityToggles();

    if (deleteAccountBtn) {
        initDeleteAccountConfirmation();
    }

    if (exportDataBtn) {
        initExportData();
    }
    
    // Gestion de la modal des notifications email
    initEmailNotificationsModal();
    
    // Initialisation de la 2FA
    initTwoFactorAuth();
    
    // Gestion des notifications simples
    const notificationToggles = ['budget-alerts', 'monthly-reports'];
    notificationToggles.forEach(id => {
        const toggle = document.getElementById(id);
        if (toggle) {
            toggle.addEventListener('change', async function() {
                const isChecked = this.checked;
                
                try {
                    // Mapper les IDs vers les types de notification
                    const notificationTypeMap = {
                        'email-notifications': 'general_email',
                        'budget-alerts': 'budget_alert',
                        'monthly-reports': 'monthly_report'
                    };
                    
                    const notificationType = notificationTypeMap[id];
                    if (!notificationType) return;
                    
                    const response = await fetch('/api/v1/profil/notifications', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                        },
                        body: JSON.stringify({
                            notification_type: notificationType,
                            email: isChecked
                        })
                    });
                    
                    const result = await response.json();
                    if (result.success || result.status === 'success') {
                        showAlert('success', `Préférence de notification mise à jour`);
                    } else {
                        showAlert('error', result.message || 'Erreur lors de la sauvegarde');
                        // Remettre le toggle dans son état précédent
                        this.checked = !isChecked;
                    }
                } catch (error) {
                    console.error('Erreur lors de la sauvegarde:', error);
                    showAlert('error', 'Erreur lors de la sauvegarde des préférences');
                    // Remettre le toggle dans son état précédent
                    this.checked = !isChecked;
                }
            });
        }
    });
    
    // Gestion des sélecteurs de préférences
    const preferenceSelectors = ['language', 'currency', 'date_format'];
    preferenceSelectors.forEach(id => {
        const selector = document.getElementById(id);
        if (selector) {
            selector.addEventListener('change', function() {
                // Ici, vous pourriez ajouter un appel API pour sauvegarder la préférence
            });
        }
    });

    /**
     * Initialise la validation des formulaires
     */
    function initFormValidation() {
        // Validation du formulaire de profil
        if (profileForm) {
            profileForm.addEventListener('submit', function(e) {
                if (!validateProfileForm()) {
                    e.preventDefault();
                } else {
                    showLoading(profileForm.querySelector('button[type="submit"]'));
                }
            });
        }

        // Validation du formulaire de mot de passe
        if (passwordForm) {
            passwordForm.addEventListener('submit', function(e) {
                if (!validatePasswordForm()) {
                    e.preventDefault();
                } else {
                    showLoading(passwordForm.querySelector('button[type="submit"]'));
                }
            });
        }
    }

    /**
     * Valide le formulaire de profil
     */
    function validateProfileForm() {
        let isValid = true;
        const email = profileForm.querySelector('input[type="email"]');
        const phone = profileForm.querySelector('input[type="tel"]');
        
        // Validation de l'email
        if (email && !isValidEmail(email.value)) {
            showError(email, 'Veuillez entrer une adresse email valide');
            isValid = false;
        }
        
        // Validation du téléphone (optionnel)
        if (phone && phone.value && !isValidPhone(phone.value)) {
            showError(phone, 'Format de téléphone invalide');
            isValid = false;
        }
        
        return isValid;
    }

    /**
     * Valide le formulaire de mot de passe
     */
    function validatePasswordForm() {
        let isValid = true;
        const currentPassword = passwordForm.querySelector('input[name="current_password"]');
        const newPassword = passwordForm.querySelector('input[name="new_password"]');
        const confirmPassword = passwordForm.querySelector('input[name="confirm_password"]');
        
        // Validation du mot de passe actuel
        if (!currentPassword.value.trim()) {
            showError(currentPassword, 'Le mot de passe actuel est requis');
            isValid = false;
        }
        
        // Validation du nouveau mot de passe
        if (newPassword.value.length < 8) {
            showError(newPassword, 'Le mot de passe doit contenir au moins 8 caractères');
            isValid = false;
        }
        
        // Validation de la confirmation
        if (newPassword.value !== confirmPassword.value) {
            showError(confirmPassword, 'Les mots de passe ne correspondent pas');
            isValid = false;
        }
        
        return isValid;
    }

    /**
     * Initialise l'upload d'avatar
     */

    /**
     * Initialise les boutons de visibilité des mots de passe
     */
    function initPasswordVisibilityToggles() {
        const toggleButtons = document.querySelectorAll('.password-toggle');
        
        toggleButtons.forEach(button => {
            button.addEventListener('click', function() {
                const input = this.previousElementSibling;
                const icon = this.querySelector('i');
                
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    input.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            });
        });
    }

    /**
     * Initialise l'export des données utilisateur
     */
    function initExportData() {
        exportDataBtn.addEventListener('click', async function() {
            const originalHtml = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<span><i class="fas fa-spinner fa-spin mr-3"></i>Export en cours...</span>';

            try {
                const response = await fetch('/api/v1/settings/export', {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                    }
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => null);
                    throw new Error(errorData?.message || 'Erreur lors de l\'export');
                }

                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'export-donnees.json';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename[^;=\n]*=(['"]?)([^'";\n]*)\1/);
                    if (match && match[2]) {
                        filename = match[2];
                    }
                }

                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                showAlert('success', 'Données exportées avec succès');
            } catch (error) {
                console.error('Erreur export:', error);
                showAlert('error', error.message || 'Erreur lors de l\'export des données');
            } finally {
                this.disabled = false;
                this.innerHTML = originalHtml;
            }
        });
    }

    /**
     * Initialise la confirmation de suppression de compte
     */
    function initDeleteAccountConfirmation() {
        const modal = document.getElementById('delete-account-modal');
        const closeBtn = document.getElementById('close-delete-account-modal');
        const cancelBtn = document.getElementById('cancel-delete-account');
        const confirmBtn = document.getElementById('confirm-delete-account');
        const passwordInput = document.getElementById('delete-account-password');
        const errorDiv = document.getElementById('delete-account-error');

        if (!modal) return;

        const openModal = () => {
            modal.classList.remove('hidden');
            modal.style.display = 'flex';
            if (passwordInput) {
                passwordInput.value = '';
                setTimeout(() => passwordInput.focus(), 200);
            }
            if (errorDiv) errorDiv.classList.add('hidden');
        };

        const closeModal = () => {
            modal.classList.add('hidden');
            modal.style.display = 'none';
            if (passwordInput) passwordInput.value = '';
            if (errorDiv) errorDiv.classList.add('hidden');
        };

        const showDeleteError = (message) => {
            if (errorDiv) {
                errorDiv.classList.remove('hidden');
                errorDiv.querySelector('p').textContent = message;
            }
        };

        deleteAccountBtn.addEventListener('click', openModal);
        closeBtn?.addEventListener('click', closeModal);
        cancelBtn?.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        confirmBtn?.addEventListener('click', async function() {
            const password = passwordInput?.value.trim();
            if (!password) {
                showDeleteError('Veuillez entrer votre mot de passe.');
                passwordInput?.focus();
                return;
            }

            const originalHtml = this.innerHTML;
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Suppression...';

            try {
                const response = await fetch('/api/v1/settings/account', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                    },
                    body: JSON.stringify({ password })
                });

                const result = await response.json();

                if (response.ok && (result.success || result.status === 'success')) {
                    closeModal();
                    showAlert('success', result.message || 'Compte désactivé. Redirection...');
                    setTimeout(() => {
                        window.location.href = '/auth/login';
                    }, 2000);
                } else {
                    showDeleteError(result.message || 'Erreur lors de la suppression du compte.');
                    passwordInput?.focus();
                    passwordInput?.select();
                }
            } catch (error) {
                console.error('Erreur suppression compte:', error);
                showDeleteError('Erreur de connexion. Veuillez réessayer.');
            } finally {
                this.disabled = false;
                this.innerHTML = originalHtml;
            }
        });

        // Allow Enter key in password field to submit
        passwordInput?.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                confirmBtn?.click();
            }
        });
    }

    /**
     * Affiche un message d'erreur sous un champ de formulaire
     */
    function showError(input, message) {
        // Supprime les erreurs existantes
        const existingError = input.parentElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // Crée et affiche le nouveau message d'erreur
        const error = document.createElement('div');
        error.className = 'error-message text-red-500 text-sm mt-1';
        error.textContent = message;
        input.parentElement.appendChild(error);
        
        // Met en surbrillance le champ en erreur
        input.classList.add('border-red-500');
        input.addEventListener('input', function clearError() {
            input.classList.remove('border-red-500');
            error.remove();
            input.removeEventListener('input', clearError);
        }, { once: true });
    }

    /**
     * Affiche une alerte à l'utilisateur
     */
    function showAlert(type, message) {
        // Supprime les alertes existantes
        const existingAlert = document.querySelector('.alert-message');
        if (existingAlert) {
            existingAlert.remove();
        }
        
        // Crée et affiche la nouvelle alerte
        const alert = document.createElement('div');
        alert.className = `alert-message fixed top-4 right-4 p-4 rounded-md shadow-lg ${
            type === 'error' ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' : 
            type === 'success' ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 
            'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'
        }`;
        alert.textContent = message;
        document.body.appendChild(alert);
        
        // Supprime l'alerte après 5 secondes
        setTimeout(() => {
            alert.remove();
        }, 5000);
    }

    /**
     * Affiche un indicateur de chargement sur un bouton
     */
    function showLoading(button) {
        const originalText = button.innerHTML;
        button.disabled = true;
        button.innerHTML = `
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${originalText}
        `;
    }

    // Gestion de l'upload de photo de profil
    const profilePictureInput = document.getElementById('avatar-upload');
    if (profilePictureInput) {
        profilePictureInput.addEventListener('change', async function() {
            const file = this.files[0];
            if (!file) return;
            
            // Validation côté client
            const maxSize = 5 * 1024 * 1024; // 5MB
            if (file.size > maxSize) {
                showAlert('error', 'La taille du fichier ne doit pas dépasser 5 Mo');
                this.value = '';
                return;
            }
            
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
            if (!allowedTypes.includes(file.type)) {
                showAlert('error', 'Seuls les fichiers JPG, PNG et GIF sont autorisés');
                this.value = '';
                return;
            }
            
            // Upload du fichier
            try {
                const formData = new FormData();
                formData.append('profile_picture', file);
                
                // Récupérer le token CSRF depuis le meta tag ou depuis un input hidden
                let csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
                if (!csrfToken) {
                    // Fallback: chercher dans les inputs hidden
                    const csrfInput = document.querySelector('input[name="csrf_token"]');
                    csrfToken = csrfInput ? csrfInput.value : '';
                }
                
                formData.append('csrf_token', csrfToken);
                
                const response = await fetch('/api/v1/profil/picture', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success || result.status === 'success') {
                    // Mettre à jour l'avatar affiché
                    const avatarContainer = document.querySelector('.profile-avatar');
                    const existingImg = avatarContainer.querySelector('img');
                    
                    if (existingImg) {
                        // Mettre à jour l'image existante avec timestamp pour forcer le rechargement
                        existingImg.src = result.picture_url + '?t=' + new Date().getTime();
                    } else {
                        // Créer et insérer l'image en gardant le contenu existant masqué
                        const img = document.createElement('img');
                        img.src = result.picture_url;
                        img.alt = 'Photo de profil';
                        img.className = 'w-full h-full rounded-full object-cover';
                        img.style.position = 'absolute';
                        img.style.top = '0';
                        img.style.left = '0';
                        img.style.zIndex = '1';
                        
                        // Masquer le texte des initiales
                        const textContent = avatarContainer.childNodes;
                        textContent.forEach(node => {
                            if (node.nodeType === Node.TEXT_NODE) {
                                node.style = 'display: none;';
                            }
                        });
                        
                        avatarContainer.style.position = 'relative';
                        avatarContainer.appendChild(img);
                    }
                    
                    showAlert('success', 'Photo de profil mise à jour avec succès !');
                } else {
                    showAlert('error', 'Erreur : ' + (result.message || 'upload impossible'));
                }
            } catch (error) {
                console.error('Erreur upload:', error);
                showAlert('error', 'Erreur lors de l\'upload de l\'image');
            }
        });
    }

    // Fonctions utilitaires
    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function isValidPhone(phone) {
        return /^\+?[\d\s-]{10,}$/.test(phone);
    }

    // Gestion de la modal des notifications email
    function initEmailNotificationsModal() {
        const openBtn = document.getElementById('open-email-notifications-modal');
        const modal = document.getElementById('email-notifications-modal');
        const closeBtn = document.getElementById('close-email-notifications-modal');
        const cancelBtn = document.getElementById('cancel-email-notifications');
        const saveBtn = document.getElementById('save-email-notifications');
        const selectAllBtn = document.getElementById('select-all-notifications');
        const deselectAllBtn = document.getElementById('deselect-all-notifications');

        if (!openBtn || !modal) return;

        // Ouvrir la modal
        openBtn.addEventListener('click', async () => {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            await loadCurrentNotificationPreferences();
        });

        // Fermer la modal
        const closeModal = () => {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
        };

        closeBtn?.addEventListener('click', closeModal);
        cancelBtn?.addEventListener('click', closeModal);

        // Clic en dehors de la modal
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });

        // Sélectionner/désélectionner tout
        selectAllBtn?.addEventListener('click', () => {
            document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
                checkbox.checked = true;
            });
        });

        deselectAllBtn?.addEventListener('click', () => {
            document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
                checkbox.checked = false;
            });
        });

        // Sauvegarder les préférences
        saveBtn?.addEventListener('click', async () => {
            await saveNotificationPreferences();
            closeModal();
        });
    }

    // Charger les préférences actuelles
    async function loadCurrentNotificationPreferences() {
        try {
            const response = await fetch('/api/v1/profil/notifications', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (response.ok) {
                const data = await response.json();
                
                // Cocher les cases selon les préférences
                document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
                    const notificationType = checkbox.dataset.type;
                    const preference = data.preferences?.[notificationType];
                    checkbox.checked = preference?.email || false;
                });
            }
        } catch (error) {
            console.error('Erreur lors du chargement des préférences:', error);
        }
    }

    // Sauvegarder les préférences
    async function saveNotificationPreferences() {
        try {
            const preferences = {};
            
            document.querySelectorAll('.notification-checkbox').forEach(checkbox => {
                const notificationType = checkbox.dataset.type;
                preferences[notificationType] = {
                    email: checkbox.checked,
                    push: true // Les notifications push restent toujours actives
                };
            });

            const response = await fetch('/api/v1/profil/notifications', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ preferences })
            });

            if (response.ok) {
                showSuccessMessage('Préférences de notifications mises à jour avec succès');
            } else {
                showErrorMessage('Erreur lors de la sauvegarde des préférences');
            }
        } catch (error) {
            console.error('Erreur lors de la sauvegarde:', error);
            showErrorMessage('Erreur lors de la sauvegarde des préférences');
        }
    }

    // Messages des préférences de notifications (n'affichaient rien)
    function showSuccessMessage(message) {
        showAlert('success', message);
    }

    function showErrorMessage(message) {
        console.error('❌', message);
        showAlert('error', message);
    }

    // ===============================
    // GESTION 2FA (Two-Factor Authentication)
    // ===============================

    // Variables 2FA

    // Éléments DOM 2FA
    const enable2FAModal = document.getElementById('enable-2fa-modal');
    const disable2FAModal = document.getElementById('disable-2fa-modal');
    
    // Boutons et champs
    

    // Initialisation des écouteurs 2FA supprimée - maintenant dans initTwoFactorAuth()
    
    // Vérification finale du toggle 2FA
    setTimeout(() => {
        const toggle2FA = document.getElementById('2fa-toggle');
        if (!toggle2FA) {
            console.error('🚨 ERREUR: Toggle 2FA non trouvé dans le DOM');
        }
    }, 1000);


    // Fonction supprimée - version dupliquée



    function initTwoFactorAuth() {
        
        // Éléments DOM 2FA
        const toggle2FABtn = document.getElementById('2fa-toggle');
        const enable2FAModal = document.getElementById('enable-2fa-modal');
        const disable2FAModal = document.getElementById('disable-2fa-modal');
        const close2FAModalBtns = document.querySelectorAll('.close-2fa-modal');
        

        // Event listener pour le toggle principal
        if (toggle2FABtn) {
            toggle2FABtn.addEventListener('change', function(e) {
                handle2FAToggleChange(e);
            });
        } else {
            console.error('❌ Toggle 2fa-toggle non trouvé');
        }

        // Fermer les modals
        close2FAModalBtns.forEach(btn => {
            btn.addEventListener('click', close2FAModals);
        });

        // Clic en dehors de la modal pour fermer
        if (enable2FAModal) {
            enable2FAModal.addEventListener('click', function(e) {
                if (e.target === enable2FAModal) {
                    close2FAModals();
                }
            });
        }
        
        if (disable2FAModal) {
            disable2FAModal.addEventListener('click', function(e) {
                if (e.target === disable2FAModal) {
                    close2FAModals();
                }
            });
        }

        // Email 2FA - Envoi du code
        const sendEmailCodeBtn = document.getElementById('send-email-code-btn');
        const resendEmailCodeBtn = document.getElementById('resend-email-code-btn');
        if (sendEmailCodeBtn) {
            sendEmailCodeBtn.addEventListener('click', sendEmail2FACode);
        }
        if (resendEmailCodeBtn) {
            resendEmailCodeBtn.addEventListener('click', sendEmail2FACode);
        }

        // Bouton confirmer activation 2FA
        const confirmActivationBtn = document.getElementById('confirm-2fa-activation');
        if (confirmActivationBtn) {
            confirmActivationBtn.addEventListener('click', function() {
                confirm2FAActivation();
            });
        } else {
            console.error('❌ Bouton confirm-2fa-activation non trouvé');
        }
        
        // Bouton confirmer désactivation 2FA  
        const confirmDeactivationBtn = document.getElementById('confirm-2fa-deactivation');
        if (confirmDeactivationBtn) {
            confirmDeactivationBtn.addEventListener('click', function() {
                confirm2FADeactivation();
            });
        } else {
            console.error('❌ Bouton confirm-2fa-deactivation non trouvé');
        }

        // Toggle principal 2FA déjà enregistré plus haut

        // Bouton test email
        const testEmailBtn = document.getElementById('test-email-btn');
        if (testEmailBtn) {
            testEmailBtn.addEventListener('click', showTestEmailModal);
        }

        // Modal test email
        const testEmailModal = document.getElementById('test-email-modal');
        const closeTestModalBtns = document.querySelectorAll('.close-test-modal');
        const sendTestEmailBtn = document.getElementById('send-test-email-btn');

        closeTestModalBtns.forEach(btn => {
            btn.addEventListener('click', closeTestEmailModal);
        });

        if (testEmailModal) {
            testEmailModal.addEventListener('click', function(e) {
                if (e.target === testEmailModal) {
                    closeTestEmailModal();
                }
            });
        }

        if (sendTestEmailBtn) {
            sendTestEmailBtn.addEventListener('click', sendTestEmail);
        }
        
    }

    function show2FAModal(type) {
        close2FAModals();
        
        if (type === 'enable') {
            const enable2FAModal = document.getElementById('enable-2fa-modal');
            
            if (enable2FAModal) {
                enable2FAModal.classList.remove('hidden');
                
                // Forcer l'affichage avec du CSS inline pour diagnostic
                enable2FAModal.style.display = 'flex';
                enable2FAModal.style.position = 'fixed';
                enable2FAModal.style.top = '0';
                enable2FAModal.style.left = '0';
                enable2FAModal.style.width = '100%';
                enable2FAModal.style.height = '100%';
                enable2FAModal.style.zIndex = '9999';
                enable2FAModal.style.backgroundColor = 'rgba(0,0,0,0.5)';
                
                
                // Réinitialiser et afficher le contenu d'activation
                document.getElementById('email-2fa-activation')?.classList.remove('hidden');
                document.getElementById('email-2fa-deactivation')?.classList.add('hidden');
                
                // Mettre le focus sur le champ de code après ouverture
                setTimeout(() => {
                    const codeInput = document.getElementById('email-2fa-verification-code');
                    if (codeInput) {
                        codeInput.focus();
                    }
                }, 200);

            } else {
                console.error('❌ Modal enable-2fa-modal non trouvée dans le DOM');
            }
        } else if (type === 'disable') {
            const enable2FAModal = document.getElementById('enable-2fa-modal');
            if (enable2FAModal) {
                enable2FAModal.classList.remove('hidden');
                enable2FAModal.style.display = 'flex';
                enable2FAModal.style.position = 'fixed';
                enable2FAModal.style.top = '0';
                enable2FAModal.style.left = '0';
                enable2FAModal.style.width = '100%';
                enable2FAModal.style.height = '100%';
                enable2FAModal.style.zIndex = '9999';
                enable2FAModal.style.backgroundColor = 'rgba(0,0,0,0.5)';
                
                // Afficher le contenu de désactivation
                document.getElementById('email-2fa-activation')?.classList.add('hidden');
                document.getElementById('email-2fa-deactivation')?.classList.remove('hidden');
                
                // Re-connecter les event listeners après que la modal soit visible
                setTimeout(() => {
                    const confirmBtn = document.getElementById('confirm-2fa-deactivation');
                    if (confirmBtn) {
                        // Supprimer les anciens listeners
                        confirmBtn.removeEventListener('click', confirm2FADeactivation);
                        // Ajouter le nouveau listener
                        confirmBtn.addEventListener('click', function(e) {
                            e.preventDefault();
                            confirm2FADeactivation();
                        });
                    }
                }, 100);
                
            }
        }
    }

    function close2FAModals() {
        const enable2FAModal = document.getElementById('enable-2fa-modal');
        const disable2FAModal = document.getElementById('disable-2fa-modal');
        
        if (enable2FAModal) {
            enable2FAModal.classList.add('hidden');
            // Supprimer aussi les styles inline forcés
            enable2FAModal.style.display = 'none';
        }
        if (disable2FAModal) {
            disable2FAModal.classList.add('hidden');
        }
        
        // Masquer tous les contenus internes
        document.getElementById('email-2fa-activation')?.classList.add('hidden');
        document.getElementById('email-2fa-deactivation')?.classList.add('hidden');
        
        // Nettoyer les alertes
        document.querySelectorAll('.temp-alert').forEach(alert => alert.remove());
        
        // Réinitialiser les champs
        const codeInput = document.getElementById('email-2fa-verification-code');
        const passwordInput = document.getElementById('password-2fa-deactivation');
        if (codeInput) codeInput.value = '';
        if (passwordInput) passwordInput.value = '';
        
    }


    // Fonction supprimée - version dupliquée

    function show2FAAlert(type, message) {
        // Créer un conteneur d'alerte temporaire dans la modal active
        const activeModal = !enable2FAModal.classList.contains('hidden') ? enable2FAModal : disable2FAModal;
        
        // Supprimer les alertes existantes
        activeModal.querySelectorAll('.temp-alert').forEach(alert => alert.remove());
        
        const alert = document.createElement('div');
        alert.className = `temp-alert p-3 mb-4 rounded-lg text-sm ${
            type === 'error' ? 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-300 dark:border-red-800' : 
            type === 'success' ? 'bg-green-50 text-green-700 border border-green-200 dark:bg-green-900/30 dark:text-green-300 dark:border-green-800' : 
            'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800'
        }`;
        
        alert.innerHTML = `
            <div class="flex items-center">
                <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : 
                               type === 'success' ? 'fa-check-circle' : 'fa-info-circle'} mr-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Insérer l'alerte au début du contenu de la modal
        const modalContent = activeModal.querySelector('.p-6');
        if (modalContent) {
            modalContent.insertBefore(alert, modalContent.firstChild);
            
            // Supprimer après 5 secondes
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        }
    }

    function show2FALoading(button, text) {
        if (!button) return;
        
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = `
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            ${text}
        `;
    }

    function reset2FALoading(button, originalText) {
        if (!button) return;
        
        button.disabled = false;
        button.innerHTML = originalText || button.dataset.originalText || 'Action';
    }

    // ===============================
    // FONCTIONS EMAIL 2FA
    // ===============================

    async function sendEmail2FACode(event) {
        try {
            const sendBtn = document.getElementById('send-email-code-btn');
            const currentBtn = event ? event.target : sendBtn;
            
            show2FALoading(currentBtn, 'Envoi en cours...');
            
            const response = await fetch('/api/v1/profil/email-2fa/send-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                }
            });

            const result = await response.json();

            if (result.success || result.status === 'success') {
                // Rester sur l'étape 1 et montrer un message de succès
                show2FAAlert('success', 'Code envoyé par email !');
                
                // Focus sur le champ de code
                const codeInput = document.getElementById('email-2fa-verification-code');
                if (codeInput) {
                    setTimeout(() => codeInput.focus(), 100);
                }
            } else {
                show2FAAlert('error', result.message);
            }
        } catch (error) {
            console.error('Erreur envoi email 2FA:', error);
            show2FAAlert('error', 'Erreur lors de l\'envoi du code');
        } finally {
            const currentBtn = event ? event.target : document.getElementById('send-email-code-btn');
            if (currentBtn && currentBtn.id === 'send-email-code-btn') {
                reset2FALoading(currentBtn, '<i class="fas fa-paper-plane mr-2"></i>Envoyer un code de test');
            } else {
                reset2FALoading(currentBtn, '<i class="fas fa-redo mr-2"></i>Renvoyer');
            }
        }
    }




    // Fonctions pour le toggle 2FA

    // Fonctions pour le test d'email
    function showTestEmailModal() {
        const modal = document.getElementById('test-email-modal');
        if (modal) {
            modal.classList.remove('hidden');
            // Réinitialiser le résultat
            const result = document.getElementById('test-email-result');
            if (result) {
                result.classList.add('hidden');
                result.innerHTML = '';
            }
        }
    }

    function closeTestEmailModal() {
        const modal = document.getElementById('test-email-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
    }

    async function sendTestEmail() {
        const btn = document.getElementById('send-test-email-btn');
        const result = document.getElementById('test-email-result');
        
        try {
            show2FALoading(btn, 'Envoi...');
            
            const response = await fetch('/api/v1/profil/email-2fa/send-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                }
            });

            const data = await response.json();
            
            if (result) {
                result.classList.remove('hidden');
                if (data.success) {
                    result.innerHTML = `
                        <div class="bg-green-50 border border-green-200 rounded-lg p-3 dark:bg-green-900/30 dark:border-green-800">
                            <p class="text-sm text-green-800 dark:text-green-200">
                                <i class="fas fa-check-circle mr-2"></i>
                                Email de test envoyé avec succès !
                            </p>
                        </div>
                    `;
                } else {
                    result.innerHTML = `
                        <div class="bg-red-50 border border-red-200 rounded-lg p-3 dark:bg-red-900/30 dark:border-red-800">
                            <p class="text-sm text-red-800 dark:text-red-200">
                                <i class="fas fa-exclamation-circle mr-2"></i>
                                Erreur : ${data.message}
                            </p>
                        </div>
                    `;
                }
            }
        } catch (error) {
            console.error('Erreur test email:', error);
            if (result) {
                result.classList.remove('hidden');
                result.innerHTML = `
                    <div class="bg-red-50 border border-red-200 rounded-lg p-3 dark:bg-red-900/30 dark:border-red-800">
                        <p class="text-sm text-red-800 dark:text-red-200">
                            <i class="fas fa-exclamation-circle mr-2"></i>
                            Erreur de connexion
                        </p>
                    </div>
                `;
            }
        } finally {
            reset2FALoading(btn, '<i class="fas fa-paper-plane mr-2"></i>Envoyer test');
        }
    }

    // Fonction pour le toggle 2FA principal
    function handle2FAToggleChange(event) {
        const isEnabled = event.target.checked;
        const currentStatus = event.target.dataset.currentStatus === 'true';
        
        
        if (!currentStatus && isEnabled) {
            // Activation : envoyer code et ouvrir modal activation
            show2FAModal('enable');
            setTimeout(() => sendEmail2FACode(), 500);
        } else if (currentStatus && !isEnabled) {
            // Désactivation : ouvrir modal désactivation
            show2FAModal('disable');
        }
        
        // Remettre le toggle à son état actuel en attendant confirmation
        event.target.checked = currentStatus;
    }

    // Fonction pour confirmer l'activation
    async function confirm2FAActivation() {
        const codeInput = document.getElementById('email-2fa-verification-code');
        const code = codeInput ? codeInput.value.trim() : '';
        
        if (!code || code.length !== 6) {
            show2FAAlert('error', 'Veuillez entrer un code à 6 chiffres');
            codeInput.focus();
            return;
        }
        
        try {
            const response = await fetch('/api/v1/profil/email-2fa/verify-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ code })
            });
            
            const result = await response.json();
            
            if (result.success || result.status === 'success') {
                // Mettre à jour immédiatement l'interface
                const toggle = document.getElementById('2fa-toggle');
                const statusSpan = document.getElementById('2fa-status');
                
                if (toggle) {
                    toggle.checked = true;
                    toggle.dataset.currentStatus = 'true';
                }
                if (statusSpan) {
                    statusSpan.textContent = 'Activée';
                }
                
                show2FAAlert('success', '2FA activée avec succès !');
                // Fermer immédiatement la modal
                setTimeout(() => {
                    close2FAModals();
                }, 1500);
            } else {
                show2FAAlert('error', 'Code incorrect');
                codeInput.focus();
            }
        } catch (error) {
            console.error('Erreur:', error);
            show2FAAlert('error', 'Erreur lors de la vérification');
        }
    }

    // Fonction pour confirmer la désactivation
    async function confirm2FADeactivation() {
        const passwordInput = document.getElementById('password-2fa-deactivation');
        const password = passwordInput ? passwordInput.value.trim() : '';
        
        if (!password) {
            show2FAAlert('error', 'Veuillez entrer votre mot de passe');
            passwordInput.focus();
            return;
        }
        
        try {
            const response = await fetch('/api/v1/profil/email-2fa/disable', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
                },
                body: JSON.stringify({ password })
            });
            
            const result = await response.json();
            
            if (result.success || result.status === 'success') {
                // Mettre à jour immédiatement l'interface
                const toggle = document.getElementById('2fa-toggle');
                const statusSpan = document.getElementById('2fa-status');
                
                if (toggle) {
                    toggle.checked = false;
                    toggle.dataset.currentStatus = 'false';
                }
                if (statusSpan) {
                    statusSpan.textContent = 'Désactivée';
                }
                
                show2FAAlert('success', '2FA désactivée avec succès !');
                // Fermer immédiatement la modal
                setTimeout(() => {
                    close2FAModals();
                }, 1500);
            } else {
                show2FAAlert('error', 'Mot de passe incorrect');
                passwordInput.focus();
            }
        } catch (error) {
            console.error('Erreur:', error);
            show2FAAlert('error', 'Erreur lors de la désactivation');
        }
    }
});
