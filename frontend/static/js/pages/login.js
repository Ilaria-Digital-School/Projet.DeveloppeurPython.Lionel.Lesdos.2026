document.addEventListener('DOMContentLoaded', function() {
    // Sélection des éléments du formulaire
    const loginForm = document.querySelector('form');
    const emailInput = document.querySelector('input[name="email"]');
    const passwordInput = document.querySelector('input[name="password"]');
    const rememberMeInput = document.querySelector('input[name="remember_me"]');
    const submitButton = document.querySelector('button[type="submit"]');

    // Fonction de validation de l'email
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(String(email).toLowerCase());
    }

    // Fonction d'affichage des erreurs
    function showError(input, message) {
        const formGroup = input.closest('.form-group') || input.closest('.mb-3');
        let errorElement = formGroup.querySelector('.error-message');
        
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.className = 'error-message text-danger mt-1';
            formGroup.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
        input.classList.add('is-invalid');
    }

    // Fonction de suppression des erreurs
    function clearError(input) {
        const formGroup = input.closest('.form-group') || input.closest('.mb-3');
        const errorElement = formGroup.querySelector('.error-message');
        
        if (errorElement) {
            errorElement.remove();
        }
        
        input.classList.remove('is-invalid');
    }

    // Validation du formulaire
    function validateForm() {
        let isValid = true;

        // Validation de l'email
        if (!emailInput.value.trim()) {
            showError(emailInput, 'L\'email est requis');
            isValid = false;
        } else if (!validateEmail(emailInput.value.trim())) {
            showError(emailInput, 'Veuillez entrer un email valide');
            isValid = false;
        } else {
            clearError(emailInput);
        }

        // Validation du mot de passe
        if (!passwordInput.value) {
            showError(passwordInput, 'Le mot de passe est requis');
            isValid = false;
        } else if (passwordInput.value.length < 6) {
            showError(passwordInput, 'Le mot de passe doit contenir au moins 6 caractères');
            isValid = false;
        } else {
            clearError(passwordInput);
        }

        return isValid;
    }

    // Gestion de la soumission du formulaire (authentification web classique)
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            // Validation côté client avant soumission
            if (!validateForm()) {
                e.preventDefault();
                return false;
            }
            
            const csrfInput = document.querySelector('input[name="csrf_token"]');
            
            // Temporairement désactivé - laisser Flask-WTF gérer la validation
            // if (!csrfInput || !csrfInput.value) {
            //     e.preventDefault();
            //     console.error('❌ Token CSRF manquant ou vide');
            //     alert('Jeton de sécurité manquant. Veuillez rafraîchir la page et réessayer.');
            //     return false;
            // }
            
            if (csrfInput && csrfInput.value) {
            } else {
                console.warn('⚠️ Token CSRF non trouvé côté client, Flask-WTF gérera la validation');
            }
            
            // Désactiver le bouton de soumission pour éviter les doubles clics.
            // IMPORTANT : différé via setTimeout(0). Désactiver le bouton submit de
            // façon synchrone dans le handler 'submit' fait ANNULER l'envoi du
            // formulaire sous Firefox. Le différer laisse la soumission partir,
            // puis désactive le bouton au tick suivant (anti double-clic + spinner).
            if (submitButton) {
                setTimeout(function() {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Connexion en cours...';
                }, 0);
            }
            
            // Gérer la mémorisation des données de connexion (email uniquement)
            const rememberMe = document.querySelector('input[name="remember_me"]');
            if (rememberMe && rememberMe.checked) {
                localStorage.setItem('rememberMe', 'true');
                localStorage.setItem('savedEmail', emailInput.value);
            } else {
                localStorage.removeItem('rememberMe');
                localStorage.removeItem('savedEmail');
            }
            localStorage.removeItem('savedPassword');
            
            
            // Laisser le formulaire se soumettre normalement (POST vers /auth/login)
            // Flask gérera l'authentification et la redirection côté serveur
        });
    }

    // Validation en temps réel
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            clearError(this);
        });
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            clearError(this);
        });
    }

    // Gestion de l'affichage/masquage du mot de passe
    const togglePassword = document.querySelector('.toggle-password');
    
    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function() {
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            this.textContent = type === 'password' ? '👁️' : '👁️‍🗨️';
        });
    }

    // Gestion du chargement automatique des données de connexion enregistrées
    // Nettoyage securite: supprimer tout mot de passe residuel des anciennes versions
    localStorage.removeItem('savedPassword');

    if (localStorage.getItem('rememberMe') === 'true') {
        const savedEmail = localStorage.getItem('savedEmail');

        if (savedEmail && emailInput) {
            emailInput.value = savedEmail;
        }

        if (rememberMeInput) {
            rememberMeInput.checked = true;
        }
    }

    // Gestion de l'option "Se souvenir de moi"
    // Note: seul l'email est memorise. La persistance de session est geree cote serveur.
    if (loginForm && rememberMeInput) {
        loginForm.addEventListener('submit', function() {
            if (rememberMeInput.checked) {
                localStorage.setItem('rememberMe', 'true');
                if (emailInput) {
                    localStorage.setItem('savedEmail', emailInput.value);
                }
            } else {
                localStorage.removeItem('rememberMe');
                localStorage.removeItem('savedEmail');
            }
            // Nettoyage securite: supprimer tout mot de passe residuel
            localStorage.removeItem('savedPassword');
        });
    }
});
