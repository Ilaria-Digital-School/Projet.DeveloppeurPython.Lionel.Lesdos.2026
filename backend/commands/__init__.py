"""
Commandes CLI pour l'application.
"""

import click
from flask import current_app
from flask.cli import with_appcontext
from redis import Redis
from rq.worker import Worker


def init_commands(app):
    """Initialise les commandes CLI"""

    @app.cli.group()
    def worker():
        """Commandes pour gérer les workers"""

    @worker.command()
    @with_appcontext
    def start():
        """Démarre un worker RQ"""
        redis_conn = Redis.from_url(current_app.config["REDIS_URL"])
        worker = Worker([current_app.config["QUEUE_NAME"]], connection=redis_conn)
        worker.work()

    @app.cli.group()
    def notifications():
        """Commandes pour gérer les notifications"""

    @notifications.command()
    @with_appcontext
    def retry_failed():
        """Relance les notifications en échec"""
        from core.models.notification import Notification
        from core.services.notifications import NotificationService

        failed_notifications = Notification.query.filter_by(status="failed").all()

        click.echo(f"Relance de {len(failed_notifications)} notifications échouées...")

        for notification in failed_notifications:
            try:
                NotificationService.retry_notification(notification.id)
                click.echo(f"Notification {notification.id} relancée avec succès")
            except Exception as e:
                click.echo(
                    f"Erreur lors de la relance de la notification {notification.id}: {str(e)}"
                )

    # Ajoutez d'autres commandes ici au besoin
