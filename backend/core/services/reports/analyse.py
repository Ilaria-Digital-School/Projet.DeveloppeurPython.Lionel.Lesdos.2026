"""
Analyse détaillée d'une période pour la page Rapports.

- indicateurs clés (revenus, dépenses, taux d'épargne, moyennes...) ;
- détail des dépenses par catégorie ;
- comparaison avec la période précédente de même longueur.

Les montants sont stockés en positif : le type de transaction donne le sens.
"""

import calendar
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func

from core.extensions import db
from core.models.category import Category
from core.models.transactions import Transaction, TransactionType

# Périodes comparées au(x) mois précédent(s) plutôt qu'au même nombre de jours
_DECALAGE_MOIS = {
    "current_month": 1,
    "last_month": 1,
    "current_quarter": 3,
    "last_quarter": 3,
    "last_3_months": 3,
    "last_6_months": 6,
    "last_12_months": 12,
    "current_year": 12,
    "last_year": 12,
}


def _decaler_mois(jour: date, mois: int) -> date:
    """Décale une date de N mois (le jour est ramené au dernier jour du mois)."""
    total = jour.year * 12 + (jour.month - 1) + mois
    annee, mois_idx = divmod(total, 12)
    dernier = calendar.monthrange(annee, mois_idx + 1)[1]
    return date(annee, mois_idx + 1, min(jour.day, dernier))


def periode_precedente(
    debut: date, fin: date, date_range: Optional[str] = None
) -> Tuple[date, date]:
    """Période à comparer : même durée, juste avant.

    « Ce mois-ci » (1er au 5 novembre) est comparé au 1er au 5 octobre,
    « Cette année » à la même partie de l'année précédente. Une période
    personnalisée est comparée au même nombre de jours juste avant.
    """
    decalage = _DECALAGE_MOIS.get(date_range)
    if decalage is None:
        jours = (fin - debut).days + 1
        return debut - timedelta(days=jours), debut - timedelta(days=1)

    prec_debut = _decaler_mois(debut, -decalage)
    prec_fin = _decaler_mois(fin, -decalage)
    # Fin de mois -> fin du mois précédent (31 mars -> 28/29 février)
    if (fin + timedelta(days=1)).day == 1:
        prec_fin = prec_fin.replace(
            day=calendar.monthrange(prec_fin.year, prec_fin.month)[1]
        )
    return prec_debut, prec_fin


def conditions_filtres(filtres: Optional[Dict] = None) -> List:
    """Conditions SQL des filtres facultatifs des rapports.

    filtres = {"categories": [id, ..., None], "recherche": "texte"} :
    None dans les catégories = transactions sans catégorie ; la recherche
    porte sur le libellé (sans tenir compte des majuscules).
    """
    if not filtres:
        return []
    conditions = []
    categories = filtres.get("categories")
    if categories:
        ids = [c for c in categories if c is not None]
        choix = []
        if ids:
            choix.append(Transaction.category_id.in_(ids))
        if None in categories:
            choix.append(Transaction.category_id.is_(None))
        conditions.append(db.or_(*choix))
    recherche = filtres.get("recherche")
    if recherche:
        conditions.append(Transaction.libelle.icontains(recherche, autoescape=True))
    return conditions


def _filtre_periode(
    query, user_id: int, debut: date, fin: date, filtres: Optional[Dict] = None
):
    query = query.filter(
        Transaction.user_id == user_id,
        func.date(Transaction.date_heure_transaction) >= debut,
        func.date(Transaction.date_heure_transaction) <= fin,
    )
    return query.filter(*conditions_filtres(filtres))


def _totaux(
    user_id: int, debut: date, fin: date, filtres: Optional[Dict] = None
) -> Dict[str, Decimal]:
    """Revenus et dépenses de la période (virements exclus)."""

    def somme(types):
        total = _filtre_periode(
            db.session.query(func.coalesce(func.sum(Transaction.montant), 0)),
            user_id,
            debut,
            fin,
            filtres,
        ).filter(Transaction.type_transaction.in_(types))
        return Decimal(total.scalar() or 0)

    return {
        "revenus": somme(TransactionType.income_values()),
        "depenses": somme(TransactionType.expense_values()),
    }


def _depenses_par_categorie(
    user_id: int, debut: date, fin: date, filtres: Optional[Dict] = None
) -> Dict:
    """{category_id (None = sans catégorie): (nom, couleur, montant, nombre)}."""
    lignes = (
        _filtre_periode(
            db.session.query(
                Transaction.category_id,
                Category.name,
                Category.color,
                func.sum(Transaction.montant),
                func.count(Transaction.id),
            )
            .select_from(Transaction)
            .outerjoin(Category, Transaction.category_id == Category.id),
            user_id,
            debut,
            fin,
            filtres,
        )
        .filter(Transaction.type_transaction.in_(TransactionType.expense_values()))
        .group_by(Transaction.category_id, Category.name, Category.color)
        .all()
    )
    return {
        cat_id: (nom, couleur, Decimal(montant or 0), nombre)
        for cat_id, nom, couleur, montant, nombre in lignes
    }


