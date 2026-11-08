"""
Suppression de compte demandée par l'utilisateur, avec délai de grâce.

- planifier_suppression : désactive le compte et fixe la purge à J+7.
- annuler_si_planifiee : appelée à la connexion (mot de passe vérifié) ;
  réactive le compte si la purge n'a pas encore eu lieu.
- purger_comptes_a_supprimer : supprime définitivement les comptes dont la
  date est passée (flask accounts purge-deleted, lancé chaque jour par le
  scheduler). Les clés étrangères vers users sont en ON DELETE CASCADE :
  comptes, transactions, budgets, catégories, récurrences... partent avec.

Un compte désactivé par un admin (deletion_scheduled_at NULL) n'est jamais
purgé ni réactivé par ce module.
"""

import logging
from datetime import datetime, timedelta, timezone

from core.extensions import db

logger = logging.getLogger(__name__)

DELAI_DE_GRACE = timedelta(days=7)


def _maintenant():
    return datetime.now(timezone.utc)


def _aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def planifier_suppression(user):
    """Désactive le compte et planifie sa purge. Retourne la date de purge."""
    maintenant = _maintenant()
    user.is_active = False
    user.deactivated_at = maintenant
    user.deactivation_reason = "Suppression demandée par l'utilisateur"
    user.deletion_scheduled_at = maintenant + DELAI_DE_GRACE
    db.session.commit()
    logger.info(
        "Suppression planifiée pour l'utilisateur %s le %s",
        user.id,
        user.deletion_scheduled_at.isoformat(),
    )
    return user.deletion_scheduled_at


def annuler_si_planifiee(user):
    """Réactive le compte si sa suppression est planifiée et pas encore échue."""
    if user.is_active or user.deletion_scheduled_at is None:
        return False
    if _aware(user.deletion_scheduled_at) <= _maintenant():
        return False
    user.is_active = True
    user.deactivated_at = None
    user.deactivation_reason = None
    user.deletion_scheduled_at = None
    db.session.commit()
    logger.info("Suppression annulée par reconnexion (utilisateur %s)", user.id)
    return True


def purger_comptes_a_supprimer(maintenant=None):
    """Supprime définitivement les comptes échus. Retourne le nombre supprimé."""
    maintenant = maintenant or _maintenant()
    ids = [
        row[0]
        for row in db.session.execute(
            db.text(
                "SELECT id FROM users WHERE is_active = false "
                "AND deletion_scheduled_at IS NOT NULL AND deletion_scheduled_at <= :m"
            ),
            {"m": maintenant},
        )
    ]
    for user_id in ids:
        # SQL direct : la cascade est faite par PostgreSQL (ON DELETE CASCADE) ;
        # un db.session.delete() tenterait de mettre les clés étrangères à NULL
        db.session.execute(db.text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        logger.warning(
            "Compte %s supprimé définitivement (demande de l'utilisateur)", user_id
        )
    db.session.commit()
    for user_id in ids:
        _supprimer_photo(user_id)
    return len(ids)


def _supprimer_photo(user_id):
    """Photo de profil (static/uploads/avatars/user_<id>.<ext>) : donnée personnelle."""
    import glob
    import os

    from flask import current_app

    dossier = os.path.join(current_app.static_folder or "static", "uploads", "avatars")
    for chemin in glob.glob(os.path.join(dossier, f"user_{int(user_id)}.*")):
        try:
            os.remove(chemin)
        except OSError as e:
            logger.warning("Photo %s non supprimée : %s", chemin, e)
