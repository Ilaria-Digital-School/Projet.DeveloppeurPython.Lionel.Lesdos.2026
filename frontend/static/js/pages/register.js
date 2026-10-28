/**
 * Script de validation du formulaire d'inscription
 * Gère la validation en temps réel, l'affichage des erreurs et la soumission du formulaire
 */


document.addEventListener('DOMContentLoaded', function() {
    // Sélection des éléments du formulaire
    const registerForm = document.querySelector('.register-form');
    if (!registerForm) return; // Arrêter si le formulaire n'existe pas
    
    // Sélectionner le formulaire
    const form = document.querySelector('.register-form');
    if (!form) return;
    
    // Sélectionner les champs du formulaire avec les bons sélecteurs
    const usernameInput = form.querySelector('input[name="username"]');
    const emailInput = form.querySelector('input[name="email"]');
    const passwordInput = form.querySelector('input[name="password"]');
    const password2Input = form.querySelector('input[name="password2"]');
    const submitButton = form.querySelector('button[type="submit"]');
    
    // Supprimer les références aux champs qui n'existent pas dans notre formulaire
    // const firstNameInput = null;  // Champ inexistant
    // const lastNameInput = null;   // Champ inexistant
    // const termsCheckbox = null;   // Case à cocher inexistante
    
    // Afficher les champs trouvés pour le débogage
    
    // Vérifier que les champs obligatoires existent
    const requiredInputs = [
        { input: usernameInput, name: 'Nom d\'utilisateur' },
        { input: emailInput, name: 'Email' },
        { input: passwordInput, name: 'Mot de passe' }
    ];
    
    for (const { input, name } of requiredInputs) {
        if (!input) {
            console.error(`Champ de formulaire manquant: ${name}`);
            // Ne pas arrêter le script, mais afficher un message d'erreur
            const errorDiv = document.createElement('div');
            errorDiv.className = 'alert alert-danger';
            errorDiv.textContent = `Erreur: Le champ "${name}" est manquant. Veuillez contacter l'administrateur.`;
            document.querySelector('.register-form')?.prepend(errorDiv);
            return;
        }
    }
    
    // Variables d'état
    let isSubmitting = false;

    // Fonction de validation de l'email
    function validateEmail(email) {
        if (!email) {
            return { valid: false, message: 'L\'email est requis' };
        }
        
        // Vérification du format de base
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!re.test(String(email).toLowerCase())) {
            return { valid: false, message: 'Veuillez entrer une adresse email valide' };
        }
        
        // Vérification des caractères spéciaux potentiellement dangereux
        const dangerousChars = /[\s<>\[\]\\\|]/;
        if (dangerousChars.test(email)) {
            return { valid: false, message: 'L\'email contient des caractères non autorisés' };
        }
        
        return { valid: true };
    }

    // Fonction de validation du mot de passe
    function validatePassword(password) {
        if (!password) {
            return { valid: false, message: 'Le mot de passe est requis' };
        }
        
        // Vérification de la longueur minimale
        if (password.length < 8) {
            return { valid: false, message: 'Le mot de passe doit contenir au moins 8 caractères' };
        }
        
        // Vérification de la présence d'une majuscule
        if (!/[A-Z]/.test(password)) {
            return { valid: false, message: 'Le mot de passe doit contenir au moins une majuscule' };
        }
        
        // Vérification de la présence d'une minuscule
        if (!/[a-z]/.test(password)) {
            return { valid: false, message: 'Le mot de passe doit contenir au moins une minuscule' };
        }
        
        // Vérification de la présence d'un chiffre
        if (!/\d/.test(password)) {
            return { valid: false, message: 'Le mot de passe doit contenir au moins un chiffre' };
        }
        
        // Vérification de la présence d'un caractère spécial
        if (!/[@$!%*?&;#'"{}/<>.,_+=|\\-]/.test(password)) {
            return { valid: false, message: 'Le mot de passe doit contenir au moins un caractère spécial' };
        }
        
        return { valid: true };
    }

    /**
     * Affiche un message d'erreur pour un champ de formulaire
     * @param {HTMLElement} input - L'élément de formulaire en erreur
     * @param {string} message - Le message d'erreur à afficher
     */
    function showError(input, message) {
        if (!input) return;
        
        const formGroup = input.closest('.form-group');
        if (!formGroup) return;
        
        // Supprimer les anciens messages d'erreur
        clearError(input);
        
        // Créer le conteneur du message d'erreur
        const errorElement = document.createElement('div');
        const errorId = `${input.id}Error`;
        
        errorElement.id = errorId;
        errorElement.className = 'error-message';
        errorElement.setAttribute('role', 'alert');
        errorElement.textContent = message;
        
        // Ajouter l'ARIA live pour les lecteurs d'écran
        errorElement.setAttribute('aria-live', 'polite');
        
        // Ajouter le message d'erreur après le champ de formulaire
        input.insertAdjacentElement('afterend', errorElement);
        
        // Mettre à jour les attributs ARIA
        input.setAttribute('aria-invalid', 'true');
        input.setAttribute('aria-describedby', errorId);
        
        // Ajouter la classe d'erreur visuelle
        input.classList.add('is-invalid');
        
        // Faire défiler jusqu'au premier champ en erreur
        if (!isSubmitting) {
            input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            input.focus({ preventScroll: true });
        }
    }

    /**
     * Supprime le message d'erreur d'un champ de formulaire
     * @param {HTMLElement} input - L'élément de formulaire à nettoyer
     */
    function clearError(input) {
        if (!input) return;
        
        const formGroup = input.closest('.form-group');
        if (!formGroup) return;
        
        // Supprimer les messages d'erreur existants
        const existingError = formGroup.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }
        
        // Réinitialiser les attributs ARIA
        input.removeAttribute('aria-invalid');
        
        // Mettre à jour aria-describedby pour conserver les autres descriptions
        const describedBy = input.getAttribute('aria-describedby');
        if (describedBy) {
            const descriptors = describedBy.split(' ').filter(id => !id.endsWith('Error'));
            input.setAttribute('aria-describedby', descriptors.join(' ').trim() || null);
        }
        
        // Supprimer la classe d'erreur visuelle
        input.classList.remove('is-invalid');
    }

    /**
     * Valide l'ensemble du formulaire
     * @returns {boolean} - True si le formulaire est valide, false sinon
     */
    function validateForm() {
        let isValid = true;
        isSubmitting = true;

        // Validation du nom d'utilisateur
        const username = usernameInput.value.trim();
        if (!username) {
            showError(usernameInput, 'Le nom d\'utilisateur est requis');
            isValid = false;
        } else if (username.length < 3) {
            showError(usernameInput, 'Le nom d\'utilisateur doit contenir au moins 3 caractères');
            isValid = false;
        } else if (username.length > 30) {
            showError(usernameInput, 'Le nom d\'utilisateur ne peut pas dépasser 30 caractères');
            isValid = false;
        } else if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
            showError(usernameInput, 'Le nom d\'utilisateur ne peut contenir que des lettres, chiffres, tirets et underscores');
            isValid = false;
        } else {
            clearError(usernameInput);
        }

        // Les validations pour le prénom et le nom de famille ont été supprimées
        // car ces champs n'existent pas dans notre formulaire

        // Validation de l'email
        const email = emailInput.value.trim();
        if (!email) {
            showError(emailInput, 'L\'email est requis');
            isValid = false;
        } else {
            const emailValidation = validateEmail(email);
            if (!emailValidation.valid) {
                showError(emailInput, emailValidation.message);
                isValid = false;
            } else {
                clearError(emailInput);
            }
        }

        // Validation du mot de passe
        const password = passwordInput.value;
        if (!password) {
            showError(passwordInput, 'Le mot de passe est requis');
            isValid = false;
        } else {
            const passwordValidation = validatePassword(password);
            if (!passwordValidation.valid) {
                showError(passwordInput, passwordValidation.message);
                isValid = false;
            } else {
                clearError(passwordInput);
            }
        }

        // Validation de la confirmation du mot de passe
        const password2 = password2Input.value;
        if (!password2) {
            showError(password2Input, 'Veuillez confirmer votre mot de passe');
            isValid = false;
        } else if (password !== password2) {
            showError(password2Input, 'Les mots de passe ne correspondent pas');
            isValid = false;
        } else {
            clearError(password2Input);
        }

        // La validation des conditions d'utilisation a été supprimée
        // car la case à cocher n'existe pas dans notre formulaire

        isSubmitting = false;
        return isValid;
    }

    /**
     * Initialise la gestion de la soumission du formulaire
     */
    function initFormSubmission() {
        if (!registerForm) return;
        
        registerForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            if (validateForm()) {
                // Désactiver le bouton de soumission pour éviter les soumissions multiples
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Création du compte...';
                }
                
                // Afficher un message de chargement
                const existingLoading = registerForm.querySelector('.alert-info');
                if (!existingLoading) {
                    const loadingMessage = document.createElement('div');
                    loadingMessage.className = 'alert alert-info mt-3';
                    loadingMessage.role = 'alert';
                    loadingMessage.setAttribute('aria-live', 'polite');
                    
                    const loadingContent = document.createElement('div');
                    loadingContent.className = 'alert-content';
                    
                    const spinner = document.createElement('span');
                    spinner.className = 'spinner-border spinner-border-sm me-2';
                    spinner.setAttribute('role', 'status');
                    spinner.setAttribute('aria-hidden', 'true');
                    
                    const text = document.createElement('span');
                    text.textContent = 'Traitement de votre inscription en cours...';
                    
                    loadingContent.appendChild(spinner);
                    loadingContent.appendChild(text);
                    loadingMessage.appendChild(loadingContent);
                    
                    // Insérer le message de chargement avant le bouton de soumission
                    const submitButton = registerForm.querySelector('button[type="submit"]');
                    if (submitButton) {
                        submitButton.parentNode.insertBefore(loadingMessage, submitButton);
                    } else {
                        registerForm.appendChild(loadingMessage);
                    }
                    
                    // Faire défiler jusqu'au message de chargement
                    loadingMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                // Soumettre le formulaire avec une petite temporisation pour permettre l'affichage du message
                setTimeout(() => {
                    this.submit();
                }, 300);
            } else {
                // Faire défiler jusqu'à la première erreur
                const firstError = document.querySelector('.is-invalid');
                if (firstError) {
                    firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    firstError.focus();
                }
            }
        });
    }

    /**
     * Initialise la validation en temps réel des champs du formulaire
     */
    function initRealTimeValidation() {
        const formInputs = [
            { input: usernameInput, validate: validateUsername },
            { input: emailInput, validate: validateEmail },
            { input: passwordInput, validate: validatePassword },
            { input: password2Input, validate: validatePasswordConfirmation }
        ];
        
        // Fonctions de validation spécifiques pour chaque champ
        function validateUsername(value) {
            if (!value) return { valid: false, message: 'Le nom d\'utilisateur est requis' };
            if (value.length < 3) return { valid: false, message: 'Le nom d\'utilisateur doit contenir au moins 3 caractères' };
            if (value.length > 30) return { valid: false, message: 'Le nom d\'utilisateur ne peut pas dépasser 30 caractères' };
            if (!/^[a-zA-Z0-9_-]+$/.test(value)) return { valid: false, message: 'Le nom d\'utilisateur ne peut contenir que des lettres, chiffres, tirets et underscores' };
            return { valid: true };
        }
        
        function validateName(value) {
            if (!value) return { valid: false, message: 'Ce champ est requis' };
            if (value.length > 50) return { valid: false, message: 'Ce champ ne peut pas dépasser 50 caractères' };
            return { valid: true };
        }
        
        function validatePasswordConfirmation(value) {
            if (!value) return { valid: false, message: 'Veuillez confirmer votre mot de passe' };
            if (passwordInput && value !== passwordInput.value) return { valid: false, message: 'Les mots de passe ne correspondent pas' };
            return { valid: true };
        }
        
        // Ajout des écouteurs d'événements pour la validation en temps réel
        formInputs.forEach(({ input, validate }) => {
            if (!input) return;
            
            // Validation lors de la perte de focus
            input.addEventListener('blur', function() {
                if (!this.value) return;
                
                const validation = validate(this.value);
                if (!validation.valid) {
                    showError(this, validation.message);
                } else {
                    clearError(this);
                }
            });
            
            // Nettoyage des erreurs lors de la saisie
            input.addEventListener('input', function() {
                // Ne pas valider pendant la saisie, seulement effacer les erreurs
                if (this.classList.contains('is-invalid')) {
                    clearError(this);
                }
            });
        });
        
        // Pas de validation des conditions d'utilisation car la case à cocher n'existe pas
    }

    /**
     * Initialise la fonctionnalité de basculement de la visibilité du mot de passe
     */
    function initPasswordToggle() {
        const passwordFields = [passwordInput, password2Input];
        
        passwordFields.forEach(input => {
            if (!input) return;
            
            const inputWrapper = input.closest('.password-wrapper');
            if (!inputWrapper) return;
            
            // Sélectionner le bouton de basculement existant
            const toggleButton = inputWrapper.querySelector('.toggle-password');
            if (!toggleButton) return;
            
            // Sélectionner l'icône à l'intérieur du bouton
            const toggleIcon = toggleButton.querySelector('.toggle-icon');
            if (!toggleIcon) return;
            
            // Gestionnaire d'événements pour le basculement
            toggleButton.addEventListener('click', function(e) {
                const isPassword = input.type === 'password';
                input.type = isPassword ? 'text' : 'password';
                
                // Mettre à jour l'icône et l'étiquette ARIA
                if (isPassword) {
                    toggleIcon.textContent = '👁️‍🗨️';
                    this.setAttribute('aria-label', 'Masquer le mot de passe');
                } else {
                    toggleIcon.textContent = '👁️';
                    this.setAttribute('aria-label', 'Afficher le mot de passe');
                }
                
                // Empêcher le comportement par défaut du bouton
                e.preventDefault();
                
                // Remettre le focus sur le champ après le clic
                input.focus();
            });
            
            // Gestion de la touche Espace/Entrée pour l'accessibilité
            toggleButton.addEventListener('keydown', function(e) {
                if (e.key === ' ' || e.key === 'Enter') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
    }

    /**
     * Initialise le formulaire d'inscription
     */
    function init() {
        // Initialiser les fonctionnalités
        initRealTimeValidation();
        initPasswordToggle();
        initFormSubmission();
        
        // Mettre le focus sur le premier champ si le formulaire est vide
        if (usernameInput && !usernameInput.value) {
            usernameInput.focus();
        }
    }
    
    // Démarrer l'initialisation
    init();
});
