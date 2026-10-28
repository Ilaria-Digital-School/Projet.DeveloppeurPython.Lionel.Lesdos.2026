"""Service de monitoring système pour l'administration."""

# from core.models.accounts import Account  # Import commenté temporairement
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import psutil
from flask import current_app
from sqlalchemy import inspect, text

from core.extensions import db
from core.models.user import User

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service pour collecter et analyser les métriques système."""

    # Cache simple pour éviter les appels redondants
    _cache = {}
    _cache_duration = 30  # secondes

    @staticmethod
    def _is_cache_valid(cache_key: str) -> bool:
        """Vérifie si le cache est encore valide."""
        if cache_key not in MonitoringService._cache:
            return False
        cache_time, _ = MonitoringService._cache[cache_key]
        return (time.time() - cache_time) < MonitoringService._cache_duration

    @staticmethod
    def _get_from_cache(cache_key: str) -> Any:
        """Récupère une valeur du cache."""
        if MonitoringService._is_cache_valid(cache_key):
            _, value = MonitoringService._cache[cache_key]
            return value
        return None

    @staticmethod
    def _set_cache(cache_key: str, value: Any) -> None:
        """Met en cache une valeur."""
        MonitoringService._cache[cache_key] = (time.time(), value)

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """Récupère les métriques système principales."""
        # Vérifier le cache d'abord
        cache_key = "system_metrics"
        cached = MonitoringService._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_per_core = psutil.cpu_percent(interval=0, percpu=True)

            # Mémoire
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()

            # Disque
            disk = psutil.disk_usage("/")
            disk_io = psutil.disk_io_counters()

            # Réseau
            net_io = psutil.net_io_counters()

            # Processus
            process_count = len(psutil.pids())

            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            result = {
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "per_core": cpu_per_core,
                    "load_average": (
                        os.getloadavg() if hasattr(os, "getloadavg") else [0, 0, 0]
                    ),
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                    "cached": getattr(memory, "cached", 0),
                    "buffers": getattr(memory, "buffers", 0),
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "free": swap.free,
                    "percent": swap.percent,
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent,
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0,
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "errin": net_io.errin,
                    "errout": net_io.errout,
                    "dropin": net_io.dropin,
                    "dropout": net_io.dropout,
                },
                "process": {"count": process_count},
                "uptime": {
                    "boot_time": boot_time.isoformat(),
                    "days": uptime.days,
                    "hours": uptime.seconds // 3600,
                    "minutes": (uptime.seconds % 3600) // 60,
                    "total_seconds": uptime.total_seconds(),
                },
            }
            # Mettre en cache le résultat
            MonitoringService._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(
                f"Erreur lors de la collecte des métriques système: {e}", exc_info=True
            )
            return {
                "cpu": {
                    "percent": 0,
                    "count": 0,
                    "per_core": [],
                    "load_average": [0, 0, 0],
                },
                "memory": {
                    "total": 0,
                    "available": 0,
                    "percent": 0,
                    "used": 0,
                    "free": 0,
                    "cached": 0,
                    "buffers": 0,
                },
                "swap": {"total": 0, "used": 0, "free": 0, "percent": 0},
                "disk": {
                    "total": 0,
                    "used": 0,
                    "free": 0,
                    "percent": 0,
                    "read_bytes": 0,
                    "write_bytes": 0,
                    "read_count": 0,
                    "write_count": 0,
                },
                "network": {
                    "bytes_sent": 0,
                    "bytes_recv": 0,
                    "packets_sent": 0,
                    "packets_recv": 0,
                    "errin": 0,
                    "errout": 0,
                    "dropin": 0,
                    "dropout": 0,
                },
                "process": {"count": 0},
                "uptime": {
                    "boot_time": "",
                    "days": 0,
                    "hours": 0,
                    "minutes": 0,
                    "total_seconds": 0,
                },
            }

    @staticmethod
    def get_database_metrics() -> Dict[str, Any]:
        """Récupère les métriques de la base de données."""
        try:
            current_app.config.get("SQLALCHEMY_DATABASE_URI", "")

            metrics = {"size": 0, "tables": {}, "connections": 0, "total_rows": 0}

            # Taille de la base de données
            result = db.session.execute(
                text("SELECT pg_database_size(current_database())")
            )
            metrics["size"] = result.scalar() or 0

            # Liste des tables et comptage via SQLAlchemy inspect
            inspector = inspect(db.engine)
            table_names = inspector.get_table_names()

            import re

            _safe_table_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

            for table_name in table_names:
                if table_name == "alembic_version":
                    continue
                # Valider le nom de table (défense en profondeur contre l'injection SQL)
                if not _safe_table_re.match(table_name):
                    metrics["tables"][table_name] = 0
                    continue
                try:
                    result = db.session.execute(
                        # table_name validé par _safe_table_re ci-dessus
                        text('SELECT COUNT(*) FROM "' + table_name + '"')  # nosec B608
                    )
                    count = result.scalar() or 0
                    metrics["tables"][table_name] = count
                    metrics["total_rows"] += count
                except Exception:
                    metrics["tables"][table_name] = 0

            # Nombre d'index
            index_count = 0
            for table_name in table_names:
                index_count += len(inspector.get_indexes(table_name))
            metrics["index_count"] = index_count

            # Métriques SQLAlchemy pool
            pool = db.engine.pool
            metrics["pool"] = {
                "size": pool.size() if hasattr(pool, "size") else 0,
                "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else 0,
                "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else 0,
                "overflow": pool.overflow() if hasattr(pool, "overflow") else 0,
                "total": pool.total() if hasattr(pool, "total") else 0,
            }

            return metrics

        except Exception as e:
            logger.error(
                f"Erreur lors de la collecte des métriques de base de données: {e}"
            )
            return {}

    @staticmethod
    def get_active_sessions() -> Dict[str, Any]:
        """Récupère les informations sur les sessions utilisateurs actives."""
        try:
            # Utilisateurs actifs (connectés dans les 30 dernières minutes)
            thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)

            active_users = User.query.filter(
                User.last_login_at > thirty_minutes_ago
            ).all()

            # Compter les sessions par statut
            total_users = User.query.count()
            active_count = len(active_users)

            # Détails des sessions actives
            sessions = []
            for user in active_users:
                sessions.append(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "last_activity": (
                            user.last_login_at.isoformat()
                            if user.last_login_at
                            else None
                        ),
                        "last_ip": getattr(user, "last_login_ip", None),
                        "session_duration": (
                            (
                                datetime.now(timezone.utc)
                                - user.last_login_at.replace(tzinfo=timezone.utc)
                            ).total_seconds()
                            if user.last_login_at
                            else 0
                        ),
                    }
                )

            return {
                "total_users": total_users,
                "active_users": active_count,
                "inactive_users": total_users - active_count,
                "sessions": sessions,
                "percentage_active": (
                    (active_count / total_users * 100) if total_users > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"Erreur lors de la collecte des sessions actives: {e}")
            return {
                "total_users": 0,
                "active_users": 0,
                "inactive_users": 0,
                "sessions": [],
                "percentage_active": 0,
            }

    @staticmethod
    def get_application_logs(
        limit: int = 100, level: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Récupère les logs de l'application."""
        try:
            log_file = os.path.join(current_app.root_path, "..", "logs", "app.log")
            logs = []

            if os.path.exists(log_file):
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()[-limit:]  # Dernières N lignes

                    for line in lines:
                        # Format typique: 2025-09-11 10:36:25 [INFO] Message [in file.py:123]
                        parts = line.strip().split(" ", 3)
                        if len(parts) >= 4:
                            log_level = parts[2].strip("[]")
                            log_entry = {
                                "timestamp": f"{parts[0]} {parts[1]}",
                                "level": log_level,
                                "message": parts[3],
                            }

                            # Filtrage précis par niveau si spécifié
                            if level:
                                level_upper = level.upper()
                                if level_upper == "ERROR" and log_level not in [
                                    "ERROR",
                                    "CRITICAL",
                                ]:
                                    continue
                                elif level_upper == "WARNING" and log_level not in [
                                    "WARNING",
                                    "ERROR",
                                    "CRITICAL",
                                ]:
                                    continue
                                elif level_upper == "INFO" and log_level not in [
                                    "INFO",
                                    "WARNING",
                                    "ERROR",
                                    "CRITICAL",
                                ]:
                                    continue
                                elif level_upper == "DEBUG":  # DEBUG affiche tout
                                    pass
                                elif (
                                    level_upper not in log_level
                                ):  # Pour autres niveaux spécifiques
                                    continue

                            logs.append(log_entry)

            return logs

        except Exception as e:
            logger.error(f"Erreur lors de la lecture des logs: {e}")
            return []

    @staticmethod
    def get_api_metrics() -> Dict[str, Any]:
        """Récupère les métriques des API (nécessite un middleware de tracking)."""
        try:
            # Ces métriques nécessiteraient un middleware de tracking
            # Pour l'instant, on retourne des métriques simulées
            datetime.now(timezone.utc)

            return {
                "requests_per_minute": 0,
                "requests_per_hour": 0,
                "average_response_time": 0,
                "endpoints": [],
                "status_codes": {"2xx": 0, "3xx": 0, "4xx": 0, "5xx": 0},
                "slow_queries": [],
            }

        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques API: {e}")
            return {}

    @staticmethod
    def get_alerts() -> List[Dict[str, Any]]:
        """Génère les alertes basées sur les seuils définis."""
        alerts = []

        try:
            metrics = MonitoringService.get_system_metrics()

            # Alerte CPU
            if metrics.get("cpu", {}).get("percent", 0) > 80:
                alerts.append(
                    {
                        "type": "critical",
                        "category": "cpu",
                        "message": f"Utilisation CPU élevée: {metrics['cpu']['percent']}%",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "value": metrics["cpu"]["percent"],
                    }
                )

            # Alerte Mémoire
            if metrics.get("memory", {}).get("percent", 0) > 90:
                alerts.append(
                    {
                        "type": "critical",
                        "category": "memory",
                        "message": f"Utilisation mémoire élevée: {metrics['memory']['percent']}%",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "value": metrics["memory"]["percent"],
                    }
                )

            # Alerte Disque
            if metrics.get("disk", {}).get("percent", 0) > 85:
                alerts.append(
                    {
                        "type": "warning",
                        "category": "disk",
                        "message": f"Espace disque faible: {100 - metrics['disk']['percent']:.1f}% restant",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "value": metrics["disk"]["percent"],
                    }
                )

            # Alerte Swap
            if metrics.get("swap", {}).get("percent", 0) > 50:
                alerts.append(
                    {
                        "type": "warning",
                        "category": "swap",
                        "message": f"Utilisation swap élevée: {metrics['swap']['percent']}%",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "value": metrics["swap"]["percent"],
                    }
                )

        except Exception as e:
            logger.error(f"Erreur lors de la génération des alertes: {e}")

        return alerts

    @staticmethod
    def get_dashboard_summary() -> Dict[str, Any]:
        """Récupère un résumé pour le dashboard admin."""
        try:
            system = MonitoringService.get_system_metrics()
            database = MonitoringService.get_database_metrics()
            sessions = MonitoringService.get_active_sessions()
            alerts = MonitoringService.get_alerts()

            # État de santé global
            health_status = "healthy"
            if any(a["type"] == "critical" for a in alerts):
                health_status = "critical"
            elif any(a["type"] == "warning" for a in alerts):
                health_status = "warning"

            return {
                "health_status": health_status,
                "system_overview": {
                    "cpu_percent": system.get("cpu", {}).get("percent", 0),
                    "memory_percent": system.get("memory", {}).get("percent", 0),
                    "disk_percent": system.get("disk", {}).get("percent", 0),
                    "uptime_days": system.get("uptime", {}).get("days", 0),
                },
                "users": {
                    "active": sessions.get("active_users", 0),
                    "total": sessions.get("total_users", 0),
                },
                "database": {
                    "size_mb": database.get("size", 0) / (1024 * 1024),
                    "total_rows": database.get("total_rows", 0),
                },
                "alerts": {
                    "count": len(alerts),
                    "critical": len([a for a in alerts if a["type"] == "critical"]),
                    "warning": len([a for a in alerts if a["type"] == "warning"]),
                },
                "recent_alerts": alerts[:5],
            }

        except Exception as e:
            logger.error(f"Erreur lors de la génération du résumé dashboard: {e}")
            return {}
