"""
Déroulement de la 2FA, commun à la connexion web (session) et à l'API (JWT).

- methode_2fa / demarrer_2fa : méthode du compte (e-mail ou application TOTP)
  et envoi du code e-mail le cas échéant.
- verifier_2fa : vérifie un code (e-mail ou TOTP) ou un code de secours.
- jeton_2fa / utilisateur_du_jeton_2fa : jeton signé et court qui relie les
  deux étapes de la connexion API (mot de passe, puis code), sans session.
"""

import hashlib
import json
import logging
from typing import Optional, Tuple

from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

from core.extensions import db

logger = logging.getLogger(__name__)

JETON_2FA_DUREE = 600  # secondes : le code e-mail, lui, expire en 15 minutes
_JETON_2FA_SALT = "api-2fa-v1"


def methode_2fa(user) -> str:
    """'email' si le compte n'a pas de secret TOTP exploitable, sinon 'app'."""
    secret = user.two_factor_secret
    if not secret or ("|" not in secret and len(secret) < 32):
        return "email"
    return "app"


def demarrer_2fa(user) -> Tuple[str, bool]:
    """Prépare la vérification : envoie le code par e-mail si besoin.

    Returns:
        (méthode, code_envoyé) ; code_envoyé vaut True pour la méthode 'app'.
    """
    methode = methode_2fa(user)
    if methode != "email":
        return methode, True
    from core.security.email_2fa import EmailTwoFactorAuth

    email_2fa = EmailTwoFactorAuth()
    code = email_2fa.generate_email_code()
    envoye = email_2fa.store_email_2fa_code(user, code) and email_2fa.send_2fa_email(
        user.email, code
    )
    if not envoye:
        logger.warning("Échec de l'envoi du code 2FA e-mail (user_id=%s)", user.id)
    return methode, bool(envoye)


def verifier_2fa(user, code: str = "", backup_code: str = "") -> Tuple[bool, str]:
    """Vérifie un code 2FA ou un code de secours (consommé s'il est valide)."""
    code = (code or "").strip()
    backup_code = (backup_code or "").strip()

    if code:
        if user.email_2fa_code and "|" in user.email_2fa_code:
            from core.security.email_2fa import EmailTwoFactorAuth

            return EmailTwoFactorAuth().verify_email_2fa_code(user, code)
        if user.two_factor_secret:
            from core.security.security_2fa import TwoFactorAuth

            ok, _ = TwoFactorAuth.verify_code(user.two_factor_secret, code)
            return ok, "" if ok else "Code de vérification invalide ou expiré."
        return False, "Aucun code 2FA en attente. Demandez un nouveau code."

    if backup_code:
        if not user.two_factor_backup_codes:
            return False, "Aucun code de récupération disponible."
        codes = json.loads(user.two_factor_backup_codes)
        empreinte = hashlib.sha256(backup_code.encode()).hexdigest()
        if empreinte not in codes:
            return False, "Code de récupération invalide."
        codes.remove(empreinte)
        user.two_factor_backup_codes = json.dumps(codes)
        db.session.commit()
        return True, "Code de récupération utilisé. Pensez à régénérer vos codes."

    return False, "Veuillez entrer un code de vérification ou un code de récupération."


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt=_JETON_2FA_SALT
    )


def jeton_2fa(user) -> str:
    """Jeton signé, valable JETON_2FA_DUREE secondes, pour l'étape 2 de l'API."""
    return _serializer().dumps({"uid": user.id})


def utilisateur_du_jeton_2fa(jeton: str) -> Optional[object]:
    """Utilisateur du jeton s'il est valide, non expiré et toujours en 2FA."""
    from core.models.user import User

    try:
        donnees = _serializer().loads(jeton or "", max_age=JETON_2FA_DUREE)
    except BadSignature:  # inclut SignatureExpired
        return None
    user = db.session.get(User, donnees.get("uid"))
    if user is None or not user.is_active or not user.two_factor_enabled:
        return None
    return user
