/**
 * Gestion de la page des rapports
 * Ce fichier contient la logique pour la génération et l'affichage des rapports
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialisation des variables
    const createReportModal = document.getElementById('report-modal');
    const addReportBtn = document.getElementById('new-report-btn');
    const closeReportModalBtn = document.getElementById('close-report-modal');
    const cancelReportBtn = document.getElementById('cancel-report');
    const reportForm = document.getElementById('report-form');
    const reportTypeSelect = document.getElementById('report-type');
    const reportPreview = document.getElementById('report-preview');
    const reportsList = document.getElementById('saved-reports-body');
    
    // URL de l'API pour les rapports
    const API_BASE_URL = '/api/v1/rapports';
    
    // Graphiques
    let charts = {}; // Pour stocker les instances de graphiques
    
    // Référence au sélecteur de période (c'est un <select>, pas un input date)
    const dateRangePicker = document.getElementById('date-range');
    
    // Fonction pour initialiser les graphiques avec les données réelles de l'API
    async function initCharts(showAll = false) {
        // Lire les filtres sélectionnés
        const selectedType = reportTypeSelect?.value || 'expenses';
        const selectedDateRange = dateRangePicker?.value || 'current_month';

        // Construire les paramètres de date pour l'API
        let dateParams = `date_range=${selectedDateRange}`;
        if (selectedDateRange === 'custom') {
            const startDate = document.getElementById('start-date')?.value;
            const endDate = document.getElementById('end-date')?.value;
            if (startDate) dateParams += `&start_date=${startDate}`;
            if (endDate) dateParams += `&end_date=${endDate}`;
        }

        // Filtres d'analyse (catégories, libellé) : valent pour toute la page
        majResumeFiltres();
        dateParams = avecFiltres(dateParams);

        // Indicateurs et analyses détaillées (indépendants du type choisi)
        chargerDetail(dateParams);
        chargerEvolution(dateParams);
        chargerDestinataires(dateParams);
        chargerBudgets(dateParams);

        const categoryCtx = document.getElementById('expensesByCategoryChart');
        const monthlyCtx = document.getElementById('incomeVsExpensesChart');

        // Déterminer quels graphiques afficher selon le type sélectionné
        // Au chargement initial (showAll=true), afficher les deux
        const showExpenses = showAll || (selectedType === 'expenses' || selectedType === 'custom');
        const showMonthly = showAll || (selectedType === 'income-vs-expenses' || selectedType === 'cashflow' || selectedType === 'custom');

        // Cartes des graphiques
        const cardExpenses = document.getElementById('card-expenses');
        const cardMonthly = document.getElementById('card-income-vs-expenses');

        // Graphique des dépenses par catégorie (camembert)
        if (categoryCtx) {
            destroyChartIfExists('categoryChart');

            if (!showExpenses) {
                if (cardExpenses) cardExpenses.style.display = 'none';
            } else {
                if (cardExpenses) cardExpenses.style.display = '';

                let reportData = null;
                try {
                    const response = await fetch(`${API_BASE_URL}/data?report_type=expenses_by_category&${dateParams}`, {
                        headers: { 'Accept': 'application/json', 'X-CSRFToken': getCSRFToken() }
                    });
                    if (response.ok) {
                        reportData = await response.json();
                    }
                } catch (e) {
                    console.warn('Impossible de charger les données de rapport:', e);
                }

                const categories = reportData?.data?.categories || [];
                const amounts = reportData?.data?.amounts || [];

                if (categories.length === 0) {
                    const parent = categoryCtx.parentElement;
                    if (parent) {
                        categoryCtx.style.display = 'none';
                        let emptyMsg = parent.querySelector('.empty-chart-msg');
                        if (!emptyMsg) {
                            emptyMsg = document.createElement('div');
                            emptyMsg.className = 'empty-chart-msg flex items-center justify-center h-full text-gray-400 dark:text-gray-500';
                            emptyMsg.innerHTML = '<div class="text-center"><i class="fas fa-chart-pie text-4xl mb-2"></i><p>Aucune dépense sur cette période</p></div>';
                            parent.appendChild(emptyMsg);
                        }
                    }
                } else {
                    categoryCtx.style.display = '';
                    const emptyMsg = categoryCtx.parentElement?.querySelector('.empty-chart-msg');
                    if (emptyMsg) emptyMsg.remove();

                    const backgroundColors = ['#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#6B7280', '#EF4444', '#F97316', '#84CC16', '#06B6D4'];

                    charts.categoryChart = new Chart(categoryCtx, {
                        type: 'doughnut',
                        data: {
                            labels: categories,
                            datasets: [{
                                data: amounts,
                                backgroundColor: backgroundColors.slice(0, categories.length),
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: {
                                        font: { size: 12 },
                                        padding: 10,
                                        usePointStyle: true,
                                        pointStyle: 'circle'
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.raw || 0;
                                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                            const percentage = Math.round((value / total) * 100);
                                            return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                                        }
                                    }
                                }
                            },
                            cutout: '70%',
                            radius: '90%'
                        }
                    });
                }
            }
        }

        // Graphique revenus vs dépenses par mois (barres)
        if (monthlyCtx) {
            destroyChartIfExists('monthlyChart');

            if (!showMonthly) {
                if (cardMonthly) cardMonthly.style.display = 'none';
            } else {
                if (cardMonthly) cardMonthly.style.display = '';

                // Pour le graphique mensuel, utiliser last_6_months par défaut si current_month est sélectionné
                let monthlyDateParams = dateParams;
                if (selectedDateRange === 'current_month' || selectedDateRange === 'last_month') {
                    monthlyDateParams = avecFiltres('date_range=last_6_months');
                }

                let monthlyReportData = null;
                try {
                    const response = await fetch(`${API_BASE_URL}/data?report_type=income_vs_expenses&${monthlyDateParams}`, {
                        headers: { 'Accept': 'application/json', 'X-CSRFToken': getCSRFToken() }
                    });
                    if (response.ok) {
                        monthlyReportData = await response.json();
                    }
                } catch (e) {
                    console.warn('Impossible de charger les données mensuelles:', e);
                }

                const periods = monthlyReportData?.data?.periods || [];
                const expenses = monthlyReportData?.data?.expenses || [];
                const income = monthlyReportData?.data?.income || [];

                if (periods.length === 0 || (expenses.every(v => v === 0) && income.every(v => v === 0))) {
                    const parent = monthlyCtx.parentElement;
                    if (parent) {
                        monthlyCtx.style.display = 'none';
                        let emptyMsg = parent.querySelector('.empty-chart-msg');
                        if (!emptyMsg) {
                            emptyMsg = document.createElement('div');
                            emptyMsg.className = 'empty-chart-msg flex items-center justify-center h-full text-gray-400 dark:text-gray-500';
                            emptyMsg.innerHTML = '<div class="text-center"><i class="fas fa-chart-bar text-4xl mb-2"></i><p>Aucune transaction sur cette période</p></div>';
                            parent.appendChild(emptyMsg);
                        }
                    }
                } else {
                    monthlyCtx.style.display = '';
                    const emptyMsg = monthlyCtx.parentElement?.querySelector('.empty-chart-msg');
                    if (emptyMsg) emptyMsg.remove();

                    charts.monthlyChart = new Chart(monthlyCtx, {
                        type: 'bar',
                        data: {
                            labels: periods,
                            datasets: [
                                {
                                    label: 'Revenus',
                                    data: income,
                                    backgroundColor: '#10B981',
                                    borderRadius: 4
                                },
                                {
                                    label: 'Dépenses',
                                    data: expenses,
                                    backgroundColor: '#EF4444',
                                    borderRadius: 4
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'top'
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            return `${context.dataset.label}: ${formatCurrency(context.raw)}`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false }
                                },
                                y: {
                                    border: { display: false },
                                    ticks: {
                                        callback: function(value) {
                                            return formatCurrency(value, true);
                                        }
                                    }
                                }
                            }
                        }
                    });
                }
            }
        }
    }
    
    // Détruire un graphique s'il existe
    function destroyChartIfExists(chartId) {
        if (charts[chartId]) {
            charts[chartId].destroy();
            delete charts[chartId];
        }
    }
    
    // Formater les montants
    // ---- Filtres d'analyse : une ou plusieurs catégories, libellé ---------

    const filtreCategories = new Set(); // id de catégorie ou 'none'
    let categoriesDisponibles = [];
    const champLibelle = document.getElementById('filtre-libelle');

    function filtresParams() {
        const params = new URLSearchParams();
        if (filtreCategories.size) params.set('categories', [...filtreCategories].join(','));
        const libelle = champLibelle?.value.trim();
        if (libelle) params.set('search', libelle);
        return params.toString();
    }

    function avecFiltres(params) {
        const filtres = filtresParams();
        return filtres ? `${params}&${filtres}` : params;
    }

    // Les liens vers la page Transactions gardent le filtre de libellé
    function ajouterLibelle(params) {
        const libelle = champLibelle?.value.trim();
        if (libelle && !params.has('search')) params.set('search', libelle);
        return params;
    }

    function nomCategorie(id) {
        if (id === 'none') return 'Sans catégorie';
        return categoriesDisponibles.find(c => String(c.id) === id)?.name || `#${id}`;
    }

    function majResumeFiltres() {
        const n = filtreCategories.size;
        const resume = document.getElementById('filtre-categories-resume');
        if (resume) {
            resume.textContent = n === 0 ? 'Toutes les catégories'
                : (n === 1 ? nomCategorie([...filtreCategories][0]) : `${n} catégories`);
        }
        ecrire('filtre-categories-nombre', n ? `${n} sélectionnée${n > 1 ? 's' : ''}` : '');
        const morceaux = [];
        if (n) morceaux.push(`${n > 1 ? 'catégories' : 'catégorie'} ${[...filtreCategories].map(id => `« ${escapeHtml(nomCategorie(id))} »`).join(', ')}`);
        const libelle = champLibelle?.value.trim();
        if (libelle) morceaux.push(`libellé contenant « ${escapeHtml(libelle)} »`);
        const actifs = document.getElementById('filtres-actifs');
        if (actifs) {
            actifs.classList.toggle('hidden', !morceaux.length);
            actifs.innerHTML = morceaux.length
                ? `<i class="fas fa-filter mr-1"></i>Analyse limitée : ${morceaux.join(' · ')}.` +
                  (libelle ? ' Les budgets ne suivent que le filtre de catégories.' : '')
                : '';
        }
    }

    // Recalcule la page peu après le dernier changement (cases cochées, frappe)
    let minuterieFiltres = null;
    function appliquerFiltresPlusTard(delai = 500) {
        clearTimeout(minuterieFiltres);
        minuterieFiltres = setTimeout(() => initCharts(), delai);
    }

    function afficherListeCategories() {
        const liste = document.getElementById('filtre-categories-liste');
        if (!liste) return;
        const recherche = (document.getElementById('filtre-categories-cherche')?.value || '').trim().toLowerCase();
        const groupes = [
            ['Dépenses', categoriesDisponibles.filter(c => c.type !== 'income')],
            ['Revenus', categoriesDisponibles.filter(c => c.type === 'income')],
        ];
        const caseCategorie = (id, nom) => `
            <label class="flex items-center gap-2 px-1 py-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer text-gray-800 dark:text-gray-200">
                <input type="checkbox" value="${escapeHtml(id)}" ${filtreCategories.has(String(id)) ? 'checked' : ''}
                       class="filtre-categorie rounded border-gray-300 dark:border-gray-600">
                <span class="break-words">${escapeHtml(nom)}</span>
            </label>`;
        let html = '';
        if (!recherche || 'sans catégorie'.includes(recherche)) html += caseCategorie('none', 'Sans catégorie');
        for (const [titre, cats] of groupes) {
            const visibles = cats.filter(c => !recherche || c.name.toLowerCase().includes(recherche))
                .sort((a, b) => a.name.localeCompare(b.name, 'fr'));
            if (!visibles.length) continue;
            html += `<p class="mt-2 px-1 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">${titre}</p>`;
            html += visibles.map(c => caseCategorie(c.id, c.name)).join('');
        }
        liste.innerHTML = html || '<p class="px-1 text-gray-500 dark:text-gray-400">Aucune catégorie trouvée</p>';
    }

    function reinitialiserFiltresAnalyse() {
        filtreCategories.clear();
        if (champLibelle) champLibelle.value = '';
        afficherListeCategories();
        majResumeFiltres();
    }

    async function initFiltresAnalyse() {
        const bouton = document.getElementById('filtre-categories-bouton');
        const panneau = document.getElementById('filtre-categories-panneau');
        if (!bouton || !panneau) return;
        try {
            const response = await fetch('/api/v1/categories', { headers: { 'Accept': 'application/json' } });
            const data = await response.json();
            categoriesDisponibles = data.categories || [];
        } catch (e) {
            console.warn('Impossible de charger les catégories:', e);
        }
        afficherListeCategories();

        const ouvrir = (ouvert) => {
            panneau.classList.toggle('hidden', !ouvert);
            bouton.setAttribute('aria-expanded', String(ouvert));
            if (ouvert) document.getElementById('filtre-categories-cherche')?.focus();
        };
        bouton.addEventListener('click', () => ouvrir(panneau.classList.contains('hidden')));
        document.addEventListener('click', (e) => {
            if (!panneau.contains(e.target) && !bouton.contains(e.target)) ouvrir(false);
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !panneau.classList.contains('hidden')) { ouvrir(false); bouton.focus(); }
        });
        document.getElementById('filtre-categories-cherche')?.addEventListener('input', afficherListeCategories);
        panneau.addEventListener('change', (e) => {
            if (!e.target.classList.contains('filtre-categorie')) return;
            if (e.target.checked) filtreCategories.add(e.target.value);
            else filtreCategories.delete(e.target.value);
            majResumeFiltres();
            appliquerFiltresPlusTard();
        });
        document.getElementById('filtre-categories-aucune')?.addEventListener('click', () => {
            filtreCategories.clear();
            afficherListeCategories();
            majResumeFiltres();
            appliquerFiltresPlusTard(0);
        });
        champLibelle?.addEventListener('input', () => { majResumeFiltres(); appliquerFiltresPlusTard(700); });
        champLibelle?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); appliquerFiltresPlusTard(0); }
        });
    }
    initFiltresAnalyse();

    // ---- Indicateurs clés et détail par catégorie ------------------------

    const euros = (v) => new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(v);
    // 2026-06-30 -> 30/06/2026 (format attendu par la page Transactions)
    const dateFr = (iso) => iso.split('-').reverse().join('/');

    /**
     * Évolution par rapport à la période précédente. Pour une dépense, une
     * hausse est en rouge ; pour un revenu (inverse=true), en vert.
     */
    function badgeEvolution(evolution, inverse = false) {
        if (evolution === null || evolution === undefined) {
            return '<span class="text-gray-400 dark:text-gray-500">—</span>';
        }
        if (evolution === 0) return '<span class="text-gray-500 dark:text-gray-400">=</span>';
        const hausse = evolution > 0;
        const mauvais = inverse ? !hausse : hausse;
        const couleur = mauvais ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400';
        const fleche = hausse ? 'fa-arrow-up' : 'fa-arrow-down';
        const signe = hausse ? '+' : '';
        return `<span class="${couleur} whitespace-nowrap"><i class="fas ${fleche} mr-1"></i>${signe}${evolution.toLocaleString('fr-FR')} %</span>`;
    }

    function ecrire(id, html) {
        const el = document.getElementById(id);
        if (el) el.innerHTML = html;
    }

    function afficherIndicateurs(ind, periode) {
        const vsPrec = (valeur) => `Période préc. : ${euros(valeur)}`;
        ecrire('kpi-depenses', euros(ind.depenses));
        ecrire('kpi-depenses-detail', `${badgeEvolution(ind.evolution_depenses)} · ${vsPrec(ind.depenses_precedent)}`);
        ecrire('kpi-revenus', euros(ind.revenus));
        ecrire('kpi-revenus-detail', `${badgeEvolution(ind.evolution_revenus, true)} · ${vsPrec(ind.revenus_precedent)}`);

        if (ind.taux_epargne === null) {
            ecrire('kpi-epargne', '—');
            ecrire('kpi-epargne-detail', 'Aucun revenu sur la période');
        } else {
            const couleur = ind.taux_epargne < 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400';
            ecrire('kpi-epargne', `<span class="${couleur}">${ind.taux_epargne.toLocaleString('fr-FR')} %</span>`);
            ecrire('kpi-epargne-detail', `Solde : ${euros(ind.solde)}`);
        }

        ecrire('kpi-moyenne', euros(ind.depense_moyenne_jour));
        ecrire('kpi-moyenne-detail', `Sur ${ind.jours} jour${ind.jours > 1 ? 's' : ''}`);

        const max = ind.plus_grosse_depense;
        ecrire('kpi-max', max ? euros(max.montant) : '—');
        ecrire('kpi-max-detail', max ? `${escapeHtml(max.libelle)} · ${dateFr(max.date)}` : 'Aucune dépense');

        ecrire('kpi-classer', String(ind.sans_categorie));
        const lien = document.getElementById('kpi-classer-lien');
        if (lien) {
            lien.href = `/transactions/?category=none&date_from=${dateFr(periode.debut)}&date_to=${dateFr(periode.fin)}`;
        }
    }

    function afficherDetailCategories(categories, periode, precedente) {
        ecrire('detail-comparaison',
            `Du ${dateFr(periode.debut)} au ${dateFr(periode.fin)}, comparé au ${dateFr(precedente.debut)} – ${dateFr(precedente.fin)}. ` +
            'Cliquez sur une catégorie pour voir ses transactions.');
        const tbody = document.getElementById('detail-categories-body');
        if (!tbody) return;
        if (!categories.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="px-4 py-6 text-center text-gray-500 dark:text-gray-400">Aucune dépense sur cette période ni sur la précédente</td></tr>';
            return;
        }
        const cellule = 'px-4 py-3 text-sm whitespace-nowrap';
        tbody.innerHTML = categories.map((c) => {
            const filtre = ajouterLibelle(new URLSearchParams({
                category: c.id === null ? 'none' : c.id,
                type: 'expense',
                date_from: dateFr(periode.debut),
                date_to: dateFr(periode.fin),
            }));
            const couleur = escapeHtml(c.couleur || '#9CA3AF');
            return `
                <tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td class="px-4 py-3 text-sm">
                        <a href="/transactions/?${filtre}" class="flex items-center gap-2 text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400">
                            <span class="inline-block w-3 h-3 rounded-full flex-shrink-0" style="background-color: ${couleur}"></span>
                            <span class="break-words">${escapeHtml(c.nom)}</span>
                        </a>
                    </td>
                    <td class="${cellule} text-right font-medium text-gray-900 dark:text-gray-100">${euros(c.montant)}</td>
                    <td class="${cellule}">
                        <div class="flex items-center gap-2">
                            <div class="w-20 h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                                <div class="h-2 rounded-full" style="width: ${Math.min(c.pourcentage, 100)}%; background-color: ${couleur}"></div>
                            </div>
                            <span class="text-gray-700 dark:text-gray-300">${c.pourcentage.toLocaleString('fr-FR')} %</span>
                        </div>
                    </td>
                    <td class="${cellule} text-right text-gray-700 dark:text-gray-300">${c.nombre}</td>
                    <td class="${cellule} text-right text-gray-700 dark:text-gray-300">${c.nombre ? euros(c.moyenne) : '—'}</td>
                    <td class="${cellule} text-right text-gray-500 dark:text-gray-400">${euros(c.montant_precedent)}</td>
                    <td class="${cellule} text-right">${badgeEvolution(c.evolution)}</td>
                </tr>`;
        }).join('');
    }

    // Couleurs distinctes par rang (les catégories ont souvent la même couleur)
    const PALETTE = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];
    const NB_SERIES_GRAPHIQUE = PALETTE.length;
    const COULEUR_AUTRES = '#9CA3AF';
    const NOMS_MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
    const libelleMois = (aaaaMm) => {
        const [annee, mois] = aaaaMm.split('-');
        return `${NOMS_MOIS[parseInt(mois, 10) - 1]} ${annee.slice(2)}`;
    };
    // Dernier jour d'un mois "2026-06" -> "30/06/2026"
    const finMois = (aaaaMm) => {
        const [annee, mois] = aaaaMm.split('-').map(Number);
        const jour = new Date(annee, mois, 0).getDate();
        return `${String(jour).padStart(2, '0')}/${String(mois).padStart(2, '0')}/${annee}`;
    };

    async function lireAnalyse(route, dateParams) {
        const response = await fetch(`${API_BASE_URL}/${route}?${dateParams}`, {
            headers: { 'Accept': 'application/json' }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || `HTTP ${response.status}`);
        return data;
    }

    function messageLigne(id, colonnes, texte, erreur = false) {
        const classe = erreur ? 'text-red-500' : 'text-gray-500 dark:text-gray-400';
        ecrire(id, `<tr><td colspan="${colonnes}" class="px-4 py-6 text-center ${classe}">${texte}</td></tr>`);
    }

    async function chargerEvolution(dateParams) {
        try {
            const data = await lireAnalyse('evolution', dateParams);
            afficherEvolution(data);
        } catch (error) {
            console.error('Erreur évolution mensuelle:', error);
            messageLigne('evolution-body', 1, `Impossible de charger l'évolution : ${escapeHtml(error.message)}`, true);
        }
    }

    function afficherEvolution(data) {
        const { mois, series, totaux_mois: totaux } = data;
        ecrire('evolution-sous-titre', (data.elargie
            ? `Les ${mois.length} derniers mois (la période choisie couvre moins de 2 mois).`
            : `Du ${libelleMois(mois[0])} au ${libelleMois(mois[mois.length - 1])}.`) +
            ` * Moyenne sur ${data.mois_moyenne} mois terminé${data.mois_moyenne > 1 ? 's' : ''}. Cliquez sur un montant pour voir les transactions.`);

        destroyChartIfExists('evolutionChart');
        const canvas = document.getElementById('evolutionChart');
        if (!series.length) {
            ecrire('evolution-entete', '');
            messageLigne('evolution-body', 1, 'Aucune dépense sur ces mois');
            if (canvas) canvas.style.display = 'none';
            return;
        }
        if (canvas) canvas.style.display = '';

        // Graphique : les plus grosses catégories, le reste regroupé
        const principales = series.slice(0, NB_SERIES_GRAPHIQUE);
        const autres = series.slice(NB_SERIES_GRAPHIQUE);
        const jeux = principales.map((serie, i) => ({
            label: serie.nom,
            data: serie.valeurs,
            backgroundColor: PALETTE[i],
            stack: 'depenses',
        }));
        if (autres.length) {
            jeux.push({
                label: `Autres (${autres.length})`,
                data: mois.map((_, i) => autres.reduce((somme, s) => somme + s.valeurs[i], 0)),
                backgroundColor: COULEUR_AUTRES,
                stack: 'depenses',
            });
        }
        if (canvas) {
            charts.evolutionChart = new Chart(canvas, {
                type: 'bar',
                data: { labels: mois.map(libelleMois), datasets: jeux },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { stacked: true, grid: { display: false } },
                        y: { stacked: true, ticks: { callback: (v) => formatCurrency(v, true) } },
                    },
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, pointStyle: 'circle', padding: 10 } },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.dataset.label} : ${euros(ctx.raw)}`,
                                footer: (items) => `Total du mois : ${euros(totaux[items[0].dataIndex])}`,
                            },
                        },
                    },
                },
            });
        }

        // Tableau croisé : catégories en lignes, mois en colonnes
        const th = 'px-3 py-2 text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider whitespace-nowrap';
        ecrire('evolution-entete', `<tr>
            <th scope="col" class="${th} text-left sticky left-0 bg-gray-50 dark:bg-gray-700">Catégorie</th>
            ${mois.map(m => `<th scope="col" class="${th} text-right">${libelleMois(m)}</th>`).join('')}
            <th scope="col" class="${th} text-right">Total</th>
            <th scope="col" class="${th} text-right" title="Sur les mois terminés">Moyenne / mois*</th>
        </tr>`);
        const td = 'px-3 py-2 text-right whitespace-nowrap';
        const montant = (v) => (v ? euros(v) : '<span class="text-gray-300 dark:text-gray-600">—</span>');
        const lignes = series.map((serie, i) => {
            const couleur = i < NB_SERIES_GRAPHIQUE ? PALETTE[i] : COULEUR_AUTRES;
            const cellules = serie.valeurs.map((v, j) => {
                if (!v) return `<td class="${td}">${montant(v)}</td>`;
                const filtre = ajouterLibelle(new URLSearchParams({
                    category: serie.id === null ? 'none' : serie.id,
                    type: 'expense',
                    date_from: `01/${mois[j].split('-')[1]}/${mois[j].split('-')[0]}`,
                    date_to: finMois(mois[j]),
                }));
                return `<td class="${td}"><a href="/transactions/?${filtre}" class="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">${euros(v)}</a></td>`;
            }).join('');
            return `<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td class="px-3 py-2 text-gray-900 dark:text-gray-100 sticky left-0 bg-white dark:bg-gray-800 min-w-[10rem]">
                    <span class="flex items-center gap-2">
                        <span class="inline-block w-3 h-3 rounded-full flex-shrink-0" style="background-color: ${couleur}"></span>
                        <span class="break-words">${escapeHtml(serie.nom)}</span>
                    </span>
                </td>
                ${cellules}
                <td class="${td} font-medium text-gray-900 dark:text-gray-100">${euros(serie.total)}</td>
                <td class="${td} text-gray-700 dark:text-gray-300">${euros(serie.moyenne)}</td>
            </tr>`;
        });
        const totalGeneral = totaux.reduce((a, b) => a + b, 0);
        lignes.push(`<tr class="bg-gray-50 dark:bg-gray-700 font-semibold text-gray-900 dark:text-gray-100">
            <td class="px-3 py-2 sticky left-0 bg-gray-50 dark:bg-gray-700">Total</td>
            ${totaux.map(v => `<td class="${td}">${montant(v)}</td>`).join('')}
            <td class="${td}">${euros(totalGeneral)}</td>
            <td class="${td}">${euros(data.moyenne_mensuelle)}</td>
        </tr>`);
        ecrire('evolution-body', lignes.join(''));
    }

    async function chargerDestinataires(dateParams) {
        try {
            const data = await lireAnalyse('destinataires', dateParams);
            ecrire('destinataires-sous-titre',
                `${data.destinataires.length} principaux sur ${data.nombre_destinataires}, d'après les libellés de la banque. ` +
                'Cliquez sur un nom pour voir ses transactions.');
            if (!data.destinataires.length) {
                messageLigne('destinataires-body', 5, 'Aucune dépense sur cette période');
                return;
            }
            const debut = dateFr(data.periode.debut);
            const fin = dateFr(data.periode.fin);
            const td = 'px-4 py-2 whitespace-nowrap text-right';
            ecrire('destinataires-body', data.destinataires.map((d) => {
                const filtre = new URLSearchParams({ search: d.nom, type: 'expense', date_from: debut, date_to: fin });
                return `<tr class="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td class="px-4 py-2"><a href="/transactions/?${filtre}" class="break-words text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400">${escapeHtml(d.nom)}</a></td>
                    <td class="${td} font-medium text-gray-900 dark:text-gray-100">${euros(d.montant)}</td>
                    <td class="${td} text-gray-700 dark:text-gray-300">${d.pourcentage.toLocaleString('fr-FR')} %</td>
                    <td class="${td} text-gray-700 dark:text-gray-300">${d.nombre}</td>
                    <td class="${td} text-gray-500 dark:text-gray-400">${d.derniere ? dateFr(d.derniere) : '—'}</td>
                </tr>`;
            }).join(''));
        } catch (error) {
            console.error('Erreur destinataires:', error);
            messageLigne('destinataires-body', 5, `Impossible de charger les destinataires : ${escapeHtml(error.message)}`, true);
        }
    }

    async function chargerBudgets(dateParams) {
        try {
            const { budgets } = await lireAnalyse('budgets', dateParams);
            if (!budgets.length) {
                ecrire('budgets-sous-titre', '');
                ecrire('budgets-body', `<p class="text-center text-gray-500 dark:text-gray-400">Aucun budget sur cette période.
                    <a href="/budgets/" class="text-blue-600 dark:text-blue-400 hover:underline">Créer un budget</a></p>`);
                return;
            }
            ecrire('budgets-sous-titre', 'Prévu et dépensé, période par période. Les mois d\'avant la création du budget sont indicatifs.');
            ecrire('budgets-body', budgets.map(afficherBudget).join(''));
        } catch (error) {
            console.error('Erreur suivi des budgets:', error);
            ecrire('budgets-body', `<p class="text-center text-red-500">Impossible de charger les budgets : ${escapeHtml(error.message)}</p>`);
        }
    }

    function afficherBudget(b) {
        const bilan = b.periodes_terminees
            ? (b.depassements
                ? `<span class="text-red-600 dark:text-red-400">Dépassé ${b.depassements} fois sur ${b.periodes_terminees}</span>`
                : `<span class="text-green-600 dark:text-green-400">Respecté sur ${b.periodes_terminees} période${b.periodes_terminees > 1 ? 's' : ''}</span>`)
            : '<span class="text-gray-500 dark:text-gray-400">Aucune période terminée</span>';
        const lignes = b.periodes.map((p) => {
            const largeur = Math.min(p.pourcentage, 100);
            let couleur = p.depasse ? 'bg-red-500' : (p.pourcentage >= 90 ? 'bg-yellow-500' : 'bg-green-500');
            if (p.avant_debut) couleur = 'bg-gray-400 dark:bg-gray-500';
            const etiquette = p.en_cours ? ' <span class="text-xs text-blue-600 dark:text-blue-400">(en cours)</span>'
                : (p.avant_debut ? ' <span class="text-xs text-gray-400">(avant création)</span>' : '');
            const ecart = p.ecart >= 0
                ? `<span class="text-green-600 dark:text-green-400">reste ${euros(p.ecart)}</span>`
                : `<span class="text-red-600 dark:text-red-400">dépassé de ${euros(-p.ecart)}</span>`;
            return `<div>
                <div class="flex justify-between gap-2 text-xs text-gray-700 dark:text-gray-300">
                    <span>${escapeHtml(p.label)}${etiquette}</span>
                    <span class="whitespace-nowrap">${euros(p.depense)} / ${euros(p.prevu)} · ${ecart}</span>
                </div>
                <div class="mt-1 h-2 rounded-full bg-gray-200 dark:bg-gray-600">
                    <div class="h-2 rounded-full ${couleur}" style="width: ${largeur}%"></div>
                </div>
            </div>`;
        }).join('');
        const typePeriode = { monthly: 'mensuel', yearly: 'annuel' }[b.periode] || 'personnalisé';
        return `<div class="rounded-md border border-gray-200 dark:border-gray-700 p-3">
            <div class="flex flex-wrap justify-between gap-2">
                <p class="font-medium text-gray-900 dark:text-gray-100">${escapeHtml(b.categorie)}
                    <span class="text-sm font-normal text-gray-500 dark:text-gray-400">· ${euros(b.montant)} ${typePeriode}</span></p>
                <p class="text-sm">${bilan}</p>
            </div>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">Depuis sa création, sur la période : ${euros(b.total_depense)} dépensés pour ${euros(b.total_prevu)} prévus</p>
            <div class="mt-3 space-y-2">${lignes}</div>
        </div>`;
    }

    async function chargerDetail(dateParams) {
        try {
            const response = await fetch(`${API_BASE_URL}/detail?${dateParams}`, {
                headers: { 'Accept': 'application/json' }
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || `HTTP ${response.status}`);
            afficherIndicateurs(data.indicateurs, data.periode);
            afficherDetailCategories(data.categories, data.periode, data.periode_precedente);
        } catch (error) {
            console.error('Erreur lors du chargement du détail:', error);
            ecrire('detail-categories-body',
                `<tr><td colspan="7" class="px-4 py-6 text-center text-red-500">Impossible de charger le détail : ${escapeHtml(error.message)}</td></tr>`);
        }
    }

    function formatCurrency(amount, short = false) {
        if (amount >= 1000 && short) {
            return (amount / 1000).toFixed(1) + 'k €';
        }
        return new Intl.NumberFormat('fr-FR', { 
            style: 'currency', 
            currency: 'EUR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    }
    
    // Générer un aperçu du rapport
    
    // Echappement HTML pour eviter les XSS
    
    // Fonction pour afficher/masquer la modal de création de rapport
    function openReportModal() {
        createReportModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        // Réinitialiser le formulaire
        if (reportForm) reportForm.reset();
        // Réinitialiser l'aperçu
        if (reportPreview) reportPreview.innerHTML = '';
    }
    
    function closeReportModal() {
        createReportModal.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }
    
    // Fonction pour charger la liste des rapports sauvegardés
    async function loadSavedReports() {
        if (!reportsList) return;

        try {
            const response = await fetch(API_BASE_URL);
            if (!response.ok) throw new Error('Erreur lors du chargement des rapports');

            const result = await response.json();
            const reports = result.data || [];

            // Vider la liste
            reportsList.innerHTML = '';

            if (reports.length === 0) {
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="5" class="px-6 py-4 text-center text-gray-500 dark:text-gray-400">Aucun rapport enregistré pour le moment.</td>`;
                reportsList.appendChild(row);
                return;
            }

            // Ajouter chaque rapport à la liste
            reports.forEach(report => {
                const row = document.createElement('tr');
                row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';
                row.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(report.name)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${escapeHtml(getReportTypeLabel(report.type))}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${escapeHtml(formatDate(report.created_at))}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-300">${escapeHtml(formatDate(report.updated_at))}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2"></td>
                `;

                const actionsCell = row.querySelector('td:last-child');

                const viewButton = document.createElement('button');
                viewButton.className = 'text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 p-1';
                viewButton.title = 'Voir le rapport';
                viewButton.innerHTML = '<i class="fas fa-eye"></i>';
                viewButton.addEventListener('click', () => viewReport(report.id));

                const downloadContainer = document.createElement('div');
                downloadContainer.className = 'relative inline-block';
                downloadContainer.innerHTML = `
                    <button class="text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300 p-1 download-toggle" title="Télécharger">
                        <i class="fas fa-download"></i><i class="fas fa-caret-down text-xs ml-0.5"></i>
                    </button>
                    <div class="download-menu hidden absolute right-0 bottom-full mb-1 w-48 rounded-md shadow-lg bg-white dark:bg-gray-700 ring-1 ring-black ring-opacity-5 z-50">
                        <button data-format="pdf" class="dl-opt w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 flex items-center">
                            <i class="fas fa-file-pdf text-red-500 w-4 mr-2"></i>PDF
                        </button>
                        <button data-format="pdf-charts" class="dl-opt w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 flex items-center">
                            <i class="fas fa-chart-pie text-red-400 w-4 mr-2"></i>PDF + graphiques
                        </button>
                        <button data-format="excel" class="dl-opt w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 flex items-center">
                            <i class="fas fa-file-excel text-green-500 w-4 mr-2"></i>Excel
                        </button>
                        <button data-format="excel-charts" class="dl-opt w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 flex items-center">
                            <i class="fas fa-chart-bar text-green-400 w-4 mr-2"></i>Excel + graphiques
                        </button>
                        <button data-format="csv" class="dl-opt w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 flex items-center">
                            <i class="fas fa-file-csv text-blue-500 w-4 mr-2"></i>CSV
                        </button>
                        <button data-format="json" class="dl-opt w-full text-left px-3 py-1.5 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 flex items-center">
                            <i class="fas fa-file-code text-yellow-500 w-4 mr-2"></i>JSON
                        </button>
                    </div>
                `;
                const toggleBtn = downloadContainer.querySelector('.download-toggle');
                const menu = downloadContainer.querySelector('.download-menu');
                toggleBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    document.querySelectorAll('.download-menu').forEach(m => { if (m !== menu) m.classList.add('hidden'); });
                    menu.classList.toggle('hidden');
                });
                downloadContainer.querySelectorAll('.dl-opt').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        menu.classList.add('hidden');
                        const fmt = btn.dataset.format;
                        if (fmt === 'pdf-charts') {
                            downloadReport(report.id, 'pdf', true);
                        } else if (fmt === 'excel-charts') {
                            downloadReport(report.id, 'excel', true);
                        } else {
                            downloadReport(report.id, fmt);
                        }
                    });
                });

                const deleteButton = document.createElement('button');
                deleteButton.className = 'text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 p-1';
                deleteButton.title = 'Supprimer';
                deleteButton.innerHTML = '<i class="fas fa-trash"></i>';
                deleteButton.addEventListener('click', () => deleteReport(report.id));

                actionsCell.appendChild(viewButton);
                actionsCell.appendChild(downloadContainer);
                actionsCell.appendChild(deleteButton);

                reportsList.appendChild(row);
            });

        } catch (error) {
            console.error('Erreur:', error);
        }
    }
    
    // Normaliser le type de rapport (tirets → underscores pour les comparaisons JS)
    function normalizeReportType(type) {
        if (!type) return 'expenses';
        return type.replace(/-/g, '_');
    }

    // Obtenir le libellé du type de rapport
    function getReportTypeLabel(type) {
        const normalized = normalizeReportType(type);
        const types = {
            'expenses': 'Dépenses par catégorie',
            'expenses_by_category': 'Dépenses par catégorie',
            'monthly_summary': 'Résumé mensuel',
            'income_vs_expenses': 'Revenus vs Dépenses',
            'cashflow': 'Flux de trésorerie',
            'custom': 'Personnalisé'
        };
        return types[normalized] || type;
    }
    
    // Formater une date
    function formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // Afficher un rapport
    async function viewReport(reportId) {
        try {
            showAlert('Chargement du rapport...', 'info');
            
            const response = await fetch(`${API_BASE_URL}/${reportId}`, {
                headers: {
                    'Accept': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Erreur lors du chargement du rapport');
            }
            
            const report = await response.json();
            
            // Mettre à jour l'interface avec les données du rapport
            updateReportView(report);
            
            // Faire défiler vers la section d'aperçu
            document.getElementById('report-preview-section')?.scrollIntoView({ behavior: 'smooth' });
            
        } catch (error) {
            console.error('Erreur:', error);
            showAlert(error.message || 'Erreur lors du chargement du rapport', 'error');
        }
    }
    
    // Mettre à jour la vue avec les données du rapport
    function updateReportView(report) {
        if (!reportPreview) return;
        
        // Afficher les données du rapport
        reportPreview.innerHTML = `
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <div class="flex justify-between items-start mb-4">
                    <div>
                        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">${escapeHtml(report.name)}</h3>
                        <p class="text-sm text-gray-500 dark:text-gray-400">
                            ${escapeHtml(getReportTypeLabel(report.type))} • ${escapeHtml(formatDate(report.created_at))}
                        </p>
                    </div>
                    <div class="flex flex-wrap gap-1">
                        <button onclick="downloadReport(${report.id}, 'pdf')"
                                class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
                                title="PDF">
                            <i class="fas fa-file-pdf mr-1"></i>PDF
                        </button>
                        <button onclick="downloadReport(${report.id}, 'pdf', true)"
                                class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-red-50 text-red-700 hover:bg-red-100 dark:bg-red-900/30 dark:text-red-300 dark:hover:bg-red-900/50"
                                title="PDF avec graphiques">
                            <i class="fas fa-chart-pie mr-1"></i>PDF+Graph
                        </button>
                        <button onclick="downloadReport(${report.id}, 'excel')"
                                class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/30 dark:text-green-300 dark:hover:bg-green-900/50"
                                title="Excel">
                            <i class="fas fa-file-excel mr-1"></i>Excel
                        </button>
                        <button onclick="downloadReport(${report.id}, 'csv')"
                                class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-300 dark:hover:bg-blue-900/50"
                                title="CSV">
                            <i class="fas fa-file-csv mr-1"></i>CSV
                        </button>
                        <button onclick="downloadReport(${report.id}, 'json')"
                                class="inline-flex items-center px-2 py-1 text-xs font-medium rounded bg-yellow-50 text-yellow-700 hover:bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-300 dark:hover:bg-yellow-900/50"
                                title="JSON">
                            <i class="fas fa-file-code mr-1"></i>JSON
                        </button>
                    </div>
                </div>
                
                <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h4 class="text-md font-medium mb-3 text-gray-700 dark:text-gray-300">Résumé</h4>
                        <div id="report-summary" class="space-y-2">
                            <!-- Les données du rapport seront insérées ici dynamiquement -->
                        </div>
                    </div>
                    <div>
                        <h4 class="text-md font-medium mb-3 text-gray-700 dark:text-gray-300">Graphique</h4>
                        <div class="h-64">
                            <canvas id="report-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="mt-6">
                    <h4 class="text-md font-medium mb-3 text-gray-700 dark:text-gray-300">Détails</h4>
                    <div id="report-details" class="overflow-x-auto">
                        <!-- Les données détaillées seront insérées ici dynamiquement -->
                    </div>
                </div>
            </div>
        `;
        
        // Mettre à jour les données du rapport
        updateReportData(report);
    }
    
    // Mettre à jour les données du rapport dans l'interface
    function updateReportData(report) {
        if (!report || !report.data) return;
        const rtype = normalizeReportType(report.type);

        // Mettre à jour le résumé
        const summaryElement = document.getElementById('report-summary');
        if (summaryElement) {
            // Personnaliser en fonction du type de rapport
            if (rtype === 'expenses_by_category' || rtype === 'expenses') {
                const items = report.data.items || report.data;
                const total = report.data.total || items.reduce((sum, item) => sum + (parseFloat(item.amount) || 0), 0);
                summaryElement.innerHTML = `
                    <p>Total des dépenses: <span class="font-semibold">${formatCurrency(total)}</span></p>
                    <p>Nombre de catégories: <span class="font-semibold">${items.length}</span></p>
                    <p>Période: <span class="font-semibold">${formatDate(report.parameters?.start_date)} - ${formatDate(report.parameters?.end_date) || 'Aujourd\'hui'}</span></p>
                `;
            } else if (rtype === 'income_vs_expenses') {
                const income = parseFloat(report.data.total_income) || 0;
                const expenses = parseFloat(report.data.total_expenses) || 0;
                const savings = income - expenses;
                
                summaryElement.innerHTML = `
                    <p>Revenus: <span class="font-semibold text-green-600 dark:text-green-400">${formatCurrency(income)}</span></p>
                    <p>Dépenses: <span class="font-semibold text-red-600 dark:text-red-400">-${formatCurrency(expenses)}</span></p>
                    <p>Économies: <span class="font-semibold ${savings >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">${formatCurrency(savings)}</span></p>
                `;
            }
        }
        
        // Mettre à jour le graphique
        updateReportChart(report);
        
        // Mettre à jour les détails
        const detailsElement = document.getElementById('report-details');
        if (detailsElement) {
            if (rtype === 'expenses_by_category' || rtype === 'expenses') {
                const detailItems = report.data.items || report.data;
                detailsElement.innerHTML = `
                    <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead class="bg-gray-50 dark:bg-gray-700">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Catégorie</th>
                                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Montant</th>
                                <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Pourcentage</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                            ${detailItems.map(item => `
                                <tr>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(item.category)}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-300">${formatCurrency(item.amount)}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-500 dark:text-gray-300">${escapeHtml(String(item.percentage))}%</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                `;
            } else if (rtype === 'income_vs_expenses') {
                const totalInc = report.data.total_income || 0;
                const totalExp = report.data.total_expenses || 0;
                detailsElement.innerHTML = `
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div class="bg-green-50 dark:bg-green-900/30 p-4 rounded-lg">
                            <h5 class="text-sm font-medium text-green-800 dark:text-green-200">Revenus</h5>
                            <p class="text-2xl font-bold text-green-600 dark:text-green-400">${formatCurrency(totalInc)}</p>
                        </div>
                        <div class="bg-red-50 dark:bg-red-900/30 p-4 rounded-lg">
                            <h5 class="text-sm font-medium text-red-800 dark:text-red-200">Dépenses</h5>
                            <p class="text-2xl font-bold text-red-600 dark:text-red-400">-${formatCurrency(totalExp)}</p>
                        </div>
                        <div class="bg-blue-50 dark:bg-blue-900/30 p-4 rounded-lg">
                            <h5 class="text-sm font-medium text-blue-800 dark:text-blue-200">Économies</h5>
                            <p class="text-2xl font-bold text-blue-600 dark:text-blue-400">${formatCurrency(totalInc - totalExp)}</p>
                        </div>
                    </div>
                `;
            }
        }
    }
    
    // Mettre à jour le graphique du rapport
    function updateReportChart(report) {
        const ctx = document.getElementById('report-chart');
        if (!ctx) return;
        const rtype = normalizeReportType(report.type);

        // Détruire le graphique existant s'il y en a un
        if (charts.reportChart) {
            charts.reportChart.destroy();
        }

        let chartConfig = {};

        // Configurer le graphique en fonction du type de rapport
        if ((rtype === 'expenses_by_category' || rtype === 'expenses') && report.data) {
            const items = report.data.items || report.data;
            const labels = items.map(item => item.category);
            const data = items.map(item => item.amount);
            const backgroundColors = [
                '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#6B7280',
                '#EF4444', '#F97316', '#84CC16', '#06B6D4', '#8B5CF6', '#EC4899'
            ];
            
            chartConfig = {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: backgroundColors.slice(0, data.length),
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                font: { size: 12 },
                                padding: 10,
                                usePointStyle: true,
                                pointStyle: 'circle'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = Math.round((value / total) * 100);
                                    return `${label}: ${formatCurrency(value)} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    cutout: '70%',
                    radius: '90%'
                }
            };
        } else if (rtype === 'income_vs_expenses' && report.data) {
            const labels = ['Revenus', 'Dépenses'];
            const data = [report.data.total_income || 0, report.data.total_expenses || 0];
            const backgroundColors = ['#10B981', '#EF4444'];
            
            chartConfig = {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Montant',
                        data: data,
                        backgroundColor: backgroundColors,
                        borderWidth: 0,
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.label}: ${formatCurrency(context.raw)}`;
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return formatCurrency(value, true);
                                }
                            }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            };
        }
        
        // Créer le nouveau graphique
        if (Object.keys(chartConfig).length > 0) {
            charts.reportChart = new Chart(ctx, chartConfig);
        }
    }
    
    // Télécharger un rapport sauvegardé dans un format donné
    async function downloadReport(reportId, format = 'pdf', includeCharts = false) {
        try {
            showAlert(`Préparation du téléchargement...`, 'info');

            let reportType, dateRange, startDate, endDate;

            if (reportId) {
                // Charger les infos du rapport sauvegardé pour utiliser son type réel
                try {
                    const infoResp = await fetch(`${API_BASE_URL}/${reportId}`, {
                        headers: { 'Accept': 'application/json', 'X-CSRFToken': getCSRFToken() }
                    });
                    if (infoResp.ok) {
                        const info = await infoResp.json();
                        reportType = info.type || info.report_type || 'expenses';
                        const params = info.parameters || {};
                        dateRange = params.date_range || 'current_month';
                        startDate = params.start_date || '';
                        endDate = params.end_date || '';
                    }
                } catch (e) {
                    console.warn('Impossible de charger les infos du rapport:', e);
                }
            }

            // Fallback sur les filtres du dropdown si pas de rapport sauvegardé
            if (!reportType) {
                reportType = reportTypeSelect?.value || 'expenses';
                dateRange = dateRangePicker?.value || 'current_month';
                startDate = document.getElementById('start-date')?.value || '';
                endDate = document.getElementById('end-date')?.value || '';
            }

            const formatExtensions = {
                'pdf': 'pdf', 'excel': 'xlsx', 'csv': 'csv', 'json': 'json'
            };

            let exportUrl = `${API_BASE_URL}/export?format=${format}&report_type=${reportType}&date_range=${dateRange}`;
            if (includeCharts) exportUrl += '&include_charts=true';
            if (startDate) exportUrl += `&start_date=${startDate}`;
            if (endDate) exportUrl += `&end_date=${endDate}`;

            const response = await fetch(exportUrl, {
                headers: { 'X-CSRFToken': getCSRFToken() }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.message || 'Erreur lors de la génération du rapport');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `rapport-${reportType}-${new Date().toISOString().slice(0,10)}.${formatExtensions[format] || format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();

            showAlert('Téléchargement terminé', 'success');

        } catch (error) {
            console.error('Erreur:', error);
            showAlert(error.message || 'Erreur lors du téléchargement du rapport', 'error');
        }
    }
    // Rendre downloadReport accessible globalement (pour les onclick inline)
    window.downloadReport = downloadReport;
    
    // Supprimer un rapport
    async function deleteReport(reportId) {
        if (!confirm('Êtes-vous sûr de vouloir supprimer ce rapport ? Cette action est irréversible.')) {
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/${reportId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            });
            
            if (!response.ok) throw new Error('Erreur lors de la suppression du rapport');
            
            showAlert('Rapport supprimé avec succès', 'success');
            loadSavedReports(); // Recharger la liste des rapports
            
        } catch (error) {
            console.error('Erreur:', error);
            showAlert('Une erreur est survenue lors de la suppression du rapport', 'error');
        }
    }
    
    // Obtenir le jeton CSRF
    
    // Afficher des messages d'alerte (toast notification)
    function showAlert(message, type = 'info') {
        // Supprimer les anciens toasts
        document.querySelectorAll('.toast-alert').forEach(el => el.remove());

        const colorMap = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            info: 'bg-blue-500',
            warning: 'bg-yellow-500 text-gray-900 dark:text-white'
        };
        const bgClass = colorMap[type] || colorMap.info;

        const toast = document.createElement('div');
        toast.className = `toast-alert fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg text-white ${bgClass} transition-opacity duration-300`;
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
    // Afficher/masquer les champs de date personnalisés
    if (dateRangePicker) {
        const customDateRangeDiv = document.getElementById('custom-date-range');
        dateRangePicker.addEventListener('change', function() {
            if (customDateRangeDiv) {
                customDateRangeDiv.classList.toggle('hidden', this.value !== 'custom');
            }
            // Comme le type de rapport : la période met les graphiques à jour
            // (période personnalisée : dès que les deux dates sont saisies)
            if (this.value !== 'custom') initCharts();
        });

        ['start-date', 'end-date'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', function() {
                const start = document.getElementById('start-date')?.value;
                const end = document.getElementById('end-date')?.value;
                if (dateRangePicker.value === 'custom' && start && end) initCharts();
            });
        });
    }
    const dateRangeModalSelect = document.getElementById('date-range-modal');
    if (dateRangeModalSelect) {
        const customDateRangeModalDiv = document.getElementById('custom-date-range-modal');
        dateRangeModalSelect.addEventListener('change', function() {
            if (customDateRangeModalDiv) {
                customDateRangeModalDiv.classList.toggle('hidden', this.value !== 'custom');
            }
        });
    }

    // Événements
    if (addReportBtn) {
        addReportBtn.addEventListener('click', openReportModal);
    }
    
    if (closeReportModalBtn) {
        closeReportModalBtn.addEventListener('click', closeReportModal);
    }
    
    if (cancelReportBtn) {
        cancelReportBtn.addEventListener('click', closeReportModal);
    }
    
    // Fermer la modal en cliquant en dehors
    window.addEventListener('click', (e) => {
        if (e.target === createReportModal) {
            closeReportModal();
        }
    });
    
    // Gérer la soumission du formulaire de création de rapport
    if (reportForm) {
        reportForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const reportName = formData.get('report_name')?.trim();
            const reportType = formData.get('report_type');
            const dateRange = formData.get('date_range');
            
            // Validation des données
            if (!reportName) {
                showAlert('Veuillez saisir un nom pour le rapport', 'error');
                return;
            }
            
            if (!reportType) {
                showAlert('Veuillez sélectionner un type de rapport', 'error');
                return;
            }
            
            // Préparer les données du rapport
            const reportData = {
                name: reportName,
                report_type: reportType,
                date_range: dateRange || 'current_month'
            };

            // Ajouter les dates personnalisées si nécessaire
            if (dateRange === 'custom') {
                const startDate = formData.get('start_date');
                const endDate = formData.get('end_date');
                if (startDate) reportData.start_date = startDate;
                if (endDate) reportData.end_date = endDate;
            }
            
            // Désactiver le bouton de soumission
            const submitButton = this.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Création...';
            
            try {
                const response = await fetch(`${API_BASE_URL}/generate`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken(),
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(reportData)
                });
                
                const responseData = await response.json();
                
                if (!response.ok) {
                    throw new Error(
                        responseData.msg || 
                        responseData.message || 
                        `Erreur ${response.status}: ${response.statusText}`
                    );
                }
                
                // Afficher un message de succès
                showAlert('Rapport créé avec succès', 'success');
                
                // Fermer la modal et recharger la liste des rapports
                closeReportModal();
                loadSavedReports();
                
                // Afficher le rapport créé
                if (responseData.id) {
                    // Petit délai pour laisser le temps à la liste de se charger
                    setTimeout(() => viewReport(responseData.id), 500);
                }
                
            } catch (error) {
                console.error('Erreur lors de la création du rapport:', error);
                
                // Afficher un message d'erreur détaillé
                let errorMessage = 'Une erreur est survenue lors de la création du rapport';
                
                if (error.message) {
                    errorMessage = error.message;
                } else if (error.errors) {
                    // Gérer les erreurs de validation
                    errorMessage = Object.values(error.errors)
                        .map(err => Array.isArray(err) ? err.join(', ') : err)
                        .join('\n');
                }
                
                showAlert(errorMessage, 'error');
                
            } finally {
                // Réactiver le bouton dans tous les cas
                submitButton.disabled = false;
                submitButton.innerHTML = originalText;
            }
        });
    }
    
    // Gérer le changement de type de rapport
    if (reportTypeSelect) {
        reportTypeSelect.addEventListener('change', function() {
            // Recharger les graphiques avec le nouveau type
            initCharts();
        });
    }

    // Bouton "Générer le rapport" (filtres principaux)
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function() {
            initCharts();
            showAlert('Rapport mis à jour', 'success');
        });
    }

    // Bouton "Réinitialiser"
    const resetFiltersBtn = document.getElementById('reset-filters');
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', function() {
            if (reportTypeSelect) reportTypeSelect.value = 'expenses';
            if (dateRangePicker) dateRangePicker.value = 'current_month';
            const customDateRangeDiv = document.getElementById('custom-date-range');
            if (customDateRangeDiv) customDateRangeDiv.classList.add('hidden');
            // Vider l'aperçu du rapport généré/sauvegardé
            if (reportPreview) reportPreview.innerHTML = '';
            reinitialiserFiltresAnalyse();
            initCharts(true);
            showAlert('Filtres réinitialisés', 'info');
        });
    }

    // Dropdown d'export multi-format
    const exportDropdownBtn = document.getElementById('export-dropdown-btn');
    const exportDropdownMenu = document.getElementById('export-dropdown-menu');

    if (exportDropdownBtn && exportDropdownMenu) {
        exportDropdownBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            exportDropdownMenu.classList.toggle('hidden');
        });

        // Fermer le dropdown en cliquant ailleurs
        document.addEventListener('click', function() {
            if (!exportDropdownMenu.classList.contains('hidden')) {
                exportDropdownMenu.classList.add('hidden');
            }
            // Fermer aussi les menus des rapports sauvegardés
            document.querySelectorAll('.download-menu').forEach(m => m.classList.add('hidden'));
        });

        // Handlers pour chaque option d'export
        document.querySelectorAll('.export-option').forEach(btn => {
            btn.addEventListener('click', function() {
                const format = this.dataset.format;
                exportDropdownMenu.classList.add('hidden');
                exportReport(format);
            });
        });
    }

    // Fonction d'export multi-format
    async function exportReport(format) {
        const reportType = reportTypeSelect?.value || 'expenses';
        const dateRange = dateRangePicker?.value || 'current_month';
        const startDate = document.getElementById('start-date')?.value || '';
        const endDate = document.getElementById('end-date')?.value || '';

        // Construire l'URL d'export
        let apiFormat = format;
        let includeCharts = false;
        if (format === 'pdf-charts') {
            apiFormat = 'pdf';
            includeCharts = true;
        } else if (format === 'excel-charts') {
            apiFormat = 'excel';
            includeCharts = true;
        }

        let exportUrl = `${API_BASE_URL}/export?format=${apiFormat}&report_type=${reportType}&date_range=${dateRange}`;
        if (includeCharts) exportUrl += '&include_charts=true';
        if (dateRange === 'custom' && startDate) exportUrl += `&start_date=${startDate}`;
        if (dateRange === 'custom' && endDate) exportUrl += `&end_date=${endDate}`;
        const filtresExport = filtresParams();
        if (filtresExport) exportUrl += `&${filtresExport}`;

        const formatLabels = {
            'pdf': 'PDF', 'pdf-charts': 'PDF avec graphiques',
            'excel': 'Excel', 'excel-charts': 'Excel avec graphiques',
            'csv': 'CSV', 'json': 'JSON'
        };
        const formatExtensions = {
            'pdf': 'pdf', 'pdf-charts': 'pdf',
            'excel': 'xlsx', 'excel-charts': 'xlsx', 'csv': 'csv', 'json': 'json'
        };

        try {
            showAlert(`Generation du fichier ${formatLabels[format] || format} en cours...`, 'info');
            const response = await fetch(exportUrl, {
                headers: { 'X-CSRFToken': getCSRFToken() }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.message || `Erreur lors de la generation du fichier ${formatLabels[format]}`);
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `rapport-${reportType}-${new Date().toISOString().slice(0,10)}.${formatExtensions[format] || format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
            showAlert(`${formatLabels[format] || format} telecharge avec succes`, 'success');
        } catch (error) {
            console.error(`Erreur export ${format}:`, error);
            showAlert(error.message || `Erreur lors de l'export ${formatLabels[format] || format}`, 'error');
        }
    }
    // Rendre exportReport accessible globalement
    window.exportReport = exportReport;

    // Bouton refresh des rapports sauvegardés
    const refreshReportsBtn = document.getElementById('refresh-reports');
    if (refreshReportsBtn) {
        refreshReportsBtn.addEventListener('click', function() {
            loadSavedReports();
            showAlert('Liste des rapports actualisée', 'info');
        });
    }

    // Initialisation
    loadSavedReports();
    
    // Si nous sommes sur la page de visualisation d'un rapport spécifique
    if (window.location.pathname.includes('/reports/') && !window.location.pathname.endsWith('/reports/')) {
        // Extraire l'ID du rapport de l'URL
        const reportId = window.location.pathname.split('/').pop();
        if (reportId && !isNaN(reportId)) {
            // Charger et afficher le rapport
            viewReport(parseInt(reportId));
        }
    }
    
    // Initialiser les graphiques (afficher les deux au chargement)
    initCharts(true);
});
