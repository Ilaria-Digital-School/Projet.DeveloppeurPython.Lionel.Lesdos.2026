"""
Module de gestion des rapports.

Ce module fournit les routes pour la génération, la visualisation
et l'exportation de rapports financiers.
"""

from flask import Blueprint

reports_bp = Blueprint("reports", __name__, template_folder="templates")

from . import report_routes
