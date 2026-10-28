import { menuConfig } from './menu.config.js';

class Menu {
    constructor() {
        this.config = menuConfig;
        this.init();
    }

    init() {
        this.initMobileMenu();
        this.initUserMenu();
        this.initDarkMode();
        this.initEventListeners();
    }

    getElements() {
        return {
            mobileMenuButton: document.querySelector(this.config.selectors.mobileMenuButton),
            mobileMenu: document.querySelector(this.config.selectors.mobileMenu),
            userMenuButton: document.querySelector(this.config.selectors.userMenuButton),
            userMenu: document.querySelector(this.config.selectors.userMenu),
            darkModeToggle: document.querySelector(this.config.selectors.darkModeToggle)
        };
    }

    initMobileMenu() {
        const { mobileMenuButton, mobileMenu } = this.getElements();
        if (!mobileMenuButton || !mobileMenu) return;

        const toggleMenu = (isExpanded) => {
            const ariaExpanded = isExpanded.toString();
            const ariaLabel = isExpanded 
                ? this.config.text.menuExpanded 
                : this.config.text.menuCollapsed;

            mobileMenuButton.setAttribute('aria-expanded', ariaExpanded);
            mobileMenuButton.setAttribute('aria-label', ariaLabel);
            
            // Basculer les classes pour l'animation
            if (isExpanded) {
                mobileMenu.classList.add('show');
                document.body.style.overflow = 'hidden'; // Empêcher le défilement
            } else {
                // Retirer immédiatement la classe show pour éviter l'affichage en double
                mobileMenu.classList.remove('show');
                document.body.style.overflow = ''; // Rétablir le défilement
            }
        };

        // Gestionnaire d'événements pour le clic sur le bouton
        mobileMenuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
            toggleMenu(!isExpanded);
        });

        // Fermer le menu en cliquant à l'extérieur
        document.addEventListener('click', (e) => {
            if (mobileMenu && !mobileMenu.contains(e.target) && e.target !== mobileMenuButton) {
                toggleMenu(false);
            }
        });

        // Fermer le menu lors de la navigation sur mobile
        const navLinks = mobileMenu.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', () => toggleMenu(false));
        });

        // Fermer le menu avec la touche Échap
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && mobileMenuButton.getAttribute('aria-expanded') === 'true') {
                toggleMenu(false);
                mobileMenuButton.focus();
            }
        });
    }

    initUserMenu() {
        const { userMenuButton, userMenu } = this.getElements();
        if (!userMenuButton || !userMenu) return;

        const toggleUserMenu = (isExpanded) => {
            const ariaExpanded = isExpanded.toString();
            const ariaLabel = isExpanded 
                ? this.config.text.userMenuExpanded 
                : this.config.text.userMenuCollapsed;

            userMenuButton.setAttribute('aria-expanded', ariaExpanded);
            userMenuButton.setAttribute('aria-label', ariaLabel);
            
            if (isExpanded) {
                userMenu.classList.add('show');
            } else {
                userMenu.classList.remove('show');
            }
        };

        userMenuButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const isExpanded = userMenuButton.getAttribute('aria-expanded') === 'true';
            toggleUserMenu(!isExpanded);
        });

        // Fermer le menu en cliquant à l'extérieur
        document.addEventListener('click', (e) => {
            if (userMenu && !userMenu.contains(e.target) && e.target !== userMenuButton) {
                toggleUserMenu(false);
            }
        });

        // Fermer avec la touche Échap
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && userMenuButton.getAttribute('aria-expanded') === 'true') {
                toggleUserMenu(false);
                userMenuButton.focus();
            }
        });
    }

    initDarkMode() {
        const { darkModeToggle } = this.getElements();
        if (!darkModeToggle) return;

        // Vérifier le thème stocké ou la préférence système
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const storedTheme = localStorage.getItem('theme');
        
        if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
            document.documentElement.classList.add(this.config.classes.darkMode);
        }

        // Mettre à jour l'icône
        this.updateDarkModeIcon();

        // Gérer le clic sur le bouton
        darkModeToggle.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle(this.config.classes.darkMode);
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            this.updateDarkModeIcon();
        });
    }

    updateDarkModeIcon() {
        const { darkModeToggle } = this.getElements();
        if (!darkModeToggle) return;

        const isDark = document.documentElement.classList.contains(this.config.classes.darkMode);
        const icon = darkModeToggle.querySelector('i');
        
        if (icon) {
            icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
        }
    }

    initEventListeners() {
        // Gérer les changements de préférence de thème système
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem('theme')) {
                if (e.matches) {
                    document.documentElement.classList.add(this.config.classes.darkMode);
                } else {
                    document.documentElement.classList.remove(this.config.classes.darkMode);
                }
                this.updateDarkModeIcon();
            }
        });
    }
}

// Initialisation du menu
document.addEventListener('DOMContentLoaded', () => {
    new Menu();
});

export default Menu;

