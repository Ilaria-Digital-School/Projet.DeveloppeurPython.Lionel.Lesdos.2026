/**
 * Couleurs des graphiques Chart.js selon le thème (clair / sombre).
 *
 * Chargé juste après chart.umd.js dans base.html : règle les couleurs par
 * défaut (textes, légendes, axes, grilles) et redessine tous les graphiques
 * quand la classe "dark" change sur <html>. Les pages ne doivent donc pas
 * fixer elles-mêmes la couleur des textes ou des grilles.
 */
(function () {
    if (typeof Chart === 'undefined') return;

    function couleursGraphiques() {
        const sombre = document.documentElement.classList.contains('dark');
        return {
            texte: sombre ? '#D1D5DB' : '#4B5563',
            titre: sombre ? '#F9FAFB' : '#111827',
            grille: sombre ? 'rgba(255, 255, 255, 0.12)' : 'rgba(0, 0, 0, 0.08)',
            fond: sombre ? '#1F2937' : '#FFFFFF',
            // Remplissage des graphiques sans données (jeu marqué "vide" par l'API)
            vide: sombre ? '#374151' : '#E5E7EB',
        };
    }

    function appliquerTheme() {
        const c = couleursGraphiques();
        Chart.defaults.color = c.texte;
        Chart.defaults.borderColor = c.grille;
        Chart.defaults.plugins.title.color = c.titre;
        // Séparation des parts des camemberts : couleur du fond de la carte
        Chart.defaults.elements.arc.borderColor = c.fond;
        Object.values(Chart.instances).forEach((graphique) => {
            // Chart.js recopie les couleurs des axes dans chaque graphique à sa
            // création : il faut les mettre à jour une par une.
            Object.values(graphique.options.scales || {}).forEach((axe) => {
                if (axe.ticks) axe.ticks.color = c.texte;
                if (axe.pointLabels) axe.pointLabels.color = c.texte;
                if (axe.title) axe.title.color = c.texte;
                if (axe.grid) axe.grid.color = c.grille;
                if (axe.border) axe.border.color = c.grille;
            });
            graphique.update('none');
        });
    }

    // Avant chaque dessin : couleur des jeux de données vides selon le thème
    Chart.register({
        id: 'couleurVide',
        beforeUpdate(graphique) {
            const c = couleursGraphiques();
            graphique.data.datasets.forEach((jeu) => {
                if (jeu.vide) jeu.backgroundColor = c.vide;
            });
        },
    });

    window.couleursGraphiques = couleursGraphiques;
    appliquerTheme();
    new MutationObserver(appliquerTheme).observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['class'],
    });
})();
