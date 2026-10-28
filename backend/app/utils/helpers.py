"""
Fonctions utilitaires pour l'application.

Ce module contient des fonctions utilitaires réutilisables
dans toute l'application.
"""

import os
import uuid
from datetime import datetime

from flask import current_app
from werkzeug.utils import secure_filename

CURRENCY_SYMBOLS = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF"}


def allowed_file(filename, allowed_extensions=None):
    """Vérifie si l'extension du fichier est autorisée.

    Args:
        filename (str): Le nom du fichier à vérifier
        allowed_extensions (set, optional): Ensemble des extensions autorisées.
                                          Par défaut : {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

    Returns:
        bool: True si l'extension est autorisée, False sinon
    """
    if allowed_extensions is None:
        allowed_extensions = {"png", "jpg", "jpeg", "gif", "pdf"}

    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def save_uploaded_file(file, subfolder="", filename=None):
    """Sauvegarde un fichier téléchargé sur le serveur.

    Args:
        file (FileStorage): Le fichier à sauvegarder
        subfolder (str, optional): Sous-dossier de destination. Par défaut ''.
        filename (str, optional): Nom personnalisé pour le fichier. Si None, un nom unique est généré.

    Returns:
        str: Le chemin relatif du fichier sauvegardé, ou None en cas d'erreur
    """
    if not file or file.filename == "":
        return None

    # Sécuriser le nom du fichier
    if not filename:
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
    else:
        filename = secure_filename(filename)

    # Créer le dossier de destination si nécessaire
    upload_folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_folder, exist_ok=True)

    # Chemin complet du fichier
    filepath = os.path.join(upload_folder, filename)

    # Sauvegarder le fichier
    try:
        file.save(filepath)
        # Retourner le chemin relatif
        return (
            os.path.join("uploads", subfolder, filename)
            if subfolder
            else os.path.join("uploads", filename)
        )
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la sauvegarde du fichier: {str(e)}")
        return None


def format_date(value, format="%d/%m/%Y"):
    """Formate une date selon le format spécifié.

    Args:
        value (date/datetime/str): La date à formater
        format (str, optional): Le format de sortie. Par défaut '%d/%m/%Y'.

    Returns:
        str: La date formatée, ou une chaîne vide si la date est invalide
    """
    if not value:
        return ""

    if isinstance(value, str):
        try:
            # Essayer de parser la date si c'est une chaîne
            value = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return value

    try:
        return value.strftime(format)
    except AttributeError, ValueError:
        return str(value) if value else ""


def format_datetime(value, format="%d/%m/%Y %H:%M:%S"):
    """Formate une date et une heure selon le format spécifié.

    Args:
        value (datetime/str): La date et l'heure à formater
        format (str, optional): Le format de sortie. Par défaut '%d/%m/%Y %H:%M:%S'.

    Returns:
        str: La date et l'heure formatées, ou une chaîne vide si la valeur est invalide
    """
    if not value:
        return ""

    if isinstance(value, str):
        try:
            # Essayer de parser la date et l'heure si c'est une chaîne
            value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            try:
                value = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                return value

    try:
        return value.strftime(format)
    except AttributeError, ValueError:
        return str(value) if value else ""


def paginate(query, page, per_page=20):
    """Effectue une pagination sur une requête SQLAlchemy.

    Args:
        query: La requête SQLAlchemy à paginer
        page (int): Numéro de la page (commence à 1)
        per_page (int, optional): Nombre d'éléments par page. Par défaut 20.

    Returns:
        dict: Un dictionnaire contenant les éléments de la page, le numéro de page,
              le nombre total de pages et le nombre total d'éléments
    """
    if page < 1:
        page = 1

    items = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "items": items.items,
        "page": page,
        "per_page": per_page,
        "total_pages": items.pages,
        "total_items": items.total,
        "has_prev": items.has_prev,
        "has_next": items.has_next,
        "prev_num": items.prev_num,
        "next_num": items.next_num,
    }


