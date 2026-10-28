"""
API REST v1 — Devices (Appareils).

Routes:
    GET    /api/v1/devices                       Liste des appareils de l'utilisateur
    GET    /api/v1/devices/<public_id>            Détails d'un appareil
    DELETE /api/v1/devices/<public_id>            Révoquer un appareil
    GET    /api/v1/devices/<public_id>/history    Historique de connexion
    POST   /api/v1/devices/heartbeat             Mise à jour du statut en ligne
"""

import logging
from datetime import datetime, timezone

from flask import request
from flask_login import current_user, login_required

from core.extensions import db

from . import api_v1_bp
from .helpers import api_error, api_success

logger = logging.getLogger(__name__)


@api_v1_bp.route("/devices", methods=["GET"])
@login_required
def v1_list_devices():
    """Liste des appareils de l'utilisateur."""
    try:
        from core.services.devices.device_services import DeviceService

        devices = DeviceService.get_user_devices(current_user.id)
        return api_success(
            {
                "devices": [d.to_dict() for d in devices],
                "total": len(devices),
            }
        )
    except Exception as e:
        logger.error(f"Erreur liste appareils: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/devices/<string:public_id>", methods=["GET"])
@login_required
def v1_get_device(public_id):
    """Détails d'un appareil."""
    try:
        from core.models.device import Device

        device = Device.query.filter_by(
            public_id=public_id,
            user_id=current_user.id,
        ).first()

        if not device:
            return api_error("Appareil non trouvé.", 404)

        return api_success({"device": device.to_dict(include_sensitive=True)})
    except Exception as e:
        logger.error(f"Erreur détail appareil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/devices/<string:public_id>", methods=["DELETE"])
@login_required
def v1_revoke_device(public_id):
    """Révoquer un appareil."""
    try:
        from core.models.device import Device

        device = Device.query.filter_by(
            public_id=public_id,
            user_id=current_user.id,
        ).first()

        if not device:
            return api_error("Appareil non trouvé.", 404)

        if not device.is_active:
            return api_error("Appareil déjà révoqué.", 400)

        device.revoke()

        return api_success(message="Appareil révoqué avec succès.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur révocation appareil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/devices/<string:public_id>/history", methods=["GET"])
@login_required
def v1_device_history(public_id):
    """Historique de connexion d'un appareil."""
    try:
        from core.models.device import Device
        from core.services.devices.device_services import DeviceService

        device = Device.query.filter_by(
            public_id=public_id,
            user_id=current_user.id,
        ).first()

        if not device:
            return api_error("Appareil non trouvé.", 404)

        limit = request.args.get("limit", 50, type=int)
        offset = request.args.get("offset", 0, type=int)

        entries, total = DeviceService.get_device_login_history(
            user_id=current_user.id,
            device_id=device.id,
            limit=limit,
            offset=offset,
        )

        return api_success(
            {
                "history": [e.to_dict() for e in entries],
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        )
    except Exception as e:
        logger.error(f"Erreur historique appareil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)


@api_v1_bp.route("/devices/heartbeat", methods=["POST"])
@login_required
def v1_device_heartbeat():
    """Mise à jour du statut en ligne d'un appareil."""
    try:
        from core.models.device import Device

        data = request.get_json()
        if not data or "device_id" not in data:
            return api_error("Données invalides. device_id est requis.", 400)

        device = Device.query.filter_by(
            device_id=data["device_id"],
            user_id=current_user.id,
        ).first()

        if not device:
            return api_error("Appareil non trouvé.", 404)

        device.last_heartbeat = datetime.now(timezone.utc)
        db.session.commit()

        return api_success(
            {
                "device_id": device.device_id,
                "last_heartbeat": device.last_heartbeat.isoformat(),
            }
        )

    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur heartbeat appareil: {e}", exc_info=True)
        return api_error("Une erreur interne est survenue", 500)
