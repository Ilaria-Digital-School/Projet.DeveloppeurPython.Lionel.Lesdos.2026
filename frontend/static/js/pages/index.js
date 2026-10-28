// Script spécifique à la page d'accueil
document.addEventListener('DOMContentLoaded', function() {
  // Initialisation des éléments interactifs
  initFeatureCards();
  initAuthButtons();
  
  // Animation au défilement
  setupScrollAnimations();
  
  // Gestion du chargement paresseux des images
  if ('loading' in HTMLImageElement.prototype) {
    const images = document.querySelectorAll('img[loading="lazy"]');
    images.forEach(img => {
      img.src = img.dataset.src;
    });
  }
  
  /**
   * Initialise les cartes de fonctionnalités avec des effets au survol
   */
  function initFeatureCards() {
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach((card, index) => {
      // Ajoute un délai d'animation progressif pour chaque carte
      card.style.transitionDelay = `${index * 100}ms`;
      
      // Animation au survol
      card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-5px)';
      });
      
      card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
      });
    });
  }
  
  /**
   * Initialise les boutons d'authentification
   */
  function initAuthButtons() {
    const loginBtn = document.querySelector('.btn-login');
    const registerBtn = document.querySelector('.btn-register');
    
    if (loginBtn) {
      loginBtn.addEventListener('click', function(e) {
        e.preventDefault();
        // Animation de clic
        this.classList.add('active');
        setTimeout(() => this.classList.remove('active'), 200);
        
        // Redirection vers la page de connexion
        window.location.href = this.href;
      });
    }
    
    if (registerBtn) {
      registerBtn.addEventListener('click', function(e) {
        e.preventDefault();
        // Animation de clic
        this.classList.add('active');
        setTimeout(() => this.classList.remove('active'), 200);
        
        // Redirection vers la page d'inscription
        window.location.href = this.href;
      });
    }
  }
  
  /**
   * Configure les animations au défilement
   */
  function setupScrollAnimations() {
    const observerOptions = {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('animate-fade-in');
          observer.unobserve(entry.target);
        }
      });
    }, observerOptions);
    
    // Observer les sections à animer
    const sections = document.querySelectorAll('.animate-on-scroll');
    sections.forEach(section => {
      observer.observe(section);
    });
  }
  
  // Gestion du rechargement de la page pour les animations
  window.addEventListener('beforeunload', function() {
    window.scrollTo(0, 0);
  });
});

// Export pour les tests unitaires (si nécessaire)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    initFeatureCards,
    initAuthButtons,
    setupScrollAnimations
  };
}