def _evolution(actuel: Decimal, precedent: Decimal) -> Optional[float]:
    """Évolution en % (None si la période précédente est à zéro)."""
    if not precedent:
        return None
    return round(float((actuel - precedent) / precedent * 100), 1)


def analyse_detaillee(
    user_id: int,
    debut: date,
    fin: date,
    date_range: Optional[str] = None,
    filtres: Optional[Dict] = None,
) -> Dict:
    """Indicateurs et détail par catégorie de la période, comparés à la
    période précédente."""
    prec_debut, prec_fin = periode_precedente(debut, fin, date_range)

    totaux = _totaux(user_id, debut, fin, filtres)
    totaux_prec = _totaux(user_id, prec_debut, prec_fin, filtres)
    revenus, depenses = totaux["revenus"], totaux["depenses"]
    solde = revenus - depenses

    # Jours écoulés : une période en cours s'arrête à aujourd'hui
    jours = max((min(fin, date.today()) - debut).days + 1, 1)

    plus_grosse = (
        _filtre_periode(Transaction.query, user_id, debut, fin, filtres)
        .filter(Transaction.type_transaction.in_(TransactionType.expense_values()))
        .order_by(Transaction.montant.desc(), Transaction.id.desc())
        .first()
    )

    sans_categorie = (
        _filtre_periode(Transaction.query, user_id, debut, fin, filtres)
        .filter(
            Transaction.category_id.is_(None),
            Transaction.type_transaction.in_(
                TransactionType.expense_values() + TransactionType.income_values()
            ),
        )
        .count()
    )

    actuelles = _depenses_par_categorie(user_id, debut, fin, filtres)
    precedentes = _depenses_par_categorie(user_id, prec_debut, prec_fin, filtres)

    categories = []
    for cat_id in set(actuelles) | set(precedentes):
        nom, couleur, montant, nombre = actuelles.get(
            cat_id, (None, None, Decimal(0), 0)
        )
        prec = precedentes.get(cat_id, (None, None, Decimal(0), 0))
        nom = nom or prec[0] or "Sans catégorie"
        couleur = couleur or prec[1]
        montant_prec = prec[2]
        categories.append(
            {
                "id": cat_id,
                "nom": nom,
                "couleur": couleur,
                "montant": float(montant),
                "pourcentage": (
                    round(float(montant / depenses * 100), 1) if depenses else 0.0
                ),
                "nombre": nombre,
                "moyenne": float(montant / nombre) if nombre else 0.0,
                "montant_precedent": float(montant_prec),
                "ecart": float(montant - montant_prec),
                "evolution": _evolution(montant, montant_prec),
            }
        )
    categories.sort(key=lambda c: (-c["montant"], -c["montant_precedent"], c["nom"]))

    return {
        "periode": {"debut": debut.isoformat(), "fin": fin.isoformat()},
        "periode_precedente": {
            "debut": prec_debut.isoformat(),
            "fin": prec_fin.isoformat(),
        },
        "indicateurs": {
            "revenus": float(revenus),
            "depenses": float(depenses),
            "solde": float(solde),
            "revenus_precedent": float(totaux_prec["revenus"]),
            "depenses_precedent": float(totaux_prec["depenses"]),
            "evolution_depenses": _evolution(depenses, totaux_prec["depenses"]),
            "evolution_revenus": _evolution(revenus, totaux_prec["revenus"]),
            "taux_epargne": (
                round(float(solde / revenus * 100), 1) if revenus else None
            ),
            "depense_moyenne_jour": float(depenses / jours),
            "jours": jours,
            "plus_grosse_depense": (
                {
                    "libelle": plus_grosse.libelle,
                    "montant": float(plus_grosse.montant),
                    "date": plus_grosse.date_heure_transaction.date().isoformat(),
                }
                if plus_grosse
                else None
            ),
            "sans_categorie": sans_categorie,
        },
        "categories": categories,
    }


# ---------------------------------------------------------------------------
# Évolution mois par mois des dépenses par catégorie
# ---------------------------------------------------------------------------

# En dessous de 2 mois, l'évolution montre les 6 derniers mois
NB_MOIS_MINIMUM = 2
NB_MOIS_PAR_DEFAUT = 6


def _mois_entre(debut: date, fin: date):
    """Liste des premiers jours de mois de `debut` à `fin` (inclus)."""
    mois = []
    jour = debut.replace(day=1)
    while jour <= fin:
        mois.append(jour)
        jour = _decaler_mois(jour, 1)
    return mois


