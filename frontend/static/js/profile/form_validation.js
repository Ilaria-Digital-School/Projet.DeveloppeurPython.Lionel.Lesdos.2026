/**
 * Validation en temps réel des formulaires de profil
 */

document.addEventListener('DOMContentLoaded', function() {
    // Activer la validation sur tous les formulaires avec la classe 'needs-validation'
    const forms = document.querySelectorAll('.needs-validation');
    
    // Désactiver la soumission des formulaires si des champs sont invalides
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
        
        // Activer la validation en temps réel
        setupRealTimeValidation(form);
    });
    
    // Validation personnalisée pour les mots de passe
    const passwordFields = document.querySelectorAll('input[type="password"]');
    passwordFields.forEach(field => {
        field.addEventListener('input', validatePasswordStrength);
    });
    
    // Validation des numéros de téléphone
    const phoneFields = document.querySelectorAll('input[type="tel"]');
    phoneFields.forEach(field => {
        field.addEventListener('input', formatPhoneNumber);
        field.addEventListener('blur', validatePhoneNumber);
    });
    
    // Validation des emails
    const emailFields = document.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        field.addEventListener('input', validateEmail);
    });
});

/**
 * Configuration de la validation en temps réel pour un formulaire
 */
function setupRealTimeValidation(form) {
    const fields = form.querySelectorAll('input:not([type="submit"]), select, textarea');
    
    fields.forEach(field => {
        // Ignorer les champs cachés et les boutons
        if (field.type === 'hidden' || field.type === 'submit' || field.type === 'button') {
            return;
        }
        
        // Validation lors de la perte du focus
        field.addEventListener('blur', function() {
            validateField(this);
        });
        
        // Validation pendant la saisie pour certains champs
        if (field.type !== 'file' && field.type !== 'select-one') {
            field.addEventListener('input', function() {
                if (this.value.trim() !== '') {
                    validateField(this);
                }
            });
        }
    });
}

/**
 * Validation d'un champ individuel
 */
function validateField(field) {
    // Réinitialiser les états de validation
    field.classList.remove('is-valid', 'is-invalid');
    
    // Trouver le message d'erreur associé
    const errorId = field.getAttribute('aria-describedby');
    const errorElement = errorId ? document.getElementById(errorId) : null;
    
    // Vérifier la validité du champ
    if (field.checkValidity()) {
        field.classList.add('is-valid');
        if (errorElement) {
            errorElement.textContent = '';
            errorElement.style.display = 'none';
        }
        return true;
    } else {
        field.classList.add('is-invalid');
        
        // Afficher un message d'erreur personnalisé
        if (errorElement) {
            errorElement.textContent = getErrorMessage(field);
            errorElement.style.display = 'block';
        }
        return false;
    }
}

/**
 * Validation de la force du mot de passe
 */
function validatePasswordStrength(event) {
    const password = event.target;
    const strengthMeter = document.getElementById('password-strength-meter');
    const strengthText = document.getElementById('password-strength-text');
    
    if (!password.value) {
        if (strengthMeter) strengthMeter.style.display = 'none';
        if (strengthText) strengthText.style.display = 'none';
        return;
    }
    
    // Calculer la force du mot de passe
    const strength = calculatePasswordStrength(password.value);
    
    // Mettre à jour la barre de progression
    if (strengthMeter) {
        strengthMeter.style.display = 'block';
        strengthMeter.value = strength.score * 25; // Convertir le score (0-4) en pourcentage
        
        // Changer la couleur en fonction de la force
        if (strength.score < 2) {
            strengthMeter.className = 'form-range is-invalid';
        } else if (strength.score < 4) {
            strengthMeter.className = 'form-range is-warning';
        } else {
            strengthMeter.className = 'form-range is-valid';
        }
    }
    
    // Afficher des conseils
    if (strengthText) {
        strengthText.style.display = 'block';
        
        if (strength.feedback.warning) {
            strengthText.innerHTML = `<small class="text-warning">${strength.feedback.warning}</small>`;
        } else if (strength.feedback.suggestions && strength.feedback.suggestions.length > 0) {
            strengthText.innerHTML = `<small class="text-muted">${strength.feedback.suggestions[0]}</small>`;
        } else if (strength.score >= 4) {
            strengthText.innerHTML = '<small class="text-success">Mot de passe fort</small>';
        } else {
            strengthText.innerHTML = '';
        }
    }
}

/**
 * Calcule la force d'un mot de passe
 */
