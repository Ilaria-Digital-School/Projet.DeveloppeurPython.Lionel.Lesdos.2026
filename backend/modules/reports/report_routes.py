"""
Routes web pour le module de rapports.

Ce module ne contient que la route HTML.
Les routes API JSON sont dans backend/api/v1/reports.py.
"""

import logging

from flask import render_template
from flask_login import login_required

from . import reports_bp

logger = logging.getLogger(__name__)


@reports_bp.route("/")
@login_required
def reports_page():
    """Page principale des rapports"""
    return render_template("reports.html")
