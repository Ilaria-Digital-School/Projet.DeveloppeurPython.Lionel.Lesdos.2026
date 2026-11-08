"""
Modèle pour la gestion des budgets
"""

import calendar
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func

from core.extensions import db


class Budget(db.Model):
    """Modèle pour les budgets"""

    __tablename__ = "budgets"
    __table_args__ = {
        "extend_existing": True
    }  # Permet de redéfinir la table si elle existe déjà

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), index=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    period = db.Column(db.String(20), nullable=False)  # monthly, yearly, custom
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    notification_sent = db.Column(db.Boolean, default=False)
    notification_threshold = db.Column(db.Integer, default=90)  # Pourcentage
    # Dernière alerte envoyée : "<début de période ISO>:<niveau>" (niveau =
    # seuil du budget ou 100) ; évite les doublons et repart à chaque période
    derniere_alerte = db.Column(db.String(32), nullable=True)
    # Report du reste : le non-dépensé de la période précédente s'ajoute au
    # montant de la période en cours (budgets mensuels et annuels uniquement)
    report_actif = db.Column(
        db.Boolean, nullable=False, default=False, server_default=db.false()
    )

    # Relations SQLAlchemy avec des références simples
    # Utilisation de strings pour les relations pour éviter les imports circulaires
    category = db.relationship("Category", back_populates="budgets")
    user = db.relationship("User", back_populates="budgets")

    def _bornes_naturelles(self, jour):
        """Mois ou année civils contenant `jour` (sans tenir compte des
        dates du budget). None pour un budget personnalisé."""
        if self.period == "yearly":
            return date(jour.year, 1, 1), date(jour.year, 12, 31)
        if self.period == "monthly":
            debut = jour.replace(day=1)
            fin = debut.replace(day=calendar.monthrange(debut.year, debut.month)[1])
            return debut, fin
        return None

    def periode_courante(self, today=None):
        """Période de dépense en cours : (début, fin), ou None si le budget
        n'est pas actif à cette date.

        monthly : le mois civil en cours ; yearly : l'année civile en cours ;
        autre (custom) : start_date -> end_date. Toujours limitée aux dates
        du budget.
        """
        today = today or date.today()
        if today < self.start_date or (self.end_date and today > self.end_date):
            return None
        bornes = self._bornes_naturelles(today)
        if bornes:
            debut, fin = bornes
        else:
            debut, fin = self.start_date, self.end_date or today
        debut = max(debut, self.start_date)
        if self.end_date:
            fin = min(fin, self.end_date)
        return debut, fin

    def periode_precedente(self, today=None):
        """Période qui précède la période en cours, limitée aux dates du
        budget ; None si le budget n'existait pas encore (ou est personnalisé)."""
        periode = self.periode_courante(today)
        if periode is None:
            return None
        bornes = self._bornes_naturelles(periode[0] - timedelta(days=1))
        if bornes is None or bornes[1] < self.start_date:
            return None
        return max(bornes[0], self.start_date), bornes[1]

    def montant_depense(self, debut, fin):
        """Total des dépenses de la catégorie du budget entre deux dates
        (incluses)."""
        from core.models.transactions import Transaction, TransactionType

        # Comparaison sur la date (pas la date-heure) : sinon "<= fin" excluait
        # les dépenses du dernier jour passé minuit
        query = db.session.query(
            func.coalesce(func.sum(Transaction.montant), 0)
        ).filter(
            Transaction.user_id == self.user_id,
            Transaction.type_transaction.in_(TransactionType.expense_values()),
            func.date(Transaction.date_heure_transaction) >= debut,
            func.date(Transaction.date_heure_transaction) <= fin,
        )
        if self.category_id:
            query = query.filter(Transaction.category_id == self.category_id)
        return float(query.scalar() or 0.0)

    def get_used_amount(self, today=None):
        """Montant dépensé sur la période en cours (cf. periode_courante)."""
        if not self.id:
            return 0.0
        periode = self.periode_courante(today)
        if periode is None:
            return 0.0
        return self.montant_depense(*periode)

    def montant_report(self, today=None):
        """Reste non dépensé de la période précédente, reporté sur la période
        en cours si le report est actif. Un dépassement n'est pas reporté."""
        if not self.report_actif or not self.id:
            return 0.0
        precedente = self.periode_precedente(today)
        if precedente is None:
            return 0.0
        return max(float(self.amount or 0) - self.montant_depense(*precedente), 0.0)

    def montant_disponible(self, today=None):
        """Montant du budget pour la période en cours, report inclus."""
        return float(self.amount or 0) + self.montant_report(today)

    NB_PERIODES_PROJECTION = 3

    def _reste_habituel(self, today):
        """Dépense habituelle entre demain et la fin de période : moyenne,
        sur les 3 périodes précédentes, de ce qui a été dépensé après le même
        jour de période. Rend la projection juste pour les dépenses ponctuelles
        (un loyer payé le 1er n'est pas extrapolé sur tout le mois).

        None si le budget est personnalisé ou s'il n'y a aucune dépense dans
        ces périodes (la projection retombe alors sur le rythme linéaire).
        """
        bornes = self._bornes_naturelles(today)
        if bornes is None:
            return None
        decalage = (today - bornes[0]).days + 1  # jours écoulés, aujourd'hui inclus

        totaux, restes = 0.0, []
        jour = bornes[0]
        for _ in range(self.NB_PERIODES_PROJECTION):
            debut, fin = self._bornes_naturelles(jour - timedelta(days=1))
            totaux += self.montant_depense(debut, fin)
            coupure = debut + timedelta(days=decalage)
            restes.append(self.montant_depense(coupure, fin) if coupure <= fin else 0.0)
            jour = debut
        if totaux <= 0:
            return None
        return sum(restes) / len(restes)

    def indicateurs(self, today=None):
        """Suivi de la période en cours : dépensé, restant, rythme de dépense,
        projection en fin de période et reste à dépenser par jour.

        Les jours sont comptés bornes incluses ; le jour courant compte à la
        fois dans les jours écoulés (on y a déjà dépensé) et dans les jours
        restants (on peut encore y dépenser).
        """
        today = today or date.today()
        periode = self.periode_courante(today)
        montant = float(self.amount or 0)
        if periode is None:
            return {
                "active": False,
                "period_start": None,
                "period_end": None,
                "carryover_amount": 0.0,
                "available_amount": montant,
                "spent_amount": 0.0,
                "remaining": montant,
                "spent_percentage": 0.0,
                "raw_percentage": 0.0,
                "days_total": 0,
                "days_elapsed": 0,
                "days_remaining": 0,
                "projected_amount": 0.0,
                "projected_percentage": 0.0,
                "projection_method": None,
                "daily_allowance": 0.0,
                "velocity": "inactive",
                "is_over_budget": False,
                "is_near_limit": False,
            }

        debut, fin = periode
        report = self.montant_report(today)
        disponible = montant + report
        depense = self.montant_depense(debut, fin)
        restant = disponible - depense

        jours_total = (fin - debut).days + 1
        jours_ecoules = min(max((today - debut).days + 1, 1), jours_total)
        jours_restants = jours_total - jours_ecoules + 1

        reste_habituel = self._reste_habituel(today)
        if reste_habituel is not None:
            # Les dépenses déjà saisies après aujourd'hui (loyer programmé...)
            # sont comptées dans `depense` : elles couvrent d'autant le reste
            # habituel, sinon elles seraient comptées deux fois
            a_venir = (
                self.montant_depense(today + timedelta(days=1), fin)
                if today < fin
                else 0.0
            )
            projection = depense + max(reste_habituel - a_venir, 0.0)
            methode = "history"
        else:
            projection, methode = depense / jours_ecoules * jours_total, "linear"
        pourcentage = depense / disponible * 100 if disponible > 0 else 0.0
        pourcentage_projete = projection / disponible * 100 if disponible > 0 else 0.0

        # Rythme d'après la projection : une dépense ponctuelle en début de
        # période (loyer, abonnement) n'est pas un rythme trop rapide
        if pourcentage_projete > 105:
            rythme = "high"
        elif pourcentage_projete < 85:
            rythme = "low"
        else:
            rythme = "on_track"

        seuil = self.notification_threshold or 90
        return {
            "active": True,
            "period_start": debut.isoformat(),
            "period_end": fin.isoformat(),
            "carryover_amount": round(report, 2),
            "available_amount": round(disponible, 2),
            "spent_amount": round(depense, 2),
            "remaining": round(restant, 2),
            "spent_percentage": round(min(100.0, pourcentage), 2),
            "raw_percentage": round(pourcentage, 2),
            "days_total": jours_total,
            "days_elapsed": jours_ecoules,
            "days_remaining": jours_restants,
            "projected_amount": round(projection, 2),
            "projected_percentage": round(pourcentage_projete, 2),
            "projection_method": methode,
            "daily_allowance": round(max(restant, 0.0) / jours_restants, 2),
            "velocity": rythme,
            "is_over_budget": depense > disponible,
            "is_near_limit": depense >= disponible * seuil / 100,
        }

    def historique_periodes(self, nombre=6, today=None):
        """Prévu vs réel sur les `nombre` dernières périodes (la plus
        ancienne en premier), période en cours incluse.

        Les périodes antérieures à la création du budget sont incluses (le
        réel y est utile pour calibrer le montant) et marquées
        `before_start`. Le prévu est le montant actuel du budget.
        Budget personnalisé : une seule période, start_date -> end_date.
        """
        today = today or date.today()
        reference = min(today, self.end_date) if self.end_date else today
        montant = float(self.amount or 0)

        if self.period not in ("monthly", "yearly"):
            fin = self.end_date or today
            depense = self.montant_depense(self.start_date, fin)
            return [
                {
                    "label": f"{self.start_date.isoformat()} → {fin.isoformat()}",
                    "period_start": self.start_date.isoformat(),
                    "period_end": fin.isoformat(),
                    "budget_amount": montant,
                    "spent_amount": round(depense, 2),
                    "difference": round(montant - depense, 2),
                    "before_start": False,
                    "is_current": self.periode_courante(today) is not None,
                }
            ]

        periodes = []
        jour = reference
        for _ in range(max(nombre, 1)):
            debut, fin = self._bornes_naturelles(jour)
            periodes.append((debut, fin))
            jour = debut - timedelta(days=1)
        periodes.reverse()

        resultat = []
        for debut, fin in periodes:
            depense = self.montant_depense(debut, fin)
            label = (
                str(debut.year)
                if self.period == "yearly"
                else f"{debut.month:02d}/{debut.year}"
            )
            resultat.append(
                {
                    "label": label,
                    "period_start": debut.isoformat(),
                    "period_end": fin.isoformat(),
                    "budget_amount": montant,
                    "spent_amount": round(depense, 2),
                    "difference": round(montant - depense, 2),
                    "before_start": fin < self.start_date,
                    "is_current": debut <= today <= fin,
                }
            )
        return resultat

    def to_dict(self):
        """Convertit le budget en dictionnaire avec clés anglaises."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "amount": float(self.amount) if self.amount is not None else None,
            "spent_amount": self.get_used_amount(),
            "report_actif": bool(self.report_actif),
            "period": self.period,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "notification_sent": self.notification_sent,
            "notification_threshold": self.notification_threshold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        return f"<Budget {self.id} - {self.amount}>"