def format_currency(amount, currency="EUR"):
    """Formate un montant en devise.

    Args:
        amount (float): Le montant à formater
        currency (str, optional): Le code de la devise. Par défaut 'EUR'.

    Returns:
        str: Le montant formaté avec le symbole de la devise
    """
    if amount is None:
        return "0,00 €"

    symbol = CURRENCY_SYMBOLS.get(currency, currency)

    # Formater le montant avec 2 décimales et le symbole de la devise
    return (
        f"{amount:,.2f} {symbol}".replace(",", " ")
        .replace(".", ",")
        .replace(" ", ".", 1)
    )


def get_enum_choices(enum_class):
    """Convertit une énumération en liste de choix pour les formulaires.

    Args:
        enum_class: La classe d'énumération à convertir

    Returns:
        list: Liste de tuples (valeur, libellé) pour les champs de formulaire
    """
    return [
        (member.value, member.name.replace("_", " ").title()) for member in enum_class
    ]


def validate_amount(amount):
    """Valide un montant (doit être un nombre positif).

    Args:
        amount: La valeur à valider

    Returns:
        bool: True si le montant est valide, False sinon
    """
    try:
        amount = float(amount)
        return amount >= 0
    except ValueError, TypeError:
        return False


def get_currency_symbol(currency_code):
    """Retourne le symbole d'une devise à partir de son code.

    Args:
        currency_code (str): Code ISO de la devise (ex: 'EUR', 'USD')

    Returns:
        str: Le symbole de la devise ou le code si non trouvé
    """
    return CURRENCY_SYMBOLS.get(currency_code, currency_code)


def calculate_percentage(part, total):
    """Calcule le pourcentage d'une partie par rapport à un total.

    Args:
        part: La valeur de la partie
        total: La valeur totale

    Returns:
        float: Le pourcentage arrondi à 2 décimales, ou 0 si le total est 0
    """
    if not total:
        return 0.0
    return round((part / total) * 100, 2)


def get_month_name(month_number):
    """Retourne le nom du mois à partir de son numéro.

    Args:
        month_number (int): Numéro du mois (1-12)

    Returns:
        str: Le nom du mois, ou chaîne vide si invalide
    """
    months = [
        "Janvier",
        "Février",
        "Mars",
        "Avril",
        "Mai",
        "Juin",
        "Juillet",
        "Août",
        "Septembre",
        "Octobre",
        "Novembre",
        "Décembre",
    ]

    try:
        return months[month_number - 1] if 1 <= month_number <= 12 else ""
    except TypeError, IndexError:
        return ""


def get_weekday_name(weekday_number):
    """Retourne le nom du jour de la semaine à partir de son numéro.

    Args:
        weekday_number (int): Numéro du jour (0-6, 0=lundi)

    Returns:
        str: Le nom du jour, ou chaîne vide si invalide
    """
    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

    try:
        return days[weekday_number] if 0 <= weekday_number <= 6 else ""
    except TypeError, IndexError:
        return ""


def parse_date(date_str, format="%Y-%m-%d"):
    """Convertit une chaîne de caractères en objet date.

    Args:
        date_str (str): La chaîne de date à parser
        format (str, optional): Le format de la date. Par défaut '%Y-%m-%d'.

    Returns:
        date: L'objet date correspondant, ou None en cas d'erreur
    """
    try:
        return datetime.strptime(date_str, format).date()
    except ValueError, TypeError:
        return None


def get_current_financial_year():
    """Retourne l'année fiscale en cours.

    Returns:
        int: L'année fiscale en cours
    """
    today = datetime.now()
    return today.year if today.month >= 4 else today.year - 1


def get_financial_year_range(year=None):
    """Retourne la plage de dates de l'année fiscale.

    Args:
        year (int, optional): L'année fiscale. Si None, utilise l'année en cours.

    Returns:
        tuple: (date_debut, date_fin) de l'année fiscale
    """
    if year is None:
        year = get_current_financial_year()

    start_date = datetime(year, 4, 1).date()
    end_date = datetime(year + 1, 3, 31).date()

    return start_date, end_date