function calculatePasswordStrength(password) {
    // Implémentation basique - à remplacer par une bibliothèque comme zxcvbn en production
    let score = 0;
    const feedback = {
        warning: '',
        suggestions: []
    };
    
    // Longueur minimale
    if (password.length < 8) {
        feedback.warning = 'Trop court';
        feedback.suggestions.push('Utilisez au moins 12 caractères');
        return { score: 0, feedback };
    }
    
    // Ajouter des points pour différentes caractéristiques
    if (/[a-z]/.test(password)) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    if (password.length >= 12) score = Math.min(4, score + 1);
    
    // Ajuster le score en fonction de la longueur
    if (password.length > 20) score = Math.min(4, score + 1);
    
    // Ajouter des suggestions
    if (!/[A-Z]/.test(password)) {
        feedback.suggestions.push('Ajoutez une majuscule');
    }
    if (!/[0-9]/.test(password)) {
        feedback.suggestions.push('Ajoutez un chiffre');
    }
    if (!/[^A-Za-z0-9]/.test(password)) {
        feedback.suggestions.push('Ajoutez un caractère spécial');
    }
    
    return { score, feedback };
}

/**
 * Formatage des numéros de téléphone
 */
function formatPhoneNumber(event) {
    const input = event.target;
    let value = input.value.replace(/\D/g, ''); // Supprimer tous les caractères non numériques
    
    // Appliquer un formatage basique pour la France
    if (value.startsWith('0')) {
        if (value.length > 2) value = value.substring(0, 2) + ' ' + value.substring(2);
        if (value.length > 5) value = value.substring(0, 5) + ' ' + value.substring(5);
        if (value.length > 8) value = value.substring(0, 8) + ' ' + value.substring(8);
        if (value.length > 11) value = value.substring(0, 11) + ' ' + value.substring(11);
    } else if (value.startsWith('+33') || value.startsWith('0033')) {
        // Format international pour la France
        if (value.startsWith('00')) {
            value = '+33' + value.substring(4);
        }
        if (value.length > 3) value = value.substring(0, 3) + ' ' + value.substring(3);
        if (value.length > 6) value = value.substring(0, 6) + ' ' + value.substring(6);
        if (value.length > 8) value = value.substring(0, 8) + ' ' + value.substring(8);
        if (value.length > 10) value = value.substring(0, 10) + ' ' + value.substring(10);
    }
    
    input.value = value.trim();
}

/**
 * Validation des numéros de téléphone
 */
function validatePhoneNumber(event) {
    const input = event.target;
    const value = input.value.replace(/\s+/g, ''); // Supprimer les espaces
    
    // Expression régulière pour les numéros français
    const frPhoneRegex = /^(\+33|0)[1-9](\d{2}){4}$/;
    
    if (value && !frPhoneRegex.test(value)) {
        input.setCustomValidity('Veuillez entrer un numéro de téléphone valide');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    }
}

/**
 * Validation des adresses email
 */
function validateEmail(event) {
    const input = event.target;
    const email = input.value.trim();
    
    // Expression régulière simple pour la validation d'email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    
    if (email && !emailRegex.test(email)) {
        input.setCustomValidity('Veuillez entrer une adresse email valide');
        input.classList.add('is-invalid');
    } else {
        input.setCustomValidity('');
        input.classList.remove('is-invalid');
        if (email) input.classList.add('is-valid');
    }
}

/**
 * Retourne un message d'erreur personnalisé pour un champ
 */
function getErrorMessage(field) {
    if (field.validity.valueMissing) {
        return 'Ce champ est obligatoire';
    }
    
    if (field.validity.typeMismatch) {
        if (field.type === 'email') {
            return 'Veuillez entrer une adresse email valide';
        }
        if (field.type === 'url') {
            return 'Veuillez entrer une URL valide';
        }
    }
    
    if (field.validity.tooShort) {
        return `Ce champ doit contenir au moins ${field.minLength} caractères`;
    }
    
    if (field.validity.tooLong) {
        return `Ce champ ne doit pas dépasser ${field.maxLength} caractères`;
    }
    
    if (field.validity.patternMismatch) {
        if (field.pattern) {
            return 'Le format saisi est incorrect';
        }
        if (field.type === 'password') {
            return 'Le mot de passe doit contenir au moins 12 caractères, dont des majuscules, minuscules, chiffres et caractères spéciaux';
        }
    }
    
    if (field.validity.rangeOverflow) {
        return `La valeur ne doit pas dépasser ${field.max}`;
    }
    
    if (field.validity.rangeUnderflow) {
        return `La valeur doit être supérieure ou égale à ${field.min}`;
    }
    
    if (field.validity.stepMismatch) {
        return `La valeur doit être un multiple de ${field.step || 1}`;
    }
    
    if (field.validity.badInput) {
        return 'Veuillez entrer une valeur valide';
    }
    
    return field.validationMessage || 'Valeur invalide';
}

// Exposer les fonctions pour une utilisation globale
window.FormValidation = {
    validateField,
    validatePasswordStrength,
    validatePhoneNumber,
    validateEmail
};