def evolution_mensuelle(
    user_id: int, debut: date, fin: date, filtres: Optional[Dict] = None
) -> Dict:
    """Dépenses de chaque catégorie, mois par mois.

    Si la période couvre moins de 2 mois, on prend les 6 mois qui se
    terminent par le mois de `fin` (une seule barre n'apprend rien).
    """
    mois = _mois_entre(debut, fin)
    elargie = len(mois) < NB_MOIS_MINIMUM
    if elargie:
        premier = _decaler_mois(fin.replace(day=1), -(NB_MOIS_PAR_DEFAUT - 1))
        mois = _mois_entre(premier, fin)
        debut = premier
    index = {m: i for i, m in enumerate(mois)}

    mois_sql = func.date_trunc("month", Transaction.date_heure_transaction)
    lignes = (
        _filtre_periode(
            db.session.query(
                Transaction.category_id,
                Category.name,
                mois_sql.label("mois"),
                func.sum(Transaction.montant),
            )
            .select_from(Transaction)
            .outerjoin(Category, Transaction.category_id == Category.id),
            user_id,
            debut,
            fin,
            filtres,
        )
        .filter(Transaction.type_transaction.in_(TransactionType.expense_values()))
        .group_by(Transaction.category_id, Category.name, mois_sql)
        .all()
    )

    series = {}
    totaux_mois = [0.0] * len(mois)
    for cat_id, nom, mois_dt, montant in lignes:
        i = index.get(mois_dt.date().replace(day=1))
        if i is None:
            continue
        serie = series.setdefault(
            cat_id,
            {
                "id": cat_id,
                "nom": nom or "Sans catégorie",
                "valeurs": [0.0] * len(mois),
            },
        )
        serie["valeurs"][i] += float(montant or 0)
        totaux_mois[i] += float(montant or 0)

    # Moyenne sur les mois terminés : le mois en cours la tirerait vers le bas
    aujourd_hui = date.today()
    termines = [i for i, m in enumerate(mois) if _decaler_mois(m, 1) <= aujourd_hui]
    base = termines or list(range(len(mois)))

    def moyenne(valeurs):
        return round(sum(valeurs[i] for i in base) / len(base), 2)

    resultat = []
    for serie in series.values():
        serie["valeurs"] = [round(v, 2) for v in serie["valeurs"]]
        serie["total"] = round(sum(serie["valeurs"]), 2)
        serie["moyenne"] = moyenne(serie["valeurs"])
        resultat.append(serie)
    resultat.sort(key=lambda s: (-s["total"], s["nom"]))

    return {
        "mois": [m.strftime("%Y-%m") for m in mois],
        "elargie": elargie,
        "series": resultat,
        "totaux_mois": [round(v, 2) for v in totaux_mois],
        "moyenne_mensuelle": moyenne(totaux_mois),
        "mois_moyenne": len(base),
    }


# ---------------------------------------------------------------------------
# Principaux destinataires (d'après les libellés bancaires)
# ---------------------------------------------------------------------------

# Préfixes ajoutés par la banque devant le nom du destinataire
_PREFIXES = re.compile(
    r"^(?:CB|PRLV(?:\s+SEPA)?|VIR(?:\s+(?:SEPA|INST|INSTANTANE))?|"
    r"PAYPAL\s*[·*\-]?|CHQ|CHEQUE|RETRAIT(?:\s+DAB)?|PAIEMENT(?:\s+CB)?)\s+",
    re.IGNORECASE,
)
# Suffixe "FACT 310826" des paiements par carte
_FACTURE = re.compile(r"\s+FACT\s+\d+\s*$", re.IGNORECASE)


def nom_destinataire(libelle: str) -> str:
    """« CB SUPERMARCHE FR0001 FACT 010126 » -> « SUPERMARCHE ».

    Retire les préfixes bancaires (CB, PRLV, VIR SEPA, PAYPAL ·...), la
    référence de facture, puis s'arrête au premier mot contenant un
    chiffre (code magasin, numéro de contrat). Le résultat reste une
    partie du libellé : il sert aussi de recherche dans les transactions.
    """
    texte = " ".join((libelle or "").split())
    texte = _FACTURE.sub("", texte)
    texte = _PREFIXES.sub("", texte, count=1).strip(" ·*-")
    mots = []
    for mot in texte.split():
        if any(c.isdigit() for c in mot) and mots:
            break
        mots.append(mot)
    nom = " ".join(mots[:4]).upper()
    return nom or (libelle or "").strip().upper() or "SANS LIBELLÉ"


