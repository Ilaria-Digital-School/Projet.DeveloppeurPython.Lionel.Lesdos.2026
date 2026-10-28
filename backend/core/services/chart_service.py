"""
Service pour générer les données des graphiques Chart.js
Intégration avec l'architecture existante de l'application budget
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from core.extensions import db

logger = logging.getLogger(__name__)


class ChartService:
    """Service pour générer les données des graphiques Chart.js"""

    @staticmethod
    def get_balance_evolution(user_id: int, months: int = 6):
        """
        Évolution des soldes sur X mois à partir des transactions réelles.
        Reconstruit les soldes de fin de mois en remontant dans le temps
        depuis le solde actuel des comptes.
        """
        try:
            logger.info(f"📊 Évolution soldes - user_id: {user_id}, months: {months}")

            # 1. Solde actuel des comptes
            current_result = db.session.execute(
                text("""
                    SELECT COALESCE(SUM(solde_actuel), 0)
                    FROM "ComptesBancaires"
                    WHERE utilisateur_id = :user_id AND est_actif = true
                """),
                {"user_id": user_id},
            )
            current_balance = float(current_result.scalar() or 0.0)

            # 2. Calculer la date de début (premier jour du mois le plus ancien)
            now = datetime.now()
            # Reculer de (months-1) mois avec une arithmétique calendaire exacte
            y, m = now.year, now.month
            m -= months - 1
            while m <= 0:
                m += 12
                y -= 1
            start_date = datetime(y, m, 1)

            # 3. Récupérer le net réel par mois via une seule requête
            result = db.session.execute(
                text("""
                    SELECT TO_CHAR(date_heure_transaction, 'YYYY-MM') as mois,
                           SUM(CASE
                               WHEN type_transaction IN ('salaire','SALAIRE','depot','DEPOT','income',
                                                         'REVENU_AUTRE','REMBOURSEMENT')
                                   THEN montant - COALESCE(frais_transaction, 0)
                               WHEN type_transaction IN ('achat','ACHAT','retrait','RETRAIT','expense',
                                                         'LOYER','FACTURE','ABONNEMENT','PRELEVEMENT')
                                   THEN -(montant + COALESCE(frais_transaction, 0))
                               WHEN type_transaction IN ('virement','VIREMENT')
                                   THEN -COALESCE(frais_transaction, 0)
                               ELSE 0
                           END) as net_change
                    FROM transactions
                    WHERE user_id = :user_id
                    AND date_heure_transaction >= :start_date
                    AND statut = 'completed'
                    GROUP BY TO_CHAR(date_heure_transaction, 'YYYY-MM')
                    ORDER BY mois
                """),
                {"user_id": user_id, "start_date": start_date.strftime("%Y-%m-%d")},
            )
            monthly_nets = {row[0]: float(row[1]) for row in result.fetchall()}

            # 4. Générer la liste ordonnée des mois (du plus ancien au plus récent)
            month_keys = []
            for i in range(months):
                yr, mo = now.year, now.month - i
                while mo <= 0:
                    mo += 12
                    yr -= 1
                month_keys.append(f"{yr:04d}-{mo:02d}")
            month_keys.sort()

            # 5. Ne garder que les mois à partir du premier mois avec des transactions
            if monthly_nets:
                first_month_with_data = min(monthly_nets.keys())
                month_keys = [k for k in month_keys if k >= first_month_with_data]

            # Si aucune transaction, afficher uniquement le mois courant
            if not month_keys:
                month_keys = [now.strftime("%Y-%m")]

            # 6. Reconstruire les soldes de fin de mois en remontant dans le temps
            #    solde_fin[mois_courant] = current_balance
            #    solde_fin[mois_precedent] = solde_fin[mois_suivant] - net_change[mois_suivant]
            balances = {}
            balances[month_keys[-1]] = current_balance
            for i in range(len(month_keys) - 2, -1, -1):
                next_month = month_keys[i + 1]
                net = monthly_nets.get(next_month, 0.0)
                balances[month_keys[i]] = balances[next_month] - net

            # 7. Construire les données du graphique
            monthly_data = []
            for key in month_keys:
                d = datetime.strptime(key, "%Y-%m")
                label = d.strftime("%b %Y")
                monthly_data.append(
                    {"month": label, "balance": round(balances[key], 2)}
                )

            chart_data = {
                "labels": [item["month"] for item in monthly_data],
                "datasets": [
                    {
                        "label": "Évolution du patrimoine",
                        "data": [item["balance"] for item in monthly_data],
                        "borderColor": "rgb(59, 130, 246)",
                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                        "tension": 0.4,
                        "fill": True,
                    }
                ],
            }

            logger.info(f"✅ Données évolution générées: {len(monthly_data)} points")
            return chart_data

        except Exception as e:
            logger.error(f"❌ Erreur évolution soldes: {str(e)}", exc_info=True)
            return {
                "labels": [],
                "datasets": [
                    {
                        "label": "Évolution du patrimoine",
                        "data": [],
                        "borderColor": "rgb(59, 130, 246)",
                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                    }
                ],
            }

    @staticmethod
    def get_expenses_breakdown(user_id: int, period_days: int = 30):
        """
        Répartition des dépenses par catégorie
        Utilise la structure SQL existante
        """
        try:
            logger.info(
                f"🥧 Répartition dépenses - user_id: {user_id}, period: {period_days} jours"
            )

            # Calcul de la période
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            start_date_str = start_date.strftime("%Y-%m-%d")

            # Requête pour les dépenses par catégorie (types: achat, retrait, etc.)
            result = db.session.execute(
                text("""
                SELECT c.name, SUM(t.montant) as total
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE t.user_id = :user_id 
                AND t.date_heure_transaction >= :start_date
                AND t.type_transaction IN ('achat', 'ACHAT', 'retrait', 'RETRAIT', 'expense')
                GROUP BY c.id, c.name
                ORDER BY total DESC
                LIMIT 8
            """),
                {"user_id": user_id, "start_date": start_date_str},
            )

            expenses_data = result.fetchall()

            # Couleurs pour le graphique
            colors = [
                "#EF4444",
                "#F97316",
                "#EAB308",
                "#22C55E",
                "#06B6D4",
                "#3B82F6",
                "#8B5CF6",
                "#EC4899",
            ]

            chart_data = {
                "labels": [item[0] or "Sans catégorie" for item in expenses_data],
                "datasets": [
                    {
                        "data": [float(item[1]) for item in expenses_data],
                        "backgroundColor": colors[: len(expenses_data)],
                        "borderWidth": 2,
                        "borderColor": "#ffffff",
                    }
                ],
            }

            logger.info(
                f"✅ Données répartition générées: {len(expenses_data)} catégories"
            )
            return chart_data

        except Exception as e:
            logger.error(f"❌ Erreur répartition dépenses: {str(e)}", exc_info=True)
            return {
                "labels": ["Aucune donnée"],
                "datasets": [
                    {"data": [0], "backgroundColor": ["#E5E7EB"], "borderWidth": 1}
                ],
            }

    @staticmethod
    def get_income_vs_expenses(user_id: int, months: int = 12):
        """
        Comparaison revenus vs dépenses par mois
        """
        try:
            logger.info(
                f"📊 Revenus vs Dépenses - user_id: {user_id}, months: {months}"
            )

            monthly_data = []

            for i in range(months):
                # Calcul de la période
                current_date = datetime.now()
                target_date = current_date - timedelta(days=i * 30)
                month_start = target_date.replace(day=1).strftime("%Y-%m-%d")

                # Calcul du dernier jour du mois
                if target_date.month == 12:
                    next_month = target_date.replace(
                        year=target_date.year + 1, month=1, day=1
                    )
                else:
                    next_month = target_date.replace(month=target_date.month + 1, day=1)
                month_end = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")

                month_label = target_date.strftime("%b %Y")

                # Revenus du mois (types: salaire, dépôt, etc.)
                result = db.session.execute(
                    text("""
                    SELECT COALESCE(SUM(montant), 0) 
                    FROM transactions 
                    WHERE user_id = :user_id 
                    AND date_heure_transaction >= :start_date
                    AND date_heure_transaction <= :end_date
                    AND type_transaction IN ('salaire', 'SALAIRE', 'depot', 'DEPOT', 'income')
                """),
                    {
                        "user_id": user_id,
                        "start_date": month_start,
                        "end_date": month_end,
                    },
                )
                income = float(result.scalar() or 0.0)

                # Dépenses du mois (types: achat, retrait, etc.)
                result = db.session.execute(
                    text("""
                    SELECT COALESCE(SUM(montant), 0) 
                    FROM transactions 
                    WHERE user_id = :user_id 
                    AND date_heure_transaction >= :start_date
                    AND date_heure_transaction <= :end_date
                    AND type_transaction IN ('achat', 'ACHAT', 'retrait', 'RETRAIT', 'expense')
                """),
                    {
                        "user_id": user_id,
                        "start_date": month_start,
                        "end_date": month_end,
                    },
                )
                expenses = float(result.scalar() or 0.0)

                monthly_data.append(
                    {"month": month_label, "income": income, "expenses": expenses}
                )

            # Inverser pour ordre chronologique
            monthly_data.reverse()

            chart_data = {
                "labels": [item["month"] for item in monthly_data],
                "datasets": [
                    {
                        "label": "Revenus",
                        "data": [item["income"] for item in monthly_data],
                        "backgroundColor": "rgba(34, 197, 94, 0.8)",
                        "borderColor": "rgb(34, 197, 94)",
                        "borderWidth": 1,
                    },
                    {
                        "label": "Dépenses",
                        "data": [item["expenses"] for item in monthly_data],
                        "backgroundColor": "rgba(239, 68, 68, 0.8)",
                        "borderColor": "rgb(239, 68, 68)",
                        "borderWidth": 1,
                    },
                ],
            }

            logger.info(
                f"✅ Données revenus/dépenses générées: {len(monthly_data)} mois"
            )
            return chart_data

        except Exception as e:
            logger.error(f"❌ Erreur revenus/dépenses: {str(e)}", exc_info=True)
            return {
                "labels": [],
                "datasets": [
                    {
                        "label": "Revenus",
                        "data": [],
                        "backgroundColor": "rgba(34, 197, 94, 0.8)",
                    },
                    {
                        "label": "Dépenses",
                        "data": [],
                        "backgroundColor": "rgba(239, 68, 68, 0.8)",
                    },
                ],
            }

    @staticmethod
    def get_budget_progress(user_id: int):
        """
        Progression des budgets (graphique en donut)
        """
        try:
            logger.info(f"🎯 Progression budgets - user_id: {user_id}")

            # Récupérer les budgets actifs avec leurs dépenses
            current_date = datetime.now().date().strftime("%Y-%m-%d")

            result = db.session.execute(
                text("""
                SELECT
                    b.amount as budget_amount,
                    COALESCE(SUM(t.montant), 0) as spent_amount,
                    c.name as category_name
                FROM budgets b
                LEFT JOIN categories c ON b.category_id = c.id
                LEFT JOIN transactions t ON t.category_id = b.category_id
                    AND t.user_id = b.user_id
                    AND t.type_transaction IN ('achat', 'ACHAT', 'expense', 'retrait', 'RETRAIT')
                    AND CAST(t.date_heure_transaction AS DATE) >= CAST(b.start_date AS DATE)
                    AND (b.end_date IS NULL OR CAST(t.date_heure_transaction AS DATE) <= CAST(b.end_date AS DATE))
                WHERE b.user_id = :user_id
                AND b.start_date <= :current_date
                AND (b.end_date >= :current_date OR b.end_date IS NULL)
                GROUP BY b.id, b.amount, c.name
                ORDER BY b.amount DESC
                LIMIT 5
            """),
                {"user_id": user_id, "current_date": current_date},
            )

            budgets_data = result.fetchall()

            if not budgets_data:
                # Aucun budget actif
                return {
                    "labels": ["Aucun budget actif"],
                    "datasets": [
                        {
                            "data": [100],
                            "backgroundColor": ["#E5E7EB"],
                            "borderWidth": 1,
                        }
                    ],
                }

            # Calculer les données du graphique
            labels = []
            data = []
            colors = ["#EF4444", "#F97316", "#EAB308", "#22C55E", "#06B6D4"]

            for i, budget in enumerate(budgets_data):
                budget_amount = float(budget[0])
                spent_amount = float(budget[1])
                category_name = budget[2] or "Sans catégorie"

                # Calculer le pourcentage utilisé
                if budget_amount > 0:
                    percentage_used = min((spent_amount / budget_amount) * 100, 100)
                    remaining = max(100 - percentage_used, 0)

                    labels.extend(
                        [f"{category_name} (utilisé)", f"{category_name} (restant)"]
                    )
                    data.extend([percentage_used, remaining])

                else:
                    labels.append(f"{category_name}")
                    data.append(100)
                    [colors[i % len(colors)]]

            chart_data = {
                "labels": labels,
                "datasets": [
                    {
                        "data": data,
                        "backgroundColor": colors[: len(data)],
                        "borderWidth": 2,
                        "borderColor": "#ffffff",
                    }
                ],
            }

            logger.info(f"✅ Données budgets générées: {len(budgets_data)} budgets")
            return chart_data

        except Exception as e:
            logger.error(f"❌ Erreur progression budgets: {str(e)}", exc_info=True)
            return {
                "labels": ["Erreur de chargement"],
                "datasets": [
                    {"data": [100], "backgroundColor": ["#EF4444"], "borderWidth": 1}
                ],
            }

    @staticmethod
    def get_dashboard_kpis(user_id: int):
        """
        Récupère les KPIs pour les cartes du dashboard
        Réutilise la logique de dashboard_routes.py
        """
        try:
            logger.info(f"📈 KPIs Dashboard - user_id: {user_id}")

            # Solde total (même logique que dashboard_routes.py ligne 50-55)
            result = db.session.execute(
                text("""
                SELECT COALESCE(SUM(solde_actuel), 0) 
                FROM "ComptesBancaires" 
                WHERE utilisateur_id = :user_id AND est_actif = true
            """),
                {"user_id": user_id},
            )
            total_balance = float(result.scalar() or 0.0)

            # Revenus et dépenses du mois (même logique ligne 58-78)
            start_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")

            # Dépenses du mois (types: achat, retrait, etc.)
            result = db.session.execute(
                text("""
                SELECT COALESCE(SUM(montant), 0) 
                FROM transactions 
                WHERE user_id = :user_id 
                AND date_heure_transaction >= :start_date
                AND type_transaction IN ('achat', 'ACHAT', 'retrait', 'RETRAIT', 'expense')
            """),
                {"user_id": user_id, "start_date": start_of_month},
            )
            monthly_expenses = float(result.scalar() or 0.0)

            # Revenus du mois (types: salaire, dépôt, etc.)
            result = db.session.execute(
                text("""
                SELECT COALESCE(SUM(montant), 0) 
                FROM transactions 
                WHERE user_id = :user_id 
                AND date_heure_transaction >= :start_date
                AND type_transaction IN ('salaire', 'SALAIRE', 'depot', 'DEPOT', 'income')
            """),
                {"user_id": user_id, "start_date": start_of_month},
            )
            monthly_income = float(result.scalar() or 0.0)

            # Économies = Revenus - Dépenses
            savings = monthly_income - monthly_expenses

            kpis = {
                "total_balance": total_balance,
                "monthly_income": monthly_income,
                "monthly_expenses": monthly_expenses,
                "savings": savings,
            }

            logger.info(
                f"✅ KPIs générés: Balance {total_balance}€, Revenus {monthly_income}€, Dépenses {monthly_expenses}€"
            )
            return kpis

        except Exception as e:
            logger.error(f"❌ Erreur KPIs: {str(e)}", exc_info=True)
            return {
                "total_balance": 0.0,
                "monthly_income": 0.0,
                "monthly_expenses": 0.0,
                "savings": 0.0,
            }
