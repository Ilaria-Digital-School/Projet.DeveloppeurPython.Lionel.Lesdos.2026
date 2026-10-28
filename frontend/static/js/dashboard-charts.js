/**
 * Dashboard Charts avec Chart.js
 * Intégration avec l'architecture existante de l'application budget
 */

class DashboardCharts {
    constructor() {
        this.charts = {};
        this.isLoading = false;
        this.refreshInterval = null;
        
        // Configuration globale Chart.js
        this.setupChartDefaults();
        
        // Initialisation
        this.init();
    }

    /**
     * Configuration globale des graphiques
     */
    setupChartDefaults() {
        // Configuration par défaut Chart.js
        Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#6B7280';
        Chart.defaults.plugins.legend.labels.usePointStyle = true;
        Chart.defaults.plugins.legend.labels.padding = 15;
        
        // Configuration responsive
        this.defaultOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed.y !== undefined ? context.parsed.y : context.parsed;
                            return `${context.dataset.label}: ${value.toLocaleString('fr-FR', {
                                style: 'currency',
                                currency: 'EUR',
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                            })}`;
                        }
                    }
                }
            },
            animation: {
                duration: 800,
                easing: 'easeInOutQuart'
            }
        };
    }

    /**
     * Initialisation des graphiques
     */
    async init() {
        
        try {
            // Charger les KPIs en premier
            await this.loadKPIs();
            
            // Charger les graphiques
            await this.loadAllCharts();
            
            // Configurer le rafraîchissement automatique
            this.setupAutoRefresh();
            
            // Configurer les filtres
            this.setupFilters();
            
            
        } catch (error) {
            console.error('❌ Erreur initialisation Dashboard Charts:', error);
            this.showGlobalError('Impossible de charger les graphiques');
        }
    }

    /**
     * Chargement des KPIs (cartes métriques)
     */
    async loadKPIs() {
        try {
            
            const response = await fetch('/api/v1/dashboard/charts/kpis');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.updateKPICards(data.kpis);
            } else {
                throw new Error(data.message || 'Erreur chargement KPIs');
            }
            
        } catch (error) {
            console.error('❌ Erreur KPIs:', error);
            this.updateKPICards({
                total_balance: 0,
                monthly_income: 0,
                monthly_expenses: 0,
                savings: 0
            });
        }
    }

    /**
     * Mise à jour des cartes KPI
     */
    updateKPICards(kpis) {
        const formatCurrency = (value) => {
            return new Intl.NumberFormat('fr-FR', {
                style: 'currency',
                currency: 'EUR',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            }).format(value);
        };

        // Mise à jour des valeurs
        const balanceEl = document.getElementById('kpi-balance');
        const incomeEl = document.getElementById('kpi-income');
        const expensesEl = document.getElementById('kpi-expenses');
        const savingsEl = document.getElementById('kpi-savings');

        if (balanceEl) balanceEl.textContent = formatCurrency(kpis.total_balance);
        if (incomeEl) incomeEl.textContent = formatCurrency(kpis.monthly_income);
        if (expensesEl) expensesEl.textContent = formatCurrency(kpis.monthly_expenses);
        if (savingsEl) {
            savingsEl.textContent = formatCurrency(kpis.savings);
            // Changer la couleur selon le signe
            const savingsCard = savingsEl.closest('.kpi-card');
            if (savingsCard) {
                if (kpis.savings >= 0) {
                    savingsCard.className = savingsCard.className.replace(/kpi-\w+/, 'kpi-savings');
                } else {
                    savingsCard.className = savingsCard.className.replace(/kpi-\w+/, 'kpi-expenses');
                }
            }
        }
    }

    /**
     * Chargement de tous les graphiques
     */
    async loadAllCharts() {
        const chartPromises = [
            this.loadBalanceEvolution(),
            this.loadExpensesBreakdown(),
            this.loadIncomeVsExpenses(),
            this.loadBudgetProgress()
        ];

        // Charger en parallèle mais gérer les erreurs individuellement
        const results = await Promise.allSettled(chartPromises);
        
        results.forEach((result, index) => {
            if (result.status === 'rejected') {
                console.error(`❌ Erreur graphique ${index}:`, result.reason);
            }
        });
    }

    /**
     * Graphique évolution des soldes
     */
    async loadBalanceEvolution() {
        const canvasId = 'balance-evolution-chart';
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            this.showChartLoading(canvas);
            
            const months = this.getFilterValue('balance-months', 6);
            const response = await fetch(`/api/v1/dashboard/charts/balance-evolution?months=${months}`);
            const data = await response.json();

            if (data.status === 'success') {
                // Détruire le graphique existant si présent
                if (this.charts[canvasId]) {
                    this.charts[canvasId].destroy();
                }

                this.charts[canvasId] = new Chart(canvas, {
                    type: 'line',
                    data: data.chart_data,
                    options: {
                        ...this.defaultOptions,
                        plugins: {
                            ...this.defaultOptions.plugins,
                            title: {
                                display: true,
                                text: 'Évolution du patrimoine',
                                font: { size: 16, weight: 'bold' },
                                padding: 20
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
                                        return value.toLocaleString('fr-FR', {
                                            style: 'currency',
                                            currency: 'EUR',
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        });
                                    }
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                }
                            }
                        }
                    }
                });

                this.hideChartLoading(canvas);
            } else {
                throw new Error(data.message);
            }

        } catch (error) {
            console.error('❌ Erreur évolution soldes:', error);
            this.showChartError(canvas, 'Erreur de chargement');
        }
    }

    /**
     * Graphique répartition des dépenses
     */
    async loadExpensesBreakdown() {
        const canvasId = 'expenses-breakdown-chart';
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            this.showChartLoading(canvas);
            
            const period = this.getFilterValue('expenses-period', 30);
            const url = `/api/v1/dashboard/charts/expenses-breakdown?period=${period}`;
            const response = await fetch(url);
            const data = await response.json();

            if (data.status === 'success') {
                if (this.charts[canvasId]) {
                    this.charts[canvasId].destroy();
                }

                this.charts[canvasId] = new Chart(canvas, {
                    type: 'doughnut',
                    data: data.chart_data,
                    options: {
                        ...this.defaultOptions,
                        plugins: {
                            ...this.defaultOptions.plugins,
                            title: {
                                display: true,
                                text: 'Répartition des dépenses',
                                font: { size: 16, weight: 'bold' },
                                padding: 20
                            },
                            legend: {
                                position: 'right',
                                labels: {
                                    padding: 15,
                                    usePointStyle: true,
                                    generateLabels: function(chart) {
                                        const data = chart.data;
                                        if (!data.labels || !data.datasets[0] || !data.datasets[0].data) return [];
                                        
                                        const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                                        return data.labels.map((label, i) => {
                                            const value = data.datasets[0].data[i];
                                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                            return {
                                                text: `${label} (${percentage}%)`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                strokeStyle: data.datasets[0].backgroundColor[i],
                                                pointStyle: 'circle'
                                            };
                                        });
                                    }
                                }
                            }
                        }
                    }
                });

                this.hideChartLoading(canvas);
            } else {
                throw new Error(data.message);
            }

        } catch (error) {
            console.error('❌ Erreur répartition dépenses:', error);
            this.showChartError(canvas, 'Erreur de chargement');
        }
    }

    /**
     * Graphique revenus vs dépenses
     */
    async loadIncomeVsExpenses() {
        const canvasId = 'income-vs-expenses-chart';
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            this.showChartLoading(canvas);
            
            const months = this.getFilterValue('income-months', 6);
            const response = await fetch(`/api/v1/dashboard/charts/income-vs-expenses?months=${months}`);
            const data = await response.json();

            if (data.status === 'success') {
                if (this.charts[canvasId]) {
                    this.charts[canvasId].destroy();
                }

                this.charts[canvasId] = new Chart(canvas, {
                    type: 'bar',
                    data: data.chart_data,
                    options: {
                        ...this.defaultOptions,
                        plugins: {
                            ...this.defaultOptions.plugins,
                            title: {
                                display: true,
                                text: 'Revenus vs Dépenses',
                                font: { size: 16, weight: 'bold' },
                                padding: 20
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
                                        return value.toLocaleString('fr-FR', {
                                            style: 'currency',
                                            currency: 'EUR',
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        });
                                    }
                                }
                            },
                            x: {
                                grid: {
                                    display: false
                                }
                            }
                        }
                    }
                });

                this.hideChartLoading(canvas);
            } else {
                throw new Error(data.message);
            }

        } catch (error) {
            console.error('❌ Erreur revenus vs dépenses:', error);
            this.showChartError(canvas, 'Erreur de chargement');
        }
    }

    /**
     * Graphique progression des budgets
     */
    async loadBudgetProgress() {
        const canvasId = 'budget-progress-chart';
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        try {
            this.showChartLoading(canvas);
            
            const response = await fetch('/api/v1/dashboard/charts/budget-progress');
            const data = await response.json();

            if (data.status === 'success') {
                if (this.charts[canvasId]) {
                    this.charts[canvasId].destroy();
                }

                this.charts[canvasId] = new Chart(canvas, {
                    type: 'doughnut',
                    data: data.chart_data,
                    options: {
                        ...this.defaultOptions,
                        plugins: {
                            ...this.defaultOptions.plugins,
                            title: {
                                display: true,
                                text: 'Progression des budgets',
                                font: { size: 16, weight: 'bold' },
                                padding: 20
                            }
                        }
                    }
                });

                this.hideChartLoading(canvas);
            } else {
                throw new Error(data.message);
            }

        } catch (error) {
            console.error('❌ Erreur progression budgets:', error);
            this.showChartError(canvas, 'Erreur de chargement');
        }
    }

    /**
     * Configuration des filtres
     */
    setupFilters() {
        // Bouton de rafraîchissement
        const refreshBtn = document.getElementById('chart-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshAllCharts();
            });
        }

        // Filtres de période
        const filters = document.querySelectorAll('.chart-filter');
        filters.forEach(filter => {
            filter.addEventListener('change', () => {
                if (filter.id === 'balance-months') {
                    this.loadBalanceEvolution();
                } else if (filter.id === 'expenses-period') {
                    this.loadExpensesBreakdown();
                } else if (filter.id === 'income-months') {
                    this.loadIncomeVsExpenses();
                }
            });
        });
    }

    /**
     * Configuration du rafraîchissement automatique
     */
    setupAutoRefresh() {
        // Rafraîchir toutes les 5 minutes
        this.refreshInterval = setInterval(() => {
            this.refreshAllCharts();
        }, 5 * 60 * 1000);
    }

    /**
     * Rafraîchissement de tous les graphiques
     */
    async refreshAllCharts() {
        if (this.isLoading) return;
        
        this.isLoading = true;
        const refreshBtn = document.getElementById('chart-refresh-btn');
        if (refreshBtn) {
            refreshBtn.disabled = true;
            refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Actualisation...';
        }

        try {
            await this.loadKPIs();
            await this.loadAllCharts();
        } catch (error) {
            console.error('❌ Erreur rafraîchissement:', error);
        } finally {
            this.isLoading = false;
            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Actualiser';
            }
        }
    }

    /**
     * Utilitaires
     */
    getFilterValue(filterId, defaultValue) {
        const element = document.getElementById(filterId);
        return element ? parseInt(element.value) || defaultValue : defaultValue;
    }

    showChartLoading(canvas) {
        // Ne pas détruire le canvas, juste masquer et afficher le loading
        const container = canvas.parentElement;
        
        // Créer ou mettre à jour l'indicateur de chargement
        let loadingDiv = container.querySelector('.chart-loading');
        if (!loadingDiv) {
            loadingDiv = document.createElement('div');
            loadingDiv.className = 'chart-loading';
            loadingDiv.innerHTML = `
                <div class="spinner"></div>
                <span>Chargement...</span>
            `;
            loadingDiv.style.position = 'absolute';
            loadingDiv.style.top = '0';
            loadingDiv.style.left = '0';
            loadingDiv.style.width = '100%';
            loadingDiv.style.height = '100%';
            loadingDiv.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
            loadingDiv.style.zIndex = '10';
            container.appendChild(loadingDiv);
        }
        
        // Masquer le canvas
        canvas.style.display = 'none';
        loadingDiv.style.display = 'flex';
    }
    
    hideChartLoading(canvas) {
        const container = canvas.parentElement;
        const loadingDiv = container.querySelector('.chart-loading');
        if (loadingDiv) {
            loadingDiv.style.display = 'none';
        }
        canvas.style.display = 'block';
    }

    showChartError(canvas, message) {
        const container = canvas.parentElement;
        container.innerHTML = `
            <div class="chart-error">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${message}</span>
            </div>
        `;
    }

    showGlobalError(message) {
        console.error('❌ Erreur globale:', message);
        // Afficher une notification ou un message d'erreur global
    }

    /**
     * Nettoyage
     */
    destroy() {
        // Détruire tous les graphiques
        Object.values(this.charts).forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        this.charts = {};

        // Arrêter le rafraîchissement automatique
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    
    // Ne s'initialiser que sur la page dashboard
    const container = document.getElementById('dashboard-charts-container');
    if (container) {
        window.dashboardCharts = new DashboardCharts();
        
        // Nettoyage au déchargement de la page
        window.addEventListener('beforeunload', function() {
            if (window.dashboardCharts) {
                window.dashboardCharts.destroy();
            }
        });
    } else {
    }
});