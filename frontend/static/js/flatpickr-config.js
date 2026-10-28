/**
 * Configuration globale pour Flatpickr
 * Ce script initialise et configure Flatpickr pour tous les sélecteurs de date
 */

document.addEventListener('DOMContentLoaded', function() {
    // Configuration par défaut pour tous les sélecteurs de date
    const defaultOptions = {
        dateFormat: 'd/m/Y',
        locale: 'fr',
        allowInput: true,
        disableMobile: true, // Désactive le sélecteur natif sur mobile
        // Ajoutez d'autres options par défaut ici
    };

    // Initialiser Flatpickr pour tous les éléments avec la classe .datepicker
    const datepickers = document.querySelectorAll('.datepicker');
    if (datepickers.length > 0) {
        flatpickr('.datepicker', defaultOptions);
    }

    // Initialiser Flatpickr pour les champs de temps si nécessaire
    const timepickers = document.querySelectorAll('.timepicker');
    if (timepickers.length > 0) {
        flatpickr('.timepicker', {
            ...defaultOptions,
            enableTime: true,
            noCalendar: true,
            dateFormat: 'H:i',
            time_24hr: true
        });
    }

    // Initialiser Flatpickr pour les champs de date et heure
    const datetimePickers = document.querySelectorAll('.datetimepicker');
    if (datetimePickers.length > 0) {
        flatpickr('.datetimepicker', {
            ...defaultOptions,
            enableTime: true,
            dateFormat: 'd/m/Y H:i',
            time_24hr: true
        });
    }

    // Fonction utilitaire pour formater une date
    window.formatDate = function(date, format = 'd/m/Y') {
        return flatpickr.formatDate(new Date(date), format);
    };
});