def principaux_destinataires(
    user_id: int,
    debut: date,
    fin: date,
    filtres: Optional[Dict] = None,
    nombre: int = 15,
) -> Dict:
    """Destinataires des dépenses de la période, du plus gros au plus petit."""
    lignes = (
        _filtre_periode(
            db.session.query(
                Transaction.libelle,
                func.sum(Transaction.montant),
                func.count(Transaction.id),
                func.max(Transaction.date_heure_transaction),
            ),
            user_id,
            debut,
            fin,
            filtres,
        )
        .filter(Transaction.type_transaction.in_(TransactionType.expense_values()))
        .group_by(Transaction.libelle)
        .all()
    )

    groupes = {}
    total = Decimal(0)
    for libelle, montant, nb, derniere in lignes:
        nom = nom_destinataire(libelle)
        g = groupes.setdefault(
            nom, {"nom": nom, "montant": Decimal(0), "nombre": 0, "derniere": None}
        )
        g["montant"] += Decimal(montant or 0)
        g["nombre"] += nb
        if derniere and (g["derniere"] is None or derniere > g["derniere"]):
            g["derniere"] = derniere
        total += Decimal(montant or 0)

    tries = sorted(groupes.values(), key=lambda g: (-g["montant"], g["nom"]))
    return {
        "total": float(total),
        "nombre_destinataires": len(tries),
        "destinataires": [
            {
                "nom": g["nom"],
                "montant": float(g["montant"]),
                "nombre": g["nombre"],
                "pourcentage": (
                    round(float(g["montant"] / total * 100), 1) if total else 0.0
                ),
                "derniere": g["derniere"].date().isoformat() if g["derniere"] else None,
            }
            for g in tries[:nombre]
        ],
    }


# ---------------------------------------------------------------------------
# Suivi des budgets sur la période
# ---------------------------------------------------------------------------


def suivi_budgets(
    user_id: int, debut: date, fin: date, filtres: Optional[Dict] = None
) -> Dict:
    """Prévu / dépensé de chaque budget, période de budget par période de
    budget (mois ou année) sur la période du rapport.

    Les périodes antérieures à la création du budget sont données à titre
    indicatif (`avant_debut`) et ne comptent pas dans le respect du budget.
    """
    from core.models.budget import Budget

    aujourd_hui = date.today()
    query = Budget.query.filter(Budget.user_id == user_id).filter(
        db.or_(Budget.end_date.is_(None), Budget.end_date >= debut)
    )
    # Seul le filtre de catégories s'applique aux budgets
    categories = [c for c in (filtres or {}).get("categories") or [] if c]
    if categories:
        query = query.filter(Budget.category_id.in_(categories))
    budgets = query.all()

    resultat = []
    for budget in budgets:
        montant = float(budget.amount or 0)
        if budget.period in ("monthly", "yearly"):
            periodes = []
            jour = debut
            while jour <= fin:
                p_debut, p_fin = budget._bornes_naturelles(jour)
                periodes.append((p_debut, p_fin))
                jour = p_fin + timedelta(days=1)
        else:
            if budget.start_date > fin:
                continue
            periodes = [(budget.start_date, budget.end_date or aujourd_hui)]

        lignes = []
        for p_debut, p_fin in periodes:
            depense = budget.montant_depense(p_debut, p_fin)
            lignes.append(
                {
                    "label": (
                        str(p_debut.year)
                        if budget.period == "yearly"
                        else (
                            f"{p_debut.month:02d}/{p_debut.year}"
                            if budget.period == "monthly"
                            else f"{p_debut.isoformat()} → {p_fin.isoformat()}"
                        )
                    ),
                    "debut": p_debut.isoformat(),
                    "fin": p_fin.isoformat(),
                    "prevu": montant,
                    "depense": round(depense, 2),
                    "ecart": round(montant - depense, 2),
                    "pourcentage": (
                        round(depense / montant * 100, 1) if montant else 0.0
                    ),
                    "depasse": depense > montant,
                    "en_cours": p_debut <= aujourd_hui <= p_fin,
                    "avant_debut": p_fin < budget.start_date,
                }
            )

        suivies = [
            ligne
            for ligne in lignes
            if not ligne["avant_debut"] and not ligne["en_cours"]
        ]
        resultat.append(
            {
                "id": budget.id,
                "categorie": budget.category.name if budget.category else "Toutes",
                "category_id": budget.category_id,
                "periode": budget.period,
                "montant": montant,
                "periodes": lignes,
                "periodes_terminees": len(suivies),
                "depassements": sum(1 for ligne in suivies if ligne["depasse"]),
                "total_prevu": round(
                    sum(ligne["prevu"] for ligne in lignes if not ligne["avant_debut"]),
                    2,
                ),
                "total_depense": round(
                    sum(
                        ligne["depense"] for ligne in lignes if not ligne["avant_debut"]
                    ),
                    2,
                ),
            }
        )
    resultat.sort(key=lambda b: b["categorie"])
    return {"budgets": resultat}
