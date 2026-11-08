"""
Contrôle de cohérence des soldes.

Invariant : solde_actuel = solde_initial + effet des transactions 'completed'
(mêmes règles que effets_sur_soldes dans transaction_services) :
dépense = -(montant + frais), revenu = montant - frais, virement avec
destination = -(montant + frais) sur la source et +montant sur la destination.

Usage : flask accounts check-balances [--fix]
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional

from core.extensions import db
from core.models.transactions import TransactionType

logger = logging.getLogger(__name__)

_SQL_SOLDES_ATTENDUS = """
WITH effets AS (
    SELECT account_id AS compte,
        CASE
            WHEN type_transaction IN :depenses
                THEN -(montant + COALESCE(frais_transaction, 0))
            WHEN type_transaction IN :revenus
                THEN montant - COALESCE(frais_transaction, 0)
            WHEN type_transaction IN :virements
                 AND destination_account_id IS NOT NULL
                 AND destination_account_id <> account_id
                THEN -(montant + COALESCE(frais_transaction, 0))
            ELSE 0
        END AS delta
    FROM transactions WHERE statut = 'completed'
    UNION ALL
    SELECT destination_account_id, montant
    FROM transactions
    WHERE statut = 'completed' AND type_transaction IN :virements
      AND destination_account_id IS NOT NULL
      AND destination_account_id <> account_id
)
SELECT c.id_compte, c.utilisateur_id, c.nom_banque, c.solde_initial, c.solde_actuel,
       c.solde_initial + COALESCE(SUM(e.delta), 0) AS solde_attendu
FROM "ComptesBancaires" c
LEFT JOIN effets e ON e.compte = c.id_compte
{filtre}
GROUP BY c.id_compte
ORDER BY c.id_compte
"""


def soldes_attendus(user_id: Optional[int] = None) -> List[Dict]:
    """Solde actuel et solde attendu de chaque compte (d'un utilisateur ou de tous)."""
    filtre = "WHERE c.utilisateur_id = :user_id" if user_id is not None else ""
    requete = db.text(_SQL_SOLDES_ATTENDUS.format(filtre=filtre)).bindparams(
        db.bindparam("depenses", expanding=True),
        db.bindparam("revenus", expanding=True),
        db.bindparam("virements", expanding=True),
    )
    params = {
        "depenses": TransactionType.expense_values(),
        "revenus": TransactionType.income_values(),
        "virements": TransactionType.transfer_values(),
    }
    if user_id is not None:
        params["user_id"] = user_id
    return [
        {
            "account_id": r.id_compte,
            "user_id": r.utilisateur_id,
            "name": r.nom_banque,
            "initial_balance": Decimal(str(r.solde_initial)),
            "balance": Decimal(str(r.solde_actuel)),
            "expected_balance": Decimal(str(r.solde_attendu)),
            "ecart": Decimal(str(r.solde_actuel)) - Decimal(str(r.solde_attendu)),
        }
        for r in db.session.execute(requete, params)
    ]


def soldes_incoherents(user_id: Optional[int] = None) -> List[Dict]:
    """Comptes dont le solde actuel diffère du solde attendu."""
    return [s for s in soldes_attendus(user_id) if s["ecart"] != 0]


def corriger_soldes(user_id: Optional[int] = None) -> List[Dict]:
    """Ramène chaque solde incohérent à sa valeur attendue. Retourne les comptes corrigés."""
    incoherents = soldes_incoherents(user_id)
    for s in incoherents:
        db.session.execute(
            db.text(
                'UPDATE "ComptesBancaires" SET solde_actuel = :attendu WHERE id_compte = :id'
            ),
            {"attendu": s["expected_balance"], "id": s["account_id"]},
        )
        logger.warning(
            "Solde corrigé : compte %s '%s' %s -> %s (écart %s)",
            s["account_id"],
            s["name"],
            s["balance"],
            s["expected_balance"],
            s["ecart"],
        )
    db.session.commit()
    return incoherents
