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
                            emptyMsg.innerHTML = '<div class="text-center"><i class="fas fa-chart-pie text-4xl mb-2"></i><p>Aucune dépense enregistrée</p></div>';
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
                                    position: 'right',
                                    labels: {
                                        color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary').trim() || '#111827',
                                        font: { size: 12 },
                                        padding: 20
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
                    monthlyDateParams = 'date_range=last_6_months';
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
                            emptyMsg.innerHTML = '<div class="text-center"><i class="fas fa-chart-bar text-4xl mb-2"></i><p>Aucune transaction enregistrée</p></div>';
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
                                    grid: { display: false },
                                    ticks: {
                                        color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim() || '#6B7280'
                                    }
                                },
                                y: {
                                    grid: {
                                        color: getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim() || '#E5E7EB',
                                        drawBorder: false
                                    },
                                    ticks: {
                                        color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim() || '#6B7280',
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
    function generateReportPreview() {
        const reportType = reportTypeSelect.value;
        const dateRange = dateRangePicker.value;
        
        if (!reportType) {
            showAlert('Veuillez sélectionner un type de rapport', 'warning');
            return;
        }
        
        if (dateRange) {
            // Mettre à jour la prévisualisation
            if (reportPreview) reportPreview.classList.remove('hidden');

            // Initialiser les graphiques avec les données réelles
            initCharts();

            // Mettre à jour le tableau des transactions récentes
            updateRecentTransactions();
        } else {
            showAlert('Veuillez sélectionner une plage de dates', 'warning');
        }
    }
    
    // Echappement HTML pour eviter les XSS
    function escapeHtml(str) {
        if (str == null) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Mettre à jour le tableau des transactions récentes depuis l'API
    async function updateRecentTransactions() {
        const tbody = document.querySelector('#recent-transactions tbody');
        if (!tbody) return;

        // Vider le tableau
        tbody.innerHTML = '';

        // Récupérer les transactions réelles depuis l'API
        let transactions = [];
        try {
            const response = await fetch('/api/v1/transactions?per_page=5&sort=-date_heure_transaction', {
                headers: { 'Accept': 'application/json', 'X-CSRFToken': getCSRFToken() }
            });
            if (response.ok) {
                const result = await response.json();
                transactions = result.transactions || result.data || [];
            }
        } catch (e) {
            console.warn('Impossible de charger les transactions récentes:', e);
        }

        // Afficher un message si aucune transaction
        if (transactions.length === 0) {
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="5" class="px-6 py-8 text-center text-gray-400 dark:text-gray-500">
                <i class="fas fa-receipt text-3xl mb-2"></i>
                <p>Aucune transaction enregistrée</p>
            </td>`;
            tbody.appendChild(row);
            return;
        }

        // Ajouter les transactions
        transactions.forEach(transaction => {
            const row = document.createElement('tr');
            row.className = 'hover:bg-gray-50 dark:hover:bg-gray-700';

            // Formater la date (API retourne dd/mm/yyyy ou ISO)
            const dateStr = transaction.date || transaction.date_heure_transaction || '';
            let formattedDate = dateStr;
            if (dateStr && !dateStr.includes('/')) {
                const date = new Date(dateStr);
                formattedDate = date.toLocaleDateString('fr-FR', {
                    day: '2-digit',
                    month: 'short',
                    year: 'numeric'
                });
            }

            // Déterminer le montant et sa direction
            const amount = parseFloat(transaction.amount || transaction.montant || 0);
            const type = transaction.type || transaction.type_transaction || '';
            const isExpense = ['achat', 'ACHAT', 'expense', 'EXPENSE', 'retrait', 'RETRAIT', 'loyer', 'LOYER', 'facture', 'FACTURE', 'abonnement', 'ABONNEMENT', 'prelevement', 'PRELEVEMENT'].includes(type);
            const displayAmount = isExpense ? -Math.abs(amount) : Math.abs(amount);

            const amountClass = displayAmount >= 0
                ? 'text-green-600 dark:text-green-400'
                : 'text-red-600 dark:text-red-400';

            const description = transaction.description || transaction.libelle || '';
            const category = transaction.category || transaction.category_name || '';
            const balance = transaction.balance != null ? parseFloat(transaction.balance) : null;

            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-900 dark:text-white">${escapeHtml(formattedDate)}</div>
                </td>
                <td class="px-6 py-4">
                    <div class="text-sm font-medium text-gray-900 dark:text-white">${escapeHtml(description)}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    <div class="text-sm text-gray-500 dark:text-gray-400">${escapeHtml(category)}</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                    <span class="text-sm font-medium ${amountClass}">
                        ${formatCurrency(displayAmount, false)}
                    </span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-right">
                    <span class="text-sm text-gray-500 dark:text-gray-400">
                        ${balance != null ? formatCurrency(balance, false) : '-'}
                    </span>
                </td>
            `;

            tbody.appendChild(row);
        });
    }
    
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
                    <p>Revenus: <span class="font-semibold text-green-600">${formatCurrency(income)}</span></p>
                    <p>Dépenses: <span class="font-semibold text-red-600">-${formatCurrency(expenses)}</span></p>
                    <p>Économies: <span class="font-semibold ${savings >= 0 ? 'text-green-600' : 'text-red-600'}">${formatCurrency(savings)}</span></p>
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
                            position: 'right',
                            labels: {
                                color: getComputedStyle(document.documentElement).getPropertyValue('--color-text-primary').trim() || '#111827',
                                font: { size: 12 },
                                padding: 20
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
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
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
    function getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
    }
    
    // Afficher des messages d'alerte (toast notification)
    function showAlert(message, type = 'info') {
        // Supprimer les anciens toasts
        document.querySelectorAll('.toast-alert').forEach(el => el.remove());

        const colorMap = {
            success: 'bg-green-500',
            error: 'bg-red-500',
            info: 'bg-blue-500',
            warning: 'bg-yellow-500 text-gray-900'
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
            updateRecentTransactions();
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
            initCharts(true);
            updateRecentTransactions();
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
        }

        let exportUrl = `${API_BASE_URL}/export?format=${apiFormat}&report_type=${reportType}&date_range=${dateRange}`;
        if (includeCharts) exportUrl += '&include_charts=true';
        if (dateRange === 'custom' && startDate) exportUrl += `&start_date=${startDate}`;
        if (dateRange === 'custom' && endDate) exportUrl += `&end_date=${endDate}`;

        const formatLabels = {
            'pdf': 'PDF', 'pdf-charts': 'PDF avec graphiques',
            'excel': 'Excel', 'csv': 'CSV', 'json': 'JSON'
        };
        const formatExtensions = {
            'pdf': 'pdf', 'pdf-charts': 'pdf',
            'excel': 'xlsx', 'csv': 'csv', 'json': 'json'
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
    
    // Mettre à jour les transactions récentes si nécessaire
    if (document.getElementById('recent-transactions')) {
        updateRecentTransactions();
    }
});
